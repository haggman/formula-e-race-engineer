# Student Guide — Build a Formula E Race Engineer

You are about to build an AI race engineer. Not a chatbot about racing — a
copilot that watches a live Formula E race, decides for itself when
something deserves a radio call, answers the driver's questions by reaching
into live telemetry and race history, and speaks its calls aloud over team
radio.

The race is real: Berlin 2024, Round 10. The driver is real: car #13,
António Félix da Costa, who started P10 and won. The data is real: every
lap, every overtake, every attack-mode activation, 1.28 million telemetry
samples. The race replays through your project at up to 5× speed, and your
agent rides along.

You saw the finished product in the opening demo. Today you build its
brain.

---

## What's already running in your project (and what's yours)

The line to understand before anything else:

**The DATA PLANE lives in GCP** — deployed by the setup script you ran at
the start (`setup/all.sh`):

| Piece | Where | What it does |
|---|---|---|
| Simulator | Cloud Run (`fe-simulator`) | Replays the race, publishing 1 Hz frames to Pub/Sub |
| State Writer | Cloud Run (`fe-state-writer`) | Pub/Sub → Firestore: the live "now" |
| Firestore | GCP | Current race state + event stream |
| BigQuery | GCP (`fe_race10`) | The recorded race + 10 seasons of career history |
| MCP Toolbox | Cloud Run (`fe-toolbox`) | 14 curated BigQuery tools your agent will call |

**YOUR code runs in Cloud Shell** — the agent (and the pit-wall frontend
that hosts it). This is deliberate: the part you iterate on has a
seconds-long edit loop. Change a prompt, restart, hear the difference.

Two more directories matter:

- **`starter/race_engineer/` — you work HERE.** A partially built agent
  with clearly marked TODOs.
- **`solution/race_engineer/` — the answer key.** The complete reference,
  same file layout, file for file. This is a hackathon, not an exam:
  if you're stuck, open the same filename in `solution/` and read. You
  learn more from shipping than from suffering.

The `AGENT_PACKAGE` environment variable selects which package the whole
system runs (your shell defaults to `starter.race_engineer`). Every test
tool prints which package it loaded — check the banner if results confuse
you.

## Getting started

WHERE: Cloud Shell, repo root — and in EVERY new tab you open:

```bash
source activate.sh
```

That creates/activates the venv, installs requirements, and exports
PROJECT_ID, REGION, TOOLBOX_URL, AGENT_PACKAGE. If a script ever complains
about missing env, the fix is always the same line.

If your setup script is still running from the opening, let it finish, then:

```bash
bash setup/verify.sh        # five checks; you want the GREEN LIGHT
```

### Gemini Code Assist is sitting right there

The Cloud Shell Editor has Gemini Code Assist built in — use it.
Highlight the worked example and ask "explain how this tool reads the
race frame"; ask it to draft a docstring; ask why a type hint matters
to ADK.

One warning: Code Assist may suggest **ADK 2.0** APIs (GA since May
2026 — graph Workflow Runtime, new callback model). This lab is pinned
to **ADK 1.x**. If a suggestion or a doc page mentions *Workflow
Runtime*, *graphs*, or a *Task API*, you're reading 2.0 — back out. The
worked example in `starter/race_engineer/tools/frame_tools.py` is
ground truth for the patterns this repo uses.

### Learn ADK fast (curated, 1.x-safe)

- Function tools — plain Python functions; the docstring and type hints
  ARE the API the model sees:
  https://google.github.io/adk-docs/tools-custom/function-tools/
- Custom tools overview: https://google.github.io/adk-docs/tools-custom/
- Python quickstart (LlmAgent, runners):
  https://google.github.io/adk-docs/get-started/python/
- API reference: https://google.github.io/adk-docs/api-reference/python/
  — it now defaults to 2.0.0; trust the repo's worked example when they
  disagree.
- MCP Toolbox: https://mcp-toolbox.dev/documentation/introduction/ — our server
  runs v1.3.0 and the current docs describe the newer v2 config format,
  so when you touch `toolbox/tools.yaml`, copy the shape of the
  EXISTING tools in the file, not the docs.

---

## Two minutes of Formula E (everything your agent needs to know, you
should know too)

**The race:** Berlin E-Prix 2024 Round 10. 41 laps, ~48 minutes. Da Costa
(DAC, car 13, TAG Heuer Porsche) starts P10, carves to P3 by lap 5, and
wins. His main fights: Cassidy (CAS) — 11 position exchanges, the real
battle for the win — and Vergne (JEV), his grid neighbor. Two
retirements punctuate the story: GUE (car 7) on lap 10 and FEN (car
23) on lap 24.

**Attack Mode**, the strategic heart of Formula E:

- A fixed power boost (300 kW → 350 kW), earned by driving through an
  activation zone placed OFF the racing line (at Berlin: Turn 2) —
  taking it costs track position. When it's active, the car's halo glows magenta; everyone can
  see it.
- Every driver must use exactly TWO activations per race. The total boost
  time is 240 seconds, split per a pre-armed "scenario": 1 = 60s+180s,
  2 = 120s+120s, 3 = 180s+60s.
- An ARMING is declared intent (which scenario); an ACTIVATION is the
  actual deployment. Drivers re-arm as strategy evolves — DAC armed 9
  times this race, most in the field.
- Once activated it runs its full duration. No early exit. The clock burns
  even under safety car. This is why it's worth an AI engineer: fixed-
  duration power committed against an unknown future.
- On lap 3 of this race, about half the field activates within seconds —
  watch your position tower light up orange. DAC deliberately holds back.
- The move of this race, laps 7–9: DAC deliberately hands back the lead
  to take his short 60s activation, drops to P3, and repasses with the
  boost still lit — a planned sacrifice. An engineer that calls it as
  it happens earns its seat.

**Energy:** every car finishes with exactly 100% of its budget consumed
(the data is normalized), so what matters is mid-race deltas versus the
field average — is DAC spending faster or slower than rivals right now?

## The two worlds (the architecture in one idea)

Every question your engineer answers draws on one or both of:

| World | Store | Latency | Example |
|---|---|---|---|
| **Now** | Firestore, via your frame tools | instant | "Who's behind us?" |
| **Then** | BigQuery, via MCP Toolbox | seconds | "What was our fastest lap?" |

The agent decides which world a question needs. The best questions span
both without the asker saying so — "how's our energy versus Cassidy?"
needs current state AND consumption history, fused. That orchestration is
what you're building, and it's the whole reason this hackathon exists.

One rule that makes the demo honest: the agent is *time-honest*. History
tools only return events up to the replay's current moment. Ask about lap
20 while the race is on lap 8 and your engineer doesn't know yet.

---

# The build — four tiers, stop anywhere with something working

Each tier has ONE testing surface and ONE checkpoint demo. Budgets assume
solo work; teams parallelize (see below).

## Tier 1 — Frame tools: teach the agent to see (~40 min)

**Where:** `starter/race_engineer/tools/frame_tools.py`
**What:** One tool is complete — `get_current_state`, the worked example.
Read it top to bottom first; every ADK mechanic you need is in it, with
comments. Then build the three `TODO(T1)` tools: `get_recent_events`,
`get_events_in_range`, `get_field_am_status`. Full specs are in the
comments above each `raise NotImplementedError`.

**Test surface:** `scripts/test_frame_tools.py` — your T1 checklist.

```bash
# WHERE: Cloud Shell, repo root, activated
python scripts/test_frame_tools.py --live
```

Unimplemented tools show as `✗ NotImplementedError: TODO(T1)`. When every
section is ✓, T1 is done.

**Checkpoint demo:** chat with your agent.

```bash
python scripts/agent_chat.py
```

Ask: *"Where are we right now?"* — then *"What just happened in the last
minute?"* Watch the tool calls print inline: the transcript shows you what
the model passed, not just what it said.

## Tier 2 — Wire the Toolbox: give it a memory (~45 min)

**Where:** `starter/race_engineer/agent.py`, the `TODO(T2)` block.
**What:** One construction — the `ToolboxToolset` pointing at your
deployed fe-toolbox — and your agent gains 14 BigQuery tools: lap history,
energy curves, overtakes, race control, career stats, plus a
schema-discovery + SQL escape hatch.

**Test surface:** `scripts/agent_chat.py` again — now ask two-worlds
questions:

- *"What was our fastest lap so far?"* (pure history)
- *"How many times have we traded places with Vergne today?"*
- *"Compare our pace to Wehrlein over the last 5 laps."* (the money
  question — watch it call get_current_state for "now", bridge the clock,
  then query history)

**The clock bridge** is the thing to understand here, and it's GIVEN in
your prompt (read the DATA DISCIPLINE section): BigQuery timestamps are
from the original 2024 race; the only valid "up to now" value is
`race_wall_time_ns` from your own frame tools. The rules in that section
exist because the model broke without them. Best lesson in the repo.

**Checkpoint demo:** the Wehrlein pace comparison, live in the chat.

## Tier 3 — Persona: make it sound like a race engineer (~30 min)

**Where:** `starter/race_engineer/prompts.py` — the `_VOICE` and
`_CALL_TYPES` sections (everything else is given; the TODO comments above
each section are your spec).
**What:** As shipped, your agent talks like a database. Write the voice:
second person to Antonio, 6–8 second calls, concrete instructions or none,
no markdown, no cheerleading. Then the three call templates. One warning
from the build: example phrases you write become the model's vocabulary —
they WILL come back out of the speaker. Choose examples you'd be happy to
hear on stage.

**Test surface:** the pit wall — this is where voice lives.

```bash
# WHERE: Cloud Shell, repo root (any tab — it sources activate.sh itself)
bash demo.sh
# Web Preview → port 8080; click 🔇 to enable audio (the click unlocks it);
# RESTART on the SIM bar; 2× is a good build speed.
```

**Checkpoint demo:** lap 3. Half the field takes attack mode, your scorer
fires, and your engineer — in YOUR voice — explains it out loud. Hold
SPACE and ask a question with your actual voice. That's the moment.

## Tier 4 — Make the engineer yours (overflow / team stretch)

The trigger system is given and pre-tuned: a deterministic scorer
(`shared/scorer.py`) decides WHEN the engineer speaks; the model only
decides WHAT to say. T4 is tuning that judgment:

- **The dials:** every weight is a named constant at the top of
  `shared/scorer.py` — overtake urgency, AM cluster threshold, race-control
  severities — plus the loop's debounce and must-say gap. Make your
  engineer chattier, calmer, more paranoid about rivals.
- **The challenge (build something new):** the scorer doesn't react to
  ARMING events at all — strategic intent ("Cassidy just armed scenario 3
  — he's going long") is invisible to it today. The data is there
  (`get_am_armings`, and arming events flow through the event stream).
  Write the rule, pick its weight, decide if it's must-say.
- **The missing tool:** the toolbox has no name → car-number lookup, so
  the prompt currently steers the model around it. Add a curated
  `lookup_driver` to `toolbox/tools.yaml` — copy the shape of an
  existing tool: `drivers` JOIN `startgrid`, matching
  `UPPER(driver_last_name)` OR `driver_short_name`. Redeploy with
  `bash setup/3_deploy_toolbox.sh`, then try trimming the name-steering
  from the prompt and watch the tool chains get shorter. Heads-up:
  `setup/verify.sh` expects exactly 14 tools, so your 15th flags ✗
  there — expected, not broken.

**Test surface:** `scripts/local_test.py` — the trigger loop as a fast
terminal harness:

```bash
python scripts/local_test.py --duration 380 --verbose
```

`--verbose` shows suppressed and below-threshold moments — the negative
space your tuning controls.

## Working as a team

The seam makes parallel work clean — one integration point
(`starter/race_engineer/`), four lanes, four test scripts, nobody waits
on anybody:

| Lane | You own | Validator | Needs first |
|---|---|---|---|
| **Tools** (T1) | `tools/frame_tools.py` | `python scripts/test_frame_tools.py --live` | setup green |
| **Data** (T2+) | the Toolbox TODO in `agent.py`, then treasure-hunting — this dataset has famous quirks (a broken top-speed column, two ID domains in one event stream); add a curated tool if you find something good | `python scripts/agent_chat.py` | setup green |
| **Persona** (T3) | `prompts.py` | `bash demo.sh` | T1's `get_current_state` only — start immediately |
| **Triggers** (T4) | scorer weights + the arming rule | `python scripts/local_test.py --verbose` | Tools lane green |

**Integration ritual** (10 minutes, mid-afternoon): frame tools all ✓ →
one fused question in `agent_chat.py` (the Wehrlein pace comparison) →
`bash demo.sh` and let it talk through lap 3. Three passes = your lanes
merged.

## Question bank (for your demos)

**Now:** Who's directly behind us, and does he have attack mode left? /
What's the field looking like at the front?
**Then:** What was our fastest lap? / Any race control messages I should
know about? / Who's driving car 94, and how's his race going?
**Fused:** How's our energy versus Cassidy — gaining or losing? / Compare
our pace to Wehrlein over the last 5 laps.
**Judgment:** Should we take our second attack mode now, or wait?
**The honesty test:** What's the weather looking like? — the right answer
is a clean refusal. No tool has weather; an engineer that admits what it
doesn't know is the one you trust on what it does.

## When things go sideways

| Symptom | Likely cause | Fix |
|---|---|---|
| `NotImplementedError: TODO(T1)` | That's your TODO list talking | Implement it — spec is above the raise |
| Script complains about env/venv | New tab, not activated | `source activate.sh` |
| EVERYTHING on the local pit wall 503s | Cloud Shell session recycled; your exports are gone | Relaunch with `bash demo.sh` — it re-sources everything itself |
| Tower empty, no state | Sim not publishing / fresh reset | RESTART on the SIM bar |
| Calls dropped, log mentions limit | Tool-budget ceiling did its job | Fine in moderation; if constant, your prompt is sending the agent wandering |
| Agent answers feel stale at 5× | The world moves while it thinks | Build at 2×; savor at 1× |
| No audio | Browser autoplay policy | Click the 🔇 toggle — the click is the unlock |
| Engineer invents a driver name | It shouldn't — the HONESTY section forbids it | If you removed that section, put it back |
| Totally stuck | — | Same filename in `solution/` — that's what it's for |

## Finished early?

Open **BONUS.md** — a board of additive tickets (voice picker,
tool-call observability panel, post-race debrief, deploying YOUR agent
to a public URL), sized S/M/L. Nothing on it can break what you
already demo.

Now go build. Antonio's waiting on the radio.