#!/usr/bin/env bash
# Verify Cloud Shell environment is ready to build the race engineer agent.

set +e  # we want to keep going past failures

ok=0
fail=0

pass() { echo "  ✓ $1"; ok=$((ok+1)); }
miss() { echo "  ✗ $1 — $2"; fail=$((fail+1)); }
note() { echo "  ○ $1"; }

echo ""
echo "=== Required tooling ==="
command -v gcloud   >/dev/null && pass "gcloud installed"   || miss "gcloud"   "install gcloud SDK"
command -v bq       >/dev/null && pass "bq installed"       || miss "bq"       "comes with gcloud SDK"
command -v gsutil   >/dev/null && pass "gsutil installed"   || miss "gsutil"   "comes with gcloud SDK"
command -v git      >/dev/null && pass "git installed"      || miss "git"      "install git"
command -v python3  >/dev/null && pass "python3 installed"  || miss "python3"  "install python3"
command -v pip3     >/dev/null && pass "pip3 installed"     || miss "pip3"     "install pip"
command -v curl     >/dev/null && pass "curl installed"     || miss "curl"     "install curl"
command -v jq       >/dev/null && pass "jq installed"       || miss "jq"       "sudo apt-get install -y jq"

echo ""
echo "=== Python version ==="
PYV="$(python3 --version 2>&1 | awk '{print $2}')"
PYMAJOR=$(echo "$PYV" | cut -d. -f1)
PYMINOR=$(echo "$PYV" | cut -d. -f2)
if [[ "$PYMAJOR" -eq 3 && "$PYMINOR" -ge 10 ]]; then
    pass "python $PYV"
else
    miss "python $PYV" "need 3.10+"
fi

echo ""
echo "=== GCP context ==="
PROJECT="$(gcloud config get-value project 2>/dev/null)"
ACCOUNT="$(gcloud config get-value account 2>/dev/null)"
REGION_CFG="$(gcloud config get-value run/region 2>/dev/null)"

[[ -n "$PROJECT" ]]    && pass "project: $PROJECT"        || miss "project not set"     "gcloud config set project YOUR_PROJECT"
[[ -n "$ACCOUNT" ]]    && pass "account: $ACCOUNT"        || miss "not authenticated"   "gcloud auth login"
[[ -n "$REGION_CFG" ]] && pass "run region: $REGION_CFG"  || note "run region not set (will be configured later)"

echo ""
echo "=== Agent tooling (installed in a later chunk if missing) ==="
command -v adk >/dev/null && pass "adk CLI: $(adk --version 2>&1 | head -1)" || note "adk CLI not installed yet"
pip3 show google-adk >/dev/null 2>&1 && pass "google-adk python package" || note "google-adk not installed yet"
pip3 show google-cloud-aiplatform >/dev/null 2>&1 && pass "google-cloud-aiplatform python package" || note "google-cloud-aiplatform not installed yet"

echo ""
echo "=== Simulator (deployed in a later chunk) ==="
if [[ -n "${SIM_URL:-}" ]]; then
    if curl -sf --max-time 5 "$SIM_URL/health" >/dev/null; then
        pass "simulator reachable at $SIM_URL"
    else
        miss "simulator not reachable at $SIM_URL" "check deploy or URL"
    fi
else
    note "SIM_URL env var not set (will set after simulator deploy)"
fi

echo ""
echo "=== Data bucket access ==="
if gsutil ls gs://class-demo/formula-e/r10/simulator/frames_v1.jsonl.gz >/dev/null 2>&1; then
    pass "can read gs://class-demo/formula-e/"
else
    miss "cannot read gs://class-demo/formula-e/" "bucket owner needs to grant access to your account or project"
fi

echo ""
echo "============================================"
echo "  Summary: $ok pass, $fail fail"
if [[ $fail -eq 0 ]]; then
    echo "  ✅ Environment ready"
else
    echo "  ❌ Fix failures above before proceeding"
fi
echo "============================================"