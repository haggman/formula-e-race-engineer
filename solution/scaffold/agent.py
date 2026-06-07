"""Tiers A-C reference — the `my_engineer` scaffold, fully built.

This file is the Tier B END-STATE: the `adk create` shape plus the one tool
you write by hand. The Tier C move (ToolboxToolset) is shown at the bottom
as a commented reference — the identical construction, with full spec, also
lives at the TODO(D) block in starter/race_engineer/agent.py, because you
do it twice: once here in your scaffold, once in the production package.

What changed from the raw `adk create` output:
  - instruction/description moved to prompts.py (Tier A)
  - one hand-written tool registered (Tier B)
That's it. An ADK agent is wiring plus words plus tools.
"""
from __future__ import annotations

import os

from google.adk.agents import Agent

from solution.scaffold.prompts import (
    ROOT_AGENT_DESCRIPTION,
    ROOT_AGENT_INSTRUCTION,
)

MODEL = os.environ.get("FE_MODEL", "gemini-3.5-flash")


# ============================================================================
# Tier B — the tool you write. Read the docstring as carefully as the code:
# THE DOCSTRING IS THE TOOL DESCRIPTION. Gemini reads it to decide when to
# call this and what to pass. Naming the dataset and tables in it is what
# lets the model write its first query without guessing.
# ============================================================================


def execute_race_sql(sql: str) -> dict:
    """Run a read-only SQL SELECT query against the fe_race10 BigQuery
    dataset, which holds the recorded Berlin E-Prix 2024 Round 10 data.

    Tables (qualify as fe_race10.<name>): drivers, startgrid, laps, attack,
    energy_per_lap, racecontrol_classified, event_stream, telemetry,
    top_speed_per_lap, career_driver, career_race.

    Args:
      sql: A single SELECT statement. Keep result sets small (LIMIT 100).
    """
    from google.cloud import bigquery  # lazy: import only when called

    if not sql.strip().lower().startswith("select"):
        return {"error": "Only SELECT statements are allowed."}
    client = bigquery.Client(project=os.environ["GOOGLE_CLOUD_PROJECT"])
    try:
        rows = list(client.query(sql).result(max_results=100))
    except Exception as e:  # surface BQ errors to the model verbatim
        return {"error": str(e)}
    return {"rows": [dict(r) for r in rows], "row_count": len(rows)}


root_agent = Agent(
    name="race_engineer",
    model=MODEL,
    description=ROOT_AGENT_DESCRIPTION,
    instruction=ROOT_AGENT_INSTRUCTION,
    tools=[execute_race_sql],
)


# ============================================================================
# Tier C reference — wire the MCP Toolbox into YOUR scaffold.
# (Commented here so this file stays a clean Tier B answer key; the same
# construction, with the full fail-fast spec, is the TODO(D) block in
# starter/race_engineer/agent.py.)
#
#   from google.adk.tools.toolbox_toolset import ToolboxToolset
#
#   TOOLBOX_URL = os.environ.get("TOOLBOX_URL")
#   if not TOOLBOX_URL:
#       raise RuntimeError("TOOLBOX_URL not set — run: source activate.sh")
#   toolbox_tools = ToolboxToolset(
#       server_url=TOOLBOX_URL.rstrip("/"),
#       toolset_name="race-engineer",
#   )
#
# Then: tools=[toolbox_tools]   — and RETIRE execute_race_sql from the
# list. The curated set supersedes your prototype; your escape hatch
# survives inside it as execute_sql_bq, now wearing the data-semantics
# warnings (broken top_speed, the grid-ID overtake rows) that your raw
# tool's transcript proved necessary.
# ============================================================================
