"""Frame-state tools the race engineer agent calls during reasoning.

============================== YOUR TIER A SURFACE ==============================
ONE tool below is COMPLETE — get_current_state, the worked example. Read it
top to bottom before writing anything: it shows every ADK mechanic you need.
THREE tools are yours to build (look for TODO(A)):

    get_recent_events     "what just happened?"
    get_events_in_range   "what happened on lap N?"
    get_field_am_status   "who has attack mode left?"

The response models and helpers further down are GIVEN — you never write
Pydantic under time pressure. Validate your work with:
    python scripts/test_frame_tools.py
(seed mode against scripts/seed_test_state.py, or --live against the replay)
=============================================================================

HOW ADK FUNCTION TOOLS WORK (the lessons baked into the worked example):

  1. THE DOCSTRING IS THE TOOL DESCRIPTION. Gemini reads it to decide when
     to call your tool and what to pass. Write it for the model: what the
     tool answers, what each arg means, valid values.
  2. Type hints define the schema. Return Pydantic models — ADK serializes
     them for Gemini.
  3. ADK does NOT coerce JSON args into Python enums: enum-ish parameters
     arrive as list[str]. Take list[str] and coerce internally
     (_coerce_event_types below) with a clear error listing valid values.
  4. NEVER return raw Event objects — wrap with AgentEvent.from_event().
     Read AgentEvent's docstring for why: events carry the REPLAY machine's
     wall clock, and the model was observed grabbing it as through_time_ns
     for the 2024-clocked BigQuery tools — a whole-race future leak. Hide
     plumbing fields the model can misuse; prompt rules alone were not enough.
  5. Time bridging: get_current_state and get_field_am_status include
     race_wall_time_ns — the current moment in the ORIGINAL 2024 race's wall
     clock. The agent passes it as through_time_ns to the BigQuery tools to
     mean "history up to now."
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from starter.race_engineer.config import (
    AM_SCENARIOS,
    AM_TOTAL_BUDGET_S,
    OUR_CAR_NUMBER,
    race_time_to_wall_ns,
)
from starter.race_engineer.tools.state_client import get_state_client
from shared.models import CarState, Event, EventType, RaceState


# ============================================================================
# Tool response models — GIVEN, don't edit
# ============================================================================


class CarSummary(BaseModel):
    """Compact summary of another car — for "nearest ahead/behind" references."""
    car_number: int
    driver_short_name: str
    position: int


class CurrentStateResponse(BaseModel):
    """Snapshot of our driver's race situation right now."""
    our_car_number: int
    our_driver: str
    position: int
    current_lap: int
    energy_pct_remaining: float
    energy_pct_used: float
    speed_kmh: float
    am_active: bool
    am_scenario: int
    am_scenario_name: str
    am_activations_used: int
    am_remaining_budget_s: float
    car_ahead: Optional[CarSummary] = None
    car_behind: Optional[CarSummary] = None
    race_phase: str
    race_time_s: int
    race_wall_time_ns: int = Field(
        description="Current moment in the original 2024 race's wall clock "
                    "(ns since epoch). Pass as through_time_ns to BigQuery "
                    "tools to mean 'history up to now'."
    )
    current_leader_lap: int
    is_retired: bool


class AgentEvent(BaseModel):
    """Agent-facing view of an Event — reasoning-relevant fields only.

    Deliberately excludes ts_ns_wall (the REPLAY machine's wall clock) and
    race_id. ts_ns_wall was observed luring the model into passing a 2026
    timestamp as through_time_ns to the 2024-clocked BigQuery tools, which
    silently returns the whole race (a future leak). Events expose
    race_time_s only; the sole valid through_time_ns source remains
    race_wall_time_ns from get_current_state / get_field_am_status.
    """
    event_type: EventType
    race_time_s: int
    car_number: Optional[int] = None
    data: dict = Field(default_factory=dict)

    @classmethod
    def from_event(cls, e: Event) -> "AgentEvent":
        return cls(
            event_type=e.event_type,
            race_time_s=e.race_time_s,
            car_number=e.car_number,
            data=e.data,
        )


class RecentEventsResponse(BaseModel):
    """List of events matching a query, newest first."""
    events: list[AgentEvent]
    count: int
    filters_applied: dict = Field(default_factory=dict)


class AmCarStatus(BaseModel):
    """One car's AM situation in the field-wide summary."""
    car_number: int
    driver_short_name: str
    position: int
    active_now: bool
    activations_used: int
    scenario: int
    remaining_budget_s: float


class FieldAmStatusResponse(BaseModel):
    """Field-wide Attack Mode snapshot for strategic reasoning."""
    active_now: list[AmCarStatus]              # cars currently in AM
    used_at_least_one: list[AmCarStatus]       # used >=1 activation
    untouched: list[AmCarStatus]               # zero activations yet
    scenario_distribution: dict[int, int]      # scenario -> car count
    race_phase: str
    race_time_s: int
    race_wall_time_ns: int = Field(
        description="Current moment in the original 2024 race's wall clock "
                    "(ns since epoch). Pass as through_time_ns to BigQuery "
                    "tools to mean 'history up to now'."
    )


# ============================================================================
# THE WORKED EXAMPLE — complete; read before writing your tools
# ============================================================================


def get_current_state() -> CurrentStateResponse:
    """Get our driver's situational picture right now.

    Returns position, lap, energy, AM state, nearest cars ahead and behind,
    and overall race phase. Use this as the first call when reasoning about
    "what's happening right now."

    Source: Firestore race_states doc, cached 1s.
    """
    # 1) Fetch the current RaceState. _require_state raises a clear error if
    #    Firestore is empty (simulator not running) — better than a None
    #    propagating into the model as a confusing tool failure.
    state = _require_state()
    our = _require_our_car(state)

    # 2) Sort the running field by position so neighbor lookup is trivial.
    #    Retired cars keep stale positions — exclude them.
    cars_sorted = sorted(
        (c for c in state.cars if not c.is_retired),
        key=lambda c: c.position,
    )

    car_ahead = _find_neighbor(cars_sorted, our.position, offset=-1)
    car_behind = _find_neighbor(cars_sorted, our.position, offset=+1)

    # 3) Build the response model. Round floats for the radio (the model
    #    echoes what it sees — feed it broadcast-ready numbers), and include
    #    race_wall_time_ns: the bridge value the agent passes to BigQuery
    #    tools as through_time_ns to mean "history up to now."
    return CurrentStateResponse(
        our_car_number=our.car_number,
        our_driver=our.driver_short_name,
        position=our.position,
        current_lap=our.current_lap,
        energy_pct_remaining=round(our.energy.pct_remaining, 2),
        energy_pct_used=round(our.energy.pct_used, 2),
        speed_kmh=round(our.speed_kmh, 1),
        am_active=our.attack_mode.active,
        am_scenario=our.attack_mode.scenario,
        am_scenario_name=AM_SCENARIOS.get(our.attack_mode.scenario, "unknown"),
        am_activations_used=our.attack_mode.activations_used,
        am_remaining_budget_s=round(our.attack_mode.remaining_budget_s, 1),
        car_ahead=_summarize(car_ahead),
        car_behind=_summarize(car_behind),
        race_phase=state.race_phase.value,
        race_time_s=state.race_time_s,
        race_wall_time_ns=race_time_to_wall_ns(state.race_time_s),
        current_leader_lap=state.current_leader_lap,
        is_retired=our.is_retired,
    )


# ============================================================================
# TODO(A) — your three tools
# ============================================================================


def get_recent_events(
    seconds_back: int = 30,
    event_types: Optional[list[str]] = None,
    car_involved: Optional[int] = None,
    limit: int = 50,
) -> RecentEventsResponse:
    """Events within the last N seconds of race time.

    Optionally filter by event type(s) and/or by a car involved. Returns
    newest first. Use this for "what just happened?" reasoning.

    Args:
      seconds_back: Look back this many seconds from the current race_time_s.
      event_types: Only events of these types. Valid values: "race_control",
        "overtake", "attack_mode_activated", "attack_mode_deactivated",
        "lap_completed".
      car_involved: Only events with car_number = this value.
      limit: Cap on number of events returned (default 50).
    """
    # ------------------------------------------------------------------
    # TODO(A): implement. Spec:
    #   1. types = _coerce_event_types(event_types)   (Gemini sends strings)
    #   2. state = _require_state(); the window is
    #        from = max(0, state.race_time_s - seconds_back)
    #        to   = state.race_time_s
    #   3. events = get_state_client().query_events(
    #        from_race_time_s=..., to_race_time_s=..., event_types=types,
    #        car_involved=car_involved, limit=limit)
    #   4. Wrap EVERY event: [AgentEvent.from_event(e) for e in events]
    #      (never return raw Events — see the AgentEvent docstring)
    #   5. Return RecentEventsResponse(events=..., count=len(...),
    #        filters_applied={...the window + filters you applied, with
    #        event types as their string values...})
    # The worked example above shows the fetch pattern; the reference lives
    # at solution/race_engineer/tools/frame_tools.py if you're stuck.
    # ------------------------------------------------------------------
    raise NotImplementedError(
        "TODO(A): get_recent_events — spec in the comments above this line"
    )


def get_events_in_range(
    from_race_time_s: int,
    to_race_time_s: int,
    event_types: Optional[list[str]] = None,
    car_involved: Optional[int] = None,
    limit: int = 100,
) -> RecentEventsResponse:
    """Events in a specific race-time window.

    Use for "what happened on lap N" or "everything since safety car."
    Same shape as get_recent_events but absolute window.

    Args:
      from_race_time_s: Window start (race-relative seconds, inclusive).
      to_race_time_s: Window end (race-relative seconds, inclusive).
      event_types: Only events of these types. Valid values: "race_control",
        "overtake", "attack_mode_activated", "attack_mode_deactivated",
        "lap_completed".
      car_involved: Only events with car_number = this value.
      limit: Cap on number of events returned (default 100).
    """
    # ------------------------------------------------------------------
    # TODO(A): implement. Same shape as get_recent_events, except the
    # window is the caller's absolute [from_race_time_s, to_race_time_s] —
    # no current-state fetch needed. Coerce types, query, wrap with
    # AgentEvent.from_event, return RecentEventsResponse with
    # filters_applied describing the window.
    # ------------------------------------------------------------------
    raise NotImplementedError(
        "TODO(A): get_events_in_range — spec in the comments above this line"
    )


def get_field_am_status() -> FieldAmStatusResponse:
    """Snapshot of Attack Mode activity across the whole field.

    Returns three buckets (active now / used at least one / untouched) and
    the scenario distribution. Use for "should I activate now?" reasoning —
    AM is most effective when the field around you is not also using it.
    """
    # ------------------------------------------------------------------
    # TODO(A): implement. Spec:
    #   1. state = _require_state()
    #   2. Walk state.cars, SKIPPING retired cars. For each, build an
    #      AmCarStatus (round remaining_budget_s to 1 decimal) and place it
    #      in exactly one bucket:
    #        attack_mode.active            -> active_now
    #        elif activations_used > 0     -> used_at_least_one
    #        else                          -> untouched
    #   3. Tally scenario_distribution: {scenario: car count} across the
    #      running field.
    #   4. Sort each bucket by position (readability for the model).
    #   5. Return FieldAmStatusResponse with race_phase (its .value),
    #      race_time_s, and race_wall_time_ns via race_time_to_wall_ns —
    #      this tool is one of the TWO valid through_time_ns sources.
    # ------------------------------------------------------------------
    raise NotImplementedError(
        "TODO(A): get_field_am_status — spec in the comments above this line"
    )


# ============================================================================
# Helpers — GIVEN, don't edit (use them in your tools)
# ============================================================================


def _coerce_event_types(
    event_types: Optional[list[str]],
) -> Optional[list[EventType]]:
    """Coerce string event types (as Gemini sends them) to EventType enums.

    ADK passes function args straight from JSON — enum coercion is on us.
    Accepts EventType instances too (our own tests pass them directly).
    """
    if not event_types:
        return None
    coerced: list[EventType] = []
    for t in event_types:
        if isinstance(t, EventType):
            coerced.append(t)
            continue
        try:
            coerced.append(EventType(t))
        except ValueError:
            valid = ", ".join(e.value for e in EventType)
            raise ValueError(
                f"Unknown event type {t!r}. Valid values: {valid}"
            )
    return coerced


def _require_state() -> RaceState:
    """Fetch RaceState, raise if it doesn't exist (e.g. before first frame)."""
    state = get_state_client().get_race_state()
    if state is None:
        raise RuntimeError(
            "No RaceState in Firestore yet. The simulator may not be running, "
            "or the State Writer hasn't received its first frame."
        )
    return state


def _require_our_car(state: RaceState) -> CarState:
    """Look up our driver's car. Raise if missing (shouldn't happen)."""
    car = state.car_by_number(OUR_CAR_NUMBER)
    if car is None:
        raise RuntimeError(
            f"Car {OUR_CAR_NUMBER} not in RaceState — frame schema mismatch?"
        )
    return car


def _find_neighbor(
    cars_sorted_by_pos: list[CarState], our_position: int, offset: int
) -> Optional[CarState]:
    """Find the car at our_position + offset, or None if at the edge."""
    target = our_position + offset
    for car in cars_sorted_by_pos:
        if car.position == target:
            return car
    return None


def _summarize(car: Optional[CarState]) -> Optional[CarSummary]:
    if car is None:
        return None
    return CarSummary(
        car_number=car.car_number,
        driver_short_name=car.driver_short_name,
        position=car.position,
    )
