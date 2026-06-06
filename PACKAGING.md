# PACKAGING.md — Phase 2 Progress — Formula E Race Engineer (Challenge 2)

**Repo:** [haggman/formula-e-race-engineer](https://github.com/haggman/formula-e-race-engineer)
**Last updated:** 2026-06-05 (P1.5 complete incl. the P1.5.1 index-poll fix; P1.6 desk checks in progress — the last P1 gate)

**What this doc is:** the living record of Phase 2 (packaging the Fork 2 reference
into the 3-hour hackathon product). `PROGRESS.md` is the FROZEN Fork 2 build
record — never edit it; its Findings section remains the gotchas bible. This doc
supersedes `docs/PACKAGING_BRIEF.md` (the handoff brief that opened this phase);
all of the brief's open questions are now settled below. Mark the brief
superseded with a header note in P1, don't delete it.

**Handoff protocol:** attach the repo to a fresh conversation and open with:
"Phase 2 packaging — read PACKAGING.md first, then PROGRESS.md for build
history. Pick up at the next unchecked chunk."

---

## Where we are

**P1 (restructure + scripts) is COMPLETE** — all six chunks done,
regression-verified, and committed. Two real bugs found and fixed by the
regressions themselves: P1.5.1 (the firestore index poll that burned 900s
on a dead gcloud filter key) and P1.6.1 (the engine staging stale-check
false positive on agent_pkg.py). Both fixes made the failing CHECK
structurally smarter rather than looser — a pattern worth keeping.

P2 (docs) is fully delivered: STUDENT_GUIDE.md, RUN_OF_SHOW.md, the README
router rewrite, the DEMO.md patch (cross-ref header + the
demo-the-REFERENCE fix — without it the post-P1.4 shell default would have
an instructor demoing the flat starter), and the SUPERSEDED header on
docs/PACKAGING_BRIEF.md. RUN_OF_SHOW carries [___] timing cells and three
[VERIFY IN TEST 1] rows that acceptance Test 1 closes.

**Next action: P3 — Patrick runs acceptance Test 1 (fresh-project presenter
run: time every setup step, perform the opening out loud, restart-resilience
pass), then Test 2 (the student run, tier budgets, peek log).**

**Verify finding #3 (pre-demo check-in, 2026-06-05):** on the long-lived
stack, verify reported "RaceState stale with the sim running — check
fe-state-writer logs," sending Patrick toward the writer. Actual cause: the
race had FINISHED (LOOP off) ~67 min earlier — a 2918s race plus silence
matches the 4053s staleness; the sim publishes nothing at the chequered
flag, so staleness is expected and the pipeline was fine. Fix
(p2_verify_race_done_fix.tar.gz → setup/verify_checks.py): the sim check
now derives race_done from /status seconds_remaining, and the stale branch
has THREE diagnoses — paused (note), race finished (✗ with "RESTART and
re-verify" + the LOOP tip), and genuinely mid-race-stale (✗ blaming the
writer/subscription, now correctly reserved for real breakage). Same theme
as findings 1-2: make the check smarter, not looser.

**Finding #4 (pre-demo check-in): persistent Q&A session latency compounds
on the deployed frontend.** The persistent session is a documented locked
decision (PROGRESS.md Decisions + chunks 9/13) — follow-ups keep context —
but its corollary wasn't: fe-frontend runs min=max=1 with no scale-to-zero,
so ONE engine-side session accumulates every question ever asked through
that instance, and each new question replays the whole history (observed:
20-40s answers vs the ~10-15s fresh-session band). Local dev never sees it
(uvicorn restarts reset the session). Mitigation: RUN_OF_SHOW pre-flight now
bounces fe-frontend before any demo.
**Escalation (same evening):** not just latency — OUTRIGHT Q&A failure on
the deployed pit wall ("who's in car 48", the Cassidy energy question)
while agent_chat answered both and proactive triggers kept landing. The
discriminator: triggers use fresh engine sessions, Q&A uses the ONE cached
persistent session — and EngineAgentClient cached its ID forever
(`if self._qa_session_id is None`), so an expired/degraded engine-side
session means permanent Q&A death on a long-lived instance. **Diagnosis corrected (same night):** the bounce did NOT fix it,
and the frontend logs settled it — `call dropped (lap_summary)` and
`(must_say)` failures interleaved with the qa failures, all either
TimeoutError or "engine returned no text (1-2 tool calls)". Triggers use
FRESH sessions, so the persistent-session theory was falsified; this is
the chunk-13 quota signature — engine runs dying at the final generation
on the shared regional Gemini pool (gRPC code 8 / silent empty stream),
with TimeoutErrors as the slow-retry-chain flavor of the same thing.
NOT caused by the all.sh rebuild (data plane fully verified green the
same evening) and NOT fixable by frontend redeploy or a fresh project
(the pool is regional and shared). Chunk-13 precedent: evening
contention, recovered by morning. Mitigations: env-only timeout raises
(ASK_TIMEOUT_S/FIRE_TIMEOUT_S — no rebuild needed), low trigger density
(1×, PAUSE for Q&A), morning retest, local pit wall as demo Plan B
(agent_chat answered everything all evening — the local path retries
without a wall-clock ceiling). The session self-heal patch
(p3_qa_session_selfheal.tar.gz) stays in the repo as hygiene for the
real expired-session failure mode, but it is NOT the fix for this; ships
with Test 1's deploy. NEW SESSION button / session-age cap deferred. Operational corollary,
now in RUN_OF_SHOW spirit: pre-flight ends RESTART-then-PAUSE, and LOOP on
keeps a long-lived demo stack always verifiable.

---

## Decisions locked (2026-06-05 planning session)

| Area | Decision |
|---|---|
| **Build surface** | Students build the AGENT; everything else is a gift. (Carried from the brief, confirmed under pressure-testing.) |
| **No engine for students** | Students never touch Agent Runtime (formerly Agent Engine) — deploys are too slow for the room, and time-on-agent is the pedagogical point. `AGENT_MODE=local` for the entire student experience. Engine + Cloud Run frontend live in one OPTIONAL instructor script (`setup/7_deploy_cloud.sh`) — easy to skip unless showing off. |
| **One setup path, no profiles** | The student/instructor profile split is DEAD. Everyone runs the same numbered scripts 1–6 (via `setup/all.sh`); the instructor optionally adds script 7. No `--profile` flag, no branching. |
| **"Local" framing** | Honest version: the DATA PLANE lives in GCP (BigQuery, Firestore, Pub/Sub, Toolbox on Cloud Run, State Writer on Cloud Run, simulator on Cloud Run — State Writer MUST be deployed because Pub/Sub push needs a public URL). What runs "locally" in Cloud Shell: the agent (InMemoryRunner) and the frontend (uvicorn + Web Preview). This is the right split — the part students iterate on has a seconds-long edit loop. STUDENT_GUIDE must draw this line explicitly. |
| **Simulator vendored in** | `simulator/` becomes a first-class folder in THIS repo — single source of truth, no second repo to maintain. `haggman/formula-e-simulator` gets archived with a pointer here. No "upstream" language anywhere. Deploys via `cd simulator/ && gcloud run deploy --source .` (self-contained; never needs `shared/`, so the source-deploy path keeps working). The frames-building notebook comes along as reference material. README's "companion repos" section dies. |
| **Rename: `agent/` → `solution/`** | Answer-key semantics; pairs naturally with `starter/`. Atomic commit one, before anything else moves (see P1.1 touch inventory). |
| **AGENT_PACKAGE seam** | `frontend/agent_client.py` resolves the agent package via `importlib.import_module(os.environ["AGENT_PACKAGE"])` and grabs `root_agent`. `engineer_loop.py`'s three direct imports (prompts, config, snapshot) resolve through the same root, so T3+ students hear THEIR persona in proactive triggers. `activate.sh` defaults `AGENT_PACKAGE=starter.race_engineer.agent`; the instructor exports `solution.race_engineer.agent` to demo the reference through the identical pipeline. |
| **Starter mirrors solution** | `starter/race_engineer/` is file-for-file the same shape as `solution/race_engineer/` (agent.py, prompts.py, config.py, snapshot.py, tools/frame_tools.py, tools/state_client.py). "Stuck? Look at the same filename in solution/" is the whole help protocol. `pyproject.toml` adds `starter*` to package-find. Starter `__init__.py` needs the same guarded-import treatment as the reference's (adk-web discovery must not crash a Toolbox-less T1 agent). |
| **Starter content split** | GIVEN verbatim (marked `# GIVEN — infrastructure, don't edit`): config.py, snapshot.py, state_client.py, all Pydantic response models + helpers in frame_tools. T1 surface: `get_current_state` complete as the heavily-commented worked ADK example; the other 3 frame tools are signatures + docstrings + specced TODOs. T2 surface: agent.py wiring present, ToolboxToolset block is a TODO with construction spec in comments. T3 surface: prompts.py — DATA DISCIPLINE / clock-bridge / HONESTY sections GIVEN with a "hard-won, read this" banner; VOICE + CALL TYPES are skeletons with the spec as TODO comments; TTS normalization rules given as a checklist; trigger-prompt builders given (trigger-loop infrastructure). One prompts.py file; sections, not multiple files. |
| **Scorer weights ship TUNED** | Never detune the common path to enrich T4. T4 = "make the engineer yours": the weights table + debounce/must-say knobs, plus genuinely NEW rule work — e.g. the scorer doesn't score ARMING events at all today (strategic-intent calls: "Cassidy just armed scenario 3"). |
| **Testing surface per tier** | Exactly one per tier in STUDENT_GUIDE: `scripts/agent_chat.py` for T1–T2 (tool-call visibility is the teaching instrument); the frontend from T3 on (that's where voice lives). |
| **README** | Becomes a 30-second router: what this is, one architecture paragraph, then per-reader pointers (in the room → STUDENT_GUIDE; running the event → RUN_OF_SHOW; how it was built → PROGRESS.md; demoing → DEMO.md). Absorbs the old README-rewrite TODO. Kills stale facts (gemini-3-flash-preview model name, 8-tool count, companion-repo section). |
| **Setup choreography** | No Qwiklabs pre-seeding. Students kick off `setup/all.sh` in the FIRST TWO MINUTES of the instructor's 20-min opening; the demo runs from the instructor's stack while student setup churns (~20–30 min). Stated design constraint in RUN_OF_SHOW, not a contingency. |
| **Instructor morning-of** | Run `setup/all.sh` + `setup/7_deploy_cloud.sh` ~1 hour before doors (full path ~45 min, mostly the engine's silent 5–10 min and Firestore indexes). Keep it simple: two commands, per-script wall-clock expectations in RUN_OF_SHOW (numbers come from Acceptance Test 1). |
| **Opening demo (~7–8 min live)** | Laps 1–2 at 2× (P10→P6 shuffle still generates calls, ~70s), drop to 1× just before the lap-3 AM cluster, let the cluster call land, PAUSE. Into the frozen moment: one typed two-worlds question ("how's our energy versus Cassidy"), one VOICE question, then the weather honesty test (15 seconds, most disarming beat for developers). Attack-loop detour (laps 7–9) told VERBALLY, never shown live. Five proof points: proactive TTS call, cluster-as-one-call, two-worlds fusion, push-to-talk, honesty. |

---

## Target layout

```
formula-e-race-engineer/
├── README.md                  # 30-second router (rewritten in P2)
├── STUDENT_GUIDE.md           # P2
├── RUN_OF_SHOW.md             # P2
├── DEMO.md                    # stays — RUN_OF_SHOW leans on it
├── PROGRESS.md                # frozen Fork 2 build record — never edit
├── PACKAGING.md               # this doc — the living Phase 2 record
├── activate.sh                # env only; gains AGENT_PACKAGE default
├── solution/race_engineer/    # THE REFERENCE (renamed from agent/) — complete, visible, never edited in the room
├── starter/race_engineer/     # THE STUDENT PACKAGE — same internal shape as solution/
├── simulator/                 # vendored in: app code + Dockerfile + frames notebook
├── frontend/  shared/  state_writer/  toolbox/    # unchanged
├── deploy/                    # unchanged plumbing; setup/ wraps it
├── setup/                     # 1..6 + all.sh + verify.sh + 7_deploy_cloud.sh
├── scripts/  notebooks/       # unchanged (imports updated for rename)
└── docs/PACKAGING_BRIEF.md    # marked SUPERSEDED by this doc
```

---

## Setup scripts plan

Ordering rationale: simulator LAST — the moment it deploys it starts
publishing, and the State Writer subscription must already be listening
(Pub/Sub retains pushes ~10 min with no subscription; frames silently
evaporate otherwise — harmless since the sim loops, but confusing).

| Script | Wraps | Est. wall clock |
|---|---|---|
| `1_enable_apis.sh` | deploy/enable_apis.sh | <1 min |
| `2_load_bigquery.sh` | notebooks/bq_setup.py | ~4 min (telemetry load + top-speed CTAS) |
| `3_deploy_toolbox.sh` | deploy/deploy_toolbox.sh | ~3 min |
| `4_setup_firestore.sh` | deploy/setup_firestore.sh | the long pole — indexes occasionally 10+ min |
| `5_deploy_state_writer.sh` | deploy/deploy_state_writer.sh | ~4 min (Cloud Build) |
| `6_deploy_simulator.sh` | `cd simulator/ && gcloud run deploy --source .` | ~3 min |
| `all.sh` | 1–6 serially, then `verify.sh` | ~20–30 min total |
| `verify.sh` | green-light check: Firestore updating at 1 Hz, all 14 Toolbox tools answer, sim /health | ~1 min |
| `7_deploy_cloud.sh` | OPTIONAL: deploy/deploy_agent_engine.sh + deploy/deploy_frontend.sh | ~15–20 min, mostly silent |

All scripts non-interactive (`--yes` semantics throughout); the only existing
`input()` prompt in the repo is reset_race_state.py, which already has `--yes`.

---

## Phase plan

### P1 — Restructure + scripts (code phase)

- [x] **P1.1 — Rename `agent/` → `solution/`.** DONE 2026-06-05. Executed as
  a `git mv` + three sed passes (dotted imports, path-style docstring refs,
  and two targeted seds for `deploy/build_engine_app.py`'s escaped regex and
  `REPO /` path constant — the two lines a naive replace can't see), plus
  Dockerfile COPY and pyproject include. Verified: zero stragglers by grep,
  `compileall` clean, build_engine_app eyeballed (its stale-check string now
  correctly hunts `solution.race_engineer`). Regression green: editable
  reinstall, seed_test_state + test_frame_tools, agent_chat smoke. Deployed
  engine and Cloud Run frontend deliberately untouched (old paths baked into
  running images; next deploy of each picks up the new layout).
- [x] **P1.2 — AGENT_PACKAGE seam.** DONE 2026-06-05, regression green (local
  frontend stint, seam at solution default, zero behavior change). Design as
  built: `AGENT_PACKAGE` is the PACKAGE path; `agent_module(sub)` resolves
  modules from it; `engineer_loop.py` AND `main.py` both go through the seam
  so the whole frontend shares ONE state_client singleton. In P1.4a the
  resolver MOVED to `shared/agent_pkg.py` (re-exported from
  frontend/agent_client.py): the dev scripts must resolve the same package,
  and they can import `shared` (installed) but not `frontend` (not a
  package). Code default stays `solution.race_engineer` (the engine-mode
  container never sources activate.sh); activate.sh now defaults to
  `starter.race_engineer` for local work.
- [x] **P1.3 — Vendor `simulator/`.** DONE 2026-06-05. 12 files in, frames_v3
  confirmed as the default in both config.py and deploy.sh, deploy.sh fully
  env-overridable and location-agnostic (`--source=.`), README stamped with
  the moved-from note. Deployed from the new path; /status green; combined
  stint (seam + vendored sim) green. Old repo to be archived with a pointer
  (Patrick, when convenient).
- [x] **P1.4a — `starter/` extraction.** DONE 2026-06-05, regression green
  (agent_chat against the shipped starter: get_current_state answers,
  unimplemented tools reported honestly; reference unchanged through the
  same seam). Contents: the full starter package (guarded
  `__init__`, GIVEN config/snapshot/state_client, frame_tools with
  get_current_state as the heavily-commented worked example + three
  TODO(T1) tools raising NotImplementedError with full specs in comments,
  agent.py with the TODO(T2) Toolbox block — imports cleanly WITHOUT
  TOOLBOX_URL pre-T2 via `toolbox_tools = None` + conditional registration,
  prompts.py assembled from named SECTIONS with VOICE + CALL_TYPES as
  working-but-flat student placeholders and everything else GIVEN with
  hard-won banners — TODO guidance lives in Python comments, verified to
  never leak into the model-facing instruction string); `shared/agent_pkg.py`
  (the relocated resolver); `frontend/agent_client.py` v2 (imports +
  re-exports from shared); seam-ified `scripts/agent_chat.py` (prints the
  active package in its banner); `pyproject.toml` (+starter*, +simulator/
  build excludes); `activate.sh` (default → starter.race_engineer).
  Verified in sandbox: full starter import chain, instruction assembly
  (5,057 chars, no TODO leakage, clock-bridge + TTS + honesty text present),
  TODO tools raise with TODO(T1) messages, guard survives ADK-less import,
  engineer_loop resolves starter through the re-export, loud ImportError
  preserved.
- [x] **P1.4b — Seam-ify `scripts/local_test.py` + `scripts/test_frame_tools.py`.**
  DONE 2026-06-05, regression green (starter shows the TODO checklist;
  reference fully green through the same script). test_frame_tools is
  now the T1 checkpoint validator: it resolves the frame tools from the
  ACTIVE package and prints the package in its mode line, so a student's
  unimplemented tools show as ✗ NotImplementedError("TODO(T1)...") and a
  fully green run = T1 done. local_test resolves
  agent/config/prompts/snapshot/state_client through the seam and prints the
  package in its banner — the fast T4 trigger-tuning surface. Both fail
  loudly at startup on a bogus AGENT_PACKAGE. (Dropped local_test's unused
  race_time_to_wall_ns import while in there.) Sandbox-verified:
  test_frame_tools full module import against the real starter, TODO raise
  intact, both scripts compile, local_test's seam block resolves all five
  modules.
- [x] **P1.5 — `setup/` scripts.** DONE 2026-06-05 (incl. P1.5.1 below):
  setup/4 reruns in ~15s, verify.sh GREEN LIGHT on five checks. As built: `setup/_lib.sh` (shared require_activation guard —
  every script fails fast with "source activate.sh" if PROJECT_ID/REGION or,
  where Python runs, the venv is missing); six numbered wrappers
  (1_enable_apis, 2_load_bigquery, 3_deploy_toolbox, 4_setup_firestore,
  5_deploy_state_writer, 6_deploy_simulator — sim last, with the
  Pub/Sub-retention rationale in its header) delegating to the proven
  deploy/ scripts; `all.sh` runs 1-6 with per-step + total wall-clock
  timing then verify; `verify.sh` discovers SIM_URL/TOOLBOX_URL from Cloud
  Run and runs `verify_checks.py` — four checks (sim /status, Firestore
  RaceState FRESHNESS which proves the whole chain end-to-end with a
  paused-sim soft case, BQ row sanity on laps+telemetry, Toolbox toolset
  14/14), exit code = failures, every ✗ names the setup script that fixes
  it; `7_deploy_cloud.sh` is the optional instructor extra (engine +
  Cloud Run frontend, TOOLBOX_URL re-discovery guard, silent-create
  warning, engine_smoke pointer). Sandbox-verified: bash -n on all ten
  scripts, verify_checks compiles and imports with main() guarded,
  unactivated-shell guard fires with the fix line.
  **P1.5.1 fix (found in regression):** the inherited setup_firestore.sh
  index poll used `--filter="collectionGroup=race_events"`, a key gcloud
  no longer exposes ("filter keys were not present in any resource") — so
  READY was never detected and EVERY run burned the full 900s timeout, with
  all three indexes sitting READY the whole time. Pre-existing DB/indexes
  were NOT the cause (creates no-op'd correctly). Fix
  (p15_1_firestore_fix.tar.gz): deploy/setup_firestore.sh now submits index
  creates async and RETURNS — no polling anywhere in setup; index readiness
  became verify check 3/5 in setup/verify_checks.py via the Firestore
  ADMIN API (FirestoreAdminClient.list_indexes scoped to the race_events
  collection group — structured data, no gcloud text-scraping), with a
  bounded wait (VERIFY_INDEX_WAIT_S=600, env-overridable) since verify is
  the only consumer that genuinely needs the indexes and by then the
  builds have overlapped steps 5-6's Cloud Builds.
- [x] **P1.6 — Desk-check tests.** DONE 2026-06-05, all five green (incl.
  P1.6.1 below); P1 phase committed. Five checks: (a) seed-mode test_frame_tools against BOTH
  packages — sim paused, canonical frame seeded; starter shows the TODO
  checklist with get_current_state's exact asserts green, solution all
  green; then reset + RESTART; (b) toolbox_test.py — all 14 tools against
  the deployed fe-toolbox; (c) `python deploy/build_engine_app.py` staging
  self-check — proves the renamed vendoring path (solution/ source, regex,
  import rewrite, stale-string check) WITHOUT a 10-minute engine deploy;
  (d) starter-T1 frontend smoke — shipped starter in uvicorn: Q&A
  "where are we?" answers via get_current_state, proactive calls run flat
  but functional off the prompt snapshot, occasional drops when the model
  reaches for an unimplemented tool are EXPECTED (drop-with-cooldown is the
  designed behavior); (e) git sweep + the P1 phase commit. Deployed engine
  + Cloud Run frontend remain on pre-rename images by design; Test 1's
  7_deploy_cloud.sh exercises their redeploy.
  **P1.6.1 fix (found in check c):** the staging self-check greps staged
  files for the raw string "solution.race_engineer" — and the verbatim-
  vendored `shared/agent_pkg.py` (new in P1.4) contains it twice, in its
  docstring and as the AGENT_PACKAGE env default. False positive: neither
  is an import, and nothing on the engine imports agent_pkg (the seam is
  client-side; the engine IS the solution agent). Fix
  (p16_engine_staging_fix.tar.gz, deploy/build_engine_app.py): (1)
  agent_pkg.py is EXCLUDED from engine staging — dead code there, with the
  rationale in the module docstring and a staging assertion enforcing it;
  (2) the stale check is now an import-statement regex (multiline
  `^\s*(from|import)\s+solution\.race_engineer\b`) so prose/string
  mentions in shared files can never trip it, while a REAL unrewritten
  import still fails the build. Sandbox-verified both ways: clean staging
  with a comment-mention in shared, and a planted
  `from solution.race_engineer import ...` in a shared module caught.

### P2 — Docs

- [x] STUDENT_GUIDE.md — DELIVERED, awaiting Patrick's voice/structure pass
  (Test 2 is the real review). As written: the
  two-worlds framing up front; the deployed-vs-yours line drawn explicitly
  (data plane in GCP, agent + pit wall in Cloud Shell); starter/ vs
  solution/ with the open-answer-key policy stated; self-contained Attack
  Mode + race-story context (seeded from DEMO.md); four tiers with budgets
  (T1 40 / T2 45 / T3 30 / T4 overflow), each with its ONE testing surface,
  its checkpoint demo, and exact commands; team-role split; question bank;
  troubleshooting quick hits. T4 open item RESOLVED as a guided suggestion:
  the arming-events scorer rule is sketched with pointers (get_am_armings,
  scorer.py shape) but not specced to the line — tuning the weights table
  is the floor, the new rule is the ceiling.
- [x] RUN_OF_SHOW.md — DELIVERED; Test 1 closes its [___] and [VERIFY]
  items. As written: morning-of
  command box + per-step timing table ([___] cells for Test 1's measured
  numbers) + pre-flight checklist (audio unlock and mic permission BEFORE
  doors — the two silent demo-killers); the 20-minute opening scripted to
  the minute, with the students-kick-off-setup-first beat stated as a
  design constraint and the demo choreography (2× laps 1-2 → 1× for the
  cluster → PAUSE → typed fused question, voice question, weather honesty
  test → the attack-loop detour told verbally → resume 5×); per-tier
  checkpoint talking points each paired with a build-finding story
  (future-leak, overtake identity, prompt-examples-become-vocabulary);
  wrap format; instructor-grade troubleshooting incl. the gRPC-code-8-is-
  the-429 row and three [VERIFY IN TEST 1] restart-resilience rows; a
  closing checklist of exactly what Test 1 must fill in.
- [x] README router rewrite — DELIVERED: 30-second orientation, per-reader
  router table, quick start, current architecture (gemini-3.5-flash, 14
  Toolbox tools, AGENT_MODE + AGENT_PACKAGE), repo map. Stale facts killed
  (old model name, 8-tool count, companion-repo section).
- [x] DEMO.md touch-ups — DELIVERED as a verified, assert-guarded patch:
  RUN_OF_SHOW cross-ref header; run block now exports
  AGENT_PACKAGE=solution.race_engineer and notes the deployed-pit-wall
  alternative. (No path fixes needed — DEMO.md never referenced agent/.)
- [x] Mark docs/PACKAGING_BRIEF.md superseded — DELIVERED (newline-safe
  prepend in the P2.3 patch box).

### P3 — Acceptance tests (Patrick-run)

- [ ] **Test 1 — presenter run.** Fresh Qwiklabs project, nothing cached.
  `all.sh` then `7_deploy_cloud.sh`, TIMING EVERY SCRIPT (numbers go verbatim
  into RUN_OF_SHOW). Then perform the actual opening out loud, timed — the
  2×→1× lap choreography, pause at the cluster, three questions including
  voice and the weather test. Doubles as the formal 1× end-to-end pass the
  build phase skipped (closes that PROGRESS TODO). Include the
  **restart-resilience pass**: kill uvicorn mid-race and relaunch, RESTART the
  sim mid-Q&A, close/reopen the browser — the room will do all of these by
  accident in the first half hour; observations feed the troubleshooting table.
- [ ] **Test 2 — student run.** Play student: load the starter, run tier by
  tier against the 40/45/30 budgets, checkpoint-demo exactly as STUDENT_GUIDE
  instructs. Discipline: don't peek at solution/ until genuinely stuck, and
  LOG EVERY PEEK — each one is either an under-specified starter TODO or a
  STUDENT_GUIDE gap. Calibration: Patrick is a worst-case proxy (knows ADK
  cold); if any tier takes him more than ~60% of its budget, real students
  blow it — the starter gives more.

---

## Open items

- Qwiklabs project-template specifics (pre-enabled APIs, org policies) —
  observe during Test 1; adjust 1_enable_apis if anything's pre-done or blocked.
- Exact prose of the "GIVEN — hard-won" banners in starter prompts.py — draft
  during P1.4, sanity-check during Test 2.
- Whether verify.sh should also assert the agent answers one question (a
  mini engine-smoke for local mode) — decide in P1.5.
- PARKED (for the STUDENT_GUIDE rewrite): **Formula E primer upgrade.**
  Assume the audience knows "electric race cars" and nothing else. The
  existing "Two minutes of Formula E" section is the seed — expand it into
  a proper primer: what an ACTIVATION ZONE physically is (painted loop OFF
  the racing line; driving through it costs track position — that's the
  strategic tax), arming vs activation as intent vs deployment, the three
  scenarios and why a driver re-arms (DAC armed 9x this race), the
  magenta halo (everyone SEES who's boosted), why AM exists at all
  (fixed-duration power committed against an unknown future = the whole
  reason an AI engineer is plausible), energy normalization (every car
  finishes at 100% — only mid-race deltas mean anything), no pit stops /
  one car (Gen3 context), and the Berlin R10 story arc (DAC P10->win, the
  lap-3 cluster, the Cassidy battle, the lap 7-9 attack-loop sacrifice).
  Format options: glossary box + a "the race you're watching" story
  paragraph; consider a primer slide for the opening (or a Nano Banana
  track diagram showing the attack loop off-line). Tone: a fan explaining
  to a friend, not a rulebook. Cross-check every claim against DEMO.md's
  question-bank facts so the primer and the agent never disagree.
- PARKED (for the STUDENT_GUIDE rewrite): **Gemini Code Assist + ADK docs
  links.** (a) Students work in Cloud Shell Editor, which has Gemini Code
  Assist built in — tell them to USE it (a line in Getting Started + an
  opening talking point; it pairs naturally with the answer-key-open
  policy). (b) We assume Python but NOT ADK — the guide needs a short
  curated "learn ADK fast" links block: function tools, ToolboxToolset,
  Agent constructor, runners. CRITICAL VERSION CAVEAT: the lab is built on
  ADK 1.x and ADK 2.0 is out (breaking changes: graph Workflow Runtime,
  callbacks, exception handling) — every link must be version-pinned or
  verified to apply to 1.x, and the guide should say explicitly "we use
  ADK 1.x; if a doc page mentions Workflow Runtime/graphs, you're reading
  2.0 — back out." Also warn that Code Assist may suggest 2.0-style APIs;
  the worked example in frame_tools.py is the ground truth pattern.
- PARKED: **message-type taxonomy + expected-volume baselines.** Be crisp
  about the four call types and their gates so a glance at a running pit
  wall says healthy-or-not: EVENT REACTION (scorer >= threshold, subject
  to debounce + cooldown), LAP SUMMARY (floor: every 2 laps —
  summary_every=2), MUST-SAY (severity overrides debounce, has its own
  min-gap), Q&A (human-initiated, persistent session). Plus the two
  silent categories: SUPPRESSED (below threshold/debounced — visible in
  local_test --verbose) and DROPPED (budget ceiling / timeout —
  drop-with-cooldown by design). Observed baseline to validate (Patrick,
  5x, 26 laps, local): summaries every 2-3 laps (floor is 2; the 3s are
  drops), 3 must-says, but only ONE event reaction — plausibly correct at
  5x (event density x5 vs fixed agent throughput => coalescing + drops)
  but low enough to check; ties into the latency investigation (slow LLM
  calls starve the loop). Action: add fired/suppressed/dropped counters
  per type to the loop log, record baselines at 1x/2x/5x during Test 1,
  publish the table in RUN_OF_SHOW ("what healthy looks like") +
  STUDENT_GUIDE.
- PARKED (for the STUDENT_GUIDE rewrite in the cascade): **team lane map —
  independent test surfaces.** Make explicit that each lane validates
  WITHOUT the other lanes being done: a "lane map" table (lane -> file ->
  test script -> what it needs). TOOLS lane: scripts/test_frame_tools.py
  needs only frame_tools.py + the data plane (use seed_test_state.py for a
  deterministic frozen frame instead of chasing the live replay). AGENT
  lane: agent_chat runs even with T1 unfinished — unimplemented tools
  raise cleanly, so history-only questions validate the Toolbox wiring
  before the tools lane lands. PERSONA lane: agent_chat + the given
  get_current_state is enough to start immediately. TRIGGERS lane:
  scripts/local_test.py drives the loop against the starter as shipped.
  toolbox_test.py validates the deployed toolbox with no agent at all.
  Note WHY merging is painless: lanes touch different files, so
  integration is copy-level; suggest the integration ritual (after lanes
  merge: test_frame_tools all-green + one fused question in agent_chat).
  Surfaces in: STUDENT_GUIDE team section, RUN_OF_SHOW opening talking
  point ("four lanes, four test scripts, nobody waits on anybody").
- PARKED (URGENT-when-back): **all backend Cloud Run services returning
  503 simultaneously** (fe-toolbox / fe-simulator / fe-state-writer; hit
  while re-running the local demo). Simultaneity = one environmental
  cause, not N service bugs. Suspects, likelihood order for a lab/Argolis
  project: (1) COLD-START CRASH after overnight scale-to-zero — something
  changed under the containers (service account disabled, org-policy
  enforcement job, billing state) so first morning request fails to boot
  the instance -> 503; (2) lab project TTL/cleanup or billing disable;
  (3) regional Cloud Run incident (rare; check status dashboard last).
  Triage order (60s): [a] gcloud projects describe $PROJECT_ID (lifecycle
  ACTIVE?); [b] gcloud run services list --region=$REGION (do they still
  exist?); [c] the decisive one — startup logs of ONE failing service:
  gcloud logging read 'resource.type="cloud_run_revision" AND
  resource.labels.service_name="fe-toolbox" AND severity>=ERROR'
  --freshness=1h --limit=30 — a cold-start crash names its cause in the
  first traceback; [d] if project is dead: fresh project + setup/all.sh
  IS the recovery path (and doubles as Test 1). NOTE: this breaks the
  LOCAL demo too — local agent still needs fe-toolbox + SIM_URL.
- RESOLVED incident (evening before stakeholder demo): **sudden 503s from
  "all backend services" on the local pit wall.** Root cause: uvicorn was
  running in a Cloud Shell session WITHOUT the manual exports (SIM_URL /
  AGENT_PACKAGE) — Cloud Shell session recycling silently dropped them,
  the frontend's simulator-bound calls had no target, and the UI surfaced
  it as universal 503s. Fix: re-run the exports + relaunch. NOT auth, NOT
  Cloud Run, NOT Gemini. Hardening for the cascade: (a) startup guard in
  frontend local mode — if SIM_URL unset, exit with the exact export
  command to run, instead of starting broken; (b) fold the local-launch
  box (activate + exports + uvicorn) into a single demo.sh so launch has
  no rememberable parts. RUN_OF_SHOW troubleshooting table gets the row:
  "everything 503s locally -> your session lost its env; re-run the
  launch box."
- STAKEHOLDER DEMO (morning after the incident evening): DONE, well
  received — application, architecture, and event plan all landed. One
  observed weakness: Q&A latency appeared AGAIN, in the MORNING — which
  weakens time-of-day quota weather as the sole cause and raises the
  priority of the structural suspects (chain depth, session growth).
  This makes the latency investigation the top of the queue.
- NEXT (priority 1, NEW conversation): **troubleshoot Q&A latency.** Even in local
  mode (InMemoryRunner, agent_chat / local pit wall) the engineer sometimes
  takes very long to answer. Hypotheses to test, in rough likelihood order:
  (1) retry backoff absorbing 429s — shared_config retries up to 10 attempts,
  exp backoff capped 8s + jitter, so a contended quota window can silently
  add 30-60s per LLM call while looking like "thinking" (logs say gRPC code
  8, never "429"); (2) long tool chains on fused questions —
  MAX_LLM_CALLS_PER_QA=12 permits deep research loops, and each tool call =
  a full LLM round trip + (for Toolbox tools) a network hop to fe-toolbox;
  (3) the model wandering into schema discovery / execute_sql_bq when a
  curated tool would have answered; (4) Q&A SESSION GROWTH compounding
  with (1): the persistent session replays full history every question,
  and bigger requests both run slower AND burn more tokens-per-minute
  quota -> more 429s -> more backoff. (Can't explain trigger drops —
  those are fresh sessions — but is a genuine Q&A multiplier.)
  Candidate session-management fixes if measurement confirms (4), cheap
  to rich: turn-cap rotation (recreate every N questions); SLIDING
  WINDOW — fresh session per question + last 2-3 exchanges as preamble
  (keeps follow-ups, caps growth — likely winner); or full
  trigger-style: fresh session + snapshot + recent-exchange summary per
  question (most consistent with the trigger design philosophy). Diagnostic plan: add per-step timing to
  agent_chat (timestamp each tool call + each LLM gap), turn on genai client
  retry logging to make backoff visible, time one known-fast question
  (pure get_current_state) vs one fused question in the same minute —
  separates quota weather from chain depth — and log per-Q&A (turn count,
  input tokens, wall secs): latency climbing with turns = hypothesis 4
  confirmed, build the sliding window; flat-but-spiky = quota weather,
  build the progress indicator. TELEMETRY plan (do this first — it's free): (i) local: crank
  google_genai + httpx loggers to DEBUG in agent_chat — the genai client
  LOGS its retry attempts, so one slow question photographs the backoff
  (429 -> growing gaps -> retry); (ii) richer: ADK's built-in
  OpenTelemetry tracing / Cloud Trace on the engine side — span waterfall
  per Q&A turns "took 40s" into "31s = two backoff stalls on calls 2+4";
  (iii) keep the per-Q&A log line (turns, input tokens, wall secs).
  SESSION-TECH research note: the deployed path ALREADY uses Agent Engine
  managed sessions (that's what _new_session_sync creates) — and local
  slowness reproduces under InMemoryRunner, so storage location is NOT
  the cost; replayed TOKENS are. Managed session offload != faster.
  Worth researching instead: Memory Bank-style managed extraction
  (compact memories vs verbatim replay — the sliding-window idea as a
  service), checking what ADK 1.x can reach vs 2.0-only. Possible
  outcomes: sliding window (still favorite), an ASK-side progress
  indicator ("checking history..."), tighter QA call ceiling, prompt
  steering to curated tools. DEMO-DAY note: 40s silent answers are the
  real cost — until fixed, mitigate theatrically (paused race so Q&A owns
  the quota lane, talk over the gap, ask a warm-up question at T-5).
  Fold findings into RUN_OF_SHOW troubleshooting.
- PARKED (post-demo, with the T2/T4 cascade): **BONUS.md bonus board** for
  fast finishers — additive-only, never carve features out of the given
  product (SIM bar is load-bearing for troubleshooting + demo). Structure:
  three areas, two tickets each, format = surface + spec + demo payoff, no
  solutions. UI: [S] Chirp HD voice picker (re-voice the engineer live);
  [M] live tool-call observability panel (ADK eventing lesson, makes the
  clock bridge visible). AGENT: [M] post-race DEBRIEF button at the
  chequered flag — agent writes the race story from history tools; [L]
  re-cast the agent for another car (OUR_CAR_NUMBER + persona — Cassidy's
  losing side of the same race; best wrap-demo payoff). VOICE & DATA: [S]
  Portuguese radio (Antonio's language — TTS locale + prompt rule); [M]
  mini eval harness (5 canned questions; assert no invented names, clean
  weather refusal). DEPLOY: [L]
  ship YOUR agent to Agent Engine + a public Cloud Run pit wall — the
  setup/7_deploy_cloud.sh path, promoted from instructor-only to a bonus
  ticket; mostly wait time (engine create 5-10 min silent), which suits a
  finished-early team, and it ends with a shareable public URL running
  THEIR persona. PREREQ CODE CHANGE: deploy/build_engine_app.py hardcodes
  the solution package (REPO/"solution"/race_engineer + its rewrite regex)
  — it must respect AGENT_PACKAGE or students would deploy the reference,
  not their build; same for deploy_frontend's baked env. Alternates if any
  ticket dies: AM countdown timers on the tower, radio transcript log w/
  replay. The new-curated-Toolbox-tool idea stays in T4's menu, NOT on the
  board (no double-listing).
  **Requires one GIVEN-product addition (ours, not a student ticket):
  FINISH RACE** — SIM-bar button + simulator /seek endpoint jumping the
  cursor to ~10s before the final frame, then playing out naturally so the
  chequered state lands. Key insight: BQ already holds the whole race and
  access is gated only by race_wall_time_ns, so finishing = moving the
  clock; no event flood, no State Writer load. Firestore's event log gets
  a gap for skipped laps — fine, the debrief is a history-tools job.
  Side benefit: instructor rehearsals + Test 1 get a fast path to
  end-of-race states (cf. the verify race-done finding). Test 2 does not
  budget-validate board tickets; sanity-poke one or two.
- T4 arming-rule exercise: spec it in STUDENT_GUIDE or leave as an open
  prompt? Decide in P2.

---

## How to use this doc

Same workflow as PROGRESS.md: update after every completed chunk — move
checkboxes, add findings, record timing numbers from the acceptance tests.
Claude maintains a canonical copy in its workspace and applies targeted edits
per chunk; after each update, Claude presents the latest version and Patrick
overwrites his local `PACKAGING.md` in the repo. If this conversation ends
abruptly, a fresh session reading this doc + the repo should know exactly
where packaging stands and what's next.