<!-- TINYURL: https://tinyurl.com/FE-Hack-2 -->

# Build a Formula E Race Engineer

---

## STEP 0 — do this FIRST, before the instructor starts talking

> **WHERE:** your lab project's Google Cloud console → Cloud Shell (the `>_`
> icon, top right) → Open Terminal. Authorize if prompted.
> **WHAT — paste all four lines:**
> ```bash
> git clone https://github.com/haggman/formula-e-race-engineer.git
> cd formula-e-race-engineer
> source activate.sh
> bash setup/all.sh
> ```

That last command deploys your personal race-data plane (~10 minutes,
budget 20). **Don't watch it.** Open a second Cloud Shell tab (the `+`)
and get your editor ready instead:

> ```bash
> cd formula-e-race-engineer
> cloudshell workspace .        # opens the Cloud Shell Editor in the repo
> ```

⏸ **STOP HERE. Eyes up front — the instructor takes it from here.**
When they send you back to this guide, pick up at **Welcome back** below.

---

## Welcome back

You just watched the finished product: an AI race engineer that watches a
live Formula E race, decides for itself when something deserves a radio
call, answers questions by reaching into live telemetry *and* race
history, and speaks over team radio. Today you build its brain.

The race is real: Berlin 2024, Round 10. The driver is real: car #13,
António Félix da Costa, who started P10 and won. The data is real: every
lap, every overtake, every attack-mode activation, 1.28 million telemetry
samples. The race replays through your project at up to 5× speed, and
your agent rides along.

First, confirm your Step-0 setup finished:

> **WHERE:** Cloud Shell, repo root (`cd ~/formula-e-race-engineer` if needed)
> **WHAT:**
> ```bash
> source activate.sh        # every new tab needs this — it's always the fix
> bash setup/verify.sh      # five checks; you want the GREEN LIGHT
> ```

If a check is ✗, it names the setup script to rerun. Indexes "still
building" just means wait a few minutes and re-verify.

## The map

![Architecture](docs/architecture.svg)

Read it left to right. The **Race Replay** column and the **Pit Wall**
column are GIVEN — deployed plumbing and a finished UI. The **Agent**
column is YOURS: six tiers, A through F — you build the agent twice,
on purpose, and every tier ends with something running.

| Piece | Where | What it does |
|---|---|---|
| Simulator | Cloud Run (`fe-simulator`) | Replays the race, publishing 1 Hz frames to Pub/Sub |
| State Writer | Cloud Run (`fe-state-writer`) | Pub/Sub → Firestore: the live "now" |
| Firestore | GCP | Current race state + event stream |
| BigQuery | GCP (`fe_race10`) | The recorded race + 10 seasons of career history |
| MCP Toolbox | Cloud Run (`fe-toolbox`) | 14 BigQuery tools your agent will call |
| Pit-wall frontend | **your Cloud Shell** | The UI, voice loop, and trigger system — given |
| `my_engineer/` | your editor | **Tiers A–C happen here** — a scaffold YOU create in Tier A |
| `starter/race_engineer/` | your editor | The production package — **you graduate here in Tier D** (one TODO, plus the best given reading in the repo) |
| `solution/race_engineer/` | your editor | The answer key: same layout, file for file. Tiers A–C have their own key at `solution/scaffold/`. Stuck? Open the same filename and read. You learn more from shipping than from suffering. |

Your code runs in Cloud Shell on purpose: the part you iterate on has a
seconds-long edit loop. Change a prompt, restart, hear the difference.
The `AGENT_PACKAGE` env var selects which package the system runs (your
shell defaults to `starter.race_engineer`); every test tool prints which
package it loaded — check the banner if results confuse you.

**Names, two registers:** the pit wall displays driver SURNAMES (Da Costa,
Cassidy, Wehrlein), but the data — tool responses, BigQuery tables, test
output — speaks 3-letter codes (DAC, CAS, WEH). You'll see both;
they're the same people. `get_field_am_status` is the agent's code→car
directory.

**Before you write any code:** read [`HOW_IT_WORKS.md`](HOW_IT_WORKS.md)
— ten minutes on what a *frame* is, why there are two data worlds, what
makes the engineer decide to talk, and which files are yours versus
plumbing. It will save you an hour of reverse-engineering.

## Two minutes of Formula E

**The race:** Berlin E-Prix 2024 Round 10. 41 laps, ~48 minutes. Da Costa
(DAC, car 13, TAG Heuer Porsche) starts P10, carves to P3 by lap 5, and
wins. His main fights: Cassidy (CAS) — 11 position exchanges, the real
battle for the win — and Vergne (JEV), his grid neighbor. Two retirements
punctuate the story: Günther (car 7) on lap 10 and Fenestraz (car 23) on
lap 24.

**Attack Mode**, the strategic heart of Formula E:

- A fixed power boost (300 kW → 350 kW), earned by driving through an
  activation zone placed OFF the racing line (at Berlin: Turn 2) — taking
  it costs track position. When it's active, the car's halo glows
  magenta; everyone can see it.
- Every driver must use exactly TWO activations per race. The total boost
  time is 240 seconds, split per a pre-armed "scenario": 1 = 60s+180s,
  2 = 120s+120s, 3 = 180s+60s.
- An ARMING is declared intent (which scenario); an ACTIVATION is the
  actual deployment. Drivers re-arm as strategy evolves — DAC armed 9
  times this race, most in the field.
- Once activated it runs its full duration. No early exit. The clock
  burns even under safety car. This is why it's worth an AI engineer:
  fixed-duration power committed against an unknown future.
- On lap 3 of this race, about half the field activates within seconds —
  watch your position tower light up orange. DAC deliberately holds back.
- The move of this race, laps 7–9: DAC deliberately hands back the lead
  to take his short 60s activation, drops to P3, and repasses with the
  boost still lit — a planned sacrifice. An engineer that calls it as it
  happens earns its seat.

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

## Gemini Code Assist is sitting right there

The Cloud Shell Editor has Gemini Code Assist built in — use it.
Highlight the worked example and ask "explain how this tool reads the
race frame"; ask it to draft a docstring; ask why a type hint matters to
ADK.

One warning: Code Assist may suggest **ADK 2.0** APIs (GA since May 2026
— graph Workflow Runtime, new callback model). This lab is pinned to
**ADK 1.x**. If a suggestion or a doc page mentions *Workflow Runtime*,
*graphs*, or a *Task API*, you're reading 2.0 — back out. The worked
example in `starter/race_engineer/tools/frame_tools.py` is ground truth
for the patterns this repo uses.

## Learn ADK fast (curated, 1.x-safe)

- Function tools — plain Python functions; the docstring and type hints
  ARE the API the model sees:
  https://google.github.io/adk-docs/tools-custom/function-tools/
- Custom tools overview: https://google.github.io/adk-docs/tools-custom/
- Python quickstart (LlmAgent, runners):
  https://google.github.io/adk-docs/get-started/python/
- API reference: https://google.github.io/adk-docs/api-reference/python/
  — it now defaults to 2.0.0; trust the repo's worked example when they
  disagree.
- MCP Toolbox: https://mcp-toolbox.dev/documentation/introduction/ — our
  server runs v1.3.0 and the current docs describe the newer v2 config
  format, so when you touch `toolbox/tools.yaml`, copy the shape of the
  EXISTING tools in the file, not the docs.

---

# The build — six tiers, stop anywhere with something working

You build the agent twice, on purpose. Tiers A–C happen in a scaffold YOU
create from nothing — three files, your name on the folder — and every
tier ends with the agent failing in a new, instructive way. Tier D
graduates you into the production package, where the given plumbing turns
those failures off. Tiers E–F make the engineer yours: its voice, its
judgment. Budgets: A ~15 / B ~20 / C ~15 / D ~25 / E ~30 / F overflow —
about 95 minutes on the spine before persona. Each tier follows the same
scaffold: open this → do this → run this → what just happened (and why
that's the point).

## Tier A — Build an agent from nothing (~15 min)

**Open:** a terminal. There's no file to open — you're creating the folder.

**Your challenge:** scaffold a brand-new agent and give it a job.

> **WHERE:** Cloud Shell, repo root, activated
> **WHAT:**
> ```bash
> adk create my_engineer --model gemini-3.5-flash \
>     --project "$PROJECT_ID" --region global
> ```

Look at what you got: three files. `__init__.py` (one import), `.env`
(your project config), and `agent.py` — a `root_agent` with a model, a
name, a description, and an instruction. That is the entire anatomy of an
ADK agent. Everything you do for the rest of the day is editing this
shape.

Two edits before you run it:

1. **Move the words out of the wiring.** Create `my_engineer/prompts.py`,
   put `ROOT_AGENT_DESCRIPTION` and `ROOT_AGENT_INSTRUCTION` strings in
   it, and import them in `agent.py`. This is the exact layout the
   production package uses — agent.py is wiring, prompts.py is words.
2. **Write the instruction.** Make it a Formula E race engineer for
   Antonio Félix da Costa, car 13, TAG Heuer Porsche, Berlin E-Prix 2024
   Round 10 (Tempelhof, 41 laps) — concise and concrete, like a real
   engineer on the radio. Your words; the reference is
   `solution/scaffold/prompts.py` if you want a starting point.

**Test it:**

> **WHERE:** Cloud Shell, repo root, activated
> **WHAT:**
> ```bash
> adk web
> # open the URL it prints (or Web Preview), pick my_engineer
> ```

Ask these three, in this order:

1. *"Who won this race, and where did we finish?"*
2. *"What lap did we take our first attack mode, and which scenario did
   we arm?"*
3. *"What was Cassidy's energy consumption percentage on lap 7?"*

**What just happened (and why that's the point):** the first answer is
probably RIGHT — this race is famous and the model's training data knows
the headline. The other two are confident fiction: the real first
activation is the famous laps 7–9 move, the real scenario splits are
60+180 / 120+120 / 180+60 seconds, and no model on earth knows Cassidy's
lap-7 energy to a decimal. Now notice the delivery: identical. Same
confidence, same radio voice, true and invented indistinguishable. An
ungrounded model is a podcast, not an instrument.

**Done looks like:** your agent answering fluently in `adk web` — and you
unable to say which answers were real without checking.

**Checkpoint demo:** the side-by-side — one true headline, one invented
telemetry readout, same straight face.

## Tier B — Ground it: one tool, the whole lesson (~20 min)

**Open:** `my_engineer/agent.py`

**Your challenge:** write ONE tool from a blank line — a generic SQL
hatch into the recorded race — and register it. In ADK a tool is a plain
Python function, and **the docstring is the API**: Gemini reads it to
decide when to call your tool and what to pass. You are not writing
documentation; you are writing the model-facing interface.

Your `execute_race_sql(sql: str) -> dict` should:

- carry a docstring that names the dataset (`fe_race10`) and its tables
  (`drivers, startgrid, laps, attack, energy_per_lap,
  racecontrol_classified, event_stream, telemetry, top_speed_per_lap,
  career_driver, career_race`) — that's what lets the model write its
  first query without guessing,
- refuse anything that isn't a `SELECT`,
- run the query with `google.cloud.bigquery` (project from
  `GOOGLE_CLOUD_PROJECT`, already in your env) capped at ~100 rows,
- return rows as a list of dicts — and return errors as
  `{"error": str(e)}` instead of raising, so the model can read the
  failure and fix its own SQL.

Register it: `tools=[execute_race_sql]` on your `root_agent`. The
complete reference is `solution/scaffold/agent.py`.

**Test it** (restart `adk web`, same place):

1. *"What was our fastest lap of the race — lap number and time? We're
   car 13."* — watch the tool calls print: it discovers the schema by
   itself, then queries. Correct answer, seconds.
2. *"What was our top speed on our fastest lap?"* — watch closely. It
   hits a column that reads 0, gets suspicious, and recovers through
   `top_speed_per_lap`. Real data lies; the schema won't tell you.
3. *"Who is directly behind us right now?"*

**What just happened:** question 3 came back confident, named a real
driver, even gave a gap — and it read the FINAL LAP. BigQuery holds the
whole recorded 2024 race; your agent has no concept of *now*, so "right
now" silently means "at the end." Grounded is not the same as honest
about time. Keep that wound open — Tier D heals it.

One more thing: at this checkpoint the instructor will put one question
to a Tier B agent from the front of the room — the Vergne overtake count
— and the answer is a small masterpiece of grounded-and-wrong. Ask it
yourself too (it's in the question bank), and remember what your agent
says. You'll ask again in fifteen minutes.

**Done looks like:** grounded answers with visible tool chains — plus a
healthy new distrust of the phrase "right now."

**Checkpoint demo:** the fastest lap and the top-speed recovery, tool
calls printing live.

## Tier C — Curate it: wire the Toolbox (~15 min)

**Open:** `my_engineer/agent.py` again.

**Your challenge:** one construction — a `ToolboxToolset` pointing at
your deployed fe-toolbox — and your agent gains 14 curated BigQuery
tools: lap history, energy curves, overtakes, race control, career
stats, plus schema discovery and a SQL escape hatch.

```python
from google.adk.tools.toolbox_toolset import ToolboxToolset
```

Read `TOOLBOX_URL` from the environment and **fail fast** if it's
missing (raise a `RuntimeError` telling the user to `source activate.sh`
— a None URL must not survive to become a cryptic connection error
later). Then:

```python
toolbox_tools = ToolboxToolset(
    server_url=TOOLBOX_URL.rstrip("/"),
    toolset_name="race-engineer",
)
```

Construction is lazy — no network at import time. Put `toolbox_tools` in
your tools list, and **retire `execute_race_sql`** from it. Your
prototype is superseded; your escape hatch survives *inside* the toolbox
as `execute_sql_bq` — now wearing the data-semantics warnings your raw
tool proved necessary.

**Test it** (restart `adk web`):

1. *"How many times did we overtake Vergne? We're car 13, he's car 25."*
   — the question from the Tier B set-piece, now answered through
   `get_overtakes_involving`. That curated tool exists because the raw
   `event_stream` carries the subject's GRID POSITION in `car_number` —
   a trap your Tier B agent fell straight into while explaining away the
   contradicting rows as "telemetry glitches." Curated tools encode the
   semantics the schema can't tell you. That is the whole argument for
   them, demonstrated.
2. *"Who is directly behind us right now?"* — still the final lap.
   Curation fixed correctness on history. It cannot invent a live feed.

**Done looks like:** the Vergne question answered correctly, fast, in
one tool call.

**Checkpoint demo:** same question, Tier B answer vs Tier C answer, side
by side.

## Tier D — Go live: graduate to the production package (~25 min)

**Open:** `starter/race_engineer/` — the production chassis. Your
scaffold retires here with honor; everything it taught you reappears in
a grown-up shape (agent.py wiring, prompts.py words, tools/ folder).

Three moves:

1. **Read `tools/frame_tools.py`.** It is COMPLETE and it is the best
   ADK reading in the repo: four live-state tools against Firestore.
   Read `get_current_state` top to bottom first — every mechanic you
   used in Tier B, commented. Then the `AgentEvent` docstring: the
   repo's best bug story (the model once stole a replay-clock timestamp
   and queried the future — the same future-leak you met in Tier B,
   caught and caged). Then the clock bridge: `race_wall_time_ns` is the
   ONLY valid "up to now" value the BigQuery tools accept.
2. **Wire the toolbox — `TODO(D)` in `agent.py`.** The exact
   construction you wrote in Tier C, now in the production package.
   Five minutes; the spec is in the comments.
3. **Verify, then light the wall.**

> **WHERE:** Cloud Shell, repo root, activated
> **WHAT:**
> ```bash
> python scripts/test_frame_tools.py --live   # given tools vs live replay — all ✓
> python scripts/agent_chat.py
> ```
> Ask: *"Who is directly behind us right now?"* — your first TRUE now.
> Then: *"Compare our pace to Wehrlein over the last 5 laps."* (the money
> question — watch it call `get_current_state` for "now", bridge the
> clock, then query history)

> **WHERE:** Cloud Shell, repo root (any tab — it sources activate.sh itself)
> **WHAT:**
> ```bash
> bash demo.sh
> # click the URL uvicorn prints (or Web Preview → port 8080)
> # click 🔇 to enable audio; RESTART on the SIM bar; 2× is a good build speed
> ```

**What just happened:** two worlds, one agent. The frame tools are the
live "now" (Firestore); the toolbox is the recorded "then" (BigQuery);
`race_wall_time_ns` is the bridge between their clocks. Every lie from
Tiers A–C now has a named fix you can point at.

**Done looks like:** the now-question answered truthfully, the Wehrlein
fusion working, and the pit wall lit.

**Checkpoint demo:** *"Who is directly behind us right now?"* at the pit
wall — compare it to what Tier B said.

## Tier E — Persona: make it sound like a race engineer (~30 min)

**Open this file:** `starter/race_engineer/prompts.py` — the `_VOICE` and
`_CALL_TYPES` sections. Everything else is GIVEN and marked so.

**Your challenge:** as shipped, your agent talks like a database. Write
the voice (second person to Antonio, 6–8 second calls, concrete
instructions or none, no markdown, no cheerleading), then the three call
templates: event reaction, end-of-lap summary, driver Q&A.

**What you need to know first:**

- The TODO comments above each section are your spec — they list every
  rule the reference enforces.
- The GIVEN sections (TTS normalization, data discipline, doctrine,
  honesty) are hard-won; read them, don't rewrite them.
- One warning from the build: example phrases you write become the
  model's vocabulary — they WILL come back out of the speaker. Choose
  examples you'd be happy to hear on stage.

**Done looks like:** the engineer sounds like a person you'd trust on
the radio, out loud.

> **WHERE:** Cloud Shell, repo root (any tab — it sources activate.sh itself)
> **WHAT:**
> ```bash
> bash demo.sh
> # click the URL uvicorn prints (or Web Preview → port 8080)
> # click 🔇 to enable audio (the click unlocks it); RESTART on the SIM
> # bar; 2× is a good build speed
> ```

**Checkpoint demo:** lap 3. Half the field takes attack mode, your
scorer fires, and your engineer — in YOUR voice — explains it out loud.
Then hold SPACE and ask a question with your actual voice. That's the
moment.

## Tier F — Make the engineer yours (overflow / team stretch)

**Open this file:** `shared/scorer.py` (the weights table at the top) —
plus `toolbox/tools.yaml` for the missing-tool challenge.

**Your challenge(s),** in rising ambition:

- **Tune the dials:** every weight is a named constant — overtake
  urgency, AM cluster threshold, race-control severities — plus the
  loop's debounce and must-say gap. Make your engineer chattier, calmer,
  more paranoid about rivals.
- **Build the arming rule:** the scorer doesn't react to ARMING events
  at all — strategic intent ("Cassidy just armed scenario 3 — he's going
  long") is invisible to it today. The data is there (`get_am_armings`,
  and arming events flow through the event stream). Write the rule, pick
  its weight, decide if it's must-say.
- **Add the missing tool:** the toolbox has no name → car-number lookup,
  so the prompt steers the model around it. Add a curated
  `lookup_driver` to `toolbox/tools.yaml` — copy the shape of an
  existing tool: `drivers` JOIN `startgrid`, matching
  `UPPER(driver_last_name)` OR `driver_short_name`. Redeploy with
  `bash setup/3_deploy_toolbox.sh`, then trim the name-steering from the
  prompt and watch the tool chains get shorter. Heads-up:
  `setup/verify.sh` expects exactly 14 tools, so your 15th flags ✗ there
  — expected, not broken.

**What you need to know first:** the trigger system is given and
pre-tuned. A deterministic scorer decides WHEN the engineer speaks; the
model only decides WHAT to say. The scorer is pure (no I/O, no clocks);
the loop in the frontend owns debounce and scheduling. HOW_IT_WORKS.md
has the full picture.

**Done looks like:** your tuned engineer's judgment, visible in the
negative space — what it now speaks on, and what it stays quiet about.

> **WHERE:** Cloud Shell, repo root, activated
> **WHAT:**
> ```bash
> python scripts/local_test.py --duration 380 --verbose
> # --verbose shows suppressed and below-threshold moments — the
> # negative space your tuning controls
> ```

**Checkpoint demo:** a trigger YOU created (or re-weighted) firing live.

## Working as a team

Three lanes, three test scripts — and because the production package
runs as shipped, two of them can start the moment setup is green:

| Lane | You own | Validator | Needs first |
|---|---|---|---|
| **Spine** (A–D) | `my_engineer/`, then the `TODO(D)` in `starter/.../agent.py` | `adk web`, then `python scripts/agent_chat.py` | setup green |
| **Persona** (E) | `starter/.../prompts.py` | `bash demo.sh` | nothing — the starter runs as shipped; start immediately |
| **Triggers** (F) | scorer weights + the arming rule | `python scripts/local_test.py --verbose` | nothing — independent of the spine |

The spine is deliberately serial — its tiers motivate each other — so on
a team, ONE person drives it while the others take Persona and Triggers
and read `HOW_IT_WORKS.md` + `frame_tools.py` between turns. Swap the
driver at each tier if you like; every tier is a clean handoff point.

**Integration ritual** (10 minutes, mid-afternoon): spine reaches Tier D
→ one fused question in `agent_chat.py` (the Wehrlein pace comparison) →
`bash demo.sh` and let it talk through lap 3 in the Persona lane's voice.
Three passes = your lanes merged.

## Question bank (for your demos)

| Ask | World | What it proves |
|---|---|---|
| "Who's directly behind us, and does he have attack mode left?" | Now | instant Firestore state |
| "What's the field looking like at the front?" | Now | full-field awareness |
| "What was our fastest lap?" | Then | BigQuery research |
| "Any race control messages I should know about?" | Then | event history |
| "Who's driving car 94, and how's his race going?" | Then | identity + career fusion |
| "How's our energy versus Cassidy — gaining or losing?" | Both | the money question: live state + consumption history, fused |
| "Compare our pace to Wehrlein over the last 5 laps." | Both | clock bridge + history |
| "Should we take our second attack mode now, or wait?" | Both | scenario judgment |
| "How many times did we overtake Vergne? We're car 13, he's car 25." | Then | **the set-piece**: a Tier B agent answers this wrong with a straight face (raw SQL meets the grid-ID trap); Tier C answers it right. Ask both and compare. |
| "Who won this race?" | Training data | the Tier A lesson — it knows headlines, it invents telemetry. (Post-Tier-D, the production prompt is time-honest about it.) |
| "What's the weather looking like?" | Neither | **the honesty test** — the right answer is a clean refusal. No tool has weather; an engineer that admits what it doesn't know is the one you trust on what it does. |

## When things go sideways

| Symptom | Likely cause | Fix |
|---|---|---|
| `adk web` doesn't list `my_engineer` | You created it outside the repo root | Re-run `adk create` from the repo root |
| Scaffold tool fails on `GOOGLE_CLOUD_PROJECT` | New tab, not activated | `source activate.sh`, restart `adk web` |
| Script complains about env/venv | New tab, not activated | `source activate.sh` |
| EVERYTHING on the local pit wall 503s | Cloud Shell session recycled; your exports are gone | Relaunch with `bash demo.sh` — it re-sources everything itself |
| Tower empty, no state | Sim not publishing / fresh reset | RESTART on the SIM bar |
| Calls dropped, log mentions limit | Tool-budget ceiling did its job | Fine in moderation; if constant, your prompt is sending the agent wandering |
| Q&A answers feel stale or reference the previous race | Long Q&A session | RESTART the sim — the session rotates with the race |
| Agent answers feel stale at 5× | The world moves while it thinks | Build at 2×; savor at 1× |
| No audio | Browser autoplay policy | Click the 🔇 toggle — the click is the unlock |
| Engineer invents a driver name | It shouldn't — the HONESTY section forbids it | If you removed that section, put it back |
| Totally stuck | — | Same filename in `solution/` — that's what it's for |

## Finished early?

Open **BONUS.md** — a board of additive tickets (voice picker, tool-call
observability panel, post-race debrief, deploying YOUR agent to a public
URL), sized S/M/L. Nothing on it can break what you already demo.

Now go build. Antonio's waiting on the radio.
