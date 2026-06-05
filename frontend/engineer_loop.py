"""The engineer's trigger loop as a service component (chunk 9, Pass 2).

This is scripts/local_test.py's loop, re-homed: poll Firestore → score with
shared.scorer → fire the agent on triggers — except deliveries are broadcast
over the websocket as {type: "radio"} messages instead of printed. All the
chunk 8 policy survives intact: per-type debounce, the pending must-say hold
(fresh snapshot at delivery, TTL expiry), the overdue-summary guarantee, the
hard tool-budget ceiling, and drop-don't-crash on failures.

Pass 3 adds ask() — user Q&A through the same runner with a persistent
session, per the locked session-management decision.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Awaitable, Callable

from google.adk.agents.run_config import RunConfig
from google.adk.runners import InMemoryRunner
from google.genai import types

from agent.race_engineer.agent import root_agent
from agent.race_engineer.config import OUR_CAR_NUMBER
from agent.race_engineer.prompts import (
    build_event_reaction_prompt,
    build_lap_summary_prompt,
)
from agent.race_engineer.snapshot import snapshot_dict
from agent.race_engineer.tools.state_client import get_state_client
from shared.models import EventType
from shared.scorer import DEFAULT_THRESHOLD, score

logger = logging.getLogger("engineer")

APP_NAME = "race_engineer_frontend"
USER_ID = "pit_wall"
AM_LOOKBACK_S = 30
FAIL_COOLDOWN_S = 5
MUST_SAY_TTL_S = 25
MAX_LLM_CALLS_PER_TRIGGER = 4
MAX_LLM_CALLS_PER_QA = 12     # human-initiated: research allowed, runaway not
QA_SESSION_ID = "pit-wall-qa" # persistent — Q&A keeps conversational context

Broadcast = Callable[[dict], Awaitable[None]]


class EngineerLoop:
    """Background trigger loop. One instance per process."""

    def __init__(
        self,
        broadcast: Broadcast,
        *,
        threshold: int = DEFAULT_THRESHOLD,
        debounce_s: float = 15.0,
        must_say_gap_s: float = 5.0,
        summary_every: int = 2,
        poll_s: float = 2.0,
    ) -> None:
        self.broadcast = broadcast
        self.threshold = threshold
        self.debounce_s = debounce_s
        self.must_say_gap_s = must_say_gap_s
        self.summary_every = summary_every
        self.poll_s = poll_s
        self.runner = InMemoryRunner(agent=root_agent, app_name=APP_NAME)
        self.client = get_state_client()
        self._qa_session_ready = False

    # ------------------------------------------------------------------
    # Agent invocation
    # ------------------------------------------------------------------

    async def _fire(self, prompt: str) -> tuple[str, int, float]:
        session_id = f"trigger-{uuid.uuid4().hex[:8]}"
        await self.runner.session_service.create_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=session_id
        )
        msg = types.Content(role="user", parts=[types.Part(text=prompt)])
        t0 = time.monotonic()
        tool_calls = 0
        final: list[str] = []
        async for event in self.runner.run_async(
            user_id=USER_ID, session_id=session_id, new_message=msg,
            run_config=RunConfig(max_llm_calls=MAX_LLM_CALLS_PER_TRIGGER),
        ):
            tool_calls += len(event.get_function_calls())
            if event.is_final_response() and event.content and event.content.parts:
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        final.append(part.text)
        return "".join(final).strip(), tool_calls, time.monotonic() - t0

    async def _deliver(self, kind: str, prompt: str, now_s: int, lap, reason: str) -> bool:
        """Fire the agent; broadcast the call. False (and cooldown) on failure."""
        try:
            text, tools, secs = await self._fire(prompt)
        except Exception as e:
            logger.warning("call dropped (%s): %s", kind,
                           str(e).splitlines()[0][:160] if str(e) else type(e).__name__)
            return False
        logger.info("[t=%s lap %s] %s (%.1fs, %d tools): %s",
                    now_s, lap, kind, secs, tools, text)
        await self.broadcast({
            "type": "radio", "kind": kind,
            "race_time_s": now_s, "lap": lap,
            "reason": reason, "text": text,
            "secs": round(secs, 1), "tools": tools,
        })
        return True

    async def ask(self, question: str) -> str:
        """Pit-wall Q&A. Persistent session (follow-ups keep context); the
        agent fetches whatever it needs — triggers carry snapshots, questions
        don't. Raises on failure; the websocket layer reports it."""
        if not self._qa_session_ready:
            await self.runner.session_service.create_session(
                app_name=APP_NAME, user_id=USER_ID, session_id=QA_SESSION_ID
            )
            self._qa_session_ready = True
        msg = types.Content(role="user", parts=[types.Part(text=question)])
        final: list[str] = []
        async for event in self.runner.run_async(
            user_id=USER_ID, session_id=QA_SESSION_ID, new_message=msg,
            run_config=RunConfig(max_llm_calls=MAX_LLM_CALLS_PER_QA),
        ):
            if event.is_final_response() and event.content and event.content.parts:
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        final.append(part.text)
        return "".join(final).strip()

    # ------------------------------------------------------------------
    # The loop
    # ------------------------------------------------------------------

    async def run(self) -> None:
        last_scored_to: int | None = None
        last_fire_wall: float = -1e9
        prev_position: int | None = None
        last_lap: int | None = None
        last_summary_lap: int | None = None
        due_summary_lap: int | None = None  # sticky: an owed summary survives blocked polls
        pending_must_say = None  # (TriggerCandidate, race_time_s first seen)

        logger.info("engineer loop online — threshold=%s debounce=%ss "
                    "must-say gap=%ss summary every %s laps",
                    self.threshold, self.debounce_s, self.must_say_gap_s,
                    self.summary_every)

        while True:
            try:
                state = self.client.get_race_state(fresh=True)
            except Exception:
                logger.exception("state read failed")
                state = None
            if state is None:
                await asyncio.sleep(self.poll_s)
                continue

            our = state.car_by_number(OUR_CAR_NUMBER)
            now_s = state.race_time_s

            if last_scored_to is not None and now_s < last_scored_to - 5:
                # race time went backwards: replay restarted — flush loop state
                logger.info("replay restart detected (t=%s < %s) — resetting", now_s, last_scored_to)
                last_scored_to = None
                prev_position = None
                last_lap = None
                last_summary_lap = None
                due_summary_lap = None
                pending_must_say = None

            from_s = (last_scored_to + 1) if last_scored_to is not None \
                else max(0, now_s - int(self.poll_s) * 10)
            try:
                new_events = self.client.query_events(
                    from_race_time_s=from_s, to_race_time_s=now_s, limit=100,
                ) if now_s >= from_s else []
                am_recent = self.client.query_events(
                    from_race_time_s=max(0, now_s - AM_LOOKBACK_S),
                    to_race_time_s=now_s,
                    event_types=[EventType.ATTACK_MODE_ACTIVATED], limit=50,
                )
            except Exception:
                logger.exception("event read failed")
                await asyncio.sleep(self.poll_s)
                continue

            candidates = score(
                state, new_events,
                our_car=OUR_CAR_NUMBER,
                recent_am_activations=len(am_recent),
                prev_our_position=prev_position,
            )
            last_scored_to = now_s
            prev_position = our.position if our else prev_position

            lap_now = our.current_lap if our else None
            lap_changed = (
                last_lap is not None and lap_now is not None
                and lap_now > last_lap and last_lap >= 1
            )
            completed_lap = last_lap if lap_changed else None
            last_lap = lap_now if lap_now is not None else last_lap
            if lap_changed and (
                last_summary_lap is None
                or (completed_lap - last_summary_lap) >= self.summary_every
            ):
                due_summary_lap = completed_lap  # newer boundary overwrites older debt

            best = candidates[0] if candidates else None
            if best and best.must_say:
                if pending_must_say is None or best.score >= pending_must_say[0].score:
                    pending_must_say = (best, now_s)
            if pending_must_say and now_s - pending_must_say[1] > MUST_SAY_TTL_S:
                logger.info("expired must-say: %s", pending_must_say[0].reason)
                pending_must_say = None

            wall_gap = time.monotonic() - last_fire_wall
            fired = False
            attempted = False

            if pending_must_say and wall_gap >= self.must_say_gap_s:
                attempted = True
                cand, _ = pending_must_say
                snap = snapshot_dict(state)
                prompt = build_event_reaction_prompt(
                    reason=cand.reason,
                    snapshot_json=json.dumps(snap),
                    events_json=json.dumps(cand.events),
                )
                fired = await self._deliver("must_say", prompt, now_s, lap_now, cand.reason)
                if fired:
                    pending_must_say = None
            elif due_summary_lap is not None and wall_gap >= self.must_say_gap_s:
                attempted = True
                snap = snapshot_dict(state)
                prompt = build_lap_summary_prompt(
                    lap_number=due_summary_lap, snapshot_json=json.dumps(snap),
                )
                fired = await self._deliver("lap_summary", prompt, now_s, lap_now,
                                            f"end of lap {due_summary_lap}")
                if fired:
                    last_summary_lap = due_summary_lap
                    due_summary_lap = None
            elif best and best.score >= self.threshold and wall_gap >= self.debounce_s:
                attempted = True
                snap = snapshot_dict(state)
                prompt = build_event_reaction_prompt(
                    reason=best.reason,
                    snapshot_json=json.dumps(snap),
                    events_json=json.dumps(best.events),
                )
                fired = await self._deliver("event", prompt, now_s, lap_now, best.reason)
            elif lap_changed and wall_gap >= self.debounce_s:
                attempted = True
                snap = snapshot_dict(state)
                prompt = build_lap_summary_prompt(
                    lap_number=completed_lap, snapshot_json=json.dumps(snap),
                )
                fired = await self._deliver("lap_summary", prompt, now_s, lap_now,
                                            f"end of lap {completed_lap}")
                if fired:
                    last_summary_lap = completed_lap

            if fired:
                last_fire_wall = time.monotonic()
            elif attempted:
                # delivery failed — cooldown before any retry, don't hammer
                last_fire_wall = time.monotonic() - self.debounce_s + FAIL_COOLDOWN_S

            await asyncio.sleep(self.poll_s)

    async def close(self) -> None:
        await self.runner.close()