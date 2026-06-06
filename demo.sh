#!/usr/bin/env bash
# demo.sh — launch the LOCAL pit wall with zero rememberable parts.
#
# WHERE: Cloud Shell (any directory — the script cd's to the repo itself)
# WHAT:  bash demo.sh                  # STUDENT mode — your agent (starter package)
#        RUN_SOLUTION=1 bash demo.sh   # SOLUTION mode — the finished reference agent
#
# Stage knobs (opt-in — plain relaunches never touch the running race):
#        RUN_SOLUTION=1 FRESH=1 SPEED=2 bash demo.sh   # audience demo: fresh race, 2×
#        RUN_SOLUTION=1 FRESH=1 SPEED=5 bash demo.sh   # rehearsal: compressed race
#
# Born from the universal-503s incident: a recycled Cloud Shell session drops
# exports, the pit wall comes up sim-less, and everything on the SIM bar 503s.
# This script re-sources activate.sh and re-derives SIM_URL on every launch,
# so a fresh tab or recycled session can never bite again.

set -eo pipefail
cd "$(dirname "$0")"

# activate.sh exits nonzero itself if no project is configured; with set -e
# that stops us right here with its own error message.
source activate.sh

if [[ "${RUN_SOLUTION:-0}" == "1" ]]; then
    export AGENT_PACKAGE=solution.race_engineer
    echo "demo.sh: RUN_SOLUTION=1 — SOLUTION mode (the finished reference agent)"
fi

export SIM_URL="${SIM_URL:-$(gcloud run services describe fe-simulator --region "$REGION" --format='value(status.url)' 2>/dev/null)}"
if [[ -z "$SIM_URL" ]]; then
    echo "ERROR: could not derive SIM_URL — is fe-simulator deployed in ${REGION}?" >&2
    exit 1
fi

# Optional stage knobs. SPEED first is cosmetic only — the simulator
# preserves the multiplier across restarts.
if [[ -n "${SPEED:-}" ]]; then
    curl -s -X POST "$SIM_URL/speed" -H 'Content-Type: application/json' \
        -d "{\"multiplier\": ${SPEED}}" >/dev/null
    echo "demo.sh: sim speed → ${SPEED}×"
fi
if [[ "${FRESH:-0}" == "1" ]]; then
    curl -s -X POST "$SIM_URL/restart" >/dev/null
    echo "demo.sh: race restarted from the grid"
fi

echo "demo.sh: AGENT_PACKAGE=${AGENT_PACKAGE:-<activate.sh default>}"
echo "demo.sh: SIM_URL=${SIM_URL}"
echo "demo.sh: open Web Preview on port 8080"
exec uvicorn frontend.main:app --host 0.0.0.0 --port 8080
