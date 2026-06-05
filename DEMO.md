# Demo Guide — The Race Engineer

How to demonstrate this system, what to ask it, and why the answers are
impressive. The README covers building and running; this covers *showing*.

## What you are looking at, in one paragraph

A live Formula E race (Berlin 2024, round 10) replays through Pub/Sub into
Firestore, giving the system a "now." The full timing history of the same
race sits in BigQuery, giving it a "then." An ADK agent — the race engineer
for car 13, António Félix da Costa — watches the now, decides for itself
when something deserves a radio call (a deterministic scorer, not the LLM,
makes that call), and answers questions by reaching into either world, or
both, choosing its own tools. Everything it says is grounded in retrieved
data, spoken aloud, and visible in the pit-wall UI.

## The two worlds — the core idea to teach

Every question the engineer answers draws on one or both of:

| World | Store | Tools | Latency | Example |
|---|---|---|---|---|
| **Now** | Firestore (written live by the State Writer) | `get_current_state`, field AM status, recent events | instant | "Who is behind us?" |
| **Then** | BigQuery (full race history) | lap history, energy curves, overtakes, race control, raw SQL | seconds | "What was our fastest lap?" |

The agent decides which world a question needs. The best demo questions
**silently span both** — that is the tool-orchestration story this
hackathon is selling, and it happens without the user specifying anything.

A detail worth saying out loud: the agent is *time-honest*. History tools
only return events up to the replay's current moment — ask about lap 20
while the race is on lap 8 and the engineer doesn't know yet.

## Running the demo

```bash
# Terminal 1 — from the repo root
source activate.sh
export SIM_URL=$(gcloud run services describe fe-simulator \
    --region=$REGION --format='value(status.url)')
uvicorn frontend.main:app --host 0.0.0.0 --port 8080
# open Web Preview on 8080
```

In the browser: click 🔇 MUTED to enable audio (browsers require the
click), set speed to 1× for a live audience, hit RESTART on the SIM bar.

The SIM bar is your stage controls: **RESTART** rewinds to the grid,
**PAUSE/RESUME** freezes the race (the engineer's "now" freezes with it —
use this), speed trades realism for pace, **LOOP** keeps it running
between sessions.

## The scripted moments (laps 1–11)

These happen on their own — your job is to not talk over them:

1. **Opening shuffle (laps 1–2).** DAC starts P10; early overtake calls
   establish the voice.
2. **The attack-mode cluster (lap 3).** Half the field arms attack mode
   within seconds. Watch the orange AM badges light the tower while the
   engineer reports it as ONE coherent call — including who *didn't* take
   it. A naive system would fire 12 alerts.
3. **The climb (laps 5–7).** P6 → P3 → P2 → P1, with position-delta
   badges and battle calls.
4. **The attack-loop detour (laps 7–9).** Leading, DAC activates attack
   mode (a must-say call with the correct 60-second duration), drops to
   P3 through the off-line activation loop, recovers. The engineer
   narrates the position sacrifice correctly in real time.
5. **Second activation (lap 10–11).** "3 minutes" — it knows the two
   activations have different durations (scenario rules), and it knows
   which one this is.

## Attack Mode in sixty seconds (you will be asked)

The rules that make it a strategy problem — and demo material:

- **What it is:** a fixed power boost (300 kW race power → 350 kW), granted
  by driving through a marked **activation zone** placed OFF the racing
  line. Taking it costs a second or two of track position — watch laps
  7–9: DAC leads, takes the loop, emerges P3, repasses with the boost.
  The engineer narrates that sacrifice correctly in real time.
- **Exactly two, mandatory:** every driver must take two activations per
  race — no more, no fewer; skipping one is a penalty.
- **Fixed durations, no early exit:** the FIA sets the event's total
  Attack Mode time and the legal splits; the team commits to one (the
  "scenario" in the radio calls — car 13 ran 60s + 180s at Berlin). Once
  activated it runs its full duration and ends automatically. You cannot
  switch it off after 10 seconds because the move worked. This is why
  it's worth an AI engineer: fixed-duration power committed against an
  unknown future.
- **The clock doesn't care:** Attack Mode keeps burning under safety car —
  activating just before an SC is the classic disaster.
- **Everyone can see it:** the halo glows magenta when active (the orange
  AM badges in our tower are the same signal). A rival in Attack Mode
  behind you is a different threat — which is why the engineer calls out
  neighbors' activations.
- **The radio pattern:** the driver activates; the pit wall sees it in
  telemetry and confirms with context — "attack mode is active, 180
  seconds" (which activation, what window), "Wehrlein has used both of
  his activations" (no counter-attack coming), "push now to pull a gap"
  (the strategic conclusion). Three facts and an instruction, six
  seconds, two data sources.

## Question bank

Ask during a pause or between calls. Grouped by what each demonstrates.

**Pure "now" — instant, Firestore only**
- "Who's directly behind us, and does he have attack mode left?"
- "What's the field looking like at the front?"

**Pure "then" — BigQuery research**
- "What was our fastest lap so far?"
- "How many times have we traded places with Vergne today?"
  (The answer is a lot — they started side by side. Real finding from
  this dataset.)
- "Any race control messages I should know about?"

**Both worlds fused — the money questions**
- "How's our energy versus Cassidy — are we gaining or losing?"
  (Current state + consumption history in one answer.)
- "Compare our pace to Wehrlein over the last 5 laps."

**Doctrine and judgment**
- "Should we take our second attack mode now, or wait?"
  (Scenario reasoning: traffic, rivals' remaining activations, energy.)
- "Explain our attack mode scenario." (It knows the split and which
  activation is still in hand.)

**Identity and color**
- "Who's driving car 94, and how's his race going?"

**The honesty test — do this one for skeptics**
- "What's the weather looking like?"
  The engineer declines: no tool has weather, so it says so instead of
  inventing. Showing what it *won't* make up is as persuasive as what it
  answers. Same honesty applies to time-gaps in seconds (it has positions
  and lap times, not gap telemetry — it will say "closing", not "1.4
  seconds").

**Choreography tip:** pause the sim mid-cluster on lap 3, ask two
questions into the frozen moment, then resume. The freeze gives the
audience time to absorb, and proves "now" and "then" are genuinely
different stores.

## Why this is hard (talking points for students)

- **The LLM never decides when to talk.** A deterministic scorer
  (shared/scorer.py) watches events and fires the agent only on moments
  that clear a threshold — with must-say events (our attack mode,
  critical race control) piercing the normal debounce. Separating
  *when to speak* (code) from *what to say* (model) is the architecture
  lesson.
- **Triggers carry their moment with them.** Each proactive call embeds
  a snapshot of the triggering instant, because at replay speed the
  world moves while the model thinks. Tool budgets are enforced three
  ways (prompt, hard LLM-call ceiling, drop-on-breach) — a late radio
  call is worse than none.
- **Every name and number comes from a tool.** The persona forbids
  invented drivers, gaps, and facts; unknown car numbers stay numbers.
- **The data fought back.** The source overtake stream encodes the
  subject's *grid position* in a field named `car_number` while the other
  participant is a real car number — two ID domains in one record. Found
  by position-adjacency scoring, fixed end to end. Ask the instructors
  about it; it is the best gotcha in the dataset.

## Security posture (you will be asked)

The Toolbox endpoint is public. That's a decision, not an oversight — and
the reasoning is the teaching point. Security effort should be proportional
to what's at risk: every Toolbox tool is a read-only SELECT over public
2024 sports data, in an ephemeral lab project, behind an unguessable URL.
Worst case, a stranger spends pennies of BigQuery scan. Compare the State
Writer, where an unauthenticated caller could corrupt race state — so THAT
service got locked down (OIDC-authenticated Pub/Sub push, no public
ingress). Same stack, two postures, each matched to its threat model. The
production lockdown recipe lives in a comment at the top of
`toolbox/tools.yaml`.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| UI loads, tower empty | No state doc in Firestore (fresh/reset) | RESTART the sim; data appears in seconds |
| "sim:" error in the SIM bar | SIM_URL not exported in the uvicorn shell | export it (see Running) and restart uvicorn |
| Calls drop, log says 429 | Gemini quota under replay pressure | run at 1–2×; drops self-heal (5s cooldown) |
| No audio | Browser autoplay policy | click the 🔇 toggle — the click unlocks audio |
| Engineer silent, state moving | engineer loop crashed at startup | check the uvicorn terminal for the traceback |