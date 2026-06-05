# Fork 2 Progress — Formula E Race Engineer Agent

**Repo:** [haggman/formula-e-race-engineer](https://github.com/haggman/formula-e-race-engineer)  
**Build doc:** [Challenge 2 Build Document](https://docs.google.com/document/d/16NqXYak3NSLkNq__ycyMNDbz-5f6bug4NHlINiCxoV4/edit)  
**Last updated:** 2026-06-05 (chunk 13 complete — frontend live on Cloud Run in engine mode; Toolbox auth flip deliberately descoped; full demo URL exists)

---

## Where we are

Chunks 1–13 complete. The whole stack is deployed: simulator → State Writer
→ Firestore, agent on Agent Engine, and now the pit-wall frontend on Cloud
Run (public demo URL), talking to the engine via the AGENT_MODE seam.
Triggers, Q&A, TTS, and push-to-talk all verified against the deployed
stack at 2× and 5×. Toolbox lockdown was descoped on purpose (read-only
public data, ephemeral lab project) and documented as a production note.
Chunks 14-15 skipped by decision: the Fork 2 BUILD is complete. Current
effort is Phase 2 — packaging for the 3-hour hackathon room (see In
progress and docs/PACKAGING_BRIEF.md).

---

## Decisions locked

| Area | Decision |
|---|---|
| **Driver** | Car #13 — António Félix da Costa (R10 winner, P10→P3 by lap 5 charge, 9 scenario armings) |
| **Architecture** | Three services + Firestore. **State Writer** (Pub/Sub push → Firestore) handles ingestion; **Agent** (Agent Engine) handles reasoning; **Frontend** (Cloud Run) handles UX, significance scoring, agent invocation. Firestore is the integration point — single source of truth for current race state and events. All three services stateless. |
| **Service topology** | (1) Simulator on Cloud Run → fe-telemetry Pub/Sub. (2) State Writer on Cloud Run subscribes to topic, writes RaceState + Event docs to Firestore. (3) Agent on Agent Engine reads Firestore via frame tools + BigQuery via MCP Toolbox. (4) Frontend on Cloud Run reads Firestore for live UI, runs significance scorer, invokes Agent. |
| **Shared models** | `shared/` package at repo root holds canonical Pydantic models for RaceState, CarState, Event. Both State Writer and Agent import from it. Single source of truth for the Firestore contract. Engine deploy vendors `shared/` into the staged app (see Engine deploy row). |
| **Model** | `gemini-3.5-flash` (switched from gemini-3-flash-preview in chunk 6), `GOOGLE_CLOUD_LOCATION=global`. Shared `GenerateContentConfig` on the agent adds exponential-backoff retries (10 attempts, 0.5s→4s, jitter) for 408/429/5xx. |
| **Agent runtime** | Vertex AI Agent Engine, deployed via `adk` CLI |
| **Agent invocation (frontend)** | `frontend/agent_client.py` seam: `AGENT_MODE=local` (InMemoryRunner in-process — the permanent dev path) vs `AGENT_MODE=engine` (deployed engine via agent_engines SDK). Engine calls run as SYNC SDK methods inside `asyncio.to_thread` (the SDK blocks the event loop, async_* variants included). Triggers AND Q&A both go remote in engine mode — settled by live stint comparison vs the chunk 8 baseline. Hard RunConfig tool ceiling is local-only; engine mode substitutes wall-clock timeouts (FIRE_TIMEOUT_S=30 / ASK_TIMEOUT_S=75) + drop-on-empty. |
| **Engine deploy** | Self-contained `build/engine_app/` staged by `deploy/build_engine_app.py` (vendors `race_engineer` + `shared`, rewrites imports, bakes `.env` with TOOLBOX_URL + PROJECT_ID); `adk deploy agent_engine` via `deploy/deploy_agent_engine.sh`; resource name persisted in `deploy/.engine_resource` so re-runs UPDATE the same engine. |
| **Frames artifact** | `frames_v3.jsonl.gz` (schema 1.2) — v1: broken top speeds + overtake noise; v2: real top speeds, zero-change overtakes dropped; v3: overtake subjects remapped grid→car. Versions kept side by side, never overwritten. |
| **BQ tooling** | MCP Toolbox for Databases — curated named queries + one SQL escape hatch. Hybrid documented in lab; we use Toolbox for the build. |
| **BQ dataset region** | us-central1 (matches bucket) |
| **State store** | Firestore Native mode, `(default)` database in lab project, free-tier sufficient. Two collections: `race_states/(default)` for current RaceState doc, `race_events/{auto-id}` for individual Event docs indexed by ts_ns, race_time_s, event_type, car_number. |
| **Frontend** | FastAPI + websocket on Cloud Run. Reads Firestore for live state, runs significance scorer, calls agent on triggers, browser UI, TTS/STT. |
| **Voice in** | Push-to-talk via MediaRecorder API → Cloud Speech-to-Text v2 |
| **Voice out** | Cloud Text-to-Speech, Chirp 3 HD British male, 1.15× rate |
| **Agent persona** | Second-person ("Antonio, ..."), real engineer style. ~6-8s spoken radio calls. No editorializing. |
| **Per-lap summary template** | Position, gaps, energy state, AM state, optional one-line strategic note |
| **Significance scorer** | Deterministic, lives in frontend, debounced (no trigger within 15s of last) |
| **Agent sessions** | Fresh per trigger for proactive announcements; persistent session for Q&A follow-ups |
| **Toolbox auth** | DESCOPED (decided end of chunk 13): stays `--allow-unauthenticated` for the lab. Threat model: read-only queries over public 2024 sports data, ephemeral Qwiklabs project, unguessable URL — worst case is pennies of BQ scan. Auth effort went where it protects state (State Writer OIDC push). Production note documented in tools.yaml/DEMO: grant the Agent Engine service agent `run.invoker` on fe-toolbox, drop `--allow-unauthenticated`, verify the toolset sends identity tokens. |
| **Pub/Sub flow** | Single subscriber: State Writer service via push subscription. Pub/Sub never reaches frontend or agent directly. |
| **R09 inclusion** | Not loaded — R10 only for Fork 2. R09 deferred. |
| **Demo stint** | Laps 1–10, anchored by lap-3 AM cluster (DAC was *not* in the cluster — strategic hold-back, contrary to ~13 cars who activated). |
| **BQML** | Stretch / Task 7 only. Not in core reference. Pattern stub may appear later for extraction into Fork 5 starter. |
| **Event-stream tool** | Built here in Fork 2; Fork 5 extracts starter version |
| **Gemini Live** | Stretch demo addition after core works. Push-to-talk + STT/TTS is the canonical path. |
| **Deploy style** | Source deploys (`gcloud run deploy --source .`) when the repo IS the app (simulator). Explicit Dockerfile + `gcloud builds submit --config` for services carved from this monorepo (state_writer, frontend): the build context must be the repo root to COPY `shared/`/`agent/`, two services can't share one root Dockerfile, and Buildpacks would install the dev requirements.txt (ADK, Toolbox — bloat plus the import trap). Teaching line: same container either way; the only difference is who writes the build recipe. |
| **Env target** | Qwiklabs student labs. Cloud Shell with Cloud Shell Editor as dev environment. Per-team GCP projects, ephemeral. |
| **Python** | 3.12, default in Cloud Shell |
| **Virtual env** | `.venv/` at repo root, created and activated by `source activate.sh` |
| **Region convention** | All scripts read `REGION` from env (set by `activate` to us-central1 default, override before sourcing). Bucket reference to `gs://class-demo` stays hardcoded — published artifact at known location. |

---

## Built so far

### Chunk 1 — Repo scaffold ✅

Files committed:
- `README.md` — architecture overview, race context, quick start
- `.gitignore` — Python + IDE + env defaults
- `scripts/env_check.sh` — Qwiklabs environment verifier (gcloud, bq, python version, bucket access)

Verified: Cloud Shell environment ready, `gs://class-demo/formula-e/` readable by Qwiklabs student account, Python 3.12.3 installed.

### Chunk 2 — BQ Setup (+ telemetry extension) ✅

`notebooks/bq_setup.py` — single Python script with `# %%` cell markers (runs end-to-end, or step-through in Editor/Colab/VS Code).

Loaded into BigQuery dataset `fe_race10` (us-central1):

| Table | Rows | Notes |
|---|---|---|
| `drivers` | 22 | Entry list with team/manufacturer |
| `startgrid` | 22 | Starting positions (DAC P10) |
| `laps` | 854 | Per-lap timing — `top_speed` column broken, ignore |
| `attack` | 129 | 44 activations + 44 deactivations + 41 scenario armings |
| `energy_per_lap` | 852 | Per-lap energy as % of budget |
| `racecontrol_classified` | 76 | RC messages with derived category |
| `event_stream` | 1,787 | Unified events (overtakes, AM, RC, laps) |
| `career_driver` | 87 | All FE drivers career stats |
| `career_race` | 2,799 | 10 seasons of FE results |
| `telemetry` | 1,281,780 | 20 Hz GPS+motion, Hive-partitioned + clustered on `car_number` |
| `top_speed_per_lap` | 854 | One-shot CTAS — recovers real top speeds from telemetry MAX |

Plus 3 views: `v_laps_with_driver`, `v_am_with_driver`, `v_overtakes`.

### Chunk 3 — MCP Toolbox (+ top_speed_history extension) ✅

`toolbox/tools.yaml` declares 11 tools in the `race-engineer` toolset:

1. `get_driver_info` — car number → name, team, manufacturer, grid pos
2. `get_lap_history` — per-lap timing (no top_speed; that's its own tool)
3. `get_top_speed_history` — real top speeds from materialized table
4. `get_energy_curve` — per-lap energy with field-average delta
5. `get_recent_race_control` — last N RC messages before time T
6. `get_am_activations` — field-wide AM on/off events
7. `get_am_armings` — per-driver scenario arming events (strategic intent)
8. `get_overtakes_involving` — overtakes for or against a car
9. `get_driver_career_stats` — career wins/podiums/poles by driver code
10. `get_field_position_at_lap` — full field snapshot at end of lap N
11. `execute_sql_bq` — SELECT-only escape hatch with schema docs

Toolbox binary v1.3.0 in `toolbox/` (gitignored). `scripts/toolbox_test.py` validates all 11 tools via the `toolbox-core` SDK against `localhost:5000` or `$TOOLBOX_URL`.

**Post-chunk cleanup:** `get_lap_history` and `get_field_position_at_lap` no longer return broken `top_speed_kmh` zeros — agent steered to `get_top_speed_history` instead. `execute_sql_bq` description now documents INT64-ns convention for time columns.

### Chunk 4 — MCP Toolbox to Cloud Run ✅

`deploy/deploy_toolbox.sh` — idempotent deploy of MCP Toolbox v1.3.0 to Cloud Run.

Deployed service: `fe-toolbox` in us-central1
- Image: `us-central1-docker.pkg.dev/database-toolbox/toolbox/toolbox:1.3.0`
- Service account: `fe-toolbox-sa` with `roles/bigquery.dataViewer` + `roles/bigquery.jobUser`
- Tools config: `tools.yaml` staged in `${PROJECT_ID}-fe-toolbox` GCS bucket, mounted at `/tools/tools.yaml` via Cloud Run GCS volume
- Resources: 1 CPU / 512Mi memory / cpu-boost on / min-instances=1 / max-instances=3
- Open auth (`--allow-unauthenticated`) — will flip to service-account invoker in chunk 13

All 11 tools validated against deployed URL via `toolbox-core` SDK 1.1.0.

### Chunk 4.5 — Cleanup pass ✅

Three concerns addressed before starting chunk 5:

- **Virtual environment** — `.venv/` at repo root, gitignored. Created by `source activate.sh`.
- **Activate script** — `activate.sh` at repo root (`source activate.sh`) sources venv + sets env vars + installs requirements (idempotent via stamp file). One command per Cloud Shell session. Verbose install output (grep-filtered) so students see what's installing.
- **Region as env var** — all scripts now read `REGION` from env, no hardcoded defaults in application code. `activate` script sets the default (us-central1). Students override with `export REGION=...` before sourcing if their lab assigns a different region.

Files added/changed:
- `activate` (new) — venv + env setup
- `deploy/setup_firestore.sh` (new) — created here so chunk 5 can run it
- `scripts/env_check.sh` — now checks venv active, REGION, PROJECT_ID
- `notebooks/bq_setup.py` — reads REGION from env, raises if unset
- `deploy/deploy_toolbox.sh` — reads REGION from env, fails fast if unset
- `.gitignore` — added `.venv/`
- `README.md` — Quick Start updated for `source activate.sh` flow
- `requirements.txt` — expanded to cover chunks 5-11 (BQ, Toolbox, Firestore, Pydantic, ADK, Agent Engine, FastAPI, Pub/Sub, TTS, STT). Strict pins only on `toolbox-core==1.1.0` and `google-adk>=1.0,<2`; everything else uses floors so pip can resolve a coherent matrix.

env_check: 14/14 pass. bq_setup.py re-ran cleanly with env-driven config.

### Chunk 5 — Data plane (State Writer + frame tools + frames_v2) ✅

The architecture pivot to three services (Simulator → **State Writer** → Firestore ← Agent + Frontend) landed here. Shared Pydantic models in `shared/` are the Firestore contract for both Writer and Agent.

**Built in this repo:**
- `shared/models.py` — RaceState, CarState, Event, EventType + nested state models (frame schema v1.x)
- `shared/script_env.py` — `require_venv()` fail-fast guard for scripts
- `state_writer/` — FastAPI Cloud Run service: Pub/Sub push → validate → Firestore. **Idempotent**: event docs use deterministic IDs (`race_id_raceTime_type_car_dataHash`), so Pub/Sub redelivery and full replays overwrite instead of append
- `agent/race_engineer/tools/` — `frame_tools.py` (4 tools: current state, recent events, events in range, field AM status) + `state_client.py` (Firestore reader, 1s TTL cache on RaceState)
- `deploy/deploy_state_writer.sh` — Cloud Build image (bundles `shared/`), Cloud Run deploy, OIDC-authenticated Pub/Sub push subscription
- `deploy/setup_firestore.sh` — Native-mode DB + 3 DESC composite indexes on `race_events`
- `scripts/seed_test_state.py` — canonical t=1449 sample frame (direct Firestore or via `/ingest`)
- `scripts/test_frame_tools.py` — seed mode (exact asserts) + `--live` mode (structural + data-quality asserts incl. nonzero top speeds)
- `scripts/reset_race_state.py` — wipes RaceState + race_events between replay sessions

**Built in the simulator repo (companion):**
- `frames_v2.jsonl.gz` (schema 1.1) — notebook Cell 13 post-process: real per-lap top speeds from 20 Hz telemetry (anchor-validated against BQ `top_speed_per_lap`), dropped 532 of 1,248 zero-change overtake events (43% noise). Defaults flipped to v2 in `config.py`/`deploy.sh`; index footer made dynamic.

**Deployed + verified:** `fe-state-writer` and `fe-simulator` on Cloud Run; live 5× replay flowing end-to-end; `test_frame_tools.py --live` green; replay idempotency proven via jump-back to t=0 (car-13 lap_completed count: 7 before → 7 after re-ingesting the same window).

### Chunk 6 — Agent definition (4 passes) ✅

- **Pass 1 — skeleton + frame tools.** `agent/race_engineer/agent.py` (pure wiring) + `prompts.py` (all NL text). Model `gemini-3.5-flash`, shared `GenerateContentConfig` with exponential-backoff retries. Four frame tools registered. Time bridge: `RACE_START_EPOCH_NS = 1_715_519_045_726_000_000` (exact int) in config; `race_wall_time_ns` field on state/AM responses for BQ `through_time_ns`. Smoke-tested in `adk web` (requires `--allow_origins "*"` behind Cloud Shell Web Preview).
- **Pass 2 — MCP Toolbox wired.** `ToolboxToolset` from `google-adk[toolbox]` (delegates to `toolbox-adk`, coexists with `toolbox-core==1.1.0` pin), `TOOLBOX_URL` auto-discovered by `activate.sh`. Adversarial mid-race test PROVED the time bridge (race control at t=655 returned only the past). Live testing found+fixed: ADK passes enum args as strings (frame tools now take `list[str]`, coerce internally); sync `runner.run()` spins a loop per question and kills the toolset (chat harness rewritten fully async).
- **Pass 2.5 — Toolbox refinement.** New `get_lap_time_windows` (lap↔ns mapping); BQ metadata discovery tools `bigquery_list_table_ids` + `bigquery_get_table_info` (structure from metadata, semantics in descriptions); `execute_sql_bq` docs rewritten semantic-only. Result: discovery-first SQL with zero guessed-column errors. Fixed latent `SERVICE_NAME` unbound var in `deploy_toolbox.sh`.
- **Pass 3 — persona.** Radio voice (second person, 6-8s proactive calls, no editorializing, no markdown), TTS normalization, three call templates (event reaction / lap summary / Q&A), racing doctrine (AM scenarios, arming vs activation, energy normalization, no invented time-gaps), honesty rules, debug carve-out. Live grading found+fixed: replay-clock leak (model used events' `ts_ns_wall` as `through_time_ns` → `AgentEvent` slim view hides it) and hallucinated driver names for unknown car numbers (names-from-tools-only rule).
- **Dev harness:** `scripts/agent_chat.py` — async terminal REPL printing every tool call + args + truncated response. The chunks 7-8 iteration surface.

### Chunk 6.5 — Overtake identity remediation ✅

Live agent testing surfaced phantom car numbers (6, 10, 12, 14, 15, 19, 20) in overtake events. Investigation via position-adjacency scoring across all 728 overtake records proved: **in the source overtake stream, `car_number` is the subject's GRID POSITION (domain 1-22); `attrs_json.other_car` is a real car number** — two ID domains in one record. Gap-distribution histogram confirmed (grid_car: monotonic decay from gap≤1 mode, 679/728 scored; car_car control: 40% mass at gap>8). Every prior overtake attribution was wrong except by grid coincidence.

Fixed end-to-end:
- `bq_setup.py` — `v_overtakes` rebuilt: grid join resolves subject, both participants as real cars + driver codes, `human_summary` REGENERATED (source strings embed grid IDs — poisoned)
- `tools.yaml` — `get_overtakes_involving` rewritten against the fixed view; `car_pattern` LIKE hack eliminated
- `frames_v3.jsonl.gz` (schema 1.2) — standalone notebook Cell 14 remaps overtake subjects through the grid map; validated (716 remapped, 0 unmappable, all 7 cars >22 now appear as subjects, DAC tops involvement at 51)
- Firestore reset + clean v3 replay; `test_frame_tools.py --live` green

### Chunk 7 — Significance scorer + local trigger harness ✅

- `shared/scorer.py` — PURE deterministic scoring (no I/O, no clocks; caller owns debounce). Tunable weights at top. Rules: our overtakes both directions (passed=90 > passing=80), our AM transitions (85/75), field AM cluster via caller-supplied 30s lookback (75, the lap-3 detector), neighbor AM activation (65), RC severity by category prefix (bumped to 88 if the message names us), net position swing vs previous check (60+5/place). Guard: the source data's one self-overtake glitch row (subject==other==13) never scores. Lives in shared/ so the chunk 9 frontend imports it unchanged.
- `scripts/local_test.py` — async poll → score → fire loop on agent_chat's Runner pattern. Fresh session per proactive call (per locked decision); the TRIGGERING SNAPSHOT rides in the prompt (state + events, authoritative for the call) so the agent doesn't re-fetch a moved-on world — proactive calls run 1-2 tools instead of 16. Lap summaries scheduled on lap change (completed lap >= 1; lap 0->1 is the green flag), never scored. Wall-clock debounce (15s default — race-time debounce breaks at replay speed). Failed calls DROP with a 5s cooldown (a late radio call is worse than a missed one); drops counted, loop survives. Triggers processed one at a time — an engineer has one mouth.
- Trigger prompt builders appended to prompts.py (event reaction + lap summary, both with a stated 2-tool budget).
- **Validated, laps 1-10 at 2x replay:** lap-3 AM cluster fired as ONE call ("five cars just activated... Evans and Vandoorne are holding off. Stay in the train") — detector saw the full 12-activation wave; lap summary template adherence solid (9.2s, 1 tool call); persona held across all calls; 429 drop handled gracefully mid-run.
- **Quota reality:** Qwiklabs shared Gemini quota can 429 through 10 retries at 5x replay trigger density. Mitigations: 2x replay for trigger development (5x stays fine for Q&A), harness drop-don't-crash, max_delay bumped 4->8s.

### Chunk 8 — Reasoning iteration ✅ (all five work-order items closed)

1. **Per-type debounce** ✅ — must-say candidates (our AM, critical RC) pierce to `--must-say-gap` (5s) AND are HELD until deliverable (pending slot, capacity 1, fresh snapshot at delivery, survives dropped calls, 25 race-s TTL). Without the hold, a gap-blocked must-say evaporated — per-event rules score new events only. `--summary-every 2` guarantees summaries; `[OVERDUE]` outranks normal events. Validated: all three AM moments in the stint announced, with correct per-scenario durations ("sixty seconds" / "three minutes" — scenario 1 short-first).
2. **Tool budget** ✅ — three layers: hardened prompt language, `RunConfig(max_llm_calls=4)` per trigger (breach raises `LlmCallsLimitExceededError`), drop-on-breach via safe_fire. Fired in anger once: killed a 4-call wander that had guessed SQL columns (skipping discovery under pressure) — correct outcome, a late call is worthless.
3. **Latency** ✅ — typical 8-13s, summaries ~10s; remaining 18-26s outliers correlate with quota-side slowness (2 tool calls), not tool wandering. Acceptable for the 1× demo.
4. **Filler scrub** ✅ — persona rule: instructions must be CONCRETE (target, action, place) or OMITTED; banned-phrase list. Validated clean across a full stint. Finding: prompt EXAMPLES leak as templates ("lift and coast into turn six" / "defend the inside of one" echo the prompt's examples) — plausible engineer-speak, accepted for demo, logged.
5. **Fact-check vs ground truth** ✅ — DAC end-of-lap positions laps 1-12 (P6,6,6,6,3,2,1,3,2,1,1,1): every end-of-lap-anchored claim in the transcripts exact, including the attack-loop detour narration (leading lap 7 → activates → P3 at the lap-8 line) and both AM durations. Safety car ~lap 11-12 confirmed via lap times (76s/102s). Summaries describe "now" (a few seconds into the next lap), not the line — by design. One ambiguous mid-lap claim led to the snapshot echo in verbose mode, so future grading is decidable.

Last scoreboard: fired {event_reaction 5, lap_summary[OVERDUE] 5, lap_summary 1, MUST-SAY 3}, suppressed 31, dropped 1 (budget ceiling).

### Chunk 9 — Frontend service ✅ (three passes + cockpit polish)

- **Pass 1 — skeleton.** `frontend/main.py`: FastAPI app, `/ws` websocket, lifespan-managed state poller broadcasting the FULL field (`ui_state` — all 22 cars, AM state, retirements) at 1s cadence. `frontend/static/index.html`: single-page pit-wall UI, no build step, vanilla JS with reconnect/backoff. The UI and the agent intentionally get different views of RaceState (full tower vs trimmed snapshot).
- **Pass 2 — the engineer in-service.** `frontend/engineer_loop.py`: the chunk 8 trigger policy verbatim as an `EngineerLoop` background task — must-say hold, sticky overdue summaries, budget ceiling, drop-don't-crash with cooldown — broadcasting `{type:"radio"}` instead of printing. `snapshot_dict` moved to `agent/race_engineer/snapshot.py`, shared by harness and frontend (local_test.py imports it).
- **Pass 3 — Q&A.** ASK bar over the same websocket. Persistent session (`pit-wall-qa`) per the locked decision — follow-ups keep context. Q&A tool ceiling 12 vs triggers' 4 (a human asked; research allowed, runaway not). Questions echo to all clients tagged YOU; answers interleave with proactive calls; failures degrade in-character ("Radio failure on that one — ask again."). Verified live: a quantified energy-vs-rival answer landed while event calls kept firing around it.
- **Cockpit polish (demo-driven):** energy as SVG needle gauge with ▲ REGEN indicator (rises >0.05%/sample — regenerative braking made visible; demo talking point); lap-progress sweep ring, alternating colors painting over the previous lap, snap-reset at boundaries (transitions suspended for that frame); position delta badge (▲/▼ vs lap start — makes the attack-loop detour pop). Needle bug fixed: SVG attribute rotation only, never mixed with CSS transform-origin.
- **SIM systems bar:** restart / pause-resume / speed (1×/2×/5×) / LOOP (the sim's auto-restart), proxied server-side via `/api/sim/*` (whitelisted actions, `SIM_URL` env) — no CORS, sim URL stays out of the browser; bar re-syncs from `/config` after restart. `/jump` deliberately excluded from the UI.
- **Restart robustness (both sides):** the engineer loop detects race time going backwards and flushes all trigger state (the stale `last_summary_lap` from a previous run had silently disabled summaries); the browser flushes lap/energy tracking when the lap number drops.
- New deps: fastapi, uvicorn[standard], httpx (requirements.txt, floors).
- Known cosmetic, deferred to the next UI pass: lap-1 ring calibrates from the pre-race countdown (t≈−10s), so it fills ~10s early and sits full until lap 2.

### Chunk 10 — TTS ✅ (the engineer speaks)

- `frontend/tts.py` — async Cloud TTS client, Chirp 3 HD `en-GB-Chirp3-HD-Charon` at 1.15× (both env-overridable: TTS_VOICE / TTS_RATE). Failure policy: a lost voice is not a lost call — synthesis errors log and the message goes out text-only.
- Architecture: `radio_broadcast` wrapper in main.py synthesizes before fan-out — `engineer_loop.py` needed ZERO changes (it already took a broadcast callback). One synthesis per call regardless of connected browsers; audio travels base64-in-message (~6s calls ≈ 100-200KB), atomically with its text. Questions (kind=question) stay silent; Q&A answers speak.
- Browser: 🔇/🔊 header toggle (the click is the autoplay-unlock gesture); sequential playback queue — overlapping calls wait their turn; muting clears the backlog.
- Normalization design fix: the chunk-6 "write words as SAID" rule produced inconsistent spelled-out numbers ("seventy-three point three"). Rule rewritten: ALL numbers as digits ("92.8 percent", "224 km/h", "P3") — the synthesizer reads digits perfectly, and the text log stays consistent. Sanctioned idiom exception: "two tenths" — real engineers say it; the digits rule governs readouts, not voice.
- Ear-test verdict: voice and rate land; Chirp prosody is natural but emotionally flat — acceptable, arguably on-brand for an engineer.
- `DEMO.md` (repo root) — the demo guide: two-worlds framing (Firestore now / BigQuery then), the five scripted moments of laps 1-11, a question bank organized by what each question proves (including the honesty test), pause-mid-cluster choreography, student teaching points, troubleshooting table.
- New dep: google-cloud-texttospeech (requirements, floor); `texttospeech.googleapis.com` enabled.

### Chunk 11 — STT push-to-talk ✅ (Chirp in, Gemini in the middle, Chirp out)

- `frontend/stt.py` — Cloud Speech V2, **Chirp 2** model (same family as the voice — deliberate symmetry), regional us-central1 endpoint, default `_` recognizer, project via google.auth.default(). MediaRecorder's webm/opus decodes via AutoDetectDecodingConfig — the browser sends its native container untouched. Env-overridable: STT_REGION / STT_MODEL / STT_LANGUAGE.
- `POST /api/stt` in main.py: raw audio bytes in, transcript out; failures 502 and the UI degrades politely ("Didn't catch that — try again or type").
- Push-to-talk UX: hold the 🎤 button (mouse/touch) OR hold **Space when focus is outside the question input** — in the input, space types spaces; the two modes never fight. ● REC while held; sub-second taps discarded; transcript lands VISIBLY in the input for 600ms before auto-sending (the audience sees what was heard — and you catch a mangled driver name before the agent does). Typed path untouched.
- Mic permission denial degrades to 🚫 with tooltip; Web Preview is HTTPS so getUserMedia works.
- **Lap-1 ring root cause fixed** (the deferred chunk 9 TODO): client lap tracking now refuses to initialize until lap ≥ 1 AND race time ≥ 0 — it calibrates from the green flag, not the pre-race countdown that made lap 1 fill ~10s early and sit.
- **API enablement consolidated**: `deploy/enable_apis.sh` — one idempotent step-zero script with the full inventory (run, pubsub, firestore, bigquery, aiplatform, texttospeech, speech, cloudbuild, artifactregistry — the last two pre-staged for chunk 13's containerization). Per-script enables left in place deliberately: each deploy script stays self-sufficient.
- DEMO.md grew an "Attack Mode in sixty seconds" teaching section (exactly two activations, fixed durations with no early exit, the SC clock trap, the activation-zone position sacrifice) plus a scenario question in the bank.
- New dep: google-cloud-speech (requirements, floor); `speech.googleapis.com` enabled.

### Chunk 12 — Agent Engine deploy ✅ (the agent leaves the laptop)

- **`deploy/build_engine_app.py`** — stages a self-contained `build/engine_app/`: `adk deploy agent_engine` ships ONLY the folder you point it at (no extra-packages mechanism in this CLI generation), so the repo's two top-level packages are vendored in. `race_engineer/` is copied with imports rewritten (`agent.race_engineer` → `race_engineer`); `shared/` is copied verbatim; `agent.py` is a sys.path-bootstrap shim re-exporting `root_agent` (the CLI's generated app does `from .agent import root_agent`, so the name is mandatory). Bakes `.env` (Vertex mode, `GOOGLE_CLOUD_LOCATION=global`, TOOLBOX_URL, PROJECT_ID) and a minimal engine `requirements.txt`. Idempotent: wipes and rebuilds each run; self-checks for unrewritten imports and importability before finishing.
- **`deploy/deploy_agent_engine.sh`** — stages, deploys, persists. Parses the `reasoningEngines` resource name from the deploy log into `deploy/.engine_resource`; re-runs pass `--agent_engine_id` so the SAME engine updates in place. Grants the Agent Engine service agent (`service-PROJECT_NUMBER@gcp-sa-aiplatform-re.iam.gserviceaccount.com`) `roles/datastore.user` AFTER the deploy — the service agent doesn't exist until the first deploy creates it, so post-deploy ordering is the only sequence that always works (and it's idempotent on updates). The create step is blocking with no progress output (5-10 min); the script prints a `gcloud logging read` one-liner for watching build logs from a second terminal.
- **`scripts/engine_smoke.py`** — remote smoke test: reads `.engine_resource`, prints the engine's registered operations first (so SDK method drift shows what IS available instead of a bare AttributeError), opens a session, asks one BigQuery-path question and one Firestore-path question, times each, and dumps raw events on any empty answer. `--verbose` prints tool responses.
- **Found + fixed — the project-number Firestore 404:** first smoke run answered the BigQuery question but returned EMPTY on the Firestore question; Logs Explorer showed `404 The database (default) does not exist for project 83898679865`. The database existed, APIs on, IAM correct (a permissions problem would have been 403). Root cause: Agent Engine supplies `GOOGLE_CLOUD_PROJECT` as the project **NUMBER**, and Firestore rejects number-addressed database paths with that misleading "does not exist" error. `state_client.py` preferred `GOOGLE_CLOUD_PROJECT`, which is the ID locally (activate.sh) but the number on the engine. Fix: `build_engine_app.py` bakes `PROJECT_ID` (the real ID) into the engine `.env`; `state_client.get_state_client()` now prefers `PROJECT_ID` over `GOOGLE_CLOUD_PROJECT` and warns if the resolved value is all digits.
- **Verified:** redeploy + `engine_smoke.py` green on both worlds — BigQuery via Toolbox ("Antonio, you are driving car 13 for TAG Heuer Porsche", 7.8s) and Firestore live state against a running replay ("P6. Energy is 94.1 percent remaining", 4.8s). The deploy's IAM grant ran clean in the post-deploy position.

### Chunk 13 — Frontend to Cloud Run (3 passes; auth flip descoped) ✅

- **Pass 1 — the seam.** `frontend/agent_client.py`: `LocalAgentClient` (the chunk 9-11 runner code verbatim — fresh session + RunConfig ceiling per trigger, persistent Q&A session) and `EngineAgentClient` (the deployed engine). `engineer_loop.py` rewired through `fire()`/`ask()`; every line of trigger policy untouched. `activate.sh` exports `AGENT_MODE` + auto-loads `AGENT_ENGINE_RESOURCE` from `deploy/.engine_resource` (and lost its duplicated Vertex env block).
  - **Found live + fixed: the agent_engines SDK BLOCKS the event loop — async_* variants included.** First engine-mode run: jerky lap ring, bursty state broadcasts, /api/stt unserved 20-30s — everything sharing the loop starved while engine calls were in flight. Fix: call the SYNC SDK methods (the exact ones engine_smoke validated) inside `asyncio.to_thread`; wall-clock timeouts (abandon-on-timeout = drop-a-stale-call policy). UI back to 1 Hz under load.
  - Stint validation settled the sub-fork: triggers AND Q&A both remote, latency comparable to the local band; remote persistent Q&A session survives frontend restarts (it lives on the engine).
- **Pass 2 — containerize + deploy.** `frontend/Dockerfile` + `frontend/requirements.txt` (slim: no ADK/Toolbox — the agent runtime lives on the engine; AGENT_MODE=local unsupported in-container by design). `deploy/deploy_frontend.sh`: Cloud Build from repo root with `-f frontend/Dockerfile`, SA `fe-frontend-sa` (datastore.user + aiplatform.user + speech.client), engine resource + SIM_URL baked into env, public URL. **Load-bearing Cloud Run flags, not tuning:** `--min-instances=1 --max-instances=1` (the engineer loop is a background task — scale-to-zero kills it; a second instance is a second engineer talking over the first) and `--no-cpu-throttling` (background tasks need CPU between requests; instance-based billing).
  - `agent/race_engineer/__init__.py` guarded: its eager `adk web` discovery import (needs google-adk + TOOLBOX_URL) would crash the slim container on package import. Now imports only when both are present; adk web unaffected.
  - **Found + fixed: STT dead on Cloud Run, fine in Cloud Shell** — Speech-to-Text V2 recognizers are IAM resources; the `_` recognizer needs `roles/speech.client` on the service SA. Worked in dev only via the student account's broad roles. Classic dev-vs-deployed IAM gap. (TTS has no equivalent resource-level IAM — voice out never broke.)
  - **Found + fixed: empty radio boxes** — an engine run that dies mid-flight (quota exhaustion, tool failure) can end its event stream with NO error event and NO text; locally that path raises, remotely it returned ("", n, secs) and broadcast an empty box. `EngineAgentClient` now raises on empty text → drop-with-cooldown handles it, and the must-say hold retries the call.
- **Pass 3 — auth flip → DESCOPED, documented.** See the Decisions row. The remaining technical risk (does the engine's ToolboxToolset attach identity tokens?) wasn't worth burning pre-hackathon days to harden a read-only public-data query surface in an ephemeral project. Descope is visible: production note in tools.yaml/DEMO, talking point about proportional security.
- **The quota post-mortem (humbling, instructive):** a 5× session showed GenerateContent errors with no "429" anywhere in the logs — quota was wrongly ruled out until `protoPayload.status` showed `code: 8` = gRPC RESOURCE_EXHAUSTED, which IS the 429 wearing its gRPC name. The chunk-7 finding held all along; "5× worked all day" just meant the SHARED Qwiklabs quota pool had headroom earlier. Two transient `Tool 'X' not found` errors fell inside the same storm window with ZERO failing requests at fe-toolbox (toolset load died client-side, never reached the server) — secondary, self-healing under drop policy, not chased. Operating guidance: 1× demos, 2× trigger dev, 5× lossy in proportion to quota-pool neighbors.

---

## In progress

**Fork 2 build: COMPLETE.** Chunks 14 (dry run) and 15 (BQML, Gemini Live)
skipped by decision on 2026-06-05 — the stack is functionally complete and
deployed through chunk 13. The stretch items remain documented above if
ever revisited.

**Phase 2: PACKAGING (new effort, separate planning conversation).** Turn
the reference into the hackathon product: numbered setup scripts, student
starter package, RUN_OF_SHOW.md (instructor) + STUDENT_GUIDE.md. Planning
brief: `docs/PACKAGING_BRIEF.md`. Event constraints: 3 hours (20 min open /
2:30 build / 10 min wrap), provided Qwiklabs projects (per-student or
per-team), developer audience with solid Python and limited GCP-AI
exposure, standalone event (no cross-challenge assumptions), quota
explicitly NOT a concern.

---

## Up next

Phase 2 packaging chunks — to be planned in the packaging conversation
(provisional: P1 setup scripts, P2 starter extraction, P3 the two docs,
P4 instructor-path rehearsal).

---

## Open questions

None pending external answers. All FE questions resolved (Will Allen, 2026-05-19, already in build doc).

For us:
- Whether to add a `top_speed` recovery exercise as a Fork 4 student task (deferred — likely yes)
- BQML inclusion: re-evaluate in chunk 8 once core agent is reasoning. Lean: Task 7 stretch only.

---

## Findings worth remembering

These didn't make the build doc but matter for downstream work:

**DAC strategic profile (R10):**
- Started P10
- P6 by laps 1–2, P3 by lap 5
- **Did NOT activate in the lap-3 AM cluster** (contrary to ~13 of 22 cars) — held back
- Armed 9 times across the race (most in the field) — scenario changes 2→3→1→2→3→...
- Top speed climbed smoothly 215.4 → 222.6 → 224.8 → 228.4 → 236.3 km/h over laps 1–5
- Battle profile (RE-VERIFIED post-identity-fix, both directions): top rivals CAS 11 exchanges (DAC gained 7 / lost 4 — the real fight for the win) and JEV 11 (grid neighbors P9/P10, 5/6 split); DEN passed DAC 6 times with no direct repass — the original "passed repeatedly by Dennis but recovered" finding was correct by grid coincidence (Dennis: P1 in car #1). FEN 7, GUE/DIG/NAT 4 each (against). One source glitch: a single DAC-overtakes-DAC record (subject and other both resolve to 13) — excluded from analysis.
- Won the race

**Data quirks (Fork 4 candidate gotchas):**
- `laps.top_speed` is broken (always 0). Use `top_speed_per_lap` (derived from telemetry).
- All time columns in BQ are **INT64 nanoseconds since epoch**, not TIMESTAMP — even when the source Parquet declared TIMESTAMP type. BQ autodetect preserved nanosecond precision by storing as INT64.
- Affected columns: `event_stream.t`, `laps.start_time`, `attack.eth_arrival_time`, `telemetry.time`, `racecontrol_classified.time`, all `loop_sectors_*_time`, `pit_out_time`.
- Compare directly, no `UNIX_MICROS` or `TIMESTAMP_MICROS` needed.

**AM data model:**
- `attack` table has THREE row types:
  - `active=true` rows → activation events (scenario column NULL — scenario lives only in arming rows)
  - `active=false` rows → deactivation events
  - `active=NULL` rows → scenario arming events (strategic intent, no actual deployment)
- Agent reasoning for "what scenario is this car currently on?" requires walking back to most recent arming row.
- Total of 44 activations, 44 deactivations, ~41 armings in R10.

**BQ Toolbox parameter binding gotcha:**
- `bigquery-sql` kind parameters can only be substituted as VALUES into a fixed SQL statement, not as expressions or as the statement itself.
- For arbitrary SQL pass-through, use `bigquery-execute-sql` kind (no parameters/statement block, agent passes `sql` field on invoke).
- For LIKE pattern building, pre-construct the pattern as a separate string parameter rather than building it inside the SQL with CONCAT.

**Top speed signal interpretation:**
- AM provides +50 kW (300 → 350 kW total). Shows up as a noticeable top-speed bump on activation laps.
- DAC's smooth climb on laps 1-5 with no step function = no AM use in that window. Lap 5's 236.3 may be his first AM activation, or clean air from the lap-3 cluster ahead.

**Telemetry partitioning:**
- Hive-style: `gs://.../telemetry/car_number=N/*.parquet`
- One file per partition, UUID-named
- Load with `LoadJobConfig(hive_partitioning=HivePartitioningOptions(mode="AUTO", source_uri_prefix=...))`
- BQ load API does NOT accept `**/*.parquet` recursive globs — use `*` plus Hive opts
- ~1200 telemetry samples per lap at 20 Hz × 60s lap

**Team name casing in source data is inconsistent** ("DS PENSKE", "Andretti Formula E", "ERT Formula E Team"). Agent system prompt should normalize for TTS output ("DS Penske", not "DS PENSKE" — TTS will shout uppercase).

**Toolbox SDK / server version alignment:**
- Toolbox server v1.x (we use 1.3.0) speaks MCP JSON-RPC at `/mcp` and disables the legacy `/api/...` REST endpoints by default
- Use `toolbox-core` SDK v1.x (we use 1.1.0) which speaks `/mcp` natively — the 0.5.x SDKs use the old REST path and 410 against modern servers
- `--enable-api` server flag re-enables the legacy endpoint if needed, but it's deprecated; use the matched 1.x SDK instead
- Server flag is `--config` in v1.x (not `--tools-file`, which is deprecated and warns at startup)

**Dependency pinning strategy:**
- Use strict `==` pins only where the version *must* match an external surface (toolbox-core matches the deployed Toolbox server's protocol; google-adk's 1.x API is the agent contract)
- Everything else uses `>=` floors so pip can resolve a coherent transitive matrix
- Aggressive strict pinning across the requirements file causes `ResolutionImpossible` errors when transitive deps (protobuf, grpcio, google-api-core) want incompatible ranges

**Pub/Sub OIDC push auth — invoker goes on the push-auth SA (Fork 4 gotcha candidate):**
- With `--push-auth-service-account=SA`, Pub/Sub mints the OIDC token *as that SA* — so Cloud Run checks `roles/run.invoker` on **that identity**, not on the Pub/Sub service agent.
- Correct bindings: (1) push-auth SA gets `run.invoker` on the service; (2) Pub/Sub service agent gets `iam.serviceAccountTokenCreator` *on* the push-auth SA (it mints the token, never invokes).
- We initially bound invoker to the service agent → hard 403 at the Cloud Run front door (request never reaches the container, only visible in request logs). Easy mistake because "grant the service agent invoker" *is* the right pattern for some other GCP push integrations.
- IAM changes take 1–3 min to propagate to push delivery; Pub/Sub's retry backoff re-delivers automatically once the binding lands (within the 600s `messageRetentionDuration`).
- Fixed in `deploy/deploy_state_writer.sh` (binding now targets `${SA_EMAIL}`, with explanatory comment).

**Agent Engine supplies GOOGLE_CLOUD_PROJECT as the project NUMBER (the marquee chunk-12 gotcha, Fork 4 candidate):**
- On Vertex AI Agent Engine, the runtime env sets `GOOGLE_CLOUD_PROJECT` to the project NUMBER (e.g. 83898679865), consistent with the engine's own resource name — locally, activate.sh sets it to the project ID.
- Firestore rejects number-addressed database paths with `404 The database (default) does not exist for project <NUMBER>` — the error ACTIVELY MISDIRECTS toward "create a database." The DB exists; the path is just addressed by number. (IAM problems would be 403, not 404.)
- The tell is IN the error string: a project number where an ID should be. Read the resource path in the error, not just the error class. (Even Gemini Cloud Assist circled this one — verified DB/APIs/IAM all fine — without landing the root cause.)
- Fix pattern: bake the real project ID into the engine `.env` (`PROJECT_ID`), and have client init prefer `PROJECT_ID` over `GOOGLE_CLOUD_PROJECT` (plus a warning if the resolved project is all digits).

**Agent Engine service agent is created by the first deploy:**
- `service-PROJECT_NUMBER@gcp-sa-aiplatform-re.iam.gserviceaccount.com` doesn't exist until an engine has been deployed in the project — so grant its Firestore role AFTER the deploy step. Post-deploy granting is idempotent on updates; pre-deploy granting fails on a fresh project.

**The agent_engines SDK blocks the event loop — async_* variants included (chunk 13, observed live):**
- Calling the deployed engine from an async service stalled the WHOLE shared loop for each call's duration: state broadcasts burst, the lap ring swept in jerks, /api/stt sat unserved 20-30s. The SDK's `async_*` methods did not help.
- Fix pattern: use the SYNC SDK methods inside `asyncio.to_thread`, one thread per call. On timeout, asyncio abandons the thread (the call completes in background, result discarded) — acceptable for read-only calls, and it IS the drop-a-stale-call policy.
- Related observation from an engine-side traceback: the Agent Engine runtime executes each query via `runners.py:_asyncio_thread_main` → `asyncio.run(...)` — a fresh worker thread + fresh event loop PER QUERY, server-side. The chunk-6 loop-binding pattern, reintroduced where we can't restructure it. Not implicated in any sustained failure (two transient toolset-load errors in one quota storm, never reproduced), but worth knowing it's there.

**Quota errors don't say "429" in Cloud Logging (chunk 13 post-mortem):**
- Vertex logs gRPC codes: `protoPayload.status.code: 8` = RESOURCE_EXHAUSTED = the 429. Searching logs for "429" and finding nothing PROVES NOTHING — a diagnosis was wrongly abandoned on exactly that null result.
- Corollary: shared Qwiklabs quota headroom varies by the hour with other tenants — "5× worked all day" is evidence about the pool's neighbors, not about your system.

**Dev-vs-deployed IAM gap — Speech-to-Text V2 (Fork 4 candidate):**
- STT V2 recognizers are IAM RESOURCES: recognizing via the `_` default recognizer requires `roles/speech.client` on the caller. In Cloud Shell the student account's broad roles mask this; a dedicated Cloud Run SA fails with the UI's polite "Didn't catch that" degradation. TTS has no equivalent resource-level IAM, so voice OUT keeps working while voice IN dies — a nicely confusing asymmetry to teach.

**Cloud Run flags that are architecture, not tuning (frontend):**
- A service with BACKGROUND TASKS (engineer loop, state poller) needs: `--min-instances=1` (scale-to-zero kills the loop), `--max-instances=1` (N instances = N engineers making duplicate radio calls), `--no-cpu-throttling` (request-based throttling freezes background work between requests; switches to instance-based billing). Cloud Run's defaults assume request/response; a service with a background brain needs all three.

**Source deploy vs explicit Dockerfile (monorepo lesson):**
- `gcloud run deploy --source` works when the directory IS the app (simulator repo). It cannot build a service that COPYs sibling packages (`shared/`, `agent/`): pointing it at the subdir puts the build context below the files it needs; pointing it at the root can't host two services' Dockerfiles; Buildpacks would install the dev requirements.txt (ADK/Toolbox bloat + the package-import trap). Pattern: build context at repo root, `gcloud builds submit --config` with `-f <service>/Dockerfile`. Both paths produce an image in Artifact Registry — the only difference is who writes the build recipe. Buildpacks' failure mode (`ModuleNotFoundError: shared`) doesn't explain itself.

**Engine runs that fail mid-flight can end with NO error event and NO text:**
- stream_query just... ends. Treat empty final text as failure (raise → drop policy), or the UI displays empty radio calls. Locally the same failures raise; the remote surface swallows them.

**`adk deploy agent_engine` stages only the target folder:**
- `source_packages` = [the folder you point it at], unconditionally — no extra-packages mechanism in this CLI generation. Any top-level repo packages the agent imports must be VENDORED into the staged folder (with imports rewritten if the package path changes). The generated app does `from .agent import root_agent`, so the staged folder must contain an `agent.py` exposing that name.

**frames_v1 → frames_v2 (data quality fixes found in live integration):**
- The broken `laps.top_speed` (always 0) had propagated into frame `lap_completed` events. v2 recovers real values from per-lap MAX of 20 Hz telemetry — same derivation as BQ `top_speed_per_lap`, anchor-validated against DAC laps 1–5 (exact to 0.1 km/h).
- 532 of 1,248 overtake events (43%) were `position_change=0` noise (no-op side of provisional swaps) — dropped at frames build. Position resolution unaffected.
- v2 written alongside v1 (never overwrite published artifacts); `schema_version` 1.1; `top_speed_kmh` now float.
- Simulator `/schema` endpoint returns the file's *midpoint* frame — t=1449, a quiet safety-car tick with empty `events[]`. Not a bug. (Same moment as our canonical seed frame, for the same reason.)

**OVERTAKE IDENTITY (the marquee Fork 4 gotcha): `car_number` in overtake records is a GRID POSITION.**
- Source overtake stream (timing.parquet → event_stream → frames): subject field named `car_number` holds the car's STARTING GRID POSITION (1-22); `other_car`/`participant` holds a real car number. Two ID domains in one record.
- Detection path worth teaching: phantom car numbers in agent answers → entry-list join showed exactly {1..22} present and ALL seven cars >22 absent → hypothesis scoring by position adjacency at event time → gap-distribution histogram as the clincher.
- Consequence pre-fix: every overtake attribution wrong except by coincidence (e.g. "Rowland: 5 overtakes" on a 13-place charge; frame events tagged car 13 were actually grid-P13 = Daruvala). Original chunk-2 finding "DAC got passed multiple times by #1 (DEN)" is SUPERSEDED — re-verify against rebuilt v_overtakes.
- Source `human_summary` strings embed the grid IDs — poisoned; regenerate, never pass through.
- Methodology note: an aggregate adjacency score of ~50% was enough to win decisively (control: 17%), but below the naive 80-90% expectation — end-of-lap position snapshots smear mid-lap AM-driven swings. Score shape (decay vs flat) was the reliable signal.

**ADK function-calling gotchas (google-adk 1.x):**
- ADK does NOT coerce JSON args into Python enums: `Optional[list[EventType]]` arrives as `list[str]` and crashes. Tool signatures should take `list[str]` and coerce internally with a clear error.
- Sync `runner.run()` spins a fresh thread+event loop PER CALL; `ToolboxToolset`'s HTTP client binds to the first loop and dies on the second ("Event loop is closed"). Any multi-turn harness must be fully async on one loop (`run_async`). `adk web` is immune (single uvicorn loop).
- Gemini function args travel as JSON numbers (float64): nanosecond timestamps lose precision (~256ns ulp at 1.7e18). Harmless at race timescales; do not rely on ns-exactness through the LLM.
- `adk run` prints ONLY text parts — tool calls and args are silently swallowed. For arg-level debugging use `adk web`'s Events tab or `scripts/agent_chat.py`.
- `adk web` behind Cloud Shell Web Preview: session creation fails (proxy rewrites origin) without `--allow_origins "*"`.
- `ToolboxToolset` comes from `google-adk[toolbox]` (the `toolbox-adk` package, which depends on toolbox-core — coexists with our `==1.1.0` pin). Construction is lazy; no network at import.

**Agent data-hygiene patterns (found via live grading):**
- Replay-clock leak: events carried `ts_ns_wall` (2026 replay clock); model grabbed it as `through_time_ns` for 2024-clocked BQ tools → whole-race future leak. Fix at the DATA level: `AgentEvent` slim view (event_type, race_time_s, car_number, data) — never show the model plumbing fields it can misuse. Prompt rules alone were insufficient.
- Hallucinated identities: model invented a driver name ("Frijns") for an unmapped car number. Fix: hard prompt rule — names ONLY from tool responses; unknown numbers stay numbers. Verified live: model hit car 10, got 0 rows from get_driver_info, correctly declined to name it.
- Structure vs semantics division for SQL escape hatches: schema discovery via `bigquery_list_table_ids`/`bigquery_get_table_info` (machine truth, never rots); tool descriptions carry ONLY semantics metadata can't express (broken columns, ns conventions, normalization caveats). Result: discovery-first behavior, zero guessed-column 400s.
- Intra-turn state drift: at 5× replay, the 1s RaceState TTL = 5 race-seconds; a 16-tool-call turn spanned ~200 race-seconds. Acceptable for Q&A; chunk 7+ triggers should pass a state snapshot. Also a latency flag for chunk 8: cap tool-call budget per radio call.
- `toolbox_test.py` POST_RACE anchor was mid-race (t≈1954s), not past chequered — tests verified mechanics, not completeness. Fixed to past-chequered value.

**Retirements in R10:** car 7 (GUE) lap 10, car 23 (FEN) lap 24. Both matter for field-size assertions and per-lap joins.

**Frame schema semantics worth teaching:** `attack_mode.remaining_budget_s` decrements on DEACTIVATION, not continuously — a car mid-activation still shows its pre-activation budget. Calls like "180 seconds remaining" mid-AM are faithful to the data. Also: prompt examples become model vocabulary — concrete examples in persona/trigger prompts ("turn six") reappear verbatim in calls; rotate or genericize examples if this matters.

**Three-service architecture rationale:**
- Two services (frontend owns ingestion + UX) would have collapsed concerns and made the lab harder to teach
- Three services (Writer / Agent / Frontend) gives the hackathon three clean team handoff points: ingestion patterns, agent reasoning, UX orchestration
- Firestore as integration point means each service is stateless; frontend can scale or restart freely; agent is fully decoupled from real-time stream
- Pub/Sub push to State Writer (vs. streaming pull) is the canonical Cloud Run pattern — scales 0→N based on message rate, no long-running subscriber loop
- Architecture lift cost: ~one extra deploy script and one Pub/Sub push subscription; reasoning quality and teachability gain far outweighs

---

## Live TODO

- [x] Chunk 1 — scaffold
- [x] Chunk 2 — BQ setup
- [x] Chunk 2.5 — telemetry + top_speed_per_lap
- [x] Chunk 3 — MCP Toolbox locally (11 tools)
- [x] Chunk 3.5 — add `get_top_speed_history` tool
- [x] Top_speed cleanup pass — dropped broken column from `get_lap_history`, `get_field_position_at_lap`, and `v_laps_with_driver`; added INT64-ns convention doc to `execute_sql_bq`
- [x] Chunk 4 — Toolbox to Cloud Run
- [x] Chunk 4.5 — venv + activate + region-env-var cleanup
- [x] Chunk 5 — data plane (shared models, State Writer, frame tools, seed + test, frames_v2, idempotent event IDs, reset script)
- [x] Cleanup: unified activate references — the file is `activate.sh` at repo root (`source activate.sh`); fixed stale refs in 9 files + repaired README quick start (mangled env_check line, stray fence, dead BUILD.md reference)
- [x] Chunk 6 — agent definition (4 passes: skeleton, Toolbox, discovery tools, persona; async chat harness)
- [x] Chunk 6.5 — overtake identity remediation (v_overtakes rebuild, tool rewrite, frames_v3)
- [x] Re-verified DAC battle list against rebuilt v_overtakes — CAS and JEV top rivals (11 each); original DEN finding confirmed by grid coincidence
- [x] Chunk 7 — significance scorer + local harness (pure scorer in shared/, snapshot-passing trigger loop, laps 1-10 validated)
- [x] Chunk 8 — reasoning iteration (per-type debounce + must-say hold, 3-layer tool budget, filler scrub, fact-check passed)
- [x] Chunk 9 — frontend (websocket UI, engineer loop in-service, Q&A, sim controls)
- [x] Lap-1 ring calibration — root fixed in chunk 11 (tracking starts at the green flag)
- [x] Chunk 10 — TTS (Chirp 3 HD via radio_broadcast wrapper; digits normalization; DEMO.md)
- [x] Chunk 11 — STT push-to-talk (Chirp 2, spacebar PTT, visible transcript; enable_apis.sh)
- [x] Chunk 12 — agent to Agent Engine (build_engine_app vendoring, deploy script + .engine_resource, engine_smoke green; project-number Firestore gotcha fixed)
- [x] Chunk 13 — frontend to Cloud Run (agent_client seam + AGENT_MODE, sync-in-thread engine calls, Dockerfile/deploy script, speech.client IAM, empty-response drop; auth flip descoped + documented)
- [ ] Write the Toolbox production note (tools.yaml header comment + DEMO.md aside): how to flip auth on, and why the lab leaves it open — text blocks already drafted, just needs pasting
- [ ] README rewrite — UNBLOCKED (deploy story settled post-chunk-13). Likely absorbed into Phase 2's STUDENT_GUIDE/RUN_OF_SHOW split; decide there before writing anything.
- [ ] Phase 2 packaging (separate planning conversation — see docs/PACKAGING_BRIEF.md)
- [ ] Once Fork 2 wraps: fold `PROGRESS.md` findings into the main build doc Decision Log + Gotchas

Skipped by decision (2026-06-05): chunk 14 formal dry run (stack exercised at 2×/5× through chunk 13 — Phase 2's instructor-path rehearsal covers a full 1× pass) and chunk 15 stretch items (BQML AM score tool, Gemini Live spike).

---

## How to use this doc

Update after every completed chunk. Move items from "Up next" to "Built so far" as they ship. Add to "Findings worth remembering" whenever something non-obvious shows up. The whole point is that if this conversation ends abruptly, a fresh Claude (or a fresh you, six weeks from now) should be able to read this and know exactly where the build stands.

**Workflow note:** Claude maintains a canonical copy in its workspace and applies targeted edits per chunk (not full rewrites). After each update, Claude presents the latest version and Patrick overwrites his local `PROGRESS.md` in the repo.