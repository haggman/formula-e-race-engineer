#!/usr/bin/env bash
# Set up Firestore Native mode database for the race engineer agent.
#
# Idempotent: safe to re-run. Skips creation if database already exists.
#
# Required env vars (set by sourcing activate.sh):
#   PROJECT_ID, REGION

set -euo pipefail

if [[ -z "${PROJECT_ID:-}" ]]; then
    echo "ERROR: PROJECT_ID env var required. Run: source activate.sh" >&2
    exit 1
fi
if [[ -z "${REGION:-}" ]]; then
    echo "ERROR: REGION env var required. Run: source activate.sh" >&2
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

# --- Composite indexes ---
echo ""
echo ">>> Creating composite indexes on race_events..."
echo "    (indexes build async — may take 1-2 minutes after this script returns)"

# Helper: create an index if it doesn't already exist.
# gcloud's `create` is not idempotent — it errors if a matching index exists.
# We detect this via grep on the error and treat it as success.
# --- Composite indexes ---
echo ""
echo ">>> Submitting composite index creates (async)..."

create_index() {
    local desc="$1"; shift
    if out="$(gcloud firestore indexes composite create \
        --database="$DATABASE_ID" \
        --project="$PROJECT_ID" \
        --collection-group=race_events \
        --query-scope=COLLECTION \
        --async \
        "$@" 2>&1)"; then
        echo "    ⏳ $desc — submitted"
    else
        if echo "$out" | grep -q "already exists"; then
            echo "    ✓ $desc — already exists"
        else
            echo "    ✗ $desc — ERROR: $out" >&2
            return 1
        fi
    fi
}

create_index "race_id + race_time_s (desc)" \
    --field-config=field-path=race_id,order=ascending \
    --field-config=field-path=race_time_s,order=descending

create_index "race_id + event_type + race_time_s (desc)" \
    --field-config=field-path=race_id,order=ascending \
    --field-config=field-path=event_type,order=ascending \
    --field-config=field-path=race_time_s,order=descending

create_index "race_id + car_number + race_time_s (desc)" \
    --field-config=field-path=race_id,order=ascending \
    --field-config=field-path=car_number,order=ascending \
    --field-config=field-path=race_time_s,order=descending

echo ""
echo ">>> Waiting for indexes to build..."
echo "    Firestore builds indexes in parallel. For ~14 docs, expect under a minute,"
echo "    but Firestore can sometimes take 5-10 minutes regardless of doc count."
echo ""

TIMEOUT_S=900     # 15 minutes — Firestore can be slow even on tiny data
INTERVAL=10
ELAPSED=0
EXPECTED=3

while (( ELAPSED < TIMEOUT_S )); do
    # Pull all race_events index states in one call, count by status.
    STATE_LIST=$(gcloud firestore indexes composite list \
        --database="$DATABASE_ID" \
        --project="$PROJECT_ID" \
        --filter="collectionGroup=race_events" \
        --format='value(state)' 2>/dev/null)

    READY_COUNT=$(echo "$STATE_LIST" | grep -c '^READY$' || true)
    CREATING_COUNT=$(echo "$STATE_LIST" | grep -c '^CREATING$' || true)
    TOTAL_COUNT=$(echo "$STATE_LIST" | grep -c '.' || true)

    if (( READY_COUNT >= EXPECTED )); then
        echo "    ✓ All ${EXPECTED} indexes READY (after ${ELAPSED}s)"
        break
    fi

    echo "    ⏳ ${READY_COUNT}/${EXPECTED} ready, ${CREATING_COUNT} building, ${TOTAL_COUNT} total visible (${ELAPSED}s elapsed)"
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done

if (( READY_COUNT < EXPECTED )); then
    echo "    ⚠ Polled for ${TIMEOUT_S}s and only ${READY_COUNT}/${EXPECTED} ready."
    echo "    Indexes are still building in the background — they will become available."
    echo "    Check status with:"
    echo "      gcloud firestore indexes composite list --database=$DATABASE_ID --project=$PROJECT_ID"
fi