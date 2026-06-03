"""
Formula E Race Engineer — BigQuery Setup
=========================================
Loads cleaned Berlin 2024 R10 Parquet files from gs://class-demo into BigQuery
dataset fe_race10 (us-central1, matching bucket region).

Run as:
    python notebooks/bq_setup.py

Or open in Cloud Shell Editor / Colab — cells separated by # %%.
Idempotent: re-running replaces existing tables and views.
"""

# %%
# Cell 1 — Imports and config
import os
import subprocess
from google.cloud import bigquery, storage

# Project: prefer GOOGLE_CLOUD_PROJECT (Cloud Run convention),
# fall back to DEVSHELL_PROJECT_ID (Cloud Shell), then gcloud config.
PROJECT_ID = (
    os.environ.get("GOOGLE_CLOUD_PROJECT")
    or os.environ.get("DEVSHELL_PROJECT_ID")
    or subprocess.check_output(
        ["gcloud", "config", "get-value", "project"], text=True
    ).strip()
)

REGION  = "us-central1"           # must match bucket region
DATASET = "fe_race10"
BUCKET  = "class-demo"

print(f"Project:  {PROJECT_ID}")
print(f"Region:   {REGION}")
print(f"Dataset:  {DATASET}")
print(f"Bucket:   gs://{BUCKET}/formula-e/")

bq  = bigquery.Client(project=PROJECT_ID, location=REGION)
gcs = storage.Client(project=PROJECT_ID)

# %%
# Cell 2 — Verify bucket access
print("\nVerifying bucket access...")
bucket = gcs.bucket(BUCKET)
sample = next(bucket.list_blobs(prefix="formula-e/berlin_2024/r10/", max_results=1))
print(f"  ✓ Can read gs://{BUCKET}/  (sample: {sample.name})")

# %%
# Cell 3 — Create dataset
print(f"\nEnsuring dataset {PROJECT_ID}.{DATASET} exists in {REGION}...")
ds = bigquery.Dataset(f"{PROJECT_ID}.{DATASET}")
ds.location = REGION
ds.description = "Formula E Berlin 2024 R10 — race engineer agent reference data"
bq.create_dataset(ds, exists_ok=True)
print(f"  ✓ Dataset ready: {PROJECT_ID}.{DATASET}")

# %%
# Cell 4 — Table inventory
# bq_table_name -> (gcs_path, expected_min_rows, description)
TABLES = {
    "drivers": (
        "formula-e/berlin_2024/r10/timing/drivers.parquet",
        22,
        "Entry list: car, driver, team, manufacturer",
    ),
    "startgrid": (
        "formula-e/berlin_2024/r10/timing/startgrid.parquet",
        22,
        "Starting grid positions",
    ),
    "laps": (
        "formula-e/berlin_2024/r10/timing/laps.parquet",
        800,
        "Per-lap timing with sectors and loops",
    ),
    "attack": (
        "formula-e/berlin_2024/r10/timing/attack.parquet",
        80,
        "Attack Mode activations + scenario armings (R10)",
    ),
    "energy_per_lap": (
        "formula-e/berlin_2024/r10/energy/energy_per_lap.parquet",
        800,
        "Per-lap energy consumption (% of budget)",
    ),
    "racecontrol_classified": (
        "formula-e/berlin_2024/r10/derived/racecontrol_classified.parquet",
        40,
        "Race control messages with derived category",
    ),
    "event_stream": (
        "formula-e/berlin_2024/r10/derived/event_stream.parquet",
        1500,
        "Unified events (laps, AM, RC, overtakes)",
    ),
    "career_driver": (
        "formula-e/cross_challenge/race_results/driver.parquet",
        80,
        "Career stats for all FE drivers",
    ),
    "career_race": (
        "formula-e/cross_challenge/race_results/race.parquet",
        2700,
        "10 seasons of FE race results",
    ),
}

print(f"\nWill load {len(TABLES)} tables:")
for name, (_, rows, desc) in TABLES.items():
    print(f"  {name:<25} ~{rows}+ rows  — {desc}")

# %%
# Cell 5 — Load function
def load_parquet(table_name: str, gcs_path: str) -> dict:
    table_id = f"{PROJECT_ID}.{DATASET}.{table_name}"
    uri = f"gs://{BUCKET}/{gcs_path}"
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        autodetect=True,
    )
    bq.load_table_from_uri(uri, table_id, job_config=job_config, location=REGION).result()
    t = bq.get_table(table_id)
    return {"table": table_name, "rows": t.num_rows, "size_mb": round(t.num_bytes / 1e6, 2)}

# %%
# Cell 6 — Run loads
print(f"\nLoading {len(TABLES)} tables...\n")
results = []
for name, (path, expected_min, _) in TABLES.items():
    print(f"  {name:<25} ", end="", flush=True)
    try:
        r = load_parquet(name, path)
        results.append({**r, "status": "ok"})
        flag = "✓" if r["rows"] >= expected_min else "⚠"
        print(f"{flag} {r['rows']:>6,} rows  ({r['size_mb']} MB)")
        if r["rows"] < expected_min:
            print(f"     WARN: expected ≥{expected_min}, got {r['rows']}")
    except Exception as e:
        results.append({"table": name, "status": "fail", "error": str(e)})
        print(f"✗ FAILED: {e}")

# %%
# Cell 7 — Convenience views
print("\nCreating convenience views...")
VIEWS = {
    "v_laps_with_driver": """
        SELECT l.car_number, d.driver_first_name, d.driver_last_name,
               d.driver_short_name, d.team, d.manufacturer,
               l.lap_num, l.time AS lap_time_ms, l.top_speed,
               l.position, l.is_valid
        FROM `{p}.{d}.laps` l
        LEFT JOIN `{p}.{d}.drivers` d USING (car_number)
    """,
    "v_am_with_driver": """
        SELECT a.car_number, d.driver_short_name, d.team,
               a.eth_arrival_time AS event_time, a.active, a.scenario
        FROM `{p}.{d}.attack` a
        LEFT JOIN `{p}.{d}.drivers` d USING (car_number)
    """,
    "v_overtakes": """
        SELECT e.t AS event_time, e.car_number, d.driver_short_name, d.team,
               e.attrs_json, e.human_summary
        FROM `{p}.{d}.event_stream` e
        LEFT JOIN `{p}.{d}.drivers` d USING (car_number)
        WHERE e.source = 'overtake'
    """,
}
for view_name, sql_t in VIEWS.items():
    sql = sql_t.format(p=PROJECT_ID, d=DATASET)
    try:
        bq.query(
            f"CREATE OR REPLACE VIEW `{PROJECT_ID}.{DATASET}.{view_name}` AS\n{sql}",
            location=REGION,
        ).result()
        print(f"  ✓ {view_name}")
    except Exception as e:
        print(f"  ✗ {view_name}: {e}")

# %%
# Cell 8 — Sanity samples
print("\nSanity checks:\n")
SAMPLES = [
    ("drivers",
     "SELECT car_number, driver_short_name, team, manufacturer "
     "FROM `{p}.{d}.drivers` ORDER BY car_number LIMIT 3"),
    ("attack (DAC car 13)",
     "SELECT car_number, active, scenario, eth_arrival_time "
     "FROM `{p}.{d}.attack` WHERE car_number = 13 ORDER BY eth_arrival_time LIMIT 5"),
    ("racecontrol_classified",
     "SELECT category, message_text FROM `{p}.{d}.racecontrol_classified` "
     "ORDER BY time LIMIT 3"),
    ("event_stream (first events)",
     "SELECT t, source, event_type, car_number, human_summary "
     "FROM `{p}.{d}.event_stream` ORDER BY t LIMIT 5"),
    ("v_overtakes",
     "SELECT event_time, driver_short_name, human_summary "
     "FROM `{p}.{d}.v_overtakes` LIMIT 3"),
    ("career_driver (DAC + CAS + EVA)",
     "SELECT shortcode, drivername, wins, podiums, points "
     "FROM `{p}.{d}.career_driver` "
     "WHERE shortcode IN ('DAC','CAS','EVA') ORDER BY shortcode"),
]
for label, sql_t in SAMPLES:
    print(f"  -- {label}")
    sql = sql_t.format(p=PROJECT_ID, d=DATASET)
    try:
        for row in bq.query(sql, location=REGION).result():
            print(f"     {dict(row.items())}")
    except Exception as e:
        print(f"     ERROR: {e}")
    print()

# %%
# Cell 9 — Summary
ok_count = sum(1 for r in results if r.get("status") == "ok")
fail_count = sum(1 for r in results if r.get("status") == "fail")
total_rows = sum(r.get("rows", 0) for r in results)
total_mb = sum(r.get("size_mb", 0) for r in results)

print("=" * 60)
print(f"  Setup complete: {PROJECT_ID}.{DATASET} ({REGION})")
print("=" * 60)
print(f"  Tables: {ok_count} loaded, {fail_count} failed")
print(f"  Total rows: {total_rows:,}")
print(f"  Total size: {total_mb:.2f} MB")
print()
print("  Next: chunk 3 — MCP Toolbox setup")
print("=" * 60)