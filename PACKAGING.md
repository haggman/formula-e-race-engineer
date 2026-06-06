# PACKAGING.md — Phase 2.5 (cascade executed, v2)

Last updated: 2026-06-06 (P2.5 v2: cascade re-verified against the live repo
at `5de4855` incl. the RECOVERED student guide; all 37 edits exact-anchored;
regression green in a clean clone — pending apply + commit). P1 (restructure
+ scripts) and P2 (docs) COMPLETE. Latency thread CLOSED. Note: P1/P2 detail
rows in this revision are summarized to their outcomes; full history lives in
git and the planning hub.

---

## Current state

- **P1 ✓** — repo restructured around the `AGENT_PACKAGE` seam
  (starter/solution mirror shape); scripts re-homed; engine-app build
  self-checks (stale-import hunt matches imports only; `agent_pkg.py` stays
  client-side).
- **P2 ✓** — docs delivered (DEMO.md, RUN_OF_SHOW.md, STUDENT_GUIDE.md —
  but see Finding #6).
- **Latency thread CLOSED** — Finding #5: chain depth is structural;
  name-steering fix shipped; QA ceiling raised 12 → 30 via
  `QA_MAX_LLM_CALLS`. Optional evening `qa_latency_probe` rerun stays parked.
- **P2.5 ✓ (this delivery)** — parked cascade items executed; see below.

## Findings log

- **#5 (latency, CLOSED):** QA latency is chain-depth, not transport.
  Structural; mitigated by name-steering in the prompt + raised call ceiling.
  Future structural fix = `lookup_driver` curated tool (now a T4 exercise in
  the student guide — deliberately NOT shipped in tools.yaml).
- **#6 (RESOLVED — STUDENT_GUIDE.md clobbered):** the repo file named
  `STUDENT_GUIDE.md` contained a stale PACKAGING.md snapshot (P1.6-era
  header) — the correct version was likely never committed. **Resolution:**
  Patrick recovered the delivered guide from the chat where it was created
  and pushed it (commit `5de4855`). The recovered text is canonical; the
  cascade guide items (primer expansion, Code Assist + ADK links, lane map)
  ship as **targeted patch edits to it**, not a rewrite. Test 2 reviews the
  new sections in context.
- **#7 (NEW — DSQ 429s; first scoreboard run):** logging fix surfaced heavy
  429s. Diagnosis: `X-Vertex-AI-LLM-Request-Type: shared` on the `global`
  endpoint = **Dynamic Shared Quota** — POOL capacity, not project quota
  (quota console correctly shows nothing near a limit). Aggravated by TWO
  engineers on one pool (deployed fe-frontend + local) at 5×. Q&A >1 min
  = retry math: attempts=10 / max_delay=8s ≈ 47s of backoff per bad LLM
  step. Mitigations shipped: retry attempts 10→4 + max_delay 4s (the
  loop's fresh-snapshot retry beats SDK grinding), FE_MODEL env knob
  (regional GA escape documented), `throttled:<kind>` counter. First 5×
  scoreboard — **PROVISIONAL, dual-engineer + throttled; re-baseline in
  the fresh project**: fired:event 1, fired:lap_summary 11,
  dropped:lap_summary 2, dropped:must_say 1, expired:must_say 1,
  suppressed 19. Headline damage: ZERO must_says fired vs ~3 expected.

## Decisions (additions this phase)

| Decision | Rationale |
|---|---|
| `DEPLOY_AGENT_PACKAGE` is its **own** env knob (default `solution.race_engineer`), not activate.sh's `AGENT_PACKAGE` | activate.sh defaults `AGENT_PACKAGE=starter` for local dev; inheriting it in the deploy path would silently ship stubs as the reference. Consequence: `setup/7_deploy_cloud.sh` needs **no change**. |
| FINISH implemented server-side as `/api/sim/finish` (`/status` → `race_time_s + seconds_remaining − 10` → POST `/jump`), registered **before** the `{action}` catch-all | Keeps `/jump` itself OFF the generic proxy whitelist (prior decision preserved); FastAPI matches routes in registration order. NOTE: `/status` exposes **no end_tick** — caught against simulator source; `/jump` clamps to the valid range. Forward jumps are safe: restart detection only fires on backwards time. |
| Scoreboard = `Counter` in the engineer loop: `fired:<kind>` / `dropped:<kind>` / `suppressed` / `expired:must_say`; logged every ~120s; dumped + cleared on replay restart | Per-race baselines with zero new infrastructure; Q&A deliberately uncounted (human-initiated). `suppressed` counts over-threshold-inside-debounce — the gate visibly earning its keep. |
| `demo.sh` = the only blessed local launch (`RUN_SOLUTION=1` pins the reference); frontend hard-fails at startup if local mode has no `SIM_URL` | Universal-503s incident hardening: recycled Cloud Shell sessions drop exports. Fail loudly with the exact fix, never limp. |
| Dockerfile copies `starter/` alongside `solution/` | Either `AGENT_PACKAGE` must resolve in-container for the bonus deploy path; harmless to the instructor flow. |
| `lookup_driver` lives in the student guide T4 menu, **not** on the BONUS board | No double-listing; it's a teaching exercise (verify.sh's 14-tool expectation flags the 15th — documented as expected in the guide). |
| `FE_MODEL` env knob (default `gemini-3.5-flash`); SDK retry attempts 4 / max_delay 4s | Different models = different DSQ pools; the sustained-429 escape is a regional GA flip (`gemini-2.5-flash` @ us-central1, visible/raisable quota). The trigger loop owns retry semantics (fresh snapshot, 5s cooldown, must-say TTL) — deep SDK backoff just shipped stale prompts late. |

## P2.5 — cascade execution (this delivery)

Delivered files:

- [x] `STUDENT_GUIDE.md` — NOT delivered as a file (Finding #6 resolved: the
  recovered guide is canonical). The cascade items land as nine targeted
  patch edits instead: Code Assist tip + ADK 2.0 warning + curated
  ADK/Toolbox links (verified 2026-06-06; Toolbox docs describe v2 config,
  server runs v1.3.0 → "copy existing tools.yaml shapes" guidance); primer
  additions (Turn 2 activation zone, laps 7–9 attack-loop sacrifice, GUE/FEN
  retirements); T3 test surface → `bash demo.sh`; T4 lookup_driver exercise
  (with the verify.sh 14-tool caveat, redeploy via `setup/3_deploy_toolbox.sh`);
  team lane map table + integration ritual; local-503s troubleshooting row;
  BONUS.md pointer.
- [x] `BONUS.md` — additive board: UI ([S] voice picker, [M] tool-call
  panel), AGENT ([M] DEBRIEF pairing with FINISH, [L] re-cast as Cassidy
  #37), VOICE&DATA ([S] Portuguese radio, [M] mini eval harness), DEPLOY
  ([L] ship YOUR agent via DEPLOY_AGENT_PACKAGE); alternates (AM countdowns,
  transcript replay).
- [x] `demo.sh` — zero-rememberable-parts local launch.
- [x] `cascade_patch.py` v2 — one-shot, ALL edits assert-guarded with exact
  anchors verified against the live repo (`5de4855`). Run once from repo
  root, then `rm`. Verified in a clean clone: 37/37 edits, compileall +
  bash -n green, both build_engine_app paths (reference + DEPLOY_AGENT_PACKAGE
  =starter) stage and self-check, route order confirmed.
- [x] This PACKAGING.md update.

Code edits in the patch:

- [x] `frontend/engineer_loop.py` — scoreboard (8 edits).
- [x] `frontend/main.py` — SIM_URL local-mode startup guard;
  `/api/sim/finish`.
- [x] `frontend/static/index.html` — FINISH button + handler.
- [x] `frontend/Dockerfile` — `COPY starter/`.
- [x] `deploy/build_engine_app.py` — DEPLOY_AGENT_PACKAGE knob, parameterized
  REWRITE_RE/STALE_IMPORT_RE, PKG_PATH guard, source-package print, docstring.
- [x] `deploy/deploy_frontend.sh` — DEPLOY_AGENT_PACKAGE default + banner +
  `AGENT_PACKAGE` in `--set-env-vars`.
- [x] `RUN_OF_SHOW.md` — 503s-locally troubleshooting row; lane-map talking
  point (13:00–18:00); fallback → `RUN_SOLUTION=1 bash demo.sh`; FINISH
  note in pre-flight; "What healthy looks like" section (taxonomy table +
  1×/2×/5× baseline cells) before Open items; baseline checklist item.
- [x] `DEMO.md` — demo.sh pointer in the run block.

Pending (Patrick, at the machine):

- [ ] Apply cascade (`apply_cascade.sh`), skim the STUDENT_GUIDE diff, run
  the live smoke, commit. (Static regression already verified in a clean
  clone of `5de4855`.)

## P3 — acceptance tests

**Test 1 (full local run):**
- [ ] Record scoreboard baselines at **1× / 2× / 5×** into the RUN_OF_SHOW
  table (prior 5× eyeball: summaries every 2–3 laps, ~3 must-says, ONE event
  reaction).
- [ ] Sanity-poke FINISH (jump lands ~10s before flag; loop treats it as a
  forward jump, no restart flush; event-log gap is per-spec).
- [ ] Confirm `7_deploy_cloud.sh` picks up the steered prompts; fused
  question on the deployed engine ~11–15s expected.
- [ ] Standard pass: T1/T2 validators, demo.sh audio unlock, Q&A spread.

**Test 2 (docs voice pass):**
- [ ] STUDENT_GUIDE.md — review the nine NEW sections in context (voice
  match against the recovered base; link spot-check). Base text is the
  recovered original and needs no re-review.
- [ ] GIVEN-banner prose sanity check (drafted P1.4).
- [ ] BONUS.md ticket sanity (surfaces exist, sizes honest).

## Open items — KEEP PARKED

- [ ] **URGENT when back at the machine:** all-backends-503 triage protocol
  (needs the live project; distinct from the *local* 503s now hardened by
  demo.sh).
- [ ] Qwiklabs template observation (carry-over).
- [ ] Optional: evening `qa_latency_probe` rerun post name-steering.

## Target repo layout (delta)

```
formula-e-race-engineer/
  demo.sh                 ← NEW (blessed local launch)
  STUDENT_GUIDE.md        ← recovered base + 9 patch edits (Finding #6)
  BONUS.md                ← NEW
  PACKAGING.md            ← this file
  DEMO.md, RUN_OF_SHOW.md ← patched
  frontend/  deploy/      ← patched per P2.5 list above
```
