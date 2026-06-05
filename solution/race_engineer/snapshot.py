"""Trigger snapshot builder — the authoritative 'moment' handed to the agent
in proactive radio-call prompts. Used by scripts/local_test.py (dev harness)
and frontend (the service). Lives in the agent package because it depends on
agent config (car number, time bridge)."""
from __future__ import annotations

from solution.race_engineer.config import OUR_CAR_NUMBER, race_time_to_wall_ns
from shared.models import RaceState


def snapshot_dict(state: RaceState) -> dict:
    """Compact authoritative snapshot for the trigger prompt."""
    our = state.car_by_number(OUR_CAR_NUMBER)
    cars = sorted((c for c in state.cars if not c.is_retired),
                  key=lambda c: c.position)
    ahead = next((c for c in cars if our and c.position == our.position - 1), None)
    behind = next((c for c in cars if our and c.position == our.position + 1), None)

    def brief(c):
        return None if c is None else {
            "car": c.car_number, "driver": c.driver_short_name, "position": c.position,
            "am_active": c.attack_mode.active,
            "am_activations_used": c.attack_mode.activations_used,
        }

    return {
        "race_time_s": state.race_time_s,
        "race_wall_time_ns": race_time_to_wall_ns(state.race_time_s),
        "race_phase": state.race_phase.value,
        "our": None if our is None else {
            "position": our.position, "lap": our.current_lap,
            "energy_pct_remaining": round(our.energy.pct_remaining, 1),
            "am_active": our.attack_mode.active,
            "am_activations_used": our.attack_mode.activations_used,
            "am_remaining_budget_s": our.attack_mode.remaining_budget_s,
            "am_scenario": our.attack_mode.scenario,
        },
        "car_ahead": brief(ahead),
        "car_behind": brief(behind),
    }