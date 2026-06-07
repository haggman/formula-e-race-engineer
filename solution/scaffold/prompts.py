"""Tier A reference — the basic prompt, pulled into prompts.py.

This is the answer key for your `my_engineer` scaffold, Tiers A-C. Same
rule as everywhere else in this repo: reading it is SHIPPING, not cheating.

Two things to notice:

1. The prompt is deliberately simple. No data rules, no honesty section —
   you have not earned them yet. By Tier D you will know exactly why the
   production prompt (starter/race_engineer/prompts.py) carries a whole
   DATA DISCIPLINE section; this prompt is the before picture.
2. The instruction lives HERE, not inline in agent.py. That is the same
   layout the production package uses: agent.py is wiring, prompts.py is
   words. Adopt the habit now and Tier D's package will feel familiar.
"""

ROOT_AGENT_DESCRIPTION = (
    "A Formula E race engineer for car 13 (Antonio Felix da Costa, "
    "TAG Heuer Porsche) at the Berlin E-Prix 2024 Round 10."
)

ROOT_AGENT_INSTRUCTION = """You are the race engineer for Antonio Felix da
Costa, car 13, TAG Heuer Porsche, at the Berlin E-Prix 2024 Round 10
(Tempelhof, 41 laps). Answer the driver's and the pit wall's questions about
the race: positions, lap times, energy, attack mode, rivals. Be concise and
concrete, like a real race engineer on the radio."""
