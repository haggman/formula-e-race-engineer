"""Agent invocation seam (chunk 13) — one interface, two runtimes.

    AGENT_MODE=local   InMemoryRunner in-process. The permanent dev path:
                       edit prompts.py, restart uvicorn, seconds. Chunk 9-11
                       behavior preserved verbatim (RunConfig tool ceilings,
                       fresh session per trigger, persistent Q&A session).

    AGENT_MODE=engine  The deployed Vertex AI Agent Engine, via
                       vertexai.agent_engines + async_stream_query — the
                       async twin of what scripts/engine_smoke.py validated.
                       Requires AGENT_ENGINE_RESOURCE (activate.sh exports it
                       from deploy/.engine_resource when present).

The engineer loop and Q&A handler call fire()/ask() and never know which
runtime answered. Same agent, two runtimes, one interface.

Engine-mode design notes:
  - RunConfig(max_llm_calls) does NOT plumb through the engine's query
    interface, so the hard per-call tool ceiling is local-only. Engine mode
    substitutes WALL-CLOCK timeouts (FIRE_TIMEOUT_S / ASK_TIMEOUT_S): per
    chunk 8 policy a stale radio call is worse than a missed one, and the
    caller's drop-with-cooldown handling already owns the failure path.
  - The agent_engines SDK BLOCKS the event loop (even its async_* variants,
    observed live: jerky UI, stalled /api/stt). Engine calls therefore run
    as the sync SDK methods inside asyncio.to_thread — see
    EngineAgentClient's class docstring.
  - agent.race_engineer.agent is imported ONLY in local mode. Importing it
    constructs the ToolboxToolset and requires TOOLBOX_URL — which the
    engine-mode frontend deliberately does not need (the engine carries its
    own baked .env).
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
import uuid

logger = logging.getLogger("agent_client")

APP_NAME = "race_engineer_frontend"
USER_ID = "pit_wall"

# Local mode — hard LLM-call ceilings (chunk 8 policy, unchanged)
MAX_LLM_CALLS_PER_TRIGGER = 4
MAX_LLM_CALLS_PER_QA = 12      # human-initiated: research allowed, runaway not
QA_SESSION_ID = "pit-wall-qa"  # persistent — Q&A keeps conversational context

# Engine mode — wall-clock ceilings standing in for the RunConfig one
FIRE_TIMEOUT_S = float(os.environ.get("FIRE_TIMEOUT_S", "30"))
ASK_TIMEOUT_S = float(os.environ.get("ASK_TIMEOUT_S", "75"))


# ============================================================================
# Local: InMemoryRunner in-process (the chunk 9-11 code, re-homed verbatim)
# ============================================================================


class LocalAgentClient:
    """Runs the ADK agent inside the frontend process."""

    def __init__(self) -> None:
        # Deferred imports: only local mode pays the ADK/Toolbox import cost
        # (and the TOOLBOX_URL requirement that comes with agent.py).
        from google.adk.runners import InMemoryRunner

        from agent.race_engineer.agent import root_agent

        self.runner = InMemoryRunner(agent=root_agent, app_name=APP_NAME)
        self._qa_session_ready = False

    async def _run(self, session_id: str, message: str, max_llm_calls: int
                   ) -> tuple[str, int]:
        from google.adk.agents.run_config import RunConfig
        from google.genai import types

        msg = types.Content(role="user", parts=[types.Part(text=message)])
        tool_calls = 0
        final: list[str] = []
        async for event in self.runner.run_async(
            user_id=USER_ID, session_id=session_id, new_message=msg,
            run_config=RunConfig(max_llm_calls=max_llm_calls),
        ):
            tool_calls += len(event.get_function_calls())
            if event.is_final_response() and event.content and event.content.parts:
                for part in event.content.parts:
                    if getattr(part, "text", None):
                        final.append(part.text)
        return "".join(final).strip(), tool_calls

    async def fire(self, prompt: str) -> tuple[str, int, float]:
        """One proactive call in a FRESH session. Returns (text, tools, secs).
        May raise (incl. LlmCallsLimitExceededError) — caller drops the call."""
        session_id = f"trigger-{uuid.uuid4().hex[:8]}"
        await self.runner.session_service.create_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=session_id
        )
        t0 = time.monotonic()
        text, tools = await self._run(session_id, prompt,
                                      MAX_LLM_CALLS_PER_TRIGGER)
        return text, tools, time.monotonic() - t0

    async def ask(self, question: str) -> str:
        """Pit-wall Q&A in the PERSISTENT session — follow-ups keep context."""
        if not self._qa_session_ready:
            await self.runner.session_service.create_session(
                app_name=APP_NAME, user_id=USER_ID, session_id=QA_SESSION_ID
            )
            self._qa_session_ready = True
        text, _ = await self._run(QA_SESSION_ID, question,
                                  MAX_LLM_CALLS_PER_QA)
        return text

    async def close(self) -> None:
        await self.runner.close()


# ============================================================================
# Engine: the deployed Agent Engine (async_stream_query, dict events)
# ============================================================================


class EngineAgentClient:
    """Calls the deployed Vertex AI Agent Engine.

    EVENT-LOOP DISCIPLINE: the agent_engines SDK's query path blocks —
    observed live, it stalls the frontend's shared asyncio loop for the
    full duration of each engine call (state broadcasts burst, the lap
    ring sweeps in jerks, /api/stt sits unserved 20-30s). The SDK's
    async_* variants did not save us. So we use the SYNC methods — the
    exact calls scripts/engine_smoke.py validated — and run each whole
    call (create_session + stream_query consumption) in a worker thread
    via asyncio.to_thread. The loop stays free; the UI stays at 1 Hz.

    We never used intermediate streamed events anyway — only the final
    text and the tool-call count — so consuming the stream inside the
    thread loses nothing.
    """

    def __init__(self, resource: str) -> None:
        import vertexai
        from vertexai import agent_engines

        # projects/{project}/locations/{location}/reasoningEngines/{id}
        parts = resource.split("/")
        project, location = parts[1], parts[3]
        vertexai.init(project=project, location=location)
        self.app = agent_engines.get(resource)
        self.resource = resource
        self._qa_session_id: str | None = None

    # ---- sync internals (run inside asyncio.to_thread) ----

    def _new_session_sync(self) -> str:
        session = self.app.create_session(user_id=USER_ID)
        return session["id"] if isinstance(session, dict) else session.id

    def _query_sync(self, session_id: str, message: str) -> tuple[str, int]:
        """Consume one query's event stream; return (text, tool_call_count).

        Event shape matches scripts/engine_smoke.py: dicts with
        content.parts[] (function_call / text) and optional error fields.
        """
        tool_calls = 0
        final: list[str] = []
        for event in self.app.stream_query(
            user_id=USER_ID, session_id=session_id, message=message,
        ):
            if not isinstance(event, dict):
                continue
            if event.get("error_message"):
                raise RuntimeError(
                    f"engine error {event.get('error_code')}: "
                    f"{event['error_message'][:200]}"
                )
            for part in (event.get("content") or {}).get("parts", []):
                if part.get("function_call"):
                    tool_calls += 1
                if part.get("text"):
                    final.append(part["text"])
        text = "".join(final).strip()
        if not text:
            # A run that dies mid-flight (quota exhaustion, tool failure) can
            # end its stream with NO error event and NO text. Locally that
            # path raises; remotely it must too, or the loop broadcasts an
            # empty radio box. Raising routes it into drop-with-cooldown.
            raise RuntimeError(
                f"engine returned no text ({tool_calls} tool calls) — "
                "run likely failed server-side; see engine logs"
            )
        return text, tool_calls

    # ---- async surface (what the engineer loop calls) ----

    async def fire(self, prompt: str) -> tuple[str, int, float]:
        """Fresh remote session per trigger; wall-clock timeout in place of
        the local RunConfig ceiling. asyncio.TimeoutError → caller drops.

        Note: on timeout, asyncio abandons the worker thread rather than
        killing it — the engine call runs to completion in the background
        and its result is discarded. Harmless (read-only call, fresh
        session) and exactly the drop-a-stale-call policy we want.
        """
        t0 = time.monotonic()

        def _go() -> tuple[str, int]:
            session_id = self._new_session_sync()
            return self._query_sync(session_id, prompt)

        text, tools = await asyncio.wait_for(
            asyncio.to_thread(_go), timeout=FIRE_TIMEOUT_S)
        return text, tools, time.monotonic() - t0

    async def ask(self, question: str) -> str:
        """Persistent remote session — and unlike InMemory sessions, this one
        lives on the engine, so it survives a frontend restart."""

        def _go() -> str:
            if self._qa_session_id is None:
                self._qa_session_id = self._new_session_sync()
            text, _ = self._query_sync(self._qa_session_id, question)
            return text

        return await asyncio.wait_for(
            asyncio.to_thread(_go), timeout=ASK_TIMEOUT_S)

    async def close(self) -> None:
        return None  # nothing to release client-side


# ============================================================================
# Factory — env-selected
# ============================================================================


def make_agent_client():
    """Build the agent client from env: AGENT_MODE = local (default) | engine."""
    mode = os.environ.get("AGENT_MODE", "local").strip().lower()

    if mode == "engine":
        resource = os.environ.get("AGENT_ENGINE_RESOURCE", "").strip()
        if not resource:
            raise RuntimeError(
                "AGENT_MODE=engine requires AGENT_ENGINE_RESOURCE "
                "(the reasoningEngines resource name). source activate.sh "
                "exports it from deploy/.engine_resource after a deploy."
            )
        logger.info("agent client: ENGINE mode — %s "
                    "(fire timeout %.0fs, ask timeout %.0fs)",
                    resource, FIRE_TIMEOUT_S, ASK_TIMEOUT_S)
        return EngineAgentClient(resource)

    if mode != "local":
        raise RuntimeError(f"unknown AGENT_MODE {mode!r} — use 'local' or 'engine'")

    logger.info("agent client: LOCAL mode (InMemoryRunner in-process)")
    return LocalAgentClient()