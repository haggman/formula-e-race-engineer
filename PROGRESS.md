# Fork 2 Progress — Formula E Race Engineer Agent

**Repo:** [haggman/formula-e-race-engineer](https://github.com/haggman/formula-e-race-engineer)  
**Build doc:** [Challenge 2 Build Document](https://docs.google.com/document/d/16NqXYak3NSLkNq__ycyMNDbz-5f6bug4NHlINiCxoV4/edit)  
**Last updated:** 2026-06-03

---

## Where we are

Chunks 1–4 complete. MCP Toolbox deployed to Cloud Run with 11/11 tools validated against the deployed URL via `toolbox-core` SDK 1.1.0. Ready to start chunk 5 (frame-state tools).

---

## Decisions locked

| Area | Decision |
|---|---|
| **Driver** | Car #13 — António Félix da Costa (R10 winner, P10→P3 by lap 5 charge, 9 scenario armings) |
| **Architecture** | Single ADK agent, two entry points. Frontend Cloud Run service is the streaming hub (subscribes to Pub/Sub, runs deterministic significance scorer, calls agent on triggers). Agent stays stateless. |
| **Model** | `gemini-3-flash-preview`, global location only |
| **Agent runtime** | Vertex AI Agent Engine, deployed via `adk` CLI |
| **BQ tooling** | MCP Toolbox for Databases — curated named queries + one SQL escape hatch. Hybrid documented in lab; we use Toolbox for the build. |
| **BQ dataset region** | us-central1 (matches bucket) |
| **Frontend** | FastAPI + websocket on Cloud Run. Live state panel, scrolling transcript, text + push-to-talk voice input |
| **Voice in** | Push-to-talk via MediaRecorder API → Cloud Speech-to-Text v2 |
| **Voice out** | Cloud Text-to-Speech, Chirp 3 HD British male, 1.15× rate |
| **Agent persona** | Second-person ("Antonio, ..."), real engineer style. ~6-8s spoken radio calls. No editorializing. |
| **Per-lap summary template** | Position, gaps, energy state, AM state, optional one-line strategic note |
| **Significance scorer** | Deterministic, lives in frontend, debounced (no trigger within 15s of last) |
| **Agent sessions** | Fresh per trigger for proactive announcements; persistent session for Q&A follow-ups |
| **Toolbox auth** | Open during dev (now), authenticated via service-account invoker when frontend deploys (chunk 13) |
| **Pub/Sub flow** | Frontend is the only subscriber. Agent never directly subscribes. State pushed to agent prompt as context per call. |
| **R09 inclusion** | Not loaded — R10 only for Fork 2. R09 deferred. |
| **Demo stint** | Laps 1–10, anchored by lap-3 AM cluster (DAC was *not* in the cluster — strategic hold-back, contrary to ~13 cars who activated). |
| **BQML** | Stretch / Task 7 only. Not in core reference. Pattern stub may appear later for extraction into Fork 5 starter. |
| **Event-stream tool** | Built here in Fork 2; Fork 5 extracts starter version |
| **Gemini Live** | Stretch demo addition after core works. Push-to-talk + STT/TTS is the canonical path. |
| **Deploy style** | Cloud Run source deploys (`gcloud run deploy --source .`); Artifact Registry mentioned as "production" alternative |
| **Env target** | Qwiklabs student labs. Cloud Shell with Cloud Shell Editor as dev environment. Per-team GCP projects, ephemeral. |
| **Python** | 3.12, default in Cloud Shell |

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

---

## In progress

*Nothing in flight. Ready to start chunk 5.*

---

## Up next

| # | Chunk | What it produces |
|---|---|---|
| **5** | Frame-state tools | `agent/frame_tools.py` — `get_current_state`, `get_recent_events`, `get_field_am_status`, unit-tested against sample frame |
| 6 | Agent definition | `agent/agent.py` + `agent/prompts.py` — ADK agent wired to model, Toolbox MCP, and frame tools. `adk web` runs locally for text chat |
| 7 | Significance scorer + local harness | `scripts/local_test.py` — pulls live Pub/Sub, scores frames, calls agent on triggers, prints + plays TTS. Validate against laps 1–10 |
| 8 | **Reasoning iteration** | Prompt and tool refinements until laps 1–10 reasoning is good. *Where most of the value lands.* |
| 9 | Frontend (text-only) | `frontend/` — FastAPI + websocket + Pub/Sub subscriber + browser UI |
| 10 | TTS wired in | Chirp 3 British male, 1.15× rate, browser playback |
| 11 | STT + push-to-talk | MediaRecorder + Cloud STT v2 |
| 12 | Agent → Agent Engine | `adk deploy agent_engine`, frontend talks to remote agent |
| 13 | Frontend → Cloud Run, auth flip | Toolbox to authenticated, service account invoker bindings, full demo URL |
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
- Got passed multiple times by car #1 (DEN) but recovered
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

---

## Live TODO

- [x] Chunk 1 — scaffold
- [x] Chunk 2 — BQ setup
- [x] Chunk 2.5 — telemetry + top_speed_per_lap
- [x] Chunk 3 — MCP Toolbox locally (11 tools)
- [x] Chunk 3.5 — add `get_top_speed_history` tool
- [x] Top_speed cleanup pass — dropped broken column from `get_lap_history`, `get_field_position_at_lap`, and `v_laps_with_driver`; added INT64-ns convention doc to `execute_sql_bq`
- [x] Chunk 4 — Toolbox to Cloud Run
- [ ] Chunk 5 — frame-state tools
- [ ] Chunk 6 — agent definition
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