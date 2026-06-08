"""Tiers A-C reference — your agent.py, fully built.

This is the answer key for the A-C shape of starter/race_engineer/agent.py.
Same rule as everywhere else in this repo: reading it is SHIPPING, not
cheating.

It shows the Tier B END-STATE: the `adk create` shape, generation 1 of the
instructions in your own words, plus the one tool you write by hand. The
Tier C move (ToolboxToolset) is at the bottom as a commented reference.

One cosmetic difference from your file: your Tier A instruction goes
straight into the `instruction=` string; here the same words sit in module
constants so the rehearsal probe (scripts/stage_probe.py) can import them.
Same generation 1 either way. At Tier D you retire these words for the
production prompt — generation 2 — and notice what the hardened version
carries that this one doesn't: every DATA DISCIPLINE rule is a fix for a
lie this agent told you.
"""
from __future__ import annotations

import os

from google.adk.agents import Agent

MODEL = os.environ.get("FE_MODEL", "gemini-3.5-flash")

ROOT_AGENT_DESCRIPTION = (
    "A Formula E race engineer for car 13 (Antonio Felix da Costa, "
    "TAG Heuer Porsche) at the Berlin E-Prix 2024 Round 10."
)

ROOT_AGENT_INSTRUCTION = """You are the race engineer for Antonio Felix da
Costa, car 13, TAG Heuer Porsche, at the Berlin E-Prix 2024 Round 10
(Tempelhof, 41 laps). Answer the driver's and the pit wall's questions about
the race: positions, lap times, energy, attack mode, rivals. Be concise and
concrete, like a real race engineer on the radio."""


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
# Tier C reference — wire the MCP Toolbox into your agent.
# (Commented here so this file stays a clean Tier B answer key.)
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
# tool's transcript proved necessary. This wiring is permanent: it rides
# this same file to the pit wall, where Tier D adds the frame tools
# beside it and links the production prompt.
# ============================================================================
