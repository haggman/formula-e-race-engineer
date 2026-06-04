"""Frame-state tools the race engineer agent calls during reasoning.

Distinct from MCP Toolbox tools (which hit BigQuery for historical data).
These tools read the live race state from Firestore — populated by the
State Writer service from Pub/Sub frames.

Tools:
  - get_current_state — our driver's situational picture right now
  - get_recent_events — events in the last N seconds, optionally filtered
  - get_events_in_range — events in a specific race-time window
  - get_field_am_status — AM activity across the field

All tools return Pydantic models that the ADK serializes for Gemini.

Time bridging: get_current_state and get_field_am_status include
race_wall_time_ns — the current moment expressed in the ORIGINAL 2024 race's
wall clock. Pass that value as `through_time_ns` to the BigQuery Toolbox
tools to mean "history up to now". (BQ timestamps are from May 2024; the
replay machine's clock is useless for this.)
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from agent.race_engineer.config import (
    AM_SCENARIOS,
    AM_TOTAL_BUDGET_S,
    OUR_CAR_NUMBER,
    race_time_to_wall_ns,
)
from agent.race_engineer.tools.state_client import get_state_client
from shared.models import CarState, Event, EventType, RaceState


# ============================================================================
# Tool response models
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


class RecentEventsResponse(BaseModel):
    """List of events matching a query, newest first."""
    events: list[Event]
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
# Tool implementations
# ============================================================================


def get_current_state() -> CurrentStateResponse:
    """Get our driver's situational picture right now.

    Returns position, lap, energy, AM state, nearest cars ahead and behind,
    and overall race phase. Use this as the first call when reasoning about
    "what's happening right now."

    Source: Firestore race_states doc, cached 1s.
    """
    state = _require_state()
    our = _require_our_car(state)

    cars_sorted = sorted(
        (c for c in state.cars if not c.is_retired),
        key=lambda c: c.position,
    )

    car_ahead = _find_neighbor(cars_sorted, our.position, offset=-1)
    car_behind = _find_neighbor(cars_sorted, our.position, offset=+1)

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


def get_recent_events(
    seconds_back: int = 30,
    event_types: Optional[list[EventType]] = None,
    car_involved: Optional[int] = None,
    limit: int = 50,
) -> RecentEventsResponse:
    """Events within the last N seconds of race time.

    Optionally filter by event type(s) and/or by a car involved. Returns
    newest first. Use this for "what just happened?" reasoning.

    Args:
      seconds_back: Look back this many seconds from the current race_time_s.
      event_types: Only events of these types (e.g. [OVERTAKE, RACE_CONTROL]).
      car_involved: Only events with car_number = this value.
      limit: Cap on number of events returned (default 50).
    """
    state = _require_state()
    to_race_time = state.race_time_s
    from_race_time = max(0, to_race_time - seconds_back)

    client = get_state_client()
    events = client.query_events(
        from_race_time_s=from_race_time,
        to_race_time_s=to_race_time,
        event_types=event_types,
        car_involved=car_involved,
        limit=limit,
    )

    return RecentEventsResponse(
        events=events,
        count=len(events),
        filters_applied={
            "from_race_time_s": from_race_time,
            "to_race_time_s": to_race_time,
            "event_types": [t.value for t in event_types] if event_types else None,
            "car_involved": car_involved,
            "limit": limit,
        },
    )


def get_events_in_range(
    from_race_time_s: int,
    to_race_time_s: int,
    event_types: Optional[list[EventType]] = None,
    car_involved: Optional[int] = None,
    limit: int = 100,
) -> RecentEventsResponse:
    """Events in a specific race-time window.

    Use for "what happened on lap N" or "everything since safety car."
    Same shape as get_recent_events but absolute window.
    """
    client = get_state_client()
    events = client.query_events(
        from_race_time_s=from_race_time_s,
        to_race_time_s=to_race_time_s,
        event_types=event_types,
        car_involved=car_involved,
        limit=limit,
    )
    return RecentEventsResponse(
        events=events,
        count=len(events),
        filters_applied={
            "from_race_time_s": from_race_time_s,
            "to_race_time_s": to_race_time_s,
            "event_types": [t.value for t in event_types] if event_types else None,
            "car_involved": car_involved,
            "limit": limit,
        },
    )


def get_field_am_status() -> FieldAmStatusResponse:
    """Snapshot of Attack Mode activity across the whole field.

    Returns three buckets (active now / used at least one / untouched) and
    the scenario distribution. Use for "should I activate now?" reasoning —
    AM is most effective when the field around you is not also using it.
    """
    state = _require_state()

    active_now: list[AmCarStatus] = []
    used: list[AmCarStatus] = []
    untouched: list[AmCarStatus] = []
    scenario_dist: dict[int, int] = {}

    for car in state.cars:
        if car.is_retired:
            continue
        status = AmCarStatus(
            car_number=car.car_number,
            driver_short_name=car.driver_short_name,
            position=car.position,
            active_now=car.attack_mode.active,
            activations_used=car.attack_mode.activations_used,
            scenario=car.attack_mode.scenario,
            remaining_budget_s=round(car.attack_mode.remaining_budget_s, 1),
        )
        if car.attack_mode.active:
            active_now.append(status)
        elif car.attack_mode.activations_used > 0:
            used.append(status)
        else:
            untouched.append(status)
        scenario_dist[car.attack_mode.scenario] = (
            scenario_dist.get(car.attack_mode.scenario, 0) + 1
        )

    # Sort by position for readability
    for bucket in (active_now, used, untouched):
        bucket.sort(key=lambda s: s.position)

    return FieldAmStatusResponse(
        active_now=active_now,
        used_at_least_one=used,
        untouched=untouched,
        scenario_distribution=scenario_dist,
        race_phase=state.race_phase.value,
        race_time_s=state.race_time_s,
        race_wall_time_ns=race_time_to_wall_ns(state.race_time_s),
    )


# ============================================================================
# Helpers
# ============================================================================


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