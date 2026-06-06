"""Q&A latency probe — the automated A/B measurement for the latency
investigation (PACKAGING.md, priority 1).

Runs the EXACT diagnostic protocol from the plan, hands-free:

  Each round asks three questions, back to back (same minute — this is what
  separates quota weather from chain depth and session growth):

    1. FAST / persistent   "what's our position+energy" in the long-lived
                           Q&A session (pure get_current_state, 1 tool)
    2. FUSED / persistent  the Cassidy energy comparison in the SAME session
                           (two worlds, multi-tool)
    3. FAST / fresh        the same fast question in a brand-new session —
                           the CONTROL ARM: constant-size request, so its
                           wall time is a pure quota-weather barometer

  Hypothesis map (how to read the table this prints):
    - fast/persistent prompt-tokens and wall CLIMB round over round while
      fast/fresh stays flat            -> H4 confirmed: session growth.
                                          Build the sliding window.
    - all three arms spiky together, retry lines > 0, tokens flat
                                       -> H1: quota weather. Build the
                                          progress indicator; retest morning.
    - fused slow even with 0 retries and flat tokens, many tool rounds
                                       -> H2/H3: chain depth / SQL wandering.
                                          Tighten the QA ceiling / steer to
                                          curated tools.

WHICH AGENT: the AGENT_PACKAGE seam, like every dev script. Run the probe
against the reference (the deployed product's agent):
    AGENT_PACKAGE=solution.race_engineer python scripts/qa_latency_probe.py

PRECONDITIONS: source activate.sh; data plane up; simulator RUNNING (live or
paused MID-RACE — the fused question needs Cassidy on track, so don't probe
from the pre-race grid). Don't run the frontend at the same time: with no
trigger loop firing, the probe owns the quota lane and the measurement is
clean.

Usage:
    python scripts/qa_latency_probe.py                       # 4 rounds
    python scripts/qa_latency_probe.py --rounds 6 --gap 8
    python scripts/qa_latency_probe.py --csv /tmp/qa_probe.csv --verbose
"""
from __future__ import annotations

from shared.script_env import require_venv
require_venv()

import argparse
import asyncio
import csv
import json
import logging
import statistics
import time
import uuid

from google.adk.runners import InMemoryRunner
from google.genai import types

from shared.agent_pkg import AGENT_PACKAGE, agent_module

root_agent = agent_module("agent").root_agent

APP_NAME = "race_engineer_qa_probe"
USER_ID = "probe"

FAST_Q = "What is our current position and energy right now?"
FUSED_Q = "How's our energy versus Cassidy — are we gaining or losing?"


# ----------------------------------------------------------------------------
# Retry/throttle log counter (same idea as agent_chat's, kept self-contained)
# ----------------------------------------------------------------------------


class LlmLogCounter(logging.Handler):
    KEYWORDS = ("retry", "retrying", "backoff", "429", "resource_exhausted",
                "resource exhausted", "503", "unavailable", "deadline")

    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.hits = 0

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = record.getMessage().lower()
        except Exception:
            return
        if any(k in msg for k in self.KEYWORDS):
            self.hits += 1

    def take(self) -> int:
        h, self.hits = self.hits, 0
        return h


def setup_counter() -> LlmLogCounter:
    counter = LlmLogCounter()
    warn = logging.StreamHandler()
    warn.setLevel(logging.WARNING)
    for name in ("google_genai", "google.genai", "httpx"):
        lg = logging.getLogger(name)
        lg.setLevel(logging.INFO if name == "httpx" else logging.DEBUG)
        lg.addHandler(counter)
        lg.addHandler(warn)
        lg.propagate = False
    return counter


# ----------------------------------------------------------------------------
# One measured ask
# ----------------------------------------------------------------------------


async def measure(runner: InMemoryRunner, session_id: str, question: str,
                  counter: LlmLogCounter, verbose: bool) -> dict:
    msg = types.Content(role="user", parts=[types.Part(text=question)])
    t0 = time.monotonic()
    last = t0
    llm_calls = 0
    tool_calls = 0
    prompt_tokens = 0
    max_llm_gap = 0.0
    got_text = False
    error = ""

    try:
        async for event in runner.run_async(
            user_id=USER_ID, session_id=session_id, new_message=msg
        ):
            now = time.monotonic()
            gap = now - last
            last = now
            calls = event.get_function_calls()
            if calls:
                max_llm_gap = max(max_llm_gap, gap)
                tool_calls += len(calls)
                if verbose:
                    for c in calls:
                        print(f"        [+{now-t0:5.1f}s llm {gap:5.1f}s] "
                              f"▶ {c.name}({json.dumps(dict(c.args or {}), default=str)[:120]})")
            elif verbose and event.get_function_responses():
                print(f"        [+{now-t0:5.1f}s tool {gap:5.1f}s] ◀ "
                      + ", ".join(fr.name for fr in event.get_function_responses()))
            usage = getattr(event, "usage_metadata", None)
            if usage is not None:
                llm_calls += 1
                pt = getattr(usage, "prompt_token_count", None)
                if pt:
                    prompt_tokens = pt
            if event.is_final_response() and event.content and event.content.parts:
                if not calls and not event.get_function_responses():
                    max_llm_gap = max(max_llm_gap, gap)
                if any(getattr(p, "text", None) for p in event.content.parts):
                    got_text = True
    except Exception as e:  # a dropped ask is data, not a probe failure
        error = f"{type(e).__name__}: {str(e).splitlines()[0][:120]}" if str(e) \
            else type(e).__name__

    return {
        "wall_s": round(time.monotonic() - t0, 1),
        "llm_calls": llm_calls,
        "tool_calls": tool_calls,
        "prompt_tokens": prompt_tokens,
        "max_llm_gap_s": round(max_llm_gap, 1),
        "retry_lines": counter.take(),
        "ok": got_text and not error,
        "error": error,
    }


# ----------------------------------------------------------------------------
# The probe
# ----------------------------------------------------------------------------


async def new_session(runner: InMemoryRunner, prefix: str) -> str:
    sid = f"{prefix}-{uuid.uuid4().hex[:8]}"
    await runner.session_service.create_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=sid)
    return sid


async def amain(args: argparse.Namespace) -> None:
    counter = setup_counter()
    runner = InMemoryRunner(agent=root_agent, app_name=APP_NAME)
    qa_sid = await new_session(runner, "qa-persistent")

    print(f"Q&A latency probe — package={AGENT_PACKAGE}, rounds={args.rounds}, "
          f"gap={args.gap}s between asks")
    print(f"  FAST : {FAST_Q}")
    print(f"  FUSED: {FUSED_Q}")
    print(f"  persistent session: {qa_sid} (fast+fused share it; "
          f"fast/fresh is the control arm)\n")

    hdr = (f"{'round':>5} {'arm':<16} {'wall_s':>7} {'llm':>4} {'tools':>5} "
           f"{'prompt_tok':>10} {'maxgap_s':>8} {'retries':>7}  note")
    print(hdr)
    print("-" * len(hdr))

    rows: list[dict] = []
    persistent_turn = 0
    for r in range(1, args.rounds + 1):
        plan = [
            ("fast/persistent", FAST_Q, qa_sid),
            ("fused/persistent", FUSED_Q, qa_sid),
            ("fast/fresh", FAST_Q, None),
        ]
        for arm, question, sid in plan:
            if sid is None:
                sid = await new_session(runner, "ctl")
            if "persistent" in arm:
                persistent_turn += 1
            m = await measure(runner, sid, question, counter, args.verbose)
            m.update(round=r, arm=arm,
                     session_turn=persistent_turn if "persistent" in arm else 1)
            rows.append(m)
            note = m["error"] or ("" if m["ok"] else "EMPTY ANSWER")
            print(f"{r:>5} {arm:<16} {m['wall_s']:>7.1f} {m['llm_calls']:>4} "
                  f"{m['tool_calls']:>5} {m['prompt_tokens']:>10} "
                  f"{m['max_llm_gap_s']:>8.1f} {m['retry_lines']:>7}  {note}")
            await asyncio.sleep(args.gap)

    await runner.close()

    # ------------------------------------------------------------------
    # Read the table for Patrick (observations, not a verdict — the human
    # closes the diagnosis)
    # ------------------------------------------------------------------
    def arm(name: str) -> list[dict]:
        return [x for x in rows if x["arm"] == name and x["ok"]]

    print("\n== Observations ==")
    fp, fr_, fu = arm("fast/persistent"), arm("fast/fresh"), arm("fused/persistent")

    if len(fp) >= 2:
        tok0, tokN = fp[0]["prompt_tokens"], fp[-1]["prompt_tokens"]
        w0, wN = fp[0]["wall_s"], fp[-1]["wall_s"]
        print(f"  fast/persistent: prompt tokens {tok0} -> {tokN} "
              f"({'GROWING' if tok0 and tokN > 1.4 * tok0 else 'roughly flat'}), "
              f"wall {w0}s -> {wN}s")
        if tok0 and tokN > 1.4 * tok0 and wN > w0:
            print("    -> H4 signature (session growth): tokens and wall climb "
                  "with turn count. Sliding window is the fix.")
    if fr_:
        walls = [x["wall_s"] for x in fr_]
        spread = max(walls) / max(min(walls), 0.1)
        print(f"  fast/fresh (control): walls {walls} "
              f"(spread {spread:.1f}x — {'SPIKY: quota weather present' if spread > 2 else 'stable'})")
    if fu:
        print(f"  fused/persistent: avg {statistics.mean(x['wall_s'] for x in fu):.1f}s, "
              f"avg tools {statistics.mean(x['tool_calls'] for x in fu):.1f}, "
              f"max single llm gap {max(x['max_llm_gap_s'] for x in fu):.1f}s")
    total_retries = sum(x["retry_lines"] for x in rows)
    print(f"  retry/throttle log lines across the probe: {total_retries}"
          + (" (H1 active in this window)" if total_retries else
             " (no visible backoff this window)"))
    failures = [x for x in rows if not x["ok"]]
    if failures:
        print(f"  {len(failures)} ask(s) failed/empty — "
              + "; ".join(f"r{x['round']} {x['arm']}: {x['error'] or 'empty'}"
                          for x in failures[:4]))

    if args.csv:
        fields = ["round", "arm", "session_turn", "wall_s", "llm_calls",
                  "tool_calls", "prompt_tokens", "max_llm_gap_s",
                  "retry_lines", "ok", "error"]
        with open(args.csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows({k: x[k] for k in fields} for x in rows)
        print(f"\nCSV written: {args.csv}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rounds", type=int, default=4,
                        help="rounds of (fast/persistent, fused/persistent, "
                             "fast/fresh) — default 4 = 12 asks")
    parser.add_argument("--gap", type=float, default=5.0,
                        help="seconds to wait between asks (default 5)")
    parser.add_argument("--csv", help="also write per-ask rows to this CSV path")
    parser.add_argument("--verbose", action="store_true",
                        help="print per-event tool/llm timing inside each ask")
    args = parser.parse_args()
    asyncio.run(amain(args))


if __name__ == "__main__":
    main()
