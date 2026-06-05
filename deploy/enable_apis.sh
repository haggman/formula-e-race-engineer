#!/usr/bin/env bash
# Enable every API the race engineer stack needs. Idempotent — run any time.
# This is lab step zero: everything else assumes these are on.
set -euo pipefail

PROJECT_ID="${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}"
echo "Enabling APIs on project: ${PROJECT_ID}"

gcloud services enable \
    run.googleapis.com \
    pubsub.googleapis.com \
    firestore.googleapis.com \
    bigquery.googleapis.com \
    aiplatform.googleapis.com \
    texttospeech.googleapis.com \
    speech.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    --project "${PROJECT_ID}"

echo "Done. Current AI/speech/data services:"
gcloud services list --enabled --project "${PROJECT_ID}" \
    --filter="config.name:(aiplatform OR texttospeech OR speech OR bigquery OR firestore OR pubsub OR run)" \
    --format="value(config.name)"
