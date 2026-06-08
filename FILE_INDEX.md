# File Index

A map of every file and folder in this repo, with a one-line description of
each. Lost? Start here. (Building the agent? `STUDENT_GUIDE.md` walks you to
just the files you touch — you don't need this map.)

## Top-level docs

| Path | What it is |
|---|---|
| `README.md` | Front door — what this is, quick start, architecture sketch, repo map. |
| `STUDENT_GUIDE.md` | The hackathon build guide: the six tiers (A–F), commands, and context for students. |
| `RUN_OF_SHOW.md` | For whoever runs the event: morning-of checklist, the 20-min opening, checkpoints, the Tier B/C set-piece. |
| `DEMO.md` | Demo choreography: question bank, Attack Mode explainer, how to drive a live showing. |
| `HOW_IT_WORKS.md` | Architecture deep-dive — how the data plane, agent, and frontend fit together. |
| `BONUS.md` | The Tier F stretch board: optional extensions for teams that finish early. |
| `PACKAGING.md` | Living Phase-2 record — packaging decisions and findings for the deliverer. |
| `SMOKE_TEST.md` | ~15-min validation pass for a fresh deployment (setup gate + agent/time-honesty/overtake/pit-wall checks). |

## Setup & deploy

| Path | What it is |
|---|---|
| `activate.sh` | Sources the dev environment (venv + project/region env). Run in every new Cloud Shell tab. |
| `demo.sh` | One-command launcher for the LOCAL pit wall. |
| `setup/` | The numbered, student-facing setup ladder (run these). |
| `setup/all.sh` | One-command data-plane setup: runs steps 1–6, then verifies. |
| `setup/1_enable_apis.sh` … `6_deploy_simulator.sh` | The six setup steps, each wrapping a `deploy/` script. |
| `setup/7_deploy_cloud.sh` | Optional instructor extras: Agent Engine + public Cloud Run pit wall. |
| `setup/verify.sh` | Green-light check over the deployed data plane (expects 14/14 tools). |
| `setup/verify_checks.py` | The actual verification logic invoked by `verify.sh`. |
| `setup/_lib.sh` | Shared helpers for the setup scripts (source, don't execute). |
| `setup/all.sh` | (see above) |
| `deploy/` | The underlying deploy scripts that the numbered `setup/` steps call. |
| `deploy/enable_apis.sh` | Enables the required GCP APIs. |
| `deploy/deploy_toolbox.sh` | Deploys the MCP Toolbox to Cloud Run (`fe-toolbox`). |
| `deploy/setup_firestore.sh` | Provisions Firestore and its indexes. |
| `deploy/deploy_state_writer.sh` | Deploys the State Writer service. |
| `deploy/deploy_agent_engine.sh` | Deploys the agent to Vertex AI Agent Engine. |
| `deploy/deploy_frontend.sh` | Deploys the pit-wall frontend to Cloud Run. |
| `deploy/build_engine_app.py` | Stages the agent app (vendoring `shared/`) for Agent Engine deploy. |

## The agent (what students build)

| Path | What it is |
|---|---|
| `starter/` | The student package — the agent they grow from Tier A to the pit wall. |
| `starter/race_engineer/` | The student agent package. **`agent.py` is intentionally absent** — students create it with `adk create`. |
| `starter/race_engineer/config.py` | GIVEN constants (incl. the time-bridge epoch). Identical to the reference. |
| `starter/race_engineer/prompts.py` | All natural-language text. Tier E surfaces (`_VOICE`, `_CALL_TYPES`) are the student's to write. |
| `starter/race_engineer/snapshot.py` | GIVEN trigger-snapshot builder. Identical to the reference. |
| `starter/race_engineer/tools/frame_tools.py` | GIVEN live-state (Firestore) tools the agent calls. |
| `starter/race_engineer/tools/state_client.py` | GIVEN Firestore reader with a 1s TTL cache. |
| `solution/` | The complete reference (the answer key). |
| `solution/race_engineer/agent.py` | The fully-built reference agent (pure wiring). |
| `solution/race_engineer/prompts.py` | The reference prompts, including the production VOICE/CALL_TYPES. |
| `solution/race_engineer/config.py` / `snapshot.py` | Reference config and snapshot builder. |
| `solution/race_engineer/tools/frame_tools.py` / `state_client.py` | Reference frame tools and Firestore reader. |
| `solution/scaffold/agent.py` | The Tiers A–C answer-key shape of `agent.py` (one raw-SQL tool). |

## Tools (BigQuery)

| Path | What it is |
|---|---|
| `toolbox/tools.yaml` | MCP Toolbox config — the 14 BigQuery tools (11 curated + schema discovery + SQL escape hatch). |

## Shared library

| Path | What it is |
|---|---|
| `shared/agent_pkg.py` | The `AGENT_PACKAGE` seam — selects starter vs. solution at load time. |
| `shared/models.py` | Pydantic models for the Firestore contract (RaceState, CarState, Event). |
| `shared/scorer.py` | The pure, deterministic significance scorer — decides WHEN the engineer speaks. |
| `shared/script_env.py` | Venv sanity check used at the top of repo scripts. |

## Frontend (the pit wall)

| Path | What it is |
|---|---|
| `frontend/main.py` | FastAPI + websocket service streaming live state and the engineer's radio calls. |
| `frontend/agent_client.py` | Agent invocation seam — one interface, two runtimes (local / engine), two packages. |
| `frontend/engineer_loop.py` | The trigger loop as a service component (scores state, fires the agent). |
| `frontend/stt.py` | Push-to-talk speech-to-text (Cloud Speech V2, Chirp). |
| `frontend/tts.py` | The engineer's voice — server-side text-to-speech (Chirp). |
| `frontend/static/index.html` | The pit-wall UI (tower, radio log, SIM bar). |
| `frontend/Dockerfile` | Container build for the frontend service. |
| `frontend/requirements.txt` | Frontend Python dependencies. |

## Data plane services

| Path | What it is |
|---|---|
| `state_writer/main.py` | State Writer — Pub/Sub push → Firestore (RaceState + Event docs). |
| `state_writer/Dockerfile` / `requirements.txt` | Container build and deps for the State Writer. |
| `simulator/` | The race replayer — plays Berlin 2024 R10 back at race pace onto Pub/Sub. |
| `simulator/src/main.py` | FastAPI entrypoint: loads frames, starts the publisher, exposes control endpoints. |
| `simulator/src/config.py` | Startup configuration. |
| `simulator/src/frame_loader.py` | Loads the precomputed frames file into memory. |
| `simulator/src/publisher.py` | Pub/Sub publisher with the replay loop. |
| `simulator/src/replay_clock.py` | Monotonic, pause- and speed-aware replay clock. |
| `simulator/notebooks/build_frames.ipynb` | One-time notebook that builds the calibrated frames file from cleaned R10 data. |
| `simulator/deploy.sh` | Deploys the simulator to Cloud Run (`fe-simulator`). |
| `simulator/Dockerfile` / `requirements.txt` / `README.md` | Container build, deps, and docs for the simulator. |

## Notebooks

| Path | What it is |
|---|---|
| `notebooks/bq_setup.py` | Loads the cleaned Berlin 2024 R10 Parquet files from GCS into BigQuery. |

## Scripts (dev & test harnesses)

| Path | What it is |
|---|---|
| `scripts/agent_chat.py` | Terminal chat harness with full tool-call visibility and per-step latency. |
| `scripts/local_test.py` | Local trigger harness — the agent decides when to speak (what the frontend reimplements). |
| `scripts/stage_probe.py` | Tier A/B rehearsal probe — batch-runs the scripted demo questions and grades the checkpoints. |
| `scripts/test_frame_tools.py` | Validates the agent's frame tools against live Firestore (Tier D). |
| `scripts/engine_smoke.py` | Smoke test for the deployed Agent Engine instance. |
| `scripts/toolbox_test.py` | Validates every Toolbox tool against a running Toolbox server. |
| `scripts/reset_race_state.py` | Wipes Firestore RaceState + events for a clean replay session. |
| `scripts/seed_test_state.py` | Seeds Firestore with a known test frame (no simulator needed). |
| `scripts/env_check.sh` | Verifies the Cloud Shell environment is ready (run after `activate.sh`). |

## Docs (assets)

| Path | What it is |
|---|---|
| `docs/architecture.svg` | The system diagram: data plane, the A–F agent journey, and the pit wall. |

## Project root files

| Path | What it is |
|---|---|
| `pyproject.toml` | Project metadata and the editable-install definition. |
| `requirements.txt` | Top-level Python dependencies. |
| `.gitignore` | Ignored paths (caches, venvs, local env, transcripts). |
