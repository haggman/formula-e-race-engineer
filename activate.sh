#!/usr/bin/env bash
# Activate the formula-e-race-engineer dev environment.
#
# Usage (must use 'source', not bash):
#     source activate/activate.sh
#
# Idempotent: safe to source multiple times per shell session.

# --- Region ---
# Default to us-central1 (matches gs://class-demo bucket region).
# Override before sourcing if your lab assigns a different region:
#     export REGION=us-east1
#     source activate/activate.sh
export REGION="${REGION:-us-central1}"

# --- Project ID ---
# Read from gcloud config (Qwiklabs sets this).
export PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
if [[ -z "$PROJECT_ID" ]]; then
    echo "ERROR: no project set. Run 'gcloud config set project YOUR_PROJECT'." >&2
    return 1 2>/dev/null || exit 1
fi

# --- Virtual environment ---
# Find the repo root (the directory containing this script's parent).
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${REPO_ROOT}/.venv"

if [[ ! -d "$VENV_DIR" ]]; then
    echo ">>> Creating virtual environment at $VENV_DIR"
    python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

# --- Install / update requirements ---
# Check if requirements are satisfied. If not, install.
# We use a stamp file so we don't run pip on every source.
REQ_FILE="${REPO_ROOT}/requirements.txt"
STAMP_FILE="${VENV_DIR}/.req-stamp"

if [[ -f "$REQ_FILE" ]]; then
    if [[ ! -f "$STAMP_FILE" ]] || [[ "$REQ_FILE" -nt "$STAMP_FILE" ]]; then
        echo ">>> Installing requirements (requirements.txt is newer than venv stamp)"
        echo "    upgrading pip, wheel, setuptools..."
        pip install --upgrade pip wheel setuptools 2>&1 | grep -E "^(Collecting|Installing|Successfully|Requirement already)" || true
        echo ""
        echo "    installing project requirements..."
        pip install -r "$REQ_FILE" 2>&1 | grep -E "^(Collecting|Installing|Successfully|Requirement already|ERROR)" || true
        touch "$STAMP_FILE"
        echo ""
        echo "    installing project packages (editable)..."
        pip install -e "$REPO_ROOT" 2>&1 | grep -E "^(Obtaining|Installing|Successfully|ERROR)" || true
    fi
fi

# --- Status ---
echo ""
echo "=================================================================="
echo "  formula-e-race-engineer activated"
echo "=================================================================="
echo "  Project: $PROJECT_ID"
echo "  Region:  $REGION"
echo "  Venv:    $VENV_DIR"
echo "  Python:  $(python3 --version)"
echo "=================================================================="
echo ""
echo "To deactivate: 'deactivate'"
echo "To re-install requirements: 'rm ${STAMP_FILE} && source activate/activate.sh'"