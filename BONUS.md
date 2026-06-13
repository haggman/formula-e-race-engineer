# BONUS board — for teams that finish early

Everything here is **additive**: nothing on this board can break the build
you already demo. Each ticket lists the surface you'll touch, the spec, and
the demo payoff — no solutions. Sizes: **[S]** < 20 min · **[M]** 30–45 min ·
**[L]** the rest of the afternoon.

---

## UI

### [S] Voice picker
- **Surface:** `frontend/tts.py` (`TTS_VOICE`, `TTS_RATE` env knobs),
  `frontend/static/index.html`.
- **Spec:** a dropdown on the pit wall that switches between Chirp 3 HD
  voices live, mid-race. Expose rate too if you're feeling fancy.
- **Payoff:** "and here's the same engineer in a different voice" — an
  instant, visceral demo beat.

### [M] Tool-call observability panel
- **Surface:** the websocket layer in `frontend/main.py` + a new panel in
  `index.html`. The agent client already knows tool counts; surface the
  *events*.
- **Spec:** stream each tool invocation (name + key args) to a side panel as
  the agent works, so the audience watches it chain live-state and history
  tools in real time.
- **Payoff:** the single best way to show *agency* — the room sees the agent
  deciding, not just answering.

### [L] Track map with live car dots
- **Surface:** `frontend/static/index.html` (replace the lap-counter circle),
  one dict in `ui_state()` in `frontend/main.py`, a one-time analysis script
  in `scripts/`.
- **Spec:** swap the lap ring for the real Tempelhof outline with a moving
  dot per car. The pieces are all waiting:
  - **Position data:** every 1 Hz frame already carries per-car
    `gps: {lat, lng, heading}` (see `shared/models.py`) — the frontend
    poller holds it and `ui_state()` currently throws it away. Three new
    fields and it's at the browser.
  - **The map:** the official **Circuit Map V.2** (clean, reads well small)
    and the Google-Earth-faithful CCTV/TSB plan live at
    `gs://class-demo/formula-e/reference/`. V2 is stylized, so do NOT
    affine-fit GPS onto it — go via *fraction of lap*: build a centerline
    polyline once from car #13's 20 Hz BigQuery trace
    (`telemetry.tv_gps_lat/long`), project each live fix onto it, take
    arc-length ÷ 2,345 m → `f`. Trace V2's blue line once as an SVG path
    (in racing direction, starting at START/FINISH) and place dots with
    `path.getPointAtLength(f * totalLength)` — dots ride the artwork by
    construction.
  - **Calibration gifts, printed on the map:** start/finish offset 0m,
    i1 @ 680m, i2 @ 1600m — three anchors if proportions need a piecewise
    stretch (at small sizes they likely won't).
- **Gotchas:** at 1 Hz a car moves ~55 m between ticks — tween the dots
  client-side or they teleport. Trace only the track outline, not the
  branded artwork.
- **Payoff:** the pit wall stops *telling* you where cars are and starts
  *showing* you — the lap-3 attack-mode cluster becomes ten dots diving
  off-line in unison.

---

## AGENT

### [M] Post-race DEBRIEF
- **Surface:** `prompts.py` (a debrief prompt builder) + a DEBRIEF button next
  to the new FINISH button (`index.html` + a small `frontend/main.py` route).
- **Spec:** at the checkered flag, one button makes the engineer narrate the
  whole race arc — using **only historical tools**. Pairs perfectly with
  FINISH: jump to the end, then debrief.
- **Payoff:** a clean closing beat for any demo: "race over — let's hear the
  story."

### [L] Re-cast: same race, different car
- **Surface:** `config.py` (`OUR_CAR_NUMBER`), `prompts.py` persona.
- **Spec:** run the identical replay as **Cassidy, car #37** — DAC's
  eleven-exchange rival — with a persona to match. The same events read
  completely differently from the other cockpit.
- **Payoff:** proves the architecture: data and policy are given, *identity*
  is just your package.

---

### [M] Build your own frame tool
- **Surface:** `starter/race_engineer/tools/frame_tools.py` (+
  `scripts/test_frame_tools.py` as your checklist).
- **Spec:** the four given tools arrived complete in Tier D — now earn
  one. Either pick one of the three event/AM tools, delete its body (keep
  the docstring — it's the API), and reimplement it against live Firestore
  via `get_state_client()`; or design a NEW one (`get_gap_to_leader`?).
  The response models and helpers at the bottom of the file are your
  toolkit. One law: wrap every event with `AgentEvent.from_event()` —
  read that docstring for the future-leak story before you start.
- **Payoff:** the docstring-is-the-API lesson with a live system on the
  other end — and `test_frame_tools.py --live` flips ✗→✓ the moment
  you're green.

## VOICE & DATA

### [S] Portuguese radio
- **Surface:** `frontend/tts.py` locale/voice settings, a line of persona in
  `prompts.py`.
- **Spec:** DAC is Portuguese — let his engineer call the race in Portuguese
  (or any locale TTS supports).
- **Payoff:** one-line change, disproportionate applause.

### [M] Mini eval harness
- **Surface:** a new script in `scripts/` built on the `agent_chat` plumbing.
- **Spec:** five canned questions with pass/fail checks — at minimum: no
  invented driver names, and a clean refusal on the weather question.
- **Payoff:** "we don't just demo it, we test it" — the judges' favorite
  sentence.

---

## DEPLOY

### [L] Ship YOUR agent to the cloud
- **Surface:** `deploy/` — no code changes; the knob already exists.
- **Spec:** the deploy path vendors whatever `DEPLOY_AGENT_PACKAGE` points
  at. Point it at your package and run the same two deploy steps the
  reference uses:

  > **WHERE:** Cloud Shell, repo root, after `source activate.sh`
  > **WHAT:**
  > ```bash
  > export DEPLOY_AGENT_PACKAGE=starter.race_engineer
  > bash setup/7_deploy_cloud.sh
  > ```
  > Engine creation is **silent for 5–10 minutes** — that's normal. You get a
  > public pit-wall URL at the end.
- **Payoff:** your team's engineer, on a public URL, on real infrastructure —
  the demo runs from a phone.

---

## Alternates (if a ticket above is blocked)

- **AM countdown timers** — surface remaining boost seconds as a live
  countdown in the our-car panel.
- **Radio transcript replay** — a scrollable log of every call with race-time
  stamps; scrub the race story after the flag.
