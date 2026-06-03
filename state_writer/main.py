"""State Writer — receives frames from Pub/Sub push subscription and writes
RaceState (current frame) + Event docs to Firestore.

This is one of three services in the data plane:
  Simulator → Pub/Sub fe-telemetry → [State Writer] → Firestore ← Agent + Frontend

Pub/Sub push delivers each frame as a base64-encoded JSON payload. We decode,
validate against the shared Pydantic models, then:
  1. Overwrite race_states/{race_id} with the current RaceState
  2. Write each event in frame.events[] as a separate doc in race_events/
"""
from __future__ import annotations

import base64
import json
import logging
import os
import time
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from google.cloud import firestore

from shared.models import Event, EventType, RaceState

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("state_writer")

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("PROJECT_ID")
if not PROJECT_ID:
    raise RuntimeError("GOOGLE_CLOUD_PROJECT (or PROJECT_ID) env var required")

# Race ID is per-deployment; for Fork 2 it's always berlin_2024_r10 but we read
# it from env for portability.
RACE_ID = os.environ.get("RACE_ID", "berlin_2024_r10")

# Firestore client. Default database, same project.
db = firestore.Client(project=PROJECT_ID)

app = FastAPI(title="Formula E State Writer")


@app.get("/health")
def health():
    return {"ok": True, "service": "state_writer", "race_id": RACE_ID}


@app.get("/status")
def status():
    """Read the current RaceState doc back, if it exists."""
    doc = db.collection("race_states").document(RACE_ID).get()
    if not doc.exists:
        return {"race_id": RACE_ID, "exists": False}
    data = doc.to_dict()
    return {
        "race_id": RACE_ID,
        "exists": True,
        "race_time_s": data.get("race_time_s"),
        "race_phase": data.get("race_phase"),
        "current_leader_lap": data.get("current_leader_lap"),
        "ts_ns_wall": data.get("ts_ns_wall"),
        "updated_at_unix": data.get("updated_at_unix"),
    }


@app.post("/")
async def pubsub_push(request: Request):
    """Pub/Sub push delivery endpoint.

    Pub/Sub POSTs an envelope like:
      {
        "message": {
          "data": "<base64-encoded JSON frame>",
          "messageId": "...",
          "publishTime": "...",
          ...
        },
        "subscription": "projects/.../subscriptions/..."
      }
    """
    try:
        envelope = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(400, "invalid JSON envelope")

    if "message" not in envelope:
        raise HTTPException(400, "missing 'message' in envelope")

    msg = envelope["message"]
    data_b64 = msg.get("data")
    if not data_b64:
        # Empty messages are valid Pub/Sub keepalives — ack with 200.
        return {"ok": True, "note": "empty message"}

    try:
        frame_json = base64.b64decode(data_b64).decode("utf-8")
        frame_dict = json.loads(frame_json)
    except (ValueError, json.JSONDecodeError) as e:
        logger.exception("failed to decode message: %s", e)
        # 400 tells Pub/Sub to NOT retry (the message is malformed).
        raise HTTPException(400, f"decode error: {e}")

    try:
        write_frame(frame_dict)
    except Exception as e:
        logger.exception("failed to write frame: %s", e)
        # 500 tells Pub/Sub to retry — likely a transient Firestore issue.
        raise HTTPException(500, f"write error: {e}")

    return {"ok": True}


@app.post("/ingest")
async def manual_ingest(request: Request):
    """Manual ingest endpoint for testing — bypasses Pub/Sub envelope.

    Body is a raw frame JSON. Used by scripts/seed_test_state.py.
    """
    try:
        frame_dict = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(400, "invalid JSON")
    try:
        write_frame(frame_dict)
    except Exception as e:
        logger.exception("failed to write frame: %s", e)
        raise HTTPException(500, f"write error: {e}")
    return {"ok": True, "race_time_s": frame_dict.get("race_time_s")}


def write_frame(frame_dict: dict[str, Any]) -> None:
    """Parse a frame dict, validate via Pydantic, write RaceState + Events.

    Idempotent on RaceState (overwrite). Events are appended; duplicates would
    appear if the same frame is delivered twice. For Fork 2 we accept that —
    Pub/Sub at-least-once delivery means rare duplicates but the agent doesn't
    care for laps-1-10 demo purposes.
    """
    # Stamp wall-clock ns onto the frame before validating
    if "ts_ns_wall" not in frame_dict:
        frame_dict["ts_ns_wall"] = time.time_ns()

    state = RaceState.model_validate(frame_dict)
    race_id = state.race_id
    race_time_s = state.race_time_s
    ts_ns_wall = state.ts_ns_wall or time.time_ns()

    # ------------------------------------------------------------------
    # 1) Overwrite the current RaceState doc
    # ------------------------------------------------------------------
    state_doc = state.model_dump(mode="json")
    state_doc["updated_at_unix"] = int(time.time())  # for monitoring
    db.collection("race_states").document(race_id).set(state_doc)

    # ------------------------------------------------------------------
    # 2) Write any events in this tick to race_events/
    # ------------------------------------------------------------------
    raw_events = frame_dict.get("events") or []
    if not raw_events:
        logger.info("frame t=%d phase=%s no events", race_time_s, state.race_phase.value)
        return

    batch = db.batch()
    written = 0
    for raw in raw_events:
        try:
            event = build_event(raw, ts_ns_wall, race_time_s, race_id)
        except (ValueError, KeyError) as e:
            logger.warning("skipping malformed event at t=%d: %s (%s)",
                           race_time_s, raw, e)
            continue
        doc_ref = db.collection("race_events").document()
        batch.set(doc_ref, event.model_dump(mode="json"))
        written += 1

    if written:
        batch.commit()
        logger.info("frame t=%d wrote %d events", race_time_s, written)


def build_event(
    raw: dict[str, Any], ts_ns_wall: int, race_time_s: int, race_id: str
) -> Event:
    """Convert a raw frame event into our Event model.

    Frame events have a "type" field plus type-specific keys. We promote
    `car_number` to a top-level indexed field and stash the rest in `data`.
    """
    event_type_str = raw.get("type")
    if not event_type_str:
        raise ValueError("event missing 'type'")

    event_type = EventType(event_type_str)  # validates against enum

    # car_number may be absent for some race_control events; preserve as None
    car_number = raw.get("car_number")

    # Everything except the well-known top-level fields goes in `data`
    data = {k: v for k, v in raw.items() if k not in ("type", "car_number")}

    return Event(
        event_type=event_type,
        ts_ns_wall=ts_ns_wall,
        race_time_s=race_time_s,
        race_id=race_id,
        car_number=car_number,
        data=data,
    )
