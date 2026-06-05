"""Terminal chat harness for the Race Engineer agent — full tool-call visibility.

Runs the agent in a persistent session and prints EVERY tool call with its
exact arguments and a truncated response, inline with the conversation.
This is the primary T1-T2 testing surface: the printed transcript shows
whether the model passed sane arguments (e.g. the right through_time_ns),
not just whether the final answer sounds plausible.

WHICH AGENT: resolved through the AGENT_PACKAGE seam (shared/agent_pkg.py).
activate.sh defaults to starter.race_engineer — the student build. To chat
with the reference instead:
    AGENT_PACKAGE=solution.race_engineer python scripts/agent_chat.py

Fully async with ONE event loop for the whole session — required because
ToolboxToolset's HTTP client binds to the loop it first runs on. (The sync
runner.run() spins a fresh loop per question, which kills the toolset after
the first turn: "Event loop is closed".)

Usage:
    python scripts/agent_chat.py
    python scripts/agent_chat.py --max-response-chars 2000   # show more of tool responses

Commands inside the chat:
    /quit            exit
    /new             start a fresh session (clears conversation history)

Requires: source activate.sh (env vars + venv), simulator running for live
questions. Same session persists across questions until /new.
"""
from __future__ import annotations

from shared.script_env import require_venv
require_venv()

import argparse
import asyncio
import json
import uuid

from google.adk.runners import InMemoryRunner
from google.genai import types

from shared.agent_pkg import AGENT_PACKAGE, agent_module

root_agent = agent_module("agent").root_agent

APP_NAME = "race_engineer_chat"
USER_ID = "dev"


def fmt_args(args: dict, limit: int = 400) -> str:
    s = json.dumps(args, default=str)
    return s if len(s) <= limit else s[:limit] + f"... (+{len(s)-limit} chars)"


def fmt_response(resp, limit: int) -> str:
    s = json.dumps(resp, default=str) if not isinstance(resp, str) else resp
    return s if len(s) <= limit else s[:limit] + f"... (+{len(s)-limit} chars)"


async def make_session(runner: InMemoryRunner) -> str:
    session_id = f"chat-{uuid.uuid4().hex[:8]}"
    await runner.session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session_id
    )
    return session_id


async def ask(
    runner: InMemoryRunner, session_id: str, question: str, resp_limit: int
) -> None:
    msg = types.Content(role="user", parts=[types.Part(text=question)])
    final_text = []
    async for event in runner.run_async(
        user_id=USER_ID, session_id=session_id, new_message=msg
    ):
        for call in event.get_function_calls():
            print(f"  ▶ TOOL CALL  {call.name}({fmt_args(dict(call.args or {}))})")
        for fr in event.get_function_responses():
            print(f"  ◀ RESPONSE   {fr.name}: {fmt_response(fr.response, resp_limit)}")
        if event.is_final_response() and event.content and event.content.parts:
            for part in event.content.parts:
                if getattr(part, "text", None):
                    final_text.append(part.text)
    print()
    print("ENGINEER:", "".join(final_text).strip() or "(no text response)")


async def amain(resp_limit: int) -> None:
    runner = InMemoryRunner(agent=root_agent, app_name=APP_NAME)
    session_id = await make_session(runner)
    print(f"Race Engineer chat — package {AGENT_PACKAGE}, session {session_id}")
    print("Tool calls print inline. /new = fresh session, /quit = exit.\n")

    while True:
        try:
            # input() blocks, but this is a single-user dev REPL — nothing
            # else needs the loop while we wait for the human.
            q = await asyncio.to_thread(input, "YOU: ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        q = q.strip()
        if not q:
            continue
        if q == "/quit":
            break
        if q == "/new":
            session_id = await make_session(runner)
            print(f"(fresh session {session_id})\n")
            continue
        print()
        try:
            await ask(runner, session_id, q, resp_limit)
        except Exception as e:
            print(f"  ✗ run failed: {type(e).__name__}: {e}")
        print()

    await runner.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-response-chars", type=int, default=600,
                        help="truncate printed tool responses to this length")
    args = parser.parse_args()
    asyncio.run(amain(args.max_response_chars))


if __name__ == "__main__":
    main()
