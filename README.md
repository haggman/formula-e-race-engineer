# Formula E Race Engineer Agent — Challenge 2

An AI race engineer for car #13 (António Félix da Costa) during a streamed
replay of Formula E Berlin 2024, Round 10. A deterministic scorer decides
WHEN the engineer speaks; a Gemini agent (Google ADK) decides WHAT to say —
grounded in live race state from Firestore and the recorded race history in
BigQuery, delivered as spoken radio calls with push-to-talk Q&A. This repo
is both the complete reference solution and the 3-hour hackathon built
around it: students receive the data plane, the pit-wall frontend, and the
trigger system, and build the agent in the middle.

## Where to go (pick your reader)

| You are... | Read |
|---|---|
| **In the hackathon room, building** | [`STUDENT_GUIDE.md`](STUDENT_GUIDE.md) — the tiers, the commands, the context |
| **Running the event** | [`RUN_OF_SHOW.md`](RUN_OF_SHOW.md) — morning-of, the 20-min opening, checkpoints |
| **Demoing the system** | [`DEMO.md`](DEMO.md) — choreography, question bank, Attack Mode explainer |
| **Understanding how it was built** | [`PROGRESS.md`](PROGRESS.md) — the full build record, decisions, and gotchas |
| **Working on the packaging** | [`PACKAGING.md`](PACKAGING.md) — the living Phase 2 record |

## Quick start

```bash
source activate.sh        # venv + env (run in every new Cloud Shell tab)
bash setup/all.sh         # deploy the full data plane (budget 20 min, ~10 typical) + verify
```

Optional instructor extras (Agent Engine + public Cloud Run pit wall):
`bash setup/7_deploy_cloud.sh`

## Architecture

```
[simulator on Cloud Run] → Pub/Sub → [State Writer on Cloud Run] → Firestore
                                                                       ↑
[Pit-wall frontend: FastAPI + websocket UI, scorer, TTS/STT] ──────────┘
        └── invokes → [ADK Race Engineer agent: gemini-3.5-flash]
                          ├── frame tools → Firestore (the live "now")
                          └── MCP Toolbox → BigQuery  (the recorded "then":
                              14 tools: 11 curated + discovery + SQL)
```

The agent runs in-process during development (`AGENT_MODE=local`) or on
Vertex AI Agent Engine (`AGENT_MODE=engine`, the deployed demo path). The
`AGENT_PACKAGE` env var selects WHICH agent the system loads:
`starter.race_engineer` (the student build — the default) or
`solution.race_engineer` (the complete reference).

## Repo map

`solution/` the reference agent · `starter/` the student package ·
`frontend/` the pit wall · `shared/` models, scorer, the package seam ·
`state_writer/` Pub/Sub→Firestore · `simulator/` the race replayer ·
`toolbox/` the BigQuery tool definitions · `setup/` numbered event setup ·
`deploy/` the underlying deploy scripts · `scripts/` dev + test harnesses ·
`notebooks/` BigQuery loading

## Race context

Berlin 2024 E-Prix Round 10 (Season 10) — 41 laps, ~48 minutes. Car #13
starts P10 and wins. Demo stint: laps 1–10, anchored by the lap-3 Attack
Mode cluster. Replay speed: 2× to build, 1× to demo.

## License

MIT