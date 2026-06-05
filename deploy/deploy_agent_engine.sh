#!/usr/bin/env bash
# Deploy the race engineer to Agent Engine on Agent Platform (chunk 12).
#
# WHERE: Cloud Shell (Qwiklabs student account), repo root, venv active
# WHAT:  bash deploy/deploy_agent_engine.sh
#
# Stages the self-contained app (build_engine_app.py), grants the Agent
# Engine service agent Firestore read access, deploys, and saves the
# resource name to deploy/.engine_resource for the frontend/smoke test.
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
REGION="${REGION:-us-central1}"
DISPLAY_NAME="fe-race-engineer"

echo "== Staging the self-contained engine app =="
python3 deploy/build_engine_app.py

echo "== Deploying to Agent Engine on Agent Platform =="
echo "   The create step is a blocking operation with NO progress output —"
echo "   typically 5-10 minutes while the runtime builds your requirements."
echo "   To watch build logs from a second terminal:"
echo "     gcloud logging read 'resource.type=\"aiplatform.googleapis.com/ReasoningEngine\"' \\"
echo "         --freshness=15m --order=asc --format='value(textPayload)' --project=$PROJECT_ID"
EXISTING_ID=""
if [[ -f deploy/.engine_resource ]]; then
    EXISTING_ID=$(sed 's|.*/reasoningEngines/||' deploy/.engine_resource)
    echo "Updating existing engine: ${EXISTING_ID}"
fi

adk deploy agent_engine \
    --project="$PROJECT_ID" \
    --region="$REGION" \
    --display_name="$DISPLAY_NAME" \
    ${EXISTING_ID:+--agent_engine_id="$EXISTING_ID"} \
    build/engine_app | tee /tmp/engine_deploy.log

RESOURCE=$(grep -oE 'projects/[^ ]+/reasoningEngines/[0-9]+' /tmp/engine_deploy.log | tail -1 || true)
if [[ -n "$RESOURCE" ]]; then
    echo "$RESOURCE" > deploy/.engine_resource
    echo "== Saved resource name to deploy/.engine_resource =="
    echo "$RESOURCE"

    echo "== Granting the Agent Engine service agent Firestore access =="
    # The service agent is created by the first deploy, so granting AFTER
    # the deploy always works (and is idempotent on updates).
    PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')
    ENGINE_SA="service-${PROJECT_NUMBER}@gcp-sa-aiplatform-re.iam.gserviceaccount.com"
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:${ENGINE_SA}" \
        --role="roles/datastore.user" \
        --condition=None --quiet >/dev/null
    echo "Granted roles/datastore.user to ${ENGINE_SA}"
else
    echo "!! Could not parse the resource name from the deploy output."
    echo "   Copy the 'reasoningEngines' name from above into deploy/.engine_resource manually."
fi