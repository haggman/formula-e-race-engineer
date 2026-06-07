# PACKAGING.md — Phase 2.6 (fresh-project validation + DSQ re-baseline, v1)

Last updated: 2026-06-06 evening (P2.6: two virgin-project installs
validated, Finding #7 re-baselined and CLOSED, Findings #8/#9 opened and
closed same-day; all fixes pushed to main). P1/P2/P2.5 COMPLETE — detail
rows summarized to outcomes; full history in git and the planning hub.

---

## Current state

- **P1 ✓ / P2 ✓ / P2.5 ✓** — repo restructured on the `AGENT_PACKAGE`
  seam; docs delivered; cascade executed (37 edits, committed `5de4855`+).
- **P2.6 ✓ (this delivery)** — fresh-install validation GREEN on two
  consecutive virgin Qwiklabs projects; fresh-project hardening shipped
  (Finding #8); Q&A freshness rule shipped (Finding #9); Finding #7
  re-baselined with zero-throttle scoreboards and a TESTED model escape;
  UI polish (surname tower, call-meta secs/tools). All pushed.
- **Remaining before the event:** Test 1 rehearsal items (opening script
  timing, lap-2 drop point, step-7 timing cell, 2×/1× baseline rows) +
  Test 2 docs voice pass + the P2.7 cascade list below.

## Findings log

- **#5 (latency, CLOSED):** chain-depth structural; name-steering +
  QA_MAX_LLM_CALLS shipped. `lookup_driver` remains a T4 exercise.
- **#6 (RESOLVED):** STUDENT_GUIDE.md recovered + patched; canonical.
- **#7 (DSQ 429s — RE-BASELINED, CLOSED 2026-06-06):**
  - **Re-baseline (fresh RESOURCED Qwiklabs project, single engineer,
    post-mitigations):** full 41-lap 5× race, `gemini-3.5-flash` @ global
    + shared header: **ZERO SDK retry lines in the whole log**, zero
    dropped/throttled/expired, **5/5 must-says fired** (1 event, 16
    summaries, 34 suppressed). The provisional dual-engineer scoreboard
    (0 must-says) is superseded.
  - **Variable isolation:** same model/endpoint/header as the morning
    storms → the project TYPE (resourced lab project) is the variable,
    not the mitigations alone (though attempts-4/max-delay-4 also
    shortened recovery in the afternoon standard-project run: 2 of 3
    must-says delivered vs 0). RECOMMENDATION: provision the event on
    the resourced project type.
  - **Escape ladder (tested top rung):** (1) `FE_MODEL=gemini-3.1-flash-lite`
    — TESTED at 5×, full race: zero retries, 5/5 must-says, MORE
    responsive (7 events / 21 summaries / 53 suppressed — faster calls =
    loop clears debounce sooner), quality gates held (must-say durations
    correct, fused question correct, weather honesty refusal clean,
    persona held). Stable model ID since the preview's 2026-07-09
    discontinuation; cheaper and faster than 2.5/3.5 Flash. (2)
    `FE_MODEL=gemini-2.5-flash GOOGLE_CLOUD_LOCATION=us-central1` —
    regional GA, visible/raisable quota; NOTE 2.5 models retire
    2026-10-16, so this rung has a shelf life. (3) Drop the
    `X-Vertex-AI-LLM-Request-Type: shared` header (opts out of the DSQ
    pool) — documented, untested, break-glass only. Non-Gemini models
    (Claude on Vertex via LiteLLM) evaluated and REJECTED for this event:
    Google hackathon optics + code-path change; noted for other contexts.
  - Default stays `gemini-3.5-flash` (carries the chunk-8 fact-check
    validation). Lite is the documented first escape; a graded fact-check
    pass would be required before promoting it to default.
- **#8 (NEW, CLOSED — fresh-project hardening):** first-ever virgin-project
  install surfaced five issues, all fixed + validated on a second virgin
  project (clean unattended GREEN, 7m18s):
  - **IAM propagation race:** create-SA-then-grant dies with "Service
    account ... does not exist" seconds after successful creation. Fix:
    retry loop (6×10s) around project-level grants in deploy_toolbox /
    deploy_state_writer / deploy_frontend. (Distinct from the chunk-12
    Agent Engine pattern — there the SA doesn't EXIST until deploy, so
    reordering was the fix; here it exists but hasn't propagated, so
    waiting is.)
  - **Hidden interactive prompt:** `gcloud run deploy --source` asks Y/n
    to create its Artifact Registry repo on first use — stalls unattended
    `setup/all.sh` and DIES on prompt timeout under `set -e` (observed).
    Fix: `--quiet` in simulator/deploy.sh. Highest-severity find of the
    session for the hackathon room.
  - **Silent multi-minute activation stall:** activate.sh's TOOLBOX_URL
    discovery (first gcloud API call on a project with Cloud Run API not
    yet enabled) hung silently ~5 min. Fix: `timeout 10` + heartbeat echo.
    Validated: second fresh project activated fast.
  - **GOOGLE_CLOUD_LOCATION clobber:** activate.sh unconditionally
    exported `global`, silently defeating the documented regional escape
    (demo.sh sources activate.sh). Fix: env-respecting default.
  - **Doomed cross-project bucket grant:** simulator/deploy.sh tried to
    bind IAM on gs://class-demo (now public-read); students lack
    getIamPolicy → caught-but-scary red ERROR. Fix: removed, replaced
    with an explanatory echo.
  - Also: `deploy/.engine_resource` untracked + gitignored (committed
    copy pointed every fresh clone at a dead project's engine).
  - **Measured fresh-install timings** (canonical, in RUN_OF_SHOW): 10s /
    55s / 48s / 12s / 155s / 88s / verify ~70s = **7m 18s total** (prior
    fresh run: 5m 34s). The advertised "~20-30 min" is now "budget 20,
    ~10 typical" — README/all.sh/STUDENT_GUIDE claims need the same edit
    (P2.7 list). Choreography upside: student setups go green BEFORE the
    opening demo ends.
- **#9 (NEW, CLOSED — Q&A staleness):** pit-wall answer to "how is our
  energy remaining?" reported lap-26-era cumulative CONSUMPTION (64.1%)
  while the live gauge read ~teens REMAINING. Three stacked causes:
  wrong tool family (get_energy_curve = normalized consumption history,
  a different instrument than get_current_state's live battery), stale
  through_lap, and the persistent Q&A session legitimizing old tool
  responses ("a tool response in this conversation" includes one from
  minutes of race-time ago). **Fresh-session control via agent_chat
  behaved CORRECTLY** (get_current_state first, right lap, right answer)
  — isolating the persistent session as the trigger. Fix: FRESHNESS
  subsection in the GIVEN data-discipline block (both packages):
  per-question state re-fetch; "remaining" answered from
  energy_pct_remaining only; energy_curve restricted to rival/field
  comparisons. Validated live post-fix (both phrasings correct at the
  pit wall). Bonus mechanism note: failed ADK runs are NOT rolled back —
  partial tool results persist in the session, so consecutive failed
  retries of one question accidentally checkpoint their way to an
  answer. Teachable.

## Decisions (additions this phase)

| Decision | Rationale |
|---|---|
| Event projects: use the resourced Qwiklabs project type | Finding #7 re-baseline: zero 429 retries across two full 5× races vs same-day storms on the standard type. Single strongest lever found. |
| Model escape ladder documented in RUN_OF_SHOW; `gemini-3.1-flash-lite` is the tested first rung; default stays `gemini-3.5-flash` | Lite passed the live quality audit but not the graded chunk-8 fact-check; defaults change on grades, not vibes. 2.5-flash demoted to second rung (retires 2026-10-16). |
| Tower shows driver SURNAMES (BQ-generated map baked into index.html), not 3-letter codes | Matches what the radio voice says; closes the audience name-mapping gap. Map generated from fe_race10.drivers at patch time — never hand-typed (the repo's own anti-hallucination lesson). |
| Radio meta line shows `secs · tools` per proactive call | Already in every payload; one-line render. Audience-visible orchestration texture WITHOUT cannibalizing the BONUS.md observability-panel ticket (that ticket streams live tool EVENTS — still distinct). |
| Patch-file conventions (workflow): patch scripts land in the REPO ROOT (Cloud Shell editor can't edit outside $HOME), are cumulative + skip-if-applied, and get rm'd after | Two-clone reality: a cumulative patch is safe on both the patched clone and a fresh one; /tmp staging is unusable in Patrick's editor. |

## P2.6 — delivered (all pushed to main)

- [x] `fresh_project_patch2.py` (cumulative, run + removed) — Finding #8
  fixes across activate.sh, 3× deploy scripts, simulator/deploy.sh.
- [x] `pre_push_patch.py` (run + removed) — Finding #9 freshness rule in
  solution+starter prompts.py; index.html surname map + meta enrichment.
- [x] `.engine_resource` untracked; .gitignore updated.
- [x] Fresh-project validation #1 (standard type): exposed #8, then GREEN.
- [x] Fresh-project validation #2 (resourced type, all fixes from clone):
  unattended GREEN 7m18s, zero patch files — the true student path.
- [x] DSQ re-baseline + model-escape test (Finding #7 closure data).
- [x] RUN_OF_SHOW.md updated (this drop): timing cells, 5× baselines both
  models, three VERIFIED troubleshooting rows, revised time claims, DSQ
  fix row rewritten around the tested ladder, new IAM-retry row.
- [x] This PACKAGING.md update.

## P2.7 — next cascade (small, batched for one patch)

- [x] index.html: REMOVE the surname tooltip (`title` attr) — dead on
  arrival: the tower rebuilds via innerHTML at 1 Hz, so the element never
  survives the hover delay. Surname itself works; tooltip is noise.
- [x] main.py: optional — stamp Q&A answers with wall secs (`_handle_ask`
  timing); tool count not cheaply available on the ask path. Patrick to
  confirm want.
- [x] README.md + setup/all.sh header + STUDENT_GUIDE.md: revise the
  "~20-30 min" setup claims to "budget 20, ~10 typical" (Finding #8).
  (Done — README + all.sh patched; STUDENT_GUIDE carried no such claim.)
- [ ] activate.sh nicety (optional): warn if `deploy/.engine_resource`
  refers to a different project than PROJECT_ID (stale-file confusion
  guard for long-lived clones).

## P3 — acceptance tests (status)

**Test 1 (full local run):** scoreboard baselines — 5× DONE both models
(see RUN_OF_SHOW); 2×/1× rows + step-7 timing cell + opening-script
timing + lap-2 drop point → capture at the run-of-show rehearsal (those
speeds get run then anyway). FINISH sanity-poked earlier (P2.5 run).
Three robustness rows VERIFIED (kill-uvicorn, RESTART mid-race, browser
bounce). Q&A spread exercised incl. the Finding #9 regression check.

**Test 2 (docs voice pass):** unchanged — STUDENT_GUIDE nine new sections
in context, GIVEN-banner prose, BONUS ticket sanity. Plus: this drop's
RUN_OF_SHOW edits get a skim in the same pass.

## Open items — KEEP PARKED

- [ ] All-backends-503 triage protocol (needs a live deployed stack —
  pairs naturally with the step-7 rehearsal).
- [ ] Qwiklabs template observation (carry-over) — NOTE: the resourced
  project type recommendation (Finding #7) feeds directly into this.
- [ ] Optional: evening `qa_latency_probe` rerun — arguably moot on the
  resourced project type (zero retries); keep parked, revisit only if
  rehearsal latency disappoints.

## Target repo layout (delta this phase)

```
formula-e-race-engineer/
  activate.sh               ← hardened (timeout, env-respecting location)
  deploy/deploy_*.sh        ← IAM grant retry (3 files)
  deploy/.engine_resource   ← UNTRACKED (gitignored; per-project artifact)
  simulator/deploy.sh       ← --quiet; bucket grant removed
  solution|starter/.../prompts.py ← FRESHNESS rule (GIVEN section)
  frontend/static/index.html ← surname tower, meta secs·tools
  RUN_OF_SHOW.md, PACKAGING.md ← this drop
```
## Phase 2.8 — rehearsal + cleanup closeout (2026-06-06)

### Findings (new this session; all patched + shipped)

**Finding #10 — persistent Q&A session survives replay restarts; failed
asks poison it.** Symptom: the Cassidy fused question ran textbook in a
fresh `agent_chat` session (name-resolve CAS→37 via field_am_status,
parallel get_energy_curve, 12.2s, zero retries) yet the pit wall returned
"Radio failure" then "no telemetry for Cassidy" — the persistent session
had checkpointed a failed ask mid-stream (the Finding #9 mechanism) and
every later ask inherited the poison. In engine mode the session even
survives frontend restarts. Fix (`qa_rotate_patch`, shipped): both agent
clients grew `reset_qa_session()` with a rotatable unique session id; the
engineer loop's restart branch calls it and logs "Q&A session rotated for
the new race". RESTART is now the designed reset; the SESSION_RESET bounce
is demoted to belt-and-braces. Verified post-deploy (proper fresh-session
answer; rotation log line confirmed sighted at restart).

**Finding #11 — deploy_frontend.sh died silently (exit 1, zero output).**
A bare `SIM_URL=$(gcloud ... 2>/dev/null)` assignment under `set -e`
killed the script on a transient gcloud failure — one line BEFORE its own
WARN guard could run. Fix (shipped, applied inline): `|| true` inside the
substitution, matching setup/7 and verify.sh (demo.sh was accidentally
immune via the `export` builtin swallowing the status). Earned the
troubleshooting row: silent script death ⇒ `echo $?`, then
`bash -x ... | tail -20`.

**Finding #12 — Finding #8's IAM race on the one unpatched surface.**
simulator/deploy.sh granted topic-level pubsub.publisher with NO retry;
on a fresh project the grant fired seconds after SA creation and died on
"service account does not exist" — at step 6, the LAST step of all.sh,
during the window students run it unattended. Hit live creating the new
rehearsal project. Fix (`sim_iam_retry_patch`, shipped): the same 6×10s
retry loop as its three siblings; RUN_OF_SHOW's "steps 3/5/6" retry row is
now literally true.

### Finding #7 addendum — lite promotion test (graded, FAIL)

Promotion test run 2026-06-06 (2× stint, laps 1–12, graded): timing facts
and AM durations exact, 3/3 must-says — but FAILED the filler scrub
(literal "Focus on…" inside a must-say) and grounding (94-behind-Wehrlein
contradiction, ungrounded rival AM claim at 0 tools, invented
power-settings speculation). Stays the tested first escape rung; default
unchanged (`gemini-3.5-flash`). Stint scoreboard for reference: 14 event /
6 summary / 3 must-say / 37 suppressed / 0 dropped.

### Decisions

- Tiers renamed **Tier A–D** (docs and code markers; "Challenge" collides
  with the hackathon-series naming).
- Default model stays `gemini-3.5-flash` — grades, not vibes (see #7
  addendum).
- Opening restructured: 0–2 students start engines / 2–4 frame / 4–10 demo
  / 10–15 what-you-have (diagram) / 15–19 goals+tiers / 19–20 logistics.
  Immovable beats: Step-0 paste by 2:00, student-screen glance, answer-key
  policy aloud. Rehearsed: demo done by 10:00; lap-3 cluster fired as ONE
  call at the deployed wall.
- RESTART rotates the Q&A session (Finding #10); pre-flight gained a
  throwaway warm-up question (first ask after deploy is slowest — inline
  session create, now visible via the Q&A secs meta).

### Phase 2.8 delivered

- STUDENT_GUIDE.md rewritten for strangers: Step-0 block (incl.
  `cloudshell workspace .`), tinyurl placeholder, ⏸ stop-here, per-tier
  scaffold (open this file → challenge → need-to-know → done-looks-like →
  test → checkpoint), question bank as rows, surname-vs-code note,
  architecture diagram embed.
- HOW_IT_WORKS.md (NEW): frames, services, two worlds + clock bridge,
  trigger loop, journey-of-a-question, YOURS/READ/PLUMBING file map.
- RUN_OF_SHOW.md rewritten for a stranger-deliverer: SAY/SHOW/WHY per
  segment; measured cells (step 7 = 8m14s first-create: engine 5m32s
  silent + frontend 2m42s); reworded pre-flight (FINISH = don't press;
  warm-up ask; bounce demoted); new troubleshooting rows (stale Q&A,
  silent-death triage, log commands); the all-backends-503 protocol;
  model-ladder note with the lite FAIL; one-engineer-per-pool rule.
- docs/architecture.svg (NEW): hand-coded, GitHub-safe, Tier A–D bar.
- Code tier markers renamed via this patch.

### Acceptance tests

- **Test 1 (instructor path) — CLOSED** with noted exceptions: step-7 cell
  filled (true first-create on a fresh resourced project), engine_smoke
  green, opening rehearsed out loud within budget, cluster-as-one-call
  confirmed at the deployed wall. Deliberately skipped: the 2×/1×
  full-race scoreboard rows (the 5× P2.6 rows stand as canonical; Patrick:
  "happy with what we have"). Deferred to event morning: the lap-2 → 1×
  drop-point confirmation (in RUN_OF_SHOW's event-morning checklist).
- **Test 2 (docs voice pass) — CLOSED**: nine sections reviewed in voice,
  all ADK links verified live, Toolbox link 404 fixed (mcp-toolbox.dev),
  README tool-count wording fixed, GIVEN banners consistent, BONUS tickets
  reference real surfaces, timing table sums.

### Open-items disposition

- all-backends-503 triage → CLOSED (protocol landed in RUN_OF_SHOW).
- qa_latency probe → CLOSED, moot (Q&A wall-secs now stamped on every
  answer via P2.7).
- Resourced-project-type provisioning for the event → PARKED, now an
  event-morning checklist item in RUN_OF_SHOW.
- Optional nits, deliberately left: setup/7 header could mention the
  DEPLOY_AGENT_PACKAGE override; DRIVERS map's `full` field is dead data
  post-tooltip (plausible BONUS consumer).


## Phase 3 — design evaluation: build-up progression vs hardened tiers (2026-06-07)

**The question.** Tier A asks a stranger to implement three tools against an
internal API surface nothing introduced — 40 minutes of repo archaeology
before any ADK learning. Before paying the P2.9 documentation debt that
design creates, evaluate the alternative: a build-up progression (v1 `adk
create` + naive prompt → hallucination; v2 one raw SQL tool → grounded but
slow/trapped; v3 MCP Toolbox → fast history, no "now"; v4 frame tools GIVEN
→ two worlds; then persona/scorer as today).

### Spike evidence

**Contract compatibility — CLOSED, PASS (live-tested this session).**
`adk create` on ADK 1.34.3 (what the repo's `>=1.0,<2` pin resolves to
today; current codelabs corroborate) emits exactly `__init__.py`
(`from . import agent`), `agent.py` exposing `root_agent`, and `.env`. That
scaffold drops CLEAN into every root_agent-only consumer through the
existing seam — `AGENT_PACKAGE=<scaffold_pkg> python scripts/agent_chat.py`
resolved and constructed with zero changes. The pit-wall frontend does NOT
consume it: main.py/engineer_loop import `config`, `prompts` (both trigger
builders), `snapshot`, and `tools.state_client` at module load (verified:
ImportError at `agent_module('config')`). Consequence, not blocker: the pit
wall enters the progression at v4, when students graduate into the starter
package — which already has the five-module shape and is already the
activate.sh default. **No frontend, seam, scorer, or data-plane changes
required by the redesign.**

**v2 viability — desk evidence strong, live behavior UNTESTED.** The raw-SQL
trap inventory is already verified in-repo: `laps.top_speed` always 0;
`event_stream` overtake rows carry the subject's GRID POSITION in
`car_number` (position-adjacency verified 2026-06-04 — raw `WHERE
car_number=13` silently returns the wrong driver); INT64-ns time columns;
normalized energy (race totals sum to 100 by construction); 1.28M-row
telemetry. The `execute_sql_bq` docstring is the fossil record of what raw
SQL against this dataset required. Verdict shape: free-form v2 is a tar
pit; SCRIPTED v2 (two wins + two traps + one future-leak) is plausibly a
20-minute teaching stage — the traps become the lesson. Unprovable off-box.

**v1 demo risk (new, found in evaluation).** The hallucination checkpoint is
load-bearing and unvalidated: Berlin 2024 R10 is pre-cutoff and
well-reported — gemini-3.5-flash may answer the famous facts CORRECTLY from
training data, or hedge, instead of confidently hallucinating. A refusal
still motivates grounding (weaker drama); a correct answer inverts the demo.
Granular questions (lap-7 energy, arming scenarios) are the mitigation.

### Decision rule (gates for the 30-minute live probe)

Probe kit shipped: `spike_engineer/` + `scripts/spike_probe.py` (v1 and v2
question scripts, timing, transcripts to `spike_transcripts/`; run v2 both
bare and with `SPIKE_SCHEMA_TOOL=1`).

- **ADOPT the hybrid** if (a) v1 answers are confidently wrong or cleanly
  refuse on the scripted asks, AND (b) v2's scripted path lands both WINs
  correct in <90s each with no error loops, with ≥1 trap producing its
  vivid wrong answer.
- **KEEP current + execute P2.9** if v1 inverts (model knows the race) or
  v2 tar-pits even scripted.

### The hybrid, if adopted (v-to-repo mapping)

v1–v3 live in a student-created scaffold at repo root (`adk create`,
consumed via AGENT_PACKAGE for agent_chat/adk web). v4 = graduate into
`starter/race_engineer` — frame_tools.py flips to COMPLETE (given reading;
teaching header becomes a tour), students port their instruction text into
prompts.py, `AGENT_PACKAGE=starter.race_engineer` (already the default),
demo.sh lights the pit wall. v5/v6 = Tiers C/D unchanged. Old Tier A TODO
content → BONUS "build your own frame tool" ticket; solution stays the
reference. Time math: v1 ~20 + v2 ~20 + v3 ~25 + v4 ~25 + C 30 ≈ 120 min vs
current 115 effective (A40+B45+C30) — a wash; the redesign's margin comes
from deleting Tier A archaeology, and every stage ends runnable (current
Tier A's mid-state is NotImplementedError-land). Teaching note recorded for
the side-by-side: today's marquee docstring-is-the-API lesson is READ, not
written (starter docstrings are given; students fill bodies); in v2 students
write one tool — docstring, schema, guard — from a blank line.

### Status

**GATED** — decision finalizes on the probe transcripts. Until then the
current design stands and the P2.9 scope (TODO mirroring + checker,
per-tier orientation in HOW_IT_WORKS, ≤5-min opening demo + editor tour)
remains the committed fallback. Hardened assets are out of scope either way.


### P3 closure — DECISION: ADOPTED (2026-06-07, live-probe gates passed)

**Gate results (transcripts in the planning hub; graded same day):**
- **v1/Tier A:** 4-of-5 asks confidently hallucinated with fabricated
  precision (invented "2+6" AM split, lap-7 energy to a decimal, "462
  overtakes"); the 1-of-5 exception — the famous fact (DAC won) — came
  back CORRECT from training data. Graded as a PASS that *strengthens*
  the beat: true headline and invented telemetry, identical delivery.
- **v2/Tier B:** all gates green in BOTH ablations — WINs correct in
  14.1s/24.5s (bare), zero error loops, worst question 70.7s. Schema-tool
  ablation moved nothing (the model self-discovers INFORMATION_SCHEMA);
  the dedicated schema tool is dropped — Tier B is ONE hand-written tool.
- **Trap grades:** top-speed trap DEFEATED both runs (model saw 0, found
  `top_speed_per_lap`, answered 226.9 correct) — repurposed as the
  recovery beat; also settles the fix-the-column question: broken column
  + visible repair stays. Overtake trap FIRED both runs (52–70s, 15–19
  calls, wrong count, contradicting rows dismissed as "telemetry
  glitches"/"loop calculation noise" — a hallucinated EXPLANATION) —
  promoted to the instructor set-piece. Future-leak fired textbook both
  runs ("Cassidy P2, gap 0.69s" off the final lap).

**Delegated calls (Patrick approved the adoption; these two were left to
the session):** (1) single letter ladder **Tier A–F** — A build / B ground
/ C curate / D go-live / E persona (old C, content unchanged) / F stretch
(old D, content unchanged); marker renames TODO(B)→(D), TODO(C)→(E).
(2) The Vergne question is an **instructor set-piece** at the B→C
checkpoint (scripted in RUN_OF_SHOW), with a question-bank row for the
curious — not on the student script.

**Delivered (this drop):**
- STUDENT_GUIDE.md — build path rewritten Tiers A–F (scaffold → ground →
  curate → go live → persona → stretch); all hardened non-build sections
  byte-identical; 3-lane team table (Persona and Triggers start
  immediately — the starter runs as shipped, so parallelization survives).
- starter/frame_tools.py flipped COMPLETE (solution bodies verbatim);
  banner now given-reading; old TODO(A) build → BONUS "build your own
  frame tool" ticket. starter agent.py = Tier D (TODO(D)); starter
  prompts.py = Tier E (TODO(E)). Validator + local_test headers updated.
- RUN_OF_SHOW: glance row, architecture SAY, goals+tiers SAY rewritten;
  checkpoint beats A–F; the Tier B set-piece scripted (with the
  "Grounding moved the lie. It didn't remove it." line); morning-of
  rehearsal gains `stage_probe.py --stage a|b`.
- HOW_IT_WORKS: two-worlds row + YOURS map → A–F (light edits, as scoped).
- docs/architecture.svg: tier bar A–D → A–F (same span, six cells).
- solution/scaffold/ (NEW): the Tiers A–C answer key (prompts.py +
  agent.py with execute_race_sql; Tier C wiring as commented reference).
- scripts/stage_probe.py (NEW, replaces spike_probe.py): the standing
  rehearsal instrument — rerun on event morning and after ANY model
  change; the Tier A/B beats are model-behavior demos. spike_engineer/
  and spike_probe.py retired (history in git; transcripts graded).

**Verification (run before the event):** `stage_probe.py` both stages
green per its GRADE notes; `test_frame_tools.py --live` all ✓ on the
shipped starter; `AGENT_PACKAGE=starter.race_engineer agent_chat` answers
the now-question and the Wehrlein fusion with only TODO(D) filled;
`RUN_SOLUTION=1`-equivalent unchanged (solution untouched); one full
Tier A→D walk as a student would, timed. Open: re-rehearse the
goals+tiers minute against the 19:00 budget (wordier than the old SAY).

### Finding #13 — service-agent IAM race (CLOSED 2026-06-07)

The #8/#12 propagation race on the one account kind the sweep didn't
cover: Google-managed SERVICE AGENTS. Hit live at setup step 5 on the P3
verification project: `services identity create` returns the Pub/Sub
agent's email immediately, but the tokenCreator binding seconds later
died with "Service account ... does not exist." Gate-on-existence was
considered and rejected: service agents live in a Google-owned tenant
project with no reliable existence probe, so the grant itself is the
probe — the retry IS the gate. Fix (`sa_agent_retry_patch`, run +
removed): the standard 6x10s retry on the two remaining unprotected
grants (state-writer tokenCreator — bitten; agent-engine datastore.user —
same class, shielded so far only by the 5-minute engine create).
RUN_OF_SHOW retry-lines note now covers steps 3/5/6/7. **Validation
owed:** one more virgin-project `setup/all.sh` after the current test
pass — re-validates #13 alongside the Tier A-F drop on the true student
path.
