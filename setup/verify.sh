#!/usr/bin/env bash
# Green-light check — verifies the whole deployed data plane.  (~1 min)
# WHERE: Cloud Shell, repo root, after `source activate.sh`
# WHAT:  bash setup/verify.sh
# Run any time; setup/all.sh runs it automatically as its last step.
set -euo pipefail
cd "$(dirname "$0")/.."
source setup/_lib.sh
require_activation venv
banner "Verify — green-light check"

# Discover service URLs (no-ops if already exported)
export SIM_URL="${SIM_URL:-$(gcloud run services describe fe-simulator --region "$REGION" --format='value(status.url)' 2>/dev/null || true)}"
export TOOLBOX_URL="${TOOLBOX_URL:-$(gcloud run services describe fe-toolbox --region "$REGION" --format='value(status.url)' 2>/dev/null || true)}"

python setup/verify_checks.py
