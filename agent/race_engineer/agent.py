"""Race Engineer agent definition (ADK) — pure wiring.

Model, retry config, and tool registration only. All natural-language text
(description, instruction) lives in prompts.py.

Chunk 6 status: Pass 1 complete (frame tools). MCP Toolbox (BigQuery
history) is wired in Pass 2; the full persona prompt lands in prompts.py
during Pass 3.

`adk web` discovers this module via agent/race_engineer/__init__.py, which
imports it and exposes `root_agent`.

Required env (exported by `source activate.sh`):
  GOOGLE_GENAI_USE_VERTEXAI=1
  GOOGLE_CLOUD_PROJECT=<lab project>
  GOOGLE_CLOUD_LOCATION=global
"""
from __future__ import annotations

from google.adk.agents import Agent
from google.genai import types

from agent.race_engineer.prompts import (
    ROOT_AGENT_DESCRIPTION,
    ROOT_AGENT_INSTRUCTION,
)
from agent.race_engineer.tools.frame_tools import (
    get_current_state,
    get_events_in_range,
    get_field_am_status,
    get_recent_events,
)

MODEL = "gemini-3.5-flash"

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
    ],
)