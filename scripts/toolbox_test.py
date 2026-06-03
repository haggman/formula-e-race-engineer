"""Validate every Toolbox tool against the deployed local Toolbox server.

Run after starting the toolbox server in another tab:
    cd toolbox && ./toolbox --tools-file tools.yaml --port 5000

Then:
    python scripts/toolbox_test.py
"""
import json
import sys
import requests

BASE = "http://localhost:5000/api/tool"

# All tools called by name with realistic args for Berlin 2024 R10.
# Wall-clock time anchors used below:
#   pre-race      ~1_715_516_000_000_000_000 ns  (R10 start window)
#   race start    ~1_715_517_840_000_000_000 ns  (rough green flag)
#   mid race      ~1_715_519_000_000_000_000 ns
#   post race     ~1_715_521_000_000_000_000 ns

POST_RACE = 1_715_521_000_000_000_000

TESTS = [
    ("get_driver_info",
     {"car_number": 13}),

    ("get_lap_history",
     {"car_number": 13, "lap_start": 1, "lap_end": 10}),

     ("get_top_speed_history",
     {"car_number": 13, "lap_start": 1, "lap_end": 10}),

    ("get_energy_curve",
     {"car_number": 13, "through_lap": 10}),

    ("get_recent_race_control",
     {"through_time_ns": POST_RACE, "limit_n": 5}),

    ("get_am_activations",
     {"through_time_ns": POST_RACE}),

    ("get_am_armings",
     {"car_number": 13, "through_time_ns": POST_RACE}),

    ("get_overtakes_involving",
     {"car_number": 13, "car_pattern": "%#13%", "through_time_ns": POST_RACE}),

    ("get_driver_career_stats",
     {"driver_code": "DAC"}),

    ("get_field_position_at_lap",
     {"lap_number": 5}),

    ("execute_sql_bq",
     {"sql": "SELECT COUNT(*) AS n FROM `fe_race10.event_stream`"}),
]


def short(obj, limit=400):
    s = json.dumps(obj, default=str, indent=2)
    return s if len(s) <= limit else s[:limit] + f"\n... ({len(s)} chars total)"


def main():
    fails = 0
    for name, args in TESTS:
        print(f"\n── {name} ──")
        print(f"args: {args}")
        try:
            r = requests.post(f"{BASE}/{name}/invoke", json=args, timeout=30)
            if r.status_code >= 400:
                print(f"  ✗ HTTP {r.status_code}")
                print(f"    body: {r.text[:500]}")
                fails += 1
                continue
            body = r.json()
        except Exception as e:
            print(f"  ✗ HTTP error: {e}")
            fails += 1
            continue
        # Toolbox returns {"result": "<json-encoded string>"} or similar
        result = body.get("result", body)
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except json.JSONDecodeError:
                pass
        # Surface row count if list, else just show
        if isinstance(result, list):
            print(f"  ✓ {len(result)} row(s)")
            for row in result[:3]:
                print(f"    {row}")
            if len(result) > 3:
                print(f"    ... +{len(result) - 3} more")
        else:
            print(f"  ✓ result: {short(result)}")

    print("\n" + "=" * 50)
    if fails:
        print(f"  ✗ {fails} tool(s) failed")
        sys.exit(1)
    else:
        print(f"  ✓ All {len(TESTS)} tools passed")


if __name__ == "__main__":
    main()