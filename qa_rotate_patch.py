#!/usr/bin/env python3
"""qa_rotate_patch.py — Finding #10 fix (one shot; run from the REPO ROOT, then delete).

FINDING #10 (found in rehearsal, 2026-06-06): the persistent pit-wall Q&A
session survives replay restarts (and, in engine mode, frontend restarts —
it lives on the engine). A restarted race therefore inherits the previous
race's tool results as legitimate conversation history, and the Finding #9
checkpoint-through-failure mechanism turns any failed ask into poisoned
context for the next one. Symptom observed live: fused Cassidy energy
question — perfect in a fresh agent_chat session, "Radio failure" then
"no energy telemetry for Cassidy" at the pit wall.

FIX: rotate the Q&A session when the engineer loop detects a replay
restart, exactly where it already flushes all trigger state. Follow-up
context is preserved WITHIN a race and dropped BETWEEN races — which is
correct: the race restarted.

Edits:
  1. frontend/agent_client.py — LocalAgentClient: unique per-rotation
     session id (InMemory sessions can't be recreated under the same id)
     + reset_qa_session()
  2. frontend/agent_client.py — EngineAgentClient: reset_qa_session()
     (drops the id; next ask creates a fresh engine session)
  3. frontend/engineer_loop.py — restart branch calls reset_qa_session()

Cumulative + idempotent: edits skip when already applied; a missing anchor
raises AssertionError naming it.
"""
from __future__ import annotations

import sys
from pathlib import Path

if not Path("activate.sh").is_file() or not Path("frontend/agent_client.py").is_file():
    sys.exit("Run this from the repo root (where activate.sh lives).")


def apply(path: str, label: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if new in text:
        print(f"  ○ {label} — already applied, skipping")
        return
    assert old in text, f"{path}: ANCHOR NOT FOUND for edit: {label}"
    assert text.count(old) == 1, f"{path}: anchor not unique for edit: {label}"
    p.write_text(text.replace(old, new), encoding="utf-8")
    print(f"  ✓ {label} — applied")


print("== qa_rotate_patch: frontend/agent_client.py (local) ==")
apply(
    "frontend/agent_client.py",
    "1a. LocalAgentClient: session-id field replaces the ready flag",
    "        self.runner = InMemoryRunner(agent=root_agent, app_name=APP_NAME)\n"
    "        self._qa_session_ready = False\n",
    "        self.runner = InMemoryRunner(agent=root_agent, app_name=APP_NAME)\n"
    "        self._qa_session_id: str | None = None\n",
)
apply(
    "frontend/agent_client.py",
    "1b. LocalAgentClient.ask: rotatable session + reset_qa_session()",
    '    async def ask(self, question: str) -> str:\n'
    '        """Pit-wall Q&A in the PERSISTENT session — follow-ups keep context."""\n'
    "        if not self._qa_session_ready:\n"
    "            await self.runner.session_service.create_session(\n"
    "                app_name=APP_NAME, user_id=USER_ID, session_id=QA_SESSION_ID\n"
    "            )\n"
    "            self._qa_session_ready = True\n"
    "        text, _ = await self._run(QA_SESSION_ID, question,\n"
    "                                  MAX_LLM_CALLS_PER_QA)\n"
    "        return text\n",
    '    async def ask(self, question: str) -> str:\n'
    '        """Pit-wall Q&A in a PERSISTENT session — follow-ups keep context.\n'
    "        The session rotates on replay restart (reset_qa_session), so a new\n"
    '        race never inherits tool results from the previous one (Finding #10).\n'
    '        """\n'
    "        if self._qa_session_id is None:\n"
    '            self._qa_session_id = f"{QA_SESSION_ID}-{uuid.uuid4().hex[:8]}"\n'
    "            await self.runner.session_service.create_session(\n"
    "                app_name=APP_NAME, user_id=USER_ID,\n"
    "                session_id=self._qa_session_id,\n"
    "            )\n"
    "        text, _ = await self._run(self._qa_session_id, question,\n"
    "                                  MAX_LLM_CALLS_PER_QA)\n"
    "        return text\n"
    "\n"
    "    def reset_qa_session(self) -> None:\n"
    '        """Drop the persistent Q&A session; the next ask starts fresh."""\n'
    "        self._qa_session_id = None\n",
)

print("== qa_rotate_patch: frontend/agent_client.py (engine) ==")
apply(
    "frontend/agent_client.py",
    "2. EngineAgentClient: reset_qa_session()",
    "    async def close(self) -> None:\n"
    "        return None  # nothing to release client-side\n",
    "    def reset_qa_session(self) -> None:\n"
    '        """Drop the persistent Q&A session id; the next ask creates a\n'
    "        fresh session on the engine (the old one is simply abandoned —\n"
    '        fine in an ephemeral lab project). Finding #10."""\n'
    "        self._qa_session_id = None\n"
    "\n"
    "    async def close(self) -> None:\n"
    "        return None  # nothing to release client-side\n",
)

print("== qa_rotate_patch: frontend/engineer_loop.py ==")
apply(
    "frontend/engineer_loop.py",
    "3. restart branch rotates the Q&A session",
    "                last_summary_lap = None\n"
    "                due_summary_lap = None\n"
    "                pending_must_say = None\n",
    "                last_summary_lap = None\n"
    "                due_summary_lap = None\n"
    "                pending_must_say = None\n"
    "                self.agent.reset_qa_session()  # Finding #10: a new race\n"
    "                logger.info(\"Q&A session rotated for the new race\")\n",
)

print("\nqa_rotate_patch complete. Review: git diff")
print("Then: rm qa_rotate_patch.py  (one-shot — do not leave it in the repo)")
