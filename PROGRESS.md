# Fork 2 Progress — Formula E Race Engineer Agent

**Repo:** [haggman/formula-e-race-engineer](https://github.com/haggman/formula-e-race-engineer)  
**Build doc:** [Challenge 2 Build Document](https://docs.google.com/document/d/16NqXYak3NSLkNq__ycyMNDbz-5f6bug4NHlINiCxoV4/edit)  
**Last updated:** 2026-06-04 (chunks 6 + 6.5 complete — agent live with 17 tools; overtake identity bug found and fixed end-to-end)

---

## Where we are

Chunks 1–6.5 complete. The ADK agent is alive and reasoning against the live replay: 4 frame tools (Firestore "now") + 13 Toolbox tools (BigQuery history + schema discovery), persona prompt in place, terminal chat harness with full tool-call visibility. Along the way, live testing exposed and we fixed a foundational data bug: overtake events' car_number was actually GRID POSITION (frames_v3 + v_overtakes rebuild + tool rewrite). Next: chunk 7, significance scorer + local trigger harness.

---

## Decisions locked

| Area | Decision |
|---|---|
| **Driver** | Car #13 — António Félix da Costa (R10 winner, P10→P3 by lap 5 charge, 9 scenario armings) |
| **Architecture** | Three services + Firestore. **State Writer** (Pub/Sub push → Firestore) handles ingestion; **Agent** (Agent Engine) handles reasoning; **Frontend** (Cloud Run) handles UX, significance scoring, agent invocation. Firestore is the integration point — single source of truth for current race state and events. All three services stateless. |
| **Service topology** | (1) Simulator on Cloud Run → fe-telemetry Pub/Sub. (2) State Writer on Cloud Run subscribes to topic, writes RaceState + Event docs to Firestore. (3) Agent on Agent Engine reads Firestore via frame tools + BigQuery via MCP Toolbox. (4) Frontend on Cloud Run reads Firestore for live UI, runs significance scorer, invokes Agent. |
| **Shared models** | `shared/` package at repo root holds canonical Pydantic models for RaceState, CarState, Event. Both State Writer and Agent import from it. Single source of truth for the Firestore contract. ADK deploy bundles `shared/` via `--extra-packages` (or symlink at deploy time — TBD chunk 6). |
| **Model** | `gemini-3.5-flash` (switched from gemini-3-flash-preview in chunk 6), `GOOGLE_CLOUD_LOCATION=global`. Shared `GenerateContentConfig` on the agent adds exponential-backoff retries (10 attempts, 0.5s→4s, jitter) for 408/429/5xx. |
| **Agent runtime** | Vertex AI Agent Engine, deployed via `adk` CLI |
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
| **Toolbox auth** | Open during dev (now), authenticated via service-account invoker when frontend deploys (chunk 13) |
| **Pub/Sub flow** | Single subscriber: State Writer service via push subscription. Pub/Sub never reaches frontend or agent directly. |
| **R09 inclusion** | Not loaded — R10 only for Fork 2. R09 deferred. |
| **Demo stint** | Laps 1–10, anchored by lap-3 AM cluster (DAC was *not* in the cluster — strategic hold-back, contrary to ~13 cars who activated). |
| **BQML** | Stretch / Task 7 only. Not in core reference. Pattern stub may appear later for extraction into Fork 5 starter. |
| **Event-stream tool** | Built here in Fork 2; Fork 5 extracts starter version |
| **Gemini Live** | Stretch demo addition after core works. Push-to-talk + STT/TTS is the canonical path. |
| **Deploy style** | Cloud Run source deploys (`gcloud run deploy --source .`); Artifact Registry mentioned as "production" alternative |
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

---

## In progress

**Chunk 7 — significance scorer + local harness.** `scripts/local_test.py`: deterministic scorer reads Firestore state + events, fires agent on triggers (significant event / end-of-lap / debounced 15s), prints transcripts. Builds on `agent_chat.py`'s async Runner pattern. Validate against laps 1-10.

---

## Up next

| # | Chunk | What it produces |
|---|---|---|
| 7 | Significance scorer + local harness | `scripts/local_test.py` — reads Firestore state, scores frames, calls agent on triggers, prints + plays TTS. Validate against laps 1–10. |
| 8 | **Reasoning iteration** | Prompt and tool refinements until laps 1–10 reasoning is good. *Where most of the value lands.* |
| 9 | Frontend (text-only) | `frontend/` — FastAPI + websocket + Firestore reader + browser UI. No Pub/Sub here; State Writer owns ingestion. |
| 10 | TTS wired in | Chirp 3 British male, 1.15× rate, browser playback |
| 11 | STT + push-to-talk | MediaRecorder + Cloud STT v2 |
| 12 | Agent → Agent Engine | `adk deploy agent_engine` (with shared/ bundled), frontend talks to remote agent |
| 13 | Frontend → Cloud Run, auth flip | Toolbox to authenticated, service account invoker bindings, State Writer auth tightened, full demo URL |
| 14 | Demo dry run | Laps 1–10 at 1.0× speed; capture what the agent says |
| 15 | *(Stretch)* | BQML AM score tool; Gemini Live spike |

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

**Deterministic event IDs = idempotent ingestion (the canonical at-least-once answer):**
- Pub/Sub is at-least-once; replays re-deliver everything. Auto-ID event docs duplicated on both (seen live: triplicate lap_completed events).
- Fix: doc ID derived from content — `{race_id}_{race_time_s}_{event_type}_{car|x}_{sha1(data)[:12]}`. Redelivery and replays converge to the same docs.
- Side effect (feature): byte-identical events in the same frame collapse to one doc.
- Strong teach point for the lab: make the *write* idempotent, not the delivery exact.

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
- [ ] Chunk 7 — significance scorer + local harness
- [ ] Chunk 8 — reasoning iteration on laps 1–10
- [ ] Chunk 9 — frontend (text-only)
- [ ] Chunk 10 — TTS
- [ ] Chunk 11 — STT + push-to-talk
- [ ] Chunk 12 — agent to Agent Engine
- [ ] Chunk 13 — frontend to Cloud Run, auth flip
- [ ] Chunk 14 — demo dry run
- [ ] Chunk 15 — stretch (BQML, Gemini Live)
- [ ] Once Fork 2 wraps: fold `PROGRESS.md` findings into the main build doc Decision Log + Gotchas

---

## How to use this doc

Update after every completed chunk. Move items from "Up next" to "Built so far" as they ship. Add to "Findings worth remembering" whenever something non-obvious shows up. The whole point is that if this conversation ends abruptly, a fresh Claude (or a fresh you, six weeks from now) should be able to read this and know exactly where the build stands.

**Workflow note:** Claude maintains a canonical copy in its workspace and applies targeted edits per chunk (not full rewrites). After each update, Claude presents the latest version and Patrick overwrites his local `PROGRESS.md` in the repo.