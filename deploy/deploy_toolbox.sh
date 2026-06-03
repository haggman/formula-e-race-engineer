#!/usr/bin/env bash
# Deploy MCP Toolbox to Cloud Run.
# Idempotent. Open auth for chunk 4 — locked down in chunk 13.

set -euo pipefail

if [[ -z "${REGION:-}" ]]; then
    echo "ERROR: REGION env var required. Run: source activate/activate.sh" >&2
    exit 1
fi
SA_NAME="${SA_NAME:-fe-toolbox-sa}"
TOOLBOX_IMAGE="${TOOLBOX_IMAGE:-us-central1-docker.pkg.dev/database-toolbox/toolbox/toolbox:1.3.0}"

PROJECT_ID="$(gcloud config get-value project 2>/dev/null)"
if [[ -z "$PROJECT_ID" ]]; then
    echo "ERROR: no project set." >&2
    exit 1
fi

SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
STAGING_BUCKET="${STAGING_BUCKET:-${PROJECT_ID}-fe-toolbox}"

echo "=================================================================="
echo "Project: $PROJECT_ID"
echo "Region:  $REGION"
echo "Service: $SERVICE_NAME"
echo "SA:      $SA_EMAIL"
echo "Image:   $TOOLBOX_IMAGE"
echo "=================================================================="

echo ">>> Enabling APIs..."
gcloud services enable \
    run.googleapis.com \
    bigquery.googleapis.com \
    --project="$PROJECT_ID"

echo ">>> Ensuring service account exists..."
if ! gcloud iam service-accounts describe "$SA_EMAIL" --project="$PROJECT_ID" >/dev/null 2>&1; then
    gcloud iam service-accounts create "$SA_NAME" \
        --display-name="Formula E MCP Toolbox" \
        --project="$PROJECT_ID"
    echo "    created SA $SA_EMAIL"
else
    echo "    SA $SA_EMAIL exists"
fi

echo ">>> Granting BigQuery roles..."
for role in roles/bigquery.dataViewer roles/bigquery.jobUser; do
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:${SA_EMAIL}" \
        --role="$role" \
        --condition=None \
        --quiet >/dev/null
    echo "    granted $role"
done

TOOLS_YAML_PATH="$(cd "$(dirname "$0")/.." && pwd)/toolbox/tools.yaml"
if [[ ! -f "$TOOLS_YAML_PATH" ]]; then
    echo "ERROR: tools.yaml not found at $TOOLS_YAML_PATH" >&2
    exit 1
fi

echo ">>> Ensuring staging bucket gs://${STAGING_BUCKET}..."
if ! gcloud storage buckets describe "gs://${STAGING_BUCKET}" --project="$PROJECT_ID" >/dev/null 2>&1; then
    gcloud storage buckets create "gs://${STAGING_BUCKET}" \
        --project="$PROJECT_ID" \
        --location="$REGION" \
        --uniform-bucket-level-access
    echo "    created"
else
    echo "    exists"
fi

gcloud storage buckets add-iam-policy-binding "gs://${STAGING_BUCKET}" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/storage.objectViewer" >/dev/null

gcloud storage cp "$TOOLS_YAML_PATH" "gs://${STAGING_BUCKET}/tools.yaml" --quiet
echo "    uploaded tools.yaml"

echo ">>> Deploying Cloud Run service..."
gcloud run deploy "$SERVICE_NAME" \
    --image="$TOOLBOX_IMAGE" \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --service-account="$SA_EMAIL" \
    --allow-unauthenticated \
    --port=5000 \
    --cpu=1 \
    --memory=512Mi \
    --cpu-boost \
    --min-instances=1 \
    --max-instances=3 \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" \
    --args="--config=/tools/tools.yaml,--address=0.0.0.0,--port=5000" \
    --add-volume="name=tools-vol,type=cloud-storage,bucket=${STAGING_BUCKET}" \
    --add-volume-mount="volume=tools-vol,mount-path=/tools"

URL=$(gcloud run services describe "$SERVICE_NAME" --region="$REGION" --format='value(status.url)')

echo ""
echo "=================================================================="
echo "Deployed!"
echo "URL: $URL"
echo "=================================================================="
echo ""
echo "Export for the next chunks:"
echo "  export TOOLBOX_URL=${URL}"
echo ""
echo "Note: min-instances=1 keeps one container warm always."
echo "      Costs ~\$5-10/month. Run 'gcloud run services delete fe-toolbox --region us-central1' when done."