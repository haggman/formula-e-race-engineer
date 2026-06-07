# Run of Show — Formula E Race Engineer hackathon (3 hours)

**Who this is for:** the person delivering the event — written assuming that
person is NOT the author. Every segment gives you three layers: **SAY**
(lines that work — use them or yours), **SHOW** (what's on the projector),
**WHY** (what the beat is for, so you can improvise without breaking it).
Students drive themselves from `STUDENT_GUIDE.md`; your job is the opening
20 minutes, the checkpoints, and the wrap.

**The one thing students need from you on a board/slide:** the tinyurl to
the rendered STUDENT_GUIDE on GitHub. `TINYURL: https://tinyurl.com/FE-Hack-2`

## The day at a glance

| When | What |
|---|---|
| −1:00 | Your morning-of setup (below) — done before doors |
| 0:00–0:20 | The opening (scripted below) |
| 0:20–2:40 | Students build Tier A→D; you circulate (checkpoint beats below) |
| 2:40–3:00 | The wrap: volunteer demos + debrief |

## Morning-of: build the instructor stack

You need: the data plane, the deployed engine, and the public pit-wall URL
— in YOUR instructor project (students get their own fresh projects).

> **WHERE:** instructor project's Cloud Shell, home dir
> **WHAT:**
> ```bash
> git clone https://github.com/haggman/formula-e-race-engineer.git
> cd formula-e-race-engineer
> source activate.sh
> bash setup/all.sh              # data plane: budget 20 min, ~10 typical
> bash setup/7_deploy_cloud.sh   # engine + public pit wall: budget 10
> python scripts/engine_smoke.py # one real call through the deployed engine
> ```

Measured timings (fresh resourced project, 2026-06-06):

| Step | Measured | Notes |
|---|---|---|
| `setup/all.sh` (steps 1–6 + verify) | ~10 min typical, budget 20 | Firestore index builds are the variable. "…IAM can't see SA yet — retry N/6" lines during steps 3/5/6 are NORMAL on a fresh project (new-SA propagation), not failures. |
| `setup/7_deploy_cloud.sh` | **8m 14s** first-create | Engine create **5m 32s** — and it is SILENT; the script prints a log-watch one-liner, open it in a second tab so the silence has a heartbeat. Frontend build+deploy **2m 42s**. Reruns (engine update) are faster. |

The script ends by printing the public pit-wall URL — that URL goes on the
projector. **One-engineer-per-pool rule:** from the moment fe-frontend is
deployed, its engineer loop is live and talking. Do not run `demo.sh`
locally in this project while it stands — two engineers on one quota pool
double-call every moment and can trigger retry storms. (Students are in
their own projects; this rule is about YOUR project only.)

## Pre-flight (15 min before doors, on the projector machine)

1. Tinyurl on the board. Deployed pit-wall URL open in the browser.
2. **Audio unlock:** click the 🔇 toggle (the click IS the unlock — browser
   autoplay policy) and confirm you HEAR one radio call over the room
   speakers, at the back of the room.
3. **Mic grant:** hold SPACE, ask anything, confirm the browser granted the
   microphone and the transcript appeared in the ask bar.
4. **SIM bar:** speed **2×**, **LOOP off**, then **RESTART**. RESTART
   resets the replay to the grid AND rotates the engineer's Q&A session —
   a fresh race with no memory of the previous one. *(Belt-and-braces only
   if Q&A ever acts haunted by a past race: bounce the frontend —
   `gcloud run services update fe-frontend --region=$REGION
   --update-env-vars=SESSION_RESET=$(date +%s)` — but RESTART alone is the
   designed reset.)*
5. **Warm-up question:** ask one throwaway ("where are we?") and let it
   answer. The first ask after a deploy is the slowest one (the persistent
   session is created inline on first use); don't let that slow ask happen
   during your demo. The Q&A meta line shows wall seconds — typical asks
   land single-digit; fused two-world questions ~10–13s.
6. **PAUSE** on the grid. You're set. Do not press **FINISH** — it exists
   (jumps the replay to the chequered flag, used by the post-race BONUS
   ticket) but it is not part of your show.

## The opening 20 minutes

| Clock | Segment | Immovable beat |
|---|---|---|
| 0:00–2:00 | Students start engines | the Step-0 paste is on student screens by 2:00 |
| 2:00–4:00 | Frame it | |
| 4:00–10:00 | The demo | lap-3 cluster lands audibly as ONE call |
| 10:00–15:00 | What you have | diagram walkthrough |
| 15:00–19:00 | Goals + tiers | answer-key policy said OUT LOUD |
| 19:00–20:00 | Logistics | |

*(Rehearsed 2026-06-06: demo comfortably done by 10:00 at these speeds.)*

### 0:00–2:00 — Students start engines

**SAY:** "Before I say anything about what we're doing: open the link on
the board, do Step 0 at the top — four lines of paste into Cloud Shell —
and come right back. It deploys your personal race-data plane in the
background while we talk. Go."
**SHOW:** the tinyurl, big.
**WHY:** the setup script needs ~10 unattended minutes; starting it at
minute 0 means it's green before anyone needs it. **Walk the room and
glance at screens** — every minute a student's paste didn't happen at 0:00
is a minute they wait later. The guide tells them to STOP after pasting and
look up; trust it.

### 2:00–4:00 — Frame it

**SAY:** "That thing you just deployed is replaying a real Formula E race —
Berlin 2024, every lap, every overtake, 1.28 million telemetry samples.
Today you build the AI race engineer that rides along: it watches live
telemetry, decides FOR ITSELF when something deserves a radio call, answers
your spoken questions from live state and race history, and talks back.
The hard part isn't getting an AI to talk about a race — it's getting it to
know when NOT to. A naive system fires twelve alerts a lap and gets muted
by lap three. The engineer you can trust is the one that's quiet until it
matters."
**SHOW:** the paused pit wall on the grid.
**WHY:** the negative-space idea (deterministic triggers, model writes the
words but never decides when) is the architecture's whole thesis — plant it
before they see code.

### 4:00–10:00 — The demo (the finished thing they're building)

Un-PAUSE at 2×. Talk over laps 1–2: the tower, the gauges, da Costa P10 on
a charge. **When the lap counter reads 2 and the track ring is past
halfway, drop speed to 1×** — you want real-time pacing before the lap-3
moment. *(Event-morning confirm: that drop lands before the first attack-
mode badge lights; at rehearsal the cluster fired as one clean call.)*

The lap-3 beat: about half the field takes attack mode within seconds —
the tower lights up orange. **SAY nothing. Let the engineer call it.** One
radio call summarizing a field-wide event. Then: "Count what just happened:
ten cars changed state and you heard ONE call. A scorer decided that
moment cleared the bar; the model only wrote the sentence."

PAUSE. Three questions, in this order:
1. **Typed, two-world fusion:** "How's our energy versus Cassidy — gaining
   or losing?" — narrate the tool calls in the log: live state, then
   history, then the math. "No tool answers that question. It planned."
2. **Voice:** hold SPACE, ask "who's directly behind us?" — the room hears
   the spoken answer.
3. **The honesty test:** "What's the weather looking like?" — it declines.
   "An engineer that admits what it doesn't know is the one you trust on
   what it does."

Then tell-don't-show the laps 7–9 attack loop: "Around lap 7 da Costa does
something that looks insane — he hands back the LEAD, on purpose, to take
his attack mode, drops to P3, and repasses with the boost still lit. Your
engineer will narrate that sacrifice live. You'll see it during the build —
we're not waiting for it now."
**WHY:** cluster = triggers; fusion = two worlds; voice = the wow; weather
= honesty doctrine; attack loop = the story carrot.

### 10:00–15:00 — What you have

**SHOW:** `docs/architecture.svg`, full screen.
**SAY**, walking left to right: "Left column — given, deployed, you just
did it in Step 0: a simulator replaying the race at up to 5×, publishing a
snapshot of all 22 cars every race-second; a writer turning those into a
live 'now' in Firestore. Bottom right — also given: the same race's full
history, plus ten seasons of careers, in BigQuery behind fourteen query
tools. Right column — given: this pit wall, the voice loop, and the trigger
system that decides when to speak. The middle column is YOURS: the agent.
Four surfaces, Tier A through D — teach it to see, give it a memory, give
it a voice, tune its judgment. Each tier ends with something you can demo."
**WHY:** ownership boundaries kill the #1 time-sink (reverse-engineering
the plumbing). Point at file paths on the cards — they're real.

### 15:00–19:00 — Goals + tiers

**SAY:** "Tier A, about forty minutes: three frame tools — there's a worked
example, the patterns are all in it. Tier B, forty-five: one construction
wires in fourteen BigQuery tools, and that's when two-world questions start
working. Tier C, thirty: the persona — your engineer, your voice, out loud.
Tier D is yours to play: trigger weights, a new strategic rule, a missing
tool. Stop anywhere and you still demo something real. Teams: there's a
lanes table — persona can start immediately, don't serialize.

And hear this clearly: `solution/` is the answer key, same layout file for
file, and using it is SHIPPING, not cheating. Stuck ten minutes? Open the
same filename, read, move on. You learn more from shipping than from
suffering."
**WHY:** the answer-key policy spoken aloud is the single best protector of
room energy. Don't skip it.

### 19:00–20:00 — Logistics

**SAY:** "Guide's at the link — Step 0 is done, pick up at 'Welcome back'.
Read HOW_IT_WORKS.md before you code; it's ten minutes and it'll save you
an hour. Verify your setup is green, build at 2×, and if you finish, the
BONUS board is waiting. Questions come to me or to Gemini Code Assist —
it's in your editor. Go build."

## During the build — your moves

- **First 15 min:** sweep for `bash setup/verify.sh` green lights. A ✗
  names its own fix; "indexes building" just means wait.
- **Checkpoint beats** (call them out as the room reaches them; each is a
  STUDENT_GUIDE "Checkpoint demo"): **Tier A** — agent_chat answering
  "where are we right now?" through THEIR tools, calls printing inline.
  **Tier B** — the Wehrlein pace comparison fusing both worlds. **Tier C**
  — the room gets loud: engineers talking in student voices over lap 3.
  Encourage speakers-on; it's the energy engine of the afternoon.
  **Tier D** — someone's custom trigger firing live.
- The question bank (guide + DEMO.md) feeds anyone whose demo needs
  material. The weather question is the crowd-pleaser.
- Mid-afternoon, nudge teams to the 10-minute integration ritual (lanes
  table in the guide).

## The wrap (last 20 minutes)

Volunteer demos — push for voice questions and custom Tier-D triggers, not
slideware. Close on the doctrine: "Every group here built the same thing
in one important sense: a system where the AI never decides WHEN to act —
deterministic code does — and is never trusted on facts it didn't pull
from a tool. That pattern transfers to everything agentic you'll build."

## What healthy looks like (so you can spot sick)

- Proactive radio calls land in ~2–8s at the deployed wall; Q&A typically
  single-digit seconds, fused two-world questions ~10–13s; the first ask
  after a deploy is the slowest (inline session create — that's why
  pre-flight warms it).
- Must-says (our AM transitions, critical race control) are near-100%
  reliable: held through debounce, expired only if stale >25s.
- The per-race scoreboard prints in the frontend log at each
  restart/finish — `scoreboard (race just ended): {...}` — followed by
  `Q&A session rotated for the new race`. Reference point from the graded
  2× stint (laps 1–12, reference agent conditions): 14 event / 6 summary /
  3-of-3 must-say / 37 suppressed / 0 dropped. High "suppressed" is the
  system WORKING — that's the negative space.
- The canonical full-race baselines were captured at 5× during P2.6
  hardening (rows in this file's git history and PACKAGING.md); 2×/1×
  full-race rows were deliberately skipped at rehearsal — expect lower
  speeds to fire MORE events (more wall-clock per debounce window) with
  the same must-say reliability.
- **Build at 2×, demo at 1×.** At 5× the world outruns the model — answers
  go stale, not wrong.

## Troubleshooting (instructor-grade)

| Symptom | Cause | Fix |
|---|---|---|
| Student: env/venv complaints | new tab | `source activate.sh` — always the fix |
| Student: everything on the LOCAL pit wall 503s | Cloud Shell recycled the session; exports gone | relaunch `bash demo.sh` (it re-sources itself) |
| "…IAM can't see SA yet — retry N/6" during setup | new-SA propagation on a fresh project | normal; the loops absorb it (steps 3/5/6) |
| Q&A references the PREVIOUS race / feels haunted | stale persistent session | RESTART on the SIM bar — rotation is automatic; bounce env-var only as belt-and-braces |
| Q&A "Radio failure" while agent_chat works perfectly | poisoned Q&A session (failed ask checkpointed mid-stream) | same: RESTART rotates the session |
| Calls slow, retries in the log, occasional drops | quota pressure (shared regional Gemini pool) | confirm one engineer per project (no demo.sh next to a live fe-frontend); drop sim speed; escape ladder below |
| A setup/deploy script dies with NO output | a bare `VAR=$(gcloud …)` failed under `set -e` | triage: `echo $?` first, then rerun as `bash -x script 2>&1 \| tail -20` — the last line names the killer; all known instances are patched (Finding #11), rerun is safe (idempotent) |
| Need frontend logs | — | follow: `gcloud beta run services logs tail fe-frontend --region=$REGION`; search: `gcloud logging read 'resource.labels.service_name="fe-frontend" textPayload:"rotated"' --freshness=30m` (plain `logs read --limit` scrolls past what you want) |

**Model escape ladder (quota emergencies only — the default stays):**
default `gemini-3.5-flash` on the `global` endpoint. Rung 1:
`FE_MODEL=gemini-3.1-flash-lite` — fast (~1.2s calls) and timing-accurate,
but the 2026-06-06 graded promotion test **FAILED** it on persona
discipline (literal "Focus on…" filler inside a must-say) and grounding
(self-contradictory positions, ungrounded rival claims, invented "power
settings"). Break-glass only: a chattier, sloppier engineer beats a silent
one. Rung 2: regional endpoint fallback per the model config comments.

**DEPLOYED pit wall up but everything errors (the 503 protocol),**
cheapest discriminator first:
1. Open `$SIM_URL/status` directly — sim answers ⇒ the data plane's front
   half is alive; problem is downstream.
2. `bash setup/verify.sh` — the green-light check IS the triage tool: it
   names the broken layer (sim / Firestore / indexes / BQ / Toolbox) and
   the setup script that fixes it.
3. Verify green but wall dead ⇒ frontend or engine:
   `python scripts/engine_smoke.py` splits them — smoke green means the
   frontend, so read its logs (command above) for a startup traceback, an
   empty `SIM_URL`, or a stale `AGENT_ENGINE_RESOURCE`.
4. Logs clean but UI dead ⇒ browser/websocket layer: hard-reload; the
   socket reconnects within ~1s by design.
5. Nuclear, in blast-radius order: `bash deploy/deploy_frontend.sh` →
   `python scripts/reset_race_state.py --yes` + RESTART → `bash
   setup/all.sh`. Deliberately NOT on the ladder: the engine — engine
   failures present as "Radio failure" Q&A and dropped calls, never as
   503s on the wall itself.

## Event-morning checklist (open items live here)

- [ ] Create/verify the **tinyurl**; write it on the board; fill both
      placeholders (this file + STUDENT_GUIDE header).
- [ ] Confirm student projects are the **resourced** Qwiklabs type (the
      quota profile every baseline and the retry-free rehearsal runs came
      from).
- [ ] During pre-flight, confirm the **lap-2 → 1× drop** lands before the
      first attack-mode badge at 2× (it did at rehearsal; this is the one
      timing beat worth re-checking on the day's hardware).
- [ ] Warm-up question asked; scoreboard + "rotated" line sighted in the
      log after your pre-flight RESTART.
