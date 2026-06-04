"""Local trigger harness — the agent decides when to speak (chunk 7).

The loop that the chunk 9 frontend will reimplement around a websocket:
  poll Firestore → score with shared.scorer → fire the agent on triggers →
  print radio calls. End-of-lap summaries are scheduled on lap change;
  event reactions fire when a scored candidate clears threshold + debounce.

Per the locked session decision, every proactive call runs in a FRESH agent
session. The triggering snapshot (state + events) rides in the prompt, so
the agent doesn't re-fetch a world that has moved on (intra-turn drift at
5x replay) and proactive calls stay within a small tool budget.

Usage (simulator running, mid-replay or restarted):
    python scripts/local_test.py                       # defaults below
    python scripts/local_test.py --duration 150        # ~laps 1-11 at 5x
    python scripts/local_test.py --threshold 70 --debounce 20 --verbose

Notes:
  - Debounce is WALL-clock seconds: at 5x replay, race-time debounce would
    let calls overlap agent latency. Tune --debounce per replay speed.
  - Triggers are processed one at a time (an engineer has one mouth). If
    the race outruns us, lower-priority moments are dropped, not queued —
    verbose mode shows what was suppressed and why.
"""
from __future__ import annotations

from shared.script_env import require_venv
require_venv()

import argparse
import asyncio
import json
import time
import uuid

from google.adk.runners import InMemoryRunner
from google.genai import types

from agent.race_engineer.agent import root_agent
from agent.race_engineer.config import OUR_CAR_NUMBER, race_time_to_wall_ns
from agent.race_engineer.prompts import (
    build_event_reaction_prompt,
    build_lap_summary_prompt,
)
from agent.race_engineer.tools.state_client import get_state_client
from shared.models import EventType, RaceState
from shared.scorer import DEFAULT_THRESHOLD, TriggerType, score

APP_NAME = "race_engineer_local_test"
USER_ID = "harness"
AM_LOOKBACK_S = 30  # race-seconds window feeding the cluster rule


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


FAIL_COOLDOWN_S = 5  # after a failed call, wait this long before trying again


async def fire(runner: InMemoryRunner, prompt: str, verbose: bool) -> tuple[str, int, float]:
    """Run one proactive call in a fresh session. Returns (text, tool_calls, secs).

    May raise (e.g. 429 RESOURCE_EXHAUSTED after the model's own retries are
    spent). Callers use safe_fire, which drops the call and keeps the loop
    alive — a late radio call is worse than a missed one.
    """
    session_id = f"trigger-{uuid.uuid4().hex[:8]}"
    await runner.session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session_id
    )
    msg = types.Content(role="user", parts=[types.Part(text=prompt)])
    t0 = time.monotonic()
    tool_calls = 0
    final: list[str] = []
    async for event in runner.run_async(
        user_id=USER_ID, session_id=session_id, new_message=msg
    ):
        calls = event.get_function_calls()
        tool_calls += len(calls)
        if verbose:
            for c in calls:
                print(f"      ▶ {c.name}({json.dumps(dict(c.args or {}), default=str)[:160]})")
        if event.is_final_response() and event.content and event.content.parts:
            for part in event.content.parts:
                if getattr(part, "text", None):
                    final.append(part.text)
    return "".join(final).strip(), tool_calls, time.monotonic() - t0


async def safe_fire(runner, prompt, verbose) -> tuple[str, int, float] | None:
    """fire(), but a failure drops the call instead of killing the harness."""
    try:
        return await fire(runner, prompt, verbose)
    except Exception as e:
        msg = str(e).splitlines()[0][:160]
        print(f"  ✗ call dropped: {type(e).__name__}: {msg}")
        return None


async def amain(args: argparse.Namespace) -> None:
    runner = InMemoryRunner(agent=root_agent, app_name=APP_NAME)
    client = get_state_client()

    last_scored_to: int | None = None     # race_time_s high-water mark
    last_fire_wall: float = -1e9          # wall-clock debounce anchor
    prev_position: int | None = None
    last_lap: int | None = None
    fired = suppressed = failed = 0

    print(f"Local trigger harness — threshold={args.threshold}, "
          f"debounce={args.debounce}s wall, duration={args.duration}s")
    print("Polling for triggers...\n")

    t_start = time.monotonic()
    while time.monotonic() - t_start < args.duration:
        state = client.get_race_state(fresh=True)
        if state is None:
            print("  (no RaceState yet — is the simulator running?)")
            await asyncio.sleep(args.poll)
            continue

        our = state.car_by_number(OUR_CAR_NUMBER)
        now_s = state.race_time_s

        # --- gather new events since last check ---
        from_s = (last_scored_to + 1) if last_scored_to is not None else max(0, now_s - args.poll * 10)
        new_events = client.query_events(
            from_race_time_s=from_s, to_race_time_s=now_s, limit=100,
        ) if now_s >= from_s else []
        am_recent = client.query_events(
            from_race_time_s=max(0, now_s - AM_LOOKBACK_S), to_race_time_s=now_s,
            event_types=[EventType.ATTACK_MODE_ACTIVATED], limit=50,
        )

        candidates = score(
            state, new_events,
            our_car=OUR_CAR_NUMBER,
            recent_am_activations=len(am_recent),
            prev_our_position=prev_position,
        )
        last_scored_to = now_s
        prev_position = our.position if our else prev_position

        # --- lap-change scheduling (not scored) ---
        lap_now = our.current_lap if our else None
        lap_changed = (
            last_lap is not None and lap_now is not None
            and lap_now > last_lap
            and last_lap >= 1  # lap 0 -> 1 is the green flag, not a completed lap
        )
        completed_lap = last_lap if lap_changed else None
        last_lap = lap_now if lap_now is not None else last_lap

        # --- pick what to say ---
        wall_since_fire = time.monotonic() - last_fire_wall
        best = candidates[0] if candidates else None

        if best and best.score >= args.threshold and wall_since_fire >= args.debounce:
            snap = snapshot_dict(state)
            prompt = build_event_reaction_prompt(
                reason=best.reason,
                snapshot_json=json.dumps(snap),
                events_json=json.dumps(best.events),
            )
            print(f"[t={now_s} lap {lap_now}] TRIGGER {best.trigger_type.value} "
                  f"score={best.score} — {best.reason}")
            result = await safe_fire(runner, prompt, args.verbose)
            if result:
                text, calls, secs = result
                print(f"  ENGINEER: {text}")
                print(f"  ({secs:.1f}s, {calls} tool calls)\n")
                last_fire_wall = time.monotonic()
                fired += 1
            else:
                failed += 1
                last_fire_wall = time.monotonic() - args.debounce + FAIL_COOLDOWN_S
        elif lap_changed and wall_since_fire >= args.debounce:
            snap = snapshot_dict(state)
            prompt = build_lap_summary_prompt(
                lap_number=completed_lap, snapshot_json=json.dumps(snap),
            )
            print(f"[t={now_s} lap {lap_now}] TRIGGER lap_summary — end of lap {completed_lap}")
            result = await safe_fire(runner, prompt, args.verbose)
            if result:
                text, calls, secs = result
                print(f"  ENGINEER: {text}")
                print(f"  ({secs:.1f}s, {calls} tool calls)\n")
                last_fire_wall = time.monotonic()
                fired += 1
            else:
                failed += 1
                last_fire_wall = time.monotonic() - args.debounce + FAIL_COOLDOWN_S
        else:
            if best and best.score >= args.threshold:
                suppressed += 1
                if args.verbose:
                    print(f"[t={now_s}] suppressed (debounce {wall_since_fire:.0f}s "
                          f"< {args.debounce}s): score={best.score} {best.reason}")
            elif args.verbose and best:
                print(f"[t={now_s}] below threshold: score={best.score} {best.reason}")

        await asyncio.sleep(args.poll)

    print(f"\nDone. Fired {fired} calls, suppressed {suppressed} by debounce, "
          f"dropped {failed} on errors.")
    await runner.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration", type=int, default=150,
                        help="run for this many wall seconds (150 ≈ laps 1-11 at 5x)")
    parser.add_argument("--poll", type=int, default=2, help="poll interval, wall seconds")
    parser.add_argument("--threshold", type=int, default=DEFAULT_THRESHOLD)
    parser.add_argument("--debounce", type=int, default=15,
                        help="min wall seconds between calls")
    parser.add_argument("--verbose", action="store_true",
                        help="show suppressed/below-threshold candidates and tool calls")
    args = parser.parse_args()
    asyncio.run(amain(args))


if __name__ == "__main__":
    main()