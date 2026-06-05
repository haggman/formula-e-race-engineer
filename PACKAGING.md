# PACKAGING.md — Phase 2 Progress — Formula E Race Engineer (Challenge 2)

**Repo:** [haggman/formula-e-race-engineer](https://github.com/haggman/formula-e-race-engineer)
**Last updated:** 2026-06-05 (P1.1 complete and regression-verified; P1.2 delivered, awaiting regression)

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

P1.1 (the `agent/` → `solution/` rename) is DONE — sed-script migration,
zero stragglers, compile clean, seed + frame-tools + agent_chat regression
passed (2026-06-05). P1.2 (the AGENT_PACKAGE seam) is delivered as four
updated files: `frontend/agent_client.py`, `frontend/engineer_loop.py`,
`frontend/main.py`, `activate.sh`.

**Next action: P1.2 regression (local frontend stint), then chunk P1.3 —
vendor the simulator.**

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
- [ ] **P1.2 — AGENT_PACKAGE seam.** DELIVERED, awaiting regression. Design
  as built (refines the planning row above): `AGENT_PACKAGE` is the PACKAGE
  path (`solution.race_engineer`, later `starter.race_engineer`), not the
  agent-module path — `frontend/agent_client.py` exposes
  `agent_module(sub)` (importlib) and LocalAgentClient grabs
  `agent_module("agent").root_agent`. `engineer_loop.py` AND `main.py` both
  resolve config/prompts/snapshot/state_client through the seam — main.py is
  included so the whole frontend shares ONE state_client module (and its
  Firestore-client singleton) instead of splitting singletons across two
  packages. Code default is `solution.race_engineer`; `activate.sh` exports
  the same default for now and FLIPS to `starter.race_engineer` in P1.4 when
  the starter exists. The deployed engine-mode container never sources
  activate.sh, so it stays on the code default (solution) — correct for the
  instructor's cloud deploy. Regression: local frontend stint with the
  default (zero behavior change vs. P1.1), plus a bogus-package run proving
  the seam fails loudly.
- [ ] **P1.3 — Vendor `simulator/`.** Move the sim repo's contents in; one
  deploy from the new path to prove `--source .` still works; archive the old
  repo with a pointer.
- [ ] **P1.4 — `starter/` extraction.** Per the content-split decision above,
  including the guarded `__init__.py` and the pyproject addition.
- [ ] **P1.5 — `setup/` scripts** per the table above, including verify.sh.
- [ ] **P1.6 — Desk-check tests.** Seed-mode frame tools, toolbox_test, a
  local_test stint, and a starter-T1 smoke: does a frame-tools-only agent
  (Toolbox TODO unfilled) answer "where are we?" in the given frontend without
  crashing anything?

### P2 — Docs

- [ ] STUDENT_GUIDE.md (tiers, the local/GCP line, one testing surface per
  tier, FE context seeded from DEMO.md, question bank)
- [ ] RUN_OF_SHOW.md (morning-of table with Test-1 timings, the opening
  script, tier checkpoints with what-to-say, troubleshooting table from the
  restart-resilience pass)
- [ ] README router rewrite
- [ ] DEMO.md touch-ups (paths post-rename; opening choreography cross-ref)
- [ ] Mark docs/PACKAGING_BRIEF.md superseded (header note)

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
