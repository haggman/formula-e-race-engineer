# Formula E Race Engineer Agent

ADK-based AI agent that acts as an autonomous race engineer copilot during a streamed replay of Formula E Berlin 2024 (Season 10, Round 10). The agent advises Car #13 (António Félix da Costa, eventual winner) on energy management, Attack Mode strategy, and situational awareness — delivering spoken recommendations and answering driver questions in real time.

This is **Challenge 2** of the seven-challenge Google Cloud + Formula E hackathon series. The reference solution in this repo is what students build toward.

## Architecture

```
[fe-simulator on Cloud Run]
    └── publishes 1 Hz frames to Pub/Sub fe-telemetry
                                │
[Frontend on Cloud Run] ◄───────┘
    ├── Pub/Sub subscriber maintains race state
    ├── Significance scorer decides when to trigger agent
    ├── Browser UI: live state, transcript, text + voice Q&A
    └── Calls agent on three triggers:
            • significant event
            • end-of-lap summary
            • user Q&A
                                │
[ADK Race Engineer Agent on Agent Engine, global] ◄─┘
    Model: gemini-3-flash-preview
    ├── Frame-state tools (current state, recent events, field AM)
    └── MCP Toolbox: 8 curated BQ queries + 1 SQL escape hatch
```

## Tech stack

Google ADK · Vertex AI Agent Engine · MCP Toolbox for Databases · BigQuery · Cloud Run · Cloud Pub/Sub · Cloud Text-to-Speech (Chirp 3 HD, en-GB) · Cloud Speech-to-Text v2

## Companion repos

- **Simulator**: [haggman/formula-e-simulator](https://github.com/haggman/formula-e-simulator) — must be deployed in your lab project before running the agent

## Quick start

Set up your environment (creates venv, installs requirements, sets REGION + PROJECT_ID):

    source ./activate

Verify it worked:

    bash scripts/env_check.shcripts/env_check.sh
```

Then follow `BUILD.md` (added in Chunk 2) for the step-by-step build sequence.

## Race context

- **Race**: Berlin 2024 E-Prix Round 10 (Season 10), May 12, 2024
- **Length**: 41 laps, 2868 seconds (~47:48)
- **Winner**: Car #13 António Félix da Costa
- **Demo stint**: Laps 1–10, anchored by the lap-3 Attack Mode cluster
- **Replay speed**: 5× default for student work, 1× for instructor demo

## License

MIT