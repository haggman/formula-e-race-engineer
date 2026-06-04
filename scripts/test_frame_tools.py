"""Validate the agent's frame tools against Firestore.

Run AFTER seeding test state:
    python scripts/seed_test_state.py
    python scripts/test_frame_tools.py

Calls each of the four frame tools with realistic args and prints the result.
Verifies that DAC is at P2 (per the seeded sample), MOR is in AM, etc.
"""
from __future__ import annotations

from shared.script_env import require_venv
require_venv()

import sys

# We import via the agent package so the path mirrors how ADK will call.
from agent.race_engineer.tools.frame_tools import (
    get_current_state,
    get_events_in_range,
    get_field_am_status,
    get_recent_events,
)
from shared.models import EventType


def header(label: str) -> None:
    print(f"\n── {label} ──")


def main():
    fails = 0

    # ------------------------------------------------------------------
    header("get_current_state")
    try:
        resp = get_current_state()
        print(f"  Our car {resp.our_car_number} ({resp.our_driver}) — P{resp.position} on lap {resp.current_lap}")
        print(f"  Speed: {resp.speed_kmh} km/h, Energy: {resp.energy_pct_remaining}% remaining")
        print(f"  AM scenario {resp.am_scenario} ({resp.am_scenario_name}), "
              f"active={resp.am_active}, used={resp.am_activations_used}, "
              f"budget={resp.am_remaining_budget_s}s")
        print(f"  Ahead: {resp.car_ahead}")
        print(f"  Behind: {resp.car_behind}")
        print(f"  Race: {resp.race_phase} at t={resp.race_time_s}s, leader on lap {resp.current_leader_lap}")

        # Sanity checks
        assert resp.our_car_number == 13, "expected car 13"
        assert resp.our_driver == "DAC", "expected DAC"
        assert resp.position == 2, "expected P2 (sample frame)"
        assert resp.car_ahead and resp.car_ahead.driver_short_name == "CAS", "expected Cassidy ahead"
        assert resp.car_behind and resp.car_behind.driver_short_name == "ROW", "expected Rowland behind"
        assert resp.race_phase == "safety_car", "expected safety_car phase"
        print("  ✓ all sanity checks pass")
    except Exception as e:
        print(f"  ✗ FAILED: {type(e).__name__}: {e}")
        fails += 1

    # ------------------------------------------------------------------
    header("get_recent_events (last 60s, all types)")
    try:
        resp = get_recent_events(seconds_back=60)
        print(f"  Found {resp.count} events in last 60s")
        for ev in resp.events:
            print(f"    [{ev.event_type.value}] t={ev.race_time_s}s car={ev.car_number} data={ev.data}")
        # Sanity: we seeded 4 events at the current race_time, all should be in window
        assert resp.count >= 4, f"expected ≥4 events, got {resp.count}"
        print("  ✓ all sanity checks pass")
    except Exception as e:
        print(f"  ✗ FAILED: {type(e).__name__}: {e}")
        fails += 1

    # ------------------------------------------------------------------
    header("get_recent_events (only race_control)")
    try:
        resp = get_recent_events(
            seconds_back=120,
            event_types=[EventType.RACE_CONTROL],
        )
        print(f"  Found {resp.count} race_control events")
        for ev in resp.events:
            print(f"    {ev.data}")
        assert resp.count >= 1, "expected at least 1 race_control event"
        print("  ✓ filter works")
    except Exception as e:
        print(f"  ✗ FAILED: {type(e).__name__}: {e}")
        fails += 1

    # ------------------------------------------------------------------
    header("get_recent_events (involving car 48 / MOR)")
    try:
        resp = get_recent_events(
            seconds_back=120,
            car_involved=48,
        )
        print(f"  Found {resp.count} events involving car 48")
        for ev in resp.events:
            print(f"    [{ev.event_type.value}] data={ev.data}")
        assert resp.count >= 1, "expected at least 1 event involving car 48 (AM activation)"
        print("  ✓ car filter works")
    except Exception as e:
        print(f"  ✗ FAILED: {type(e).__name__}: {e}")
        fails += 1

    # ------------------------------------------------------------------
    header("get_events_in_range")
    try:
        resp = get_events_in_range(
            from_race_time_s=1400,
            to_race_time_s=1500,
            event_types=[EventType.LAP_COMPLETED],
        )
        print(f"  Found {resp.count} lap_completed events in range 1400-1500s")
        for ev in resp.events:
            print(f"    car {ev.car_number}: {ev.data}")
        assert resp.count >= 2, f"expected ≥2 lap completions, got {resp.count}"
        print("  ✓ range query works")
    except Exception as e:
        print(f"  ✗ FAILED: {type(e).__name__}: {e}")
        fails += 1

    # ------------------------------------------------------------------
    header("get_field_am_status")
    try:
        resp = get_field_am_status()
        print(f"  Active now: {len(resp.active_now)} car(s)")
        for s in resp.active_now:
            print(f"    P{s.position} #{s.car_number} ({s.driver_short_name}) "
                  f"scenario {s.scenario}, budget {s.remaining_budget_s}s")
        print(f"  Used at least one: {len(resp.used_at_least_one)} cars")
        print(f"  Untouched: {len(resp.untouched)} cars")
        print(f"  Scenario distribution: {resp.scenario_distribution}")

        # Sanity: car 48 (MOR) is actively in AM per the seeded sample
        assert any(s.car_number == 48 for s in resp.active_now), \
            "expected car 48 (MOR) in active_now"
        assert resp.scenario_distribution, "expected non-empty scenario distribution"
        print("  ✓ all sanity checks pass")
    except Exception as e:
        print(f"  ✗ FAILED: {type(e).__name__}: {e}")
        fails += 1

    # ------------------------------------------------------------------
    print("\n" + "=" * 60)
    if fails:
        print(f"  ✗ {fails} test(s) failed")
        sys.exit(1)
    else:
        print("  ✓ All frame tools working against Firestore")


if __name__ == "__main__":
    main()
