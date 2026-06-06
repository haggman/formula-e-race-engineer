"""Race Engineer agent definition (ADK) — pure wiring.

Model, retry config, and tool registration only. All natural-language text
(description, instruction) lives in prompts.py.

Chunk 6 status: Pass 1 ✅ (frame tools), Pass 2 ✅ (MCP Toolbox — 11
BigQuery history tools from the deployed fe-toolbox Cloud Run service).
Pass 3 brings the full persona prompt in prompts.py.

Two tool families, one agent:
  - Frame tools (local functions → Firestore): the live "now"
  - ToolboxToolset (MCP → BigQuery): the recorded past + career history
The race_wall_time_ns field on frame-tool responses bridges the two clocks
(see config.RACE_START_EPOCH_NS).

`adk web` discovers this module via solution/race_engineer/__init__.py, which
imports it and exposes `root_agent`.

Required env (exported by `source activate.sh`):
  GOOGLE_GENAI_USE_VERTEXAI=1
  GOOGLE_CLOUD_PROJECT=<lab project>
  GOOGLE_CLOUD_LOCATION=global
  TOOLBOX_URL=<deployed fe-toolbox URL>   # auto-discovered by activate.sh
"""
from __future__ import annotations

import os

from google.adk.agents import Agent
from google.adk.tools.toolbox_toolset import ToolboxToolset
from google.genai import types

from solution.race_engineer.prompts import (
    ROOT_AGENT_DESCRIPTION,
    ROOT_AGENT_INSTRUCTION,
)
from solution.race_engineer.tools.frame_tools import (
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
# MCP Toolbox — 11 curated BigQuery tools (toolset 'race-engineer')
# ============================================================================
TOOLBOX_URL = os.environ.get("TOOLBOX_URL")
if not TOOLBOX_URL:
    raise RuntimeError(
        "TOOLBOX_URL env var required (the deployed fe-toolbox URL). "
        "Run: source activate.sh — it auto-discovers the URL from Cloud Run."
    )

toolbox_tools = ToolboxToolset(
    server_url=TOOLBOX_URL.rstrip("/"),
    toolset_name="race-engineer",
)

# ============================================================================
# Enable Provisioned Throughput (where applicable) and Exponential Backoff
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
        toolbox_tools,
    ],
)