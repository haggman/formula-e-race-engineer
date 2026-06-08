# Smoke Test

A ~15-minute pass to confirm a fresh deployment is healthy before relying on
it. Run it on a clean GCP project (e.g. a new Qwiklabs lab). Each step lists
the command and what a PASS looks like. Stop at the first failure and note
which step.

If anything prompts for input during setup, that's a finding — capture the
step and the exact line.

---

## 1. Set up the data plane

```bash
git clone https://github.com/haggman/formula-e-race-engineer.git
cd formula-e-race-engineer
gcloud config set project "$(gcloud config get-value project)"
source activate.sh
bash setup/all.sh            # steps 1-6 + verify; budget 20 min (~10 typical)
```

**PASS:** the run ends with `✓ GREEN LIGHT — the data plane is fully up`,
and check **5/5** reads `toolset 'race-engineer' loads: 14/14 tools`.

`...IAM can't see ... yet — retry N/6` lines during steps 3/5/6 are NORMAL
on a fresh project (service-account propagation), not failures.

Re-run the gate any time with `bash setup/verify.sh`.

---

## 2. Agent smoke — the reference agent end to end

```bash
AGENT_PACKAGE=solution.race_engineer python scripts/agent_chat.py
```

Ask these and check the behavior. The trace prints every tool call, so you
can see HOW it answered, not just what.

| Ask | PASS looks like |
|---|---|
| *Who's directly behind us right now?* | Names a real car/driver from `get_current_state`; fast; no BigQuery detour. |
| *What was our fastest lap so far? We're car 13.* | One clean BigQuery answer, plausible lap time (~1:05–1:10). |
| *What was our top speed on our fastest lap?* | Does NOT report 0 — recognizes the broken `top_speed` column and recovers via `get_top_speed_history`. |
| *How's our energy versus Cassidy right now?* | Fuses live state + history; speaks in mid-race deltas vs. field, not "everyone's at 100%". |
| *How many times did we overtake Vergne? We're car 13, he's car 25.* | Counts from `get_overtakes_involving` (not lap-diffing). Early race: only what's happened so far. |

**FAIL signals:** a confident specific number with no tool call behind it; a
gap quoted in seconds (it should speak in positions/trends unless it
computed the gap); answering about something that hasn't happened yet.

---

## 3. Time-honesty (do this while the race is early)

First confirm the race is early, then probe the future. Check the current
lap with `curl -s "$SIM_URL/status"` (or ask the agent) — you want a low
lap number.

| Ask (while before that lap) | PASS looks like |
|---|---|
| *What lap are we on right now?* | Reports the current (early) lap. |
| *Who wins this race?* | REFUSES — "the race is still running, I don't know yet." Does NOT call `get_field_position_at_lap(41)`. |
| *What happens on lap 35?* | REFUSES for the same reason. |
| *What was our fastest lap so far?* | Still answers normally (past/current laps are fine). |

To see whole-race answers legitimately, let the replay finish (or
`curl -s -X POST "$SIM_URL/jump" -H 'Content-Type: application/json' -d '{"race_time_s": 2850}'`,
then `sleep 15`) and ask again — now the full race is in the past.

---

## 4. Overtake total at race end

Once the replay has passed lap 38 (or after the `/jump` above), re-ask
*"How many times did we overtake Vergne? We're car 13, he's car 25."*

**PASS:** roughly **5 passes by us, 6 by Vergne** (11 lead changes), from
`get_overtakes_involving` in one call.

Data ground-truth check, independent of the agent and the race clock:

```bash
bq query --use_legacy_sql=false '
SELECT
  CASE
    WHEN car_number=13 AND position_change<0 THEN "DAC_passed_JEV"
    WHEN car_number=13 AND position_change>0 THEN "JEV_passed_DAC"
    WHEN other_car_number=13 AND position_change>0 THEN "DAC_passed_JEV"
    WHEN other_car_number=13 AND position_change<0 THEN "JEV_passed_DAC"
  END AS direction,
  COUNT(*) AS n
FROM `fe_race10.v_overtakes`
WHERE (car_number=13 OR other_car_number=13)
  AND (car_number=25 OR other_car_number=25)
GROUP BY direction'
```

**PASS:** two rows summing to 11 — 5 `DAC_passed_JEV`, 6 `JEV_passed_DAC`.

---

## 5. Pit wall first light

```bash
RUN_SOLUTION=1 FRESH=1 SPEED=2 bash demo.sh    # open Web Preview on port 8080
```

**PASS:** the tower + radio log come alive and the engineer makes calls.

> Note: the pit wall runs the *deployed* agent (Agent Engine). If you change
> a prompt or tool, redeploy with `deploy/deploy_agent_engine.sh` before
> testing here — the local `agent_chat` / `adk web` paths only need a
> restart.

---

## Result

Steps 1–3 green = the stack is sound and time-honest. Steps 4–5 confirm the
overtake data and the live demo path. Lost in the repo? See `FILE_INDEX.md`.
