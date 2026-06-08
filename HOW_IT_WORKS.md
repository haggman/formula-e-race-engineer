# How it works — the ten-minute orientation

Read this before editing code. It answers the questions the codebase
assumes you've already asked: what a frame is, why there are two data
stores, what makes the engineer decide to talk, and which files are yours
versus plumbing. Python knowledge assumed; nothing else.

## The system in one paragraph

A recorded Formula E race replays through your project as if live. A
**simulator** publishes one JSON *frame* per race-second to Pub/Sub; a
**State Writer** turns each frame into Firestore documents — that's the
"now." The same race's full timing history sits in **BigQuery** behind an
**MCP Toolbox** of 14 query tools — that's the "then." Your **agent**
(Google ADK + Gemini) reads both. A **pit-wall frontend** in your Cloud
Shell renders the live race, runs a deterministic *scorer* that decides
when something deserves a radio call, fires your agent to write the call,
speaks it aloud (Chirp TTS), and takes spoken questions (Chirp STT).

## What is a frame?

One snapshot of the entire race at one race-second, shaped like this
(heavily trimmed):

```json
{
  "race_time_s": 193,
  "race_phase": "racing",
  "cars": [
    {"car_number": 13, "driver_short_name": "DAC", "position": 6,
     "current_lap": 3, "speed_kmh": 140.3,
     "energy": {"pct_remaining": 93.05},
     "attack_mode": {"active": false, "activations_used": 0,
                     "scenario": 2, "remaining_budget_s": 240.0}},
    "... 21 more cars ..."
  ],
  "events": [
    {"type": "overtake", "car_number": 13, "...": "..."}
  ]
}
```

The simulator emits ~2,900 of these, t=−10 (pre-race grid) to a few
seconds past the chequered flag. The State Writer splits each one in two:

- the whole frame overwrites **one** Firestore doc,
  `race_states/berlin_2024_r10` — *the current state of the world*;
- each item in `events[]` becomes its own doc in `race_events/` —
  *the queryable recent past*.

Writes are idempotent (deterministic event IDs), so replays and Pub/Sub
redelivery converge instead of duplicating. Curl `$SIM_URL/schema` any
time to see a real, complete frame.

## The two worlds, and the clock bridge

| | **Now** (Firestore) | **Then** (BigQuery) |
|---|---|---|
| What | Current RaceState + recent events | Every lap, overtake, AM event, energy curve, RC message, plus 10 seasons of careers |
| Reached via | the **frame tools** (given — your Tier D reading) | **MCP Toolbox** tools (wired once, in Tier C — the wiring rides to the wall) |
| Clock | `race_time_s` — seconds since the green flag | INT64 **nanoseconds since epoch, on the original 2024 race's wall clock** |

Those two clocks are the most important subtlety in the repo. To ask
BigQuery for "history up to now," the agent must translate the replay's
current moment into 2024 wall-clock nanoseconds. Your frame tools do that
translation: `get_current_state` returns `race_wall_time_ns`, computed
from a fixed constant (`RACE_START_EPOCH_NS`, the exact green-flag
instant). The agent passes that value as `through_time_ns` to history
tools — and the prompt forbids every other timestamp source, because the
model genuinely invented timestamps until it was forbidden. This is also
what makes the agent *time-honest*: ask about lap 20 on lap 8 and the
history tools simply haven't seen it yet.

## What makes the engineer talk

The LLM **never decides when to speak.** A deterministic loop in the
frontend does, on a strict poll → score → fire cycle:

1. **Poll** Firestore every ~2s: current state + events since last check.
2. **Score** the moment with `shared/scorer.py` — pure, deterministic
   rules with named weights (our overtakes 80–90, our AM transitions
   75–85, field AM cluster 75, neighbor AM 65, race control by severity).
   Same inputs, same output, always.
3. **Fire** the agent only when the best candidate clears a threshold
   (60) *and* a debounce window (15s wall-clock) — one call at a time;
   an engineer has one mouth.

Four call types reach the radio log:

| Type | Triggered by | Notes |
|---|---|---|
| `event` | a scored moment over threshold, outside debounce | |
| `lap_summary` | every N laps (owed summaries are sticky) | |
| `must_say` | our own AM transitions, critical race control | pierces debounce; HELD until a gap opens; expires after 25s (a late radio call is worse than none) |
| Q&A | a human asked | never gated; bigger tool budget |

Proactive calls run in a **fresh agent session** carrying a *snapshot* of
the triggering instant in the prompt — at replay speed the world moves
while the model thinks, so the snapshot is authoritative and the call
needs at most two history-tool lookups (a hard per-call LLM budget
enforces it; breaches are dropped, not delivered late). Q&A runs in a
**persistent session** so follow-ups keep context — rotated automatically
when the race restarts, so a new race never inherits the old one's
history. Failures of any call are dropped with a cooldown; the loop
never crashes because one call did.

## The journey of one question

You hold SPACE and ask "who's behind us?" → the browser records audio →
`POST /api/stt` → **Chirp STT** returns the transcript (visibly, in the
ask bar — you catch a mangled name before the agent does) → the question
goes over the **websocket** → the engineer loop's persistent Q&A session
→ the **agent** picks its tools (here: one `get_current_state` call) →
the answer broadcasts to every connected browser → **Chirp TTS**
synthesizes it server-side → it plays through a one-mouth sequential
audio queue, atomically with its text in the radio log.

Every panel you see rides the same websocket: a state poller broadcasts
the full field at 1 Hz (the tower, the gauges), and radio calls
interleave as they happen.

## The file map

**YOURS — the six tiers:**

| Tier | File | What you do there |
|---|---|---|
| A–C | `starter/race_engineer/agent.py` (Tier A creates it, in place, via `adk create`) | build your agent around the given chassis: Gen-1 prompt inline, one raw SQL tool, then the Toolbox |
| D | the same `agent.py` (+ `tools/frame_tools.py` as reading) | adopt the given parts: register the frame tools, link the production prompt (Gen 2) |
| E | `starter/race_engineer/prompts.py` | write `_VOICE` and `_CALL_TYPES` |
| F | `shared/scorer.py` (+ `toolbox/tools.yaml`) | tune weights, add the arming rule, add a tool |

**READ THESE — given, but worth your time:**

- `starter/race_engineer/prompts.py`, the GIVEN sections — every rule in
  DATA DISCIPLINE and HONESTY exists because the model broke without it.
- `starter/race_engineer/tools/frame_tools.py` — all four tools,
  complete; the worked example and the `AgentEvent` docstring are the
  repo's ADK patterns and its best bug story.
- `shared/models.py` — the Pydantic contract for RaceState/Event; the
  single source of truth both the State Writer and your tools share.
- `toolbox/tools.yaml` — what the 14 BigQuery tools actually run; the
  tool *descriptions* are half the engineering.

**PLUMBING — works, ignore unless curious:**

`frontend/` (UI, engineer loop, TTS/STT, the agent-client seam) ·
`state_writer/` · `simulator/` · `setup/` and `deploy/` (idempotent
provisioning) · `scripts/` (your test harnesses — run them, don't edit
them) · `notebooks/` (one-time BigQuery loading) ·
`solution/race_engineer/` (the answer key).

## Five facts that will save you a debugging hour

1. **Every new Cloud Shell tab needs `source activate.sh`.** Env/venv
   complaints are always this.
2. **The docstring IS the API.** Gemini decides when to call your tool
   and what to pass by reading your docstring and type hints.
3. **ADK doesn't coerce enums.** JSON args arrive as strings; coerce
   inside the tool (`_coerce_event_types` is the given pattern).
4. **Never hand the model a timestamp it can misuse.** That's why events
   are wrapped in `AgentEvent` (which hides the replay machine's clock)
   and why `race_wall_time_ns` is the only blessed bridge value.
5. **Build at 2×, demo at 1×.** At 5× the world outruns the model's
   thinking — answers aren't wrong, just stale.
