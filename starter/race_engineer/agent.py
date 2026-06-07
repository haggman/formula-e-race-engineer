"""Race Engineer agent definition (ADK) — pure wiring. STARTER.

Model, retry config, and tool registration only. All natural-language text
(description, instruction) lives in prompts.py.

============================== YOUR TIER D SURFACE ==============================
The frame tools (given — your Tier D reading) are already registered below.
Tier D's build move is ONE block: wire the MCP Toolbox so the agent can
reach BigQuery — the recorded race history and career stats. Look for
TODO(D). You wired this exact construction in your scaffold at Tier C;
this is the production copy.

Until that block is done this agent has only the live "now" (Firestore).
After it, it has both worlds, and questions like "compare our pace to
Wehrlein over the last 5 laps" start working. Test in scripts/agent_chat.py.
=============================================================================

Two tool families, one agent:
  - Frame tools (local functions → Firestore): the live "now"
  - ToolboxToolset (MCP → BigQuery): the recorded past + career history
The race_wall_time_ns field on frame-tool responses bridges the two clocks
(see config.RACE_START_EPOCH_NS).

Required env (exported by `source activate.sh`):
  GOOGLE_GENAI_USE_VERTEXAI=1
  GOOGLE_CLOUD_PROJECT=<lab project>
  GOOGLE_CLOUD_LOCATION=global
  TOOLBOX_URL=<deployed fe-toolbox URL>   # needed once Tier B is wired
"""
from __future__ import annotations

import os

from google.adk.agents import Agent
from google.genai import types

from starter.race_engineer.prompts import (
    ROOT_AGENT_DESCRIPTION,
    ROOT_AGENT_INSTRUCTION,
)
from starter.race_engineer.tools.frame_tools import (
    get_current_state,
    get_events_in_range,
    get_field_am_status,
    get_recent_events,
)

# FE_MODEL env knob — flip models without code edits. Different models
# draw from different capacity pools; under SUSTAINED 429s the escape is
# a GA model on a REGIONAL endpoint (visible, raisable per-project quota
# instead of the global shared pool):
#   export FE_MODEL=gemini-2.5-flash GOOGLE_CLOUD_LOCATION=us-central1
MODEL = os.environ.get("FE_MODEL", "gemini-3.5-flash")

# ============================================================================
# TODO(D): MCP Toolbox — 14 curated BigQuery tools (toolset 'race-engineer')
# ============================================================================
# Spec:
#   1. Import: from google.adk.tools.toolbox_toolset import ToolboxToolset
#      (put it with the imports at the top)
#   2. Read TOOLBOX_URL from the environment. If it's missing, raise
#      RuntimeError with a message telling the user to `source activate.sh`
#      (which auto-discovers the URL from Cloud Run) — fail fast and clear,
#      don't let a None URL surface later as a cryptic connection error.
#   3. Construct the toolset:
#        toolbox_tools = ToolboxToolset(
#            server_url=TOOLBOX_URL.rstrip("/"),
#            toolset_name="race-engineer",
#        )
#      Construction is lazy — no network happens at import time.
#   4. Replace the placeholder assignment below with your toolset. The
#      registration logic at the bottom already appends it when non-None.
# Reference: solution/race_engineer/agent.py
# ============================================================================
toolbox_tools = None  # TODO(D): replace with the ToolboxToolset

# ============================================================================
# Retry config — GIVEN, don't edit. Exponential backoff for 408/429/5xx;
# found necessary under shared lab quota (see PROGRESS.md).
# ============================================================================
shared_config = types.GenerateContentConfig(
    http_options=types.HttpOptions(
        api_version="v1",
        headers={"X-Vertex-AI-LLM-Request-Type": "shared"},
        retry_options=types.HttpRetryOptions(
            attempts=4,             # fail FAST — ten attempts meant up to
                                    # ~47s of backoff per bad LLM step. The
                                    # trigger loop owns retry semantics:
                                    # held must-says retry with a FRESH
                                    # snapshot after the 5s cooldown, which
                                    # beats shipping a stale prompt late.
            initial_delay=0.5,      # start fast
            max_delay=4.0,          # cap each wait at 4s
            exp_base=2.0,           # doubles until capped
            jitter=1.0,             # avoid thundering-herd retries
            http_status_codes=[408, 429, 500, 502, 503, 504],
        ),
    ),
)

root_agent = Agent(
    name="race_engineer",
    model=MODEL,
    generate_content_config=shared_config,
    description=ROOT_AGENT_DESCRIPTION,
    instruction=ROOT_AGENT_INSTRUCTION,
    tools=[
        get_current_state,
        get_recent_events,
        get_events_in_range,
        get_field_am_status,
    ] + ([toolbox_tools] if toolbox_tools is not None else []),
)
