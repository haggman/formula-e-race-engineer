#!/usr/bin/env bash
# Deploy the State Writer service to Cloud Run + wire Pub/Sub push subscription.
#
# Idempotent: re-running updates the service and re-binds the subscription.
#
# Required env vars (set by sourcing ./activate):
#   PROJECT_ID, REGION

set -euo pipefail

SERVICE_NAME="${SERVICE_NAME:-fe-state-writer}"
TOPIC_NAME="${TOPIC_NAME:-fe-telemetry}"
SUBSCRIPTION_NAME="${SUBSCRIPTION_NAME:-fe-state-writer-sub}"
SA_NAME="${SA_NAME:-fe-state-writer-sa}"

if [[ -z "${PROJECT_ID:-}" ]]; then
    echo "ERROR: PROJECT_ID env var required. Run: source ./activate" >&2
    exit 1
fi
if [[ -z "${REGION:-}" ]]; then
    echo "ERROR: REGION env var required. Run: source ./activate" >&2
    exit 1
fi

SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "=================================================================="
echo "Project: $PROJECT_ID"
echo "Region:  $REGION"
echo "Service: $SERVICE_NAME"
echo "Topic:   $TOPIC_NAME"
echo "Sub:     $SUBSCRIPTION_NAME"
echo "SA:      $SA_EMAIL"
echo "=================================================================="

# --- Enable APIs ---
echo ">>> Enabling APIs..."
gcloud services enable \
    run.googleapis.com \
    pubsub.googleapis.com \
    firestore.googleapis.com \
    cloudbuild.googleapis.com \
    --project="$PROJECT_ID"

# --- Service account ---
echo ">>> Ensuring service account exists..."
if ! gcloud iam service-accounts describe "$SA_EMAIL" --project="$PROJECT_ID" >/dev/null 2>&1; then
    gcloud iam service-accounts create "$SA_NAME" \
        --display-name="Formula E State Writer" \
        --project="$PROJECT_ID"
    echo "    created SA $SA_EMAIL"
else
    echo "    SA $SA_EMAIL exists"
fi

# --- IAM grants ---
# Firestore writes
echo ">>> Granting roles..."
for role in roles/datastore.user; do
    gcloud projects add-iam-policy-binding "$PROJECT_ID" \
        --member="serviceAccount:${SA_EMAIL}" \
        --role="$role" \
        --condition=None \
        --quiet >/dev/null
    echo "    granted $role"
done

# --- Topic must exist (the simulator creates it; this is just a safety net) ---
echo ">>> Ensuring Pub/Sub topic exists..."
if ! gcloud pubsub topics describe "$TOPIC_NAME" --project="$PROJECT_ID" >/dev/null 2>&1; then
    gcloud pubsub topics create "$TOPIC_NAME" --project="$PROJECT_ID"
    echo "    created topic $TOPIC_NAME (simulator will use this)"
else
    echo "    topic $TOPIC_NAME exists"
fi

# --- Deploy Cloud Run service ---
# We need to deploy from the repo root because the Dockerfile references
# both state_writer/ and shared/.
echo ">>> Deploying Cloud Run service from $REPO_ROOT..."
gcloud run deploy "$SERVICE_NAME" \
    --source="$REPO_ROOT" \
    --dockerfile="state_writer/Dockerfile" \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --service-account="$SA_EMAIL" \
    --no-allow-unauthenticated \
    --cpu=1 \
    --memory=512Mi \
    --cpu-boost \
    --min-instances=0 \
    --max-instances=3 \
    --concurrency=10 \
    --timeout=60 \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID},RACE_ID=berlin_2024_r10"

URL=$(gcloud run services describe "$SERVICE_NAME" --region="$REGION" --format='value(status.url)')

# --- Create Pub/Sub service account that can invoke this Cloud Run service ---
# Pub/Sub push needs to authenticate to private Cloud Run.
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
PUBSUB_SA="service-${PROJECT_NUMBER}@gcp-sa-pubsub.iam.gserviceaccount.com"

echo ">>> Granting Pub/Sub SA invoker on Cloud Run service..."
gcloud run services add-iam-policy-binding "$SERVICE_NAME" \
    --member="serviceAccount:${PUBSUB_SA}" \
    --role="roles/run.invoker" \
    --region="$REGION" \
    --project="$PROJECT_ID" \
    --quiet >/dev/null

# We also need a service account that Pub/Sub uses to call our service.
# Reusing the SA we already have is the simplest approach.
gcloud iam service-accounts add-iam-policy-binding "$SA_EMAIL" \
    --member="serviceAccount:${PUBSUB_SA}" \
    --role="roles/iam.serviceAccountTokenCreator" \
    --project="$PROJECT_ID" \
    --quiet >/dev/null

# --- Create or update the push subscription ---
echo ">>> Configuring Pub/Sub push subscription..."
if gcloud pubsub subscriptions describe "$SUBSCRIPTION_NAME" --project="$PROJECT_ID" >/dev/null 2>&1; then
    gcloud pubsub subscriptions update "$SUBSCRIPTION_NAME" \
        --push-endpoint="$URL/" \
        --push-auth-service-account="$SA_EMAIL" \
        --project="$PROJECT_ID"
    echo "    updated subscription $SUBSCRIPTION_NAME"
else
    gcloud pubsub subscriptions create "$SUBSCRIPTION_NAME" \
        --topic="$TOPIC_NAME" \
        --push-endpoint="$URL/" \
        --push-auth-service-account="$SA_EMAIL" \
        --ack-deadline=60 \
        --message-retention-duration=10m \
        --project="$PROJECT_ID"
    echo "    created subscription $SUBSCRIPTION_NAME"
fi

echo ""
echo "=================================================================="
echo "Deployed!"
echo "URL: $URL"
echo ""
echo "Health check:  curl -H \"Authorization: Bearer \$(gcloud auth print-identity-token)\" $URL/health"
echo "Status:        curl -H \"Authorization: Bearer \$(gcloud auth print-identity-token)\" $URL/status"
echo "=================================================================="
echo ""
echo "Next step: deploy the simulator (companion repo) so it publishes to $TOPIC_NAME."
echo "Once the simulator is running, RaceState in Firestore will update at 1 Hz."
