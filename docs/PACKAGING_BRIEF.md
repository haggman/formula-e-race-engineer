# Packaging Brief — Phase 2 of the Formula E Race Engineer (Challenge 2)

**Purpose of this document:** hand off from the Fork 2 build conversation to
a fresh Phase 2 planning conversation. A new Claude session reading this
plus the attached repo should be able to plan and execute packaging with no
other context. The build's full history and findings live in `PROGRESS.md`;
this brief covers only what packaging needs.

All below decions should be considered possible options, but at this point nothing is set in concrete. 

---

## What exists (one paragraph)

A complete, deployed reference solution: a live Formula E race (Berlin 2024
R10) replays through a simulator → Pub/Sub → State Writer → Firestore,
while the full race history sits in BigQuery behind an MCP Toolbox (14
tools). An ADK agent — the race engineer for car 13 — runs on Agent Platform Runtime, reading both worlds. A FastAPI pit-wall frontend on Cloud Run
(public URL) renders live state, runs a deterministic significance scorer
that decides when the engineer speaks, broadcasts spoken radio calls (Chirp
3 HD TTS), and takes push-to-talk questions (Chirp 2 STT). The frontend
reaches the agent through `frontend/agent_client.py` — an env switch:
`AGENT_MODE=local` runs the agent in-process via InMemoryRunner (the dev
path), `AGENT_MODE=engine` calls the deployed engine. Everything is
idempotent, scripted, and documented in `PROGRESS.md`; `DEMO.md` is a
complete demo guide with choreography, a question bank, and an Attack Mode
explainer.

## The event (constraints, confirmed 2026-06-05)

- **Format:** 3 hours total — Current though on timing: 20 min instructor opening (live demo of the finished product + challenge framing; details live in docs, not slides), ~2:30 building, 10 min wrap.
- **Projects:** PROVIDED Qwiklabs projects — one per student or one per
  team, both options should be supported. Students never use personal projects. Provide student-run setup, where appropriate.
- **Audience:** developers — solid Python, GCP knowledge decent but THIN on
  the AI surfaces (ADK, Agent Runtime, Gemini tooling). Cloud Shell
  instructions must be explicit (every step: where to run it, what to run).
- **Standalone:** first event of the seven-challenge series; assume NOTHING
  carried over. All Formula E context (Attack Mode, the race story) must be
  self-contained — `DEMO.md`'s explainers are the seed material.
- **Quota:** explicitly NOT a concern. Drop all quota-driven design
  hedging. (Operating note "1× demos / 2× dev" stands as guidance, not
  as a constraint to engineer around.)
- **Solo and team must both work.** Solo students should have fun and ship
  something demonstrable; teams should be able to parallelize.

## The proposal (carried over from the build conversation — challenge it)

These positions were reasoned through once; the new session should treat
them as strong defaults, not settled law.

1. **Students build the agent; everything else is a gift.** The
   `agent_client.py` seam makes this clean: the full frontend (pit wall,
   voice in/out, trigger loop) runs against ANY `root_agent` in
   `AGENT_MODE=local`. The data plane (BQ + Toolbox + Firestore + State
   Writer + simulator) is pre-provisioned plumbing. The build surface is
   exactly the pedagogically interesting part: tools, two-worlds
   orchestration, persona.

2. **Students never touch Agent Engine.** 5-10 min silent deploys and the
   engine gotchas (project-number 404, vendoring) are lethal in a 3-hour
   room. `AGENT_MODE=local` for the whole student experience. The engine is
   the instructor's demo + a "how production does it" talking point.
   COROLLARY: student setup is LIGHTER than instructor setup — no engine
   deploy, no frontend Cloud Run deploy (students run the frontend locally
   via uvicorn + Web Preview). Instructor setup adds engine + Cloud Run
   frontend for the opening demo.

3. **Tiered build, checkpoint demo per tier**, so anyone can stop anywhere
   with something working (provisional timing for the 2:30 block):
   - T1 (~40 min): agent skeleton + frame tools → "where are we now?"
     answered live in the given frontend.
   - T2 (~45 min): wire MCP Toolbox → two-worlds questions ("compare our
     pace to Wehrlein over the last 5 laps").
   - T3 (~30 min): persona → it sounds like a race engineer, spoken aloud.
   - T4 (overflow/teams): trigger tuning — the loop and scorer are given
     with the weights table exposed; tune when the engineer speaks.
   Team roles fall out: tools person, SQL/data person (add a Toolbox tool;
   the data quirks in PROGRESS.md "Findings" are discoverable treasure),
   persona person, trigger tuner. Parallel work, one integration point.

4. **Starter = fill-in-the-blanks, not blank page.** A `starter/` package,
   ONE frame tool complete as the worked example, the rest as specced
   TODOs, persona prompt as a skeleton stating the rules to write. Given
   the audience (Python-strong, ADK-weak), TODOs should teach ADK mechanics
   by example, not assume them.

5. **One repo, overlay — don't reorganize.** Working deploy scripts have
   paths baked in; restructuring now buys risk, not clarity. Add:
   - `setup/` — numbered scripts (`1_apis.sh`, `2_bq.sh`, ... style), thin
     idempotent wrappers around the existing `deploy/` scripts, plus
     `all.sh`. TWO paths through them: student (no engine, no Cloud Run
     frontend) and instructor (everything). Must support both
     instructor-runs-it-that-morning and Qwiklabs-pre-seeds-it.
   - `starter/` — the student package (item 4).
   - `RUN_OF_SHOW.md` — instructor doc: morning load with wall-clock
     expectations, the 20-min opening script (lean on DEMO.md), tier
     checkpoints with what-to-say, troubleshooting.
   - `STUDENT_GUIDE.md` — what's deployed in your project, what you're
     building, the tiers, FE context, the question bank.
   - The solution agent stays visible in `agent/` — hackathon, not exam;
     stuck teams reading the reference is a feature.

6. **Provisional Phase 2 chunks:** P1 setup scripts (both paths), P2
   starter extraction, P3 the two docs, P4 instructor full-path rehearsal
   in a fresh project (which doubles as the 1× end-to-end pass the build
   phase skipped).

## Open questions for the Phase 2 conversation

- The 20-min opening: demo from the instructor's deployed stack at 1× is
  ~12 min for laps 1-11 — too long. Which DEMO.md moments make the cut?
  (Candidate: restart, let laps 1-3 play for the AM cluster, pause, two
  Q&A questions incl. one by voice, jump the speed up, done in ~8.)
- Starter granularity per tier: how much of `prompts.py` is skeleton vs
  given? The persona took 2 chunks of iteration to get right — students
  can't reproduce that in 30 min, so what's the minimum persona that
  still demos well?
- Does the student frontend ship with the scorer weights pre-tuned
  (chunk 8 values) or detuned so T4 has something to do?
- `STUDENT_GUIDE.md` vs the existing `README.md`: the README rewrite task
  (see PROGRESS TODO) should probably be absorbed here — README becomes a
  thin router to the right doc per reader.
- Qwiklabs pre-seeding mechanics: what can their startup automation run,
  and does `setup/all.sh` need a non-interactive mode for it?
- Naming/numbering of setup scripts and whether `activate.sh` absorbs the
  student/instructor path switch (e.g. `SETUP_PROFILE=student`).

## Repo orientation for the new session

- `PROGRESS.md` — full build history, locked decisions, and the Findings
  section (the gotchas list; several are flagged "Fork 4 candidates" —
  i.e., teachable).
- `DEMO.md` — demo choreography + question bank + FE explainers; the seed
  for both the opening script and STUDENT_GUIDE content.
- `agent/`, `frontend/`, `shared/`, `state_writer/`, `toolbox/`,
  `deploy/`, `scripts/`, `notebooks/` — the working system. `frontend/
  agent_client.py` is the seam everything above leans on.
- Companion repo `haggman/formula-e-simulator` — deployed per-project;
  its deploy is one of the numbered setup steps.

## How to start the new conversation

Attach the repo (as in this conversation) and open with: "Phase 2
packaging for the Formula E hackathon — read docs/PACKAGING_BRIEF.md and
PROGRESS.md, then let's pressure-test the proposal before building
anything. Start with the open questions."
