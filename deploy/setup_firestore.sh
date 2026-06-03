#!/usr/bin/env bash
# Set up Firestore Native mode database for the race engineer agent.
#
# Idempotent: safe to re-run. Skips creation if database already exists.
#
# Required env vars (set by sourcing activate/activate.sh):
#   PROJECT_ID, REGION

set -euo pipefail

if [[ -z "${PROJECT_ID:-}" ]]; then
    echo "ERROR: PROJECT_ID env var required. Run: source activate/activate.sh" >&2
    exit 1
fi
if [[ -z "${REGION:-}" ]]; then
    echo "ERROR: REGION env var required. Run: source activate/activate.sh" >&2
    exit 1
fi

# Firestore uses a "location" that maps to either a region or a multi-region.
# For single-region: same string as Cloud Run region (e.g. "us-central1").
FIRESTORE_LOCATION="${FIRESTORE_LOCATION:-${REGION}}"
DATABASE_ID="${FIRESTORE_DATABASE_ID:-(default)}"

echo "=================================================================="
echo "Project:  $PROJECT_ID"
echo "Location: $FIRESTORE_LOCATION"
echo "Database: $DATABASE_ID"
echo "=================================================================="

# --- Enable API ---
echo ">>> Enabling Firestore API..."
gcloud services enable firestore.googleapis.com --project="$PROJECT_ID"

# --- Create the (default) Native-mode database if missing ---
echo ">>> Checking for existing database..."
if gcloud firestore databases describe \
        --database="$DATABASE_ID" \
        --project="$PROJECT_ID" >/dev/null 2>&1; then
    EXISTING_TYPE="$(gcloud firestore databases describe \
        --database="$DATABASE_ID" \
        --project="$PROJECT_ID" \
        --format='value(type)')"
    EXISTING_LOC="$(gcloud firestore databases describe \
        --database="$DATABASE_ID" \
        --project="$PROJECT_ID" \
        --format='value(locationId)')"
    echo "    Database '$DATABASE_ID' already exists (type=$EXISTING_TYPE, location=$EXISTING_LOC)"
    if [[ "$EXISTING_TYPE" != "FIRESTORE_NATIVE" ]]; then
        echo "    WARN: existing DB is not Native mode. Agent code assumes Native mode."
    fi
else
    echo ">>> Creating Native-mode database in $FIRESTORE_LOCATION..."
    gcloud firestore databases create \
        --database="$DATABASE_ID" \
        --location="$FIRESTORE_LOCATION" \
        --type=firestore-native \
        --project="$PROJECT_ID"
    echo "    created"
fi

echo ""
echo "=================================================================="
echo "Firestore ready: $PROJECT_ID / $DATABASE_ID / $FIRESTORE_LOCATION"
echo "=================================================================="