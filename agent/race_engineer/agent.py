"""Race Engineer agent definition (ADK).

Pass 1 (chunk 6): agent skeleton — Gemini model + the four Firestore frame
tools, with a minimal working instruction. The full persona / radio-call
prompt moves to prompts.py in Pass 3. MCP Toolbox (BigQuery history) is
wired in Pass 2.

`adk web` discovers this module via agent/race_engineer/__init__.py, which
imports it and exposes `root_agent`.

Required env (exported by `source activate.sh`):
  GOOGLE_GENAI_USE_VERTEXAI=1
  GOOGLE_CLOUD_PROJECT=<lab project>
  GOOGLE_CLOUD_LOCATION=global       # gemini-3-flash-preview is global-only
"""
from __future__ import annotations

from google.adk.agents import Agent

from agent.race_engineer.config import (
    OUR_CAR_NUMBER,
    OUR_DRIVER_FIRST_NAME,
    OUR_DRIVER_SHORT_NAME,
)
from agent.race_engineer.tools.frame_tools import (
    get_current_state,
    get_events_in_range,
    get_field_am_status,
    get_recent_events,
)

from google.genai import types
# ============================================================================
# Enable Provisioned Throughput (where applicable) and Exponential Backoff
# ============================================================================
shared_config = types.GenerateContentConfig(
    http_options=types.HttpOptions(
        api_version="v1",
        headers={"X-Vertex-AI-LLM-Request-Type": "shared"},
        retry_options=types.HttpRetryOptions(
            attempts=10,
            initial_delay=0.5,      # start fast
            max_delay=4.0,          # cap each wait at 4s
            exp_base=2.0,           # doubles until capped
            jitter=1.0,             # avoid thundering-herd retries
            http_status_codes=[408, 429, 500, 502, 503, 504],
        ),
    ),
)

MODEL = "gemini-3.5-flash"

# Pass 1 placeholder — enough to exercise the tools sensibly in adk web.
# The real persona prompt (radio style, 6-8s calls, TTS normalization,
# AM scenario doctrine) lands in prompts.py during Pass 3.
PASS1_INSTRUCTION = f"""
You are the race engineer for Car #{OUR_CAR_NUMBER}, driven by
{OUR_DRIVER_FIRST_NAME} Félix da Costa ({OUR_DRIVER_SHORT_NAME}), during a
Formula E race (Berlin 2024, Round 10).

You observe a LIVE race via tools. Never answer race-state questions from
memory — always check the tools first:

- get_current_state: position, lap, energy, Attack Mode, cars ahead/behind.
  Call this first for any "what's happening now" question.
- get_recent_events: what just happened (overtakes, AM activations,
  race control, lap completions) in the last N seconds.
- get_events_in_range: events in a specific race-time window. One lap is
  roughly 66-68 seconds; lap N spans approximately
  [(N-1) * 67, N * 67] seconds of race time.
- get_field_am_status: Attack Mode picture across the whole field.

Speak to the driver in second person ("Antonio, ..."). Be concise and
factual, like a real race engineer on the radio. If a tool fails because no
race state exists yet, say the data feed isn't live rather than guessing.
""".strip()

root_agent = Agent(
    name="race_engineer",
    model=MODEL,
    description=(
        "Formula E race engineer copilot for Car #13 (António Félix da "
        "Costa) — live situational awareness from Firestore frame tools."
    ),
    instruction=PASS1_INSTRUCTION,
    tools=[
        get_current_state,
        get_recent_events,
        get_events_in_range,
        get_field_am_status,
    ],
)
