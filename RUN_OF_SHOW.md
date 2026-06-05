# Run of Show — Formula E Race Engineer Hackathon (Challenge 2)

Instructor document. Students never see this; they get `STUDENT_GUIDE.md`.
The demo question bank and deeper choreography live in `DEMO.md` — this doc
tells you what to do and when; that one tells you what to say when someone
asks "what's Attack Mode?"

Event shape: **3 hours** — 20 min opening (live demo + framing, students'
setup running in the background) / ~2:30 build / 10 min wrap.

---

## The morning of (start ~60-75 min before doors)

WHERE: Cloud Shell in YOUR event project, fresh tab.

```bash
git clone https://github.com/haggman/formula-e-race-engineer.git
cd formula-e-race-engineer
source activate.sh
bash setup/all.sh              # the data plane: steps 1-6 + verify
bash setup/7_deploy_cloud.sh   # the instructor extras: engine + public pit wall
```

Wall-clock expectations (measured in the acceptance rehearsal — if a step
runs far past its number, it's stalled, not slow):

| Step | Expect | Measured |
|---|---|---|
| 1 enable_apis | ~1 min | [___] |
| 2 load_bigquery | ~4 min | [___] |
| 3 deploy_toolbox | ~3 min | [___] |
| 4 setup_firestore | <1 min (indexes build async) | [___] |
| 5 deploy_state_writer | ~4 min (Cloud Build) | [___] |
| 6 deploy_simulator | ~3 min | [___] |
| verify | ~1 min, GREEN LIGHT | [___] |
| 7 deploy_cloud (optional path) | ~15-20 min; the engine create is 5-10 min of SILENCE — this is normal; the script prints a log-watch one-liner | [___] |

**Pre-flight checklist** (do these the moment 7 finishes, not at doors):

- [ ] Open the deployed pit wall URL (printed by step 7) in the projector
      browser. Click 🔇 → 🔊 NOW and play one call — the click is the
      audio unlock, and you do not want to discover a muted demo live.
- [ ] Grant mic permission NOW (hold the 🎤, say "test", see the
      transcript land). Browser permission prompts mid-demo kill momentum.
- [ ] SIM bar: speed 2×, LOOP off, then RESTART and confirm calls flow.
- [ ] PAUSE the sim. Leave it paused on the grid until showtime.
- [ ] `python scripts/engine_smoke.py` → both worlds answer.
- [ ] Bounce fe-frontend for a FRESH Q&A session (the persistent session
      accumulates every question ever asked through this instance, and
      latency grows with it):
      `gcloud run services update fe-frontend --region=$REGION --update-env-vars=SESSION_RESET=$(date +%s)`
- [ ] Have STUDENT_GUIDE.md's "Getting started" block on a slide or
      whiteboard: clone URL, `source activate.sh`, `bash setup/all.sh`.

Fallback if you skipped step 7 (or the engine misbehaves): the identical
demo runs locally — `export SIM_URL=...; uvicorn frontend.main:app --host
0.0.0.0 --port 8080` with Web Preview. Same UI, same agent behavior,
AGENT_PACKAGE=solution via your shell.

---

## The opening 20 minutes

**0:00–2:00 — Students start their engines (the load-bearing beat).**
Before you explain anything: get every student/team into their Qwiklabs
project and pasting the three lines — clone, `source activate.sh`,
`bash setup/all.sh`. Their ~20-30 min of provisioning runs WHILE you talk;
by the time you finish, their data plane is up or nearly so. This overlap
is a design constraint of the event, not a nicety — if you talk first and
provision later, T1 starts half an hour late.

**2:00–5:00 — Frame it.** The challenge in one breath: a live race
streams through the project; a complete pit wall, voice loop, and trigger
system are GIVEN; they build the brain — the agent in the middle. Draw the
two worlds (Firestore now / BigQuery then) — every good question fuses
them, and tool orchestration across them is the skill this challenge
teaches.

**5:00–13:00 — The demo.** From your deployed pit wall, audio live:

1. RESUME/RESTART at **2×**. Talk over laps 1–2 (~70s): DAC starts P10,
   the opening shuffle generates the first calls — let one land aloud,
   point at the position-delta badges.
2. When the lap counter reads 2 and the ring is past half, drop to
   **1×**. You're setting up lap 3.
3. **The attack-mode cluster.** Half the field arms within seconds — the
   tower lights orange — and the engineer reports it as ONE coherent call,
   including who held back. The line: *"a naive system fires twelve
   alerts here; a deterministic scorer decided this was one moment, and
   the model only chose the words."*
4. **PAUSE.** Into the frozen moment, three questions:
   - Typed: *"How's our energy versus Cassidy — are we gaining or
     losing?"* → two worlds fused in one answer.
   - Voice (hold SPACE): *"Who's directly behind us, and does he have
     attack mode left?"* → the full Chirp-in/Gemini/Chirp-out loop.
   - *"What's the weather looking like?"* → the honesty test. It declines:
     no tool has weather. The line: *"the engineer you can trust is the
     one that knows what it doesn't know."*
5. Tell — don't show — the attack-loop detour: *"by lap 8 this thing
   correctly narrates Antonio sacrificing the lead to take his boost,
   dropping to P3 through the off-line loop, and repassing — in real
   time."* (Laps 7–9 are the best story in the data and too slow to show.)
6. RESUME at 5×, kill the audio, leave it racing silently behind you.

**13:00–18:00 — What they build.** Tiers and budgets (T1 tools 40 / T2
toolbox 45 / T3 persona 30 / T4 triggers as stretch), one testing surface
per tier, checkpoints. State the answer-key policy out loud: `solution/`
is open, same filenames, reading it when stuck is encouraged. Teams: four
lanes (tools / data / persona / triggers), one integration point. Glance
at a student screen — setup should be around step 4–5; reassure that
verify at the end is their green light.

**18:00–20:00 — Logistics and go.** Where you'll be, when checkpoints get
roving demos, wrap format. Go.

---

## During the build — what to say at each checkpoint

Rove. When a team hits a checkpoint, give them the next-step hook and a
story:

- **T1 done** (test_frame_tools all ✓): "Your agent can see. Now ask it
  about lap 1 in agent_chat — notice it CAN'T answer history yet. That's
  T2." Story to tell: the AgentEvent wrapper exists because the model once
  stole a 2026 replay timestamp and queried the future — data-level fixes
  beat prompt rules.
- **T2 done** (Wehrlein comparison lands): "Watch the tool sequence it
  chose — nobody told it to bridge the clock." Story: the overtake stream
  encodes GRID POSITION in a field named car_number — every attribution
  was wrong until position-adjacency scoring proved it. The best gotcha in
  the dataset; the curious can find more.
- **T3 done** (their voice on the speaker): "Now make it shut up
  correctly — banned-filler and concrete-instruction rules are persona's
  hard part." Story: prompt examples become vocabulary; the reference once
  said "lift and coast into turn six" forever because an example did.
- **T4** (tuners): "Your engineer's judgment is a weights table. Make it
  paranoid. Then build the arming rule — strategic intent is sitting in
  the data unwatched."

Mid-build health checks worth announcing once: every new tab needs
`source activate.sh`; build at 2×, demo at 1×; dropped calls in
moderation are the budget ceiling working.

## The wrap (10 min)

Two or three volunteer demos from student screens — ask each to show ONE
thing: a fused question, their persona's lap summary, or a tuned trigger
firing. Close on the architecture lesson: deterministic code decided WHEN
to speak; the model decided WHAT to say; every name and number came from a
tool. Then point at the seven-challenge arc.

---

## Troubleshooting (instructor-grade)

| Symptom | Cause | Fix |
|---|---|---|
| Student setup stalled at step N | Compare against the timing table above | Idempotent: Ctrl-C and rerun `setup/all.sh`; it fast-forwards |
| verify ✗ on indexes "still building" | Firestore backend queue | Genuinely just wait; re-run verify. No action exists. |
| Tower empty | Sim not publishing / fresh project order issue | RESTART on SIM bar; if still empty, `curl $SIM_URL/status` |
| Calls drop repeatedly, logs show 429 / gRPC code 8 | Shared regional Gemini quota under trigger density (code 8 IS the 429 — logs never say "429") | Drop to 2× or 1×; drops self-heal (5s cooldown) |
| Voice OUT works, voice IN dead | STT recognizers are IAM resources (speech.client) — the classic dev-vs-deployed gap | In Cloud Shell it should work via student roles; on a deployed frontend, the deploy script grants it — re-run deploy_frontend |
| Engineer silent, state moving | Engineer loop crashed at startup | Check the uvicorn terminal traceback; usually a prompts.py syntax error from T3 editing — `python -c "from starter.race_engineer import prompts"` pinpoints it |
| "Radio failure on that one" every Q&A | Agent erroring server-side | Run the same question in agent_chat to see the real exception |
| Student killed uvicorn mid-race | Nothing — designed for | Relaunch; the loop detects race time and resyncs. [VERIFY IN TEST 1: note exact observed behavior] |
| RESTART mid-Q&A | Nothing — designed for | Loop flushes state on time-going-backwards. [VERIFY IN TEST 1] |
| Browser closed/reopened | Nothing | Websocket reconnects with backoff. [VERIFY IN TEST 1] |
| Whole project broken beyond diagnosis | — | Nuclear: `python scripts/reset_race_state.py --yes`, RESTART sim; beyond that, rerun `setup/all.sh` |

## Open items for this doc (close during acceptance Test 1)

- [ ] Fill every [___] timing cell from the fresh-project run
- [ ] Replace the three [VERIFY IN TEST 1] rows with observed behavior + words
- [ ] Time the opening script end-to-end out loud; trim to fit 13:00
- [ ] Confirm the lap-2 → 1× drop point lands before the cluster at 2×
