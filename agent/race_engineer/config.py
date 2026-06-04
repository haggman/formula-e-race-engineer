"""Agent configuration — constants used across the race_engineer package.

Single source of truth for driver identity and race scope. Change here to
serve a different driver or different race.
"""

# Our driver — Car #13 António Félix da Costa, R10 winner
OUR_CAR_NUMBER = 13
OUR_DRIVER_FIRST_NAME = "Antonio"  # for second-person address in radio calls
OUR_DRIVER_SHORT_NAME = "DAC"

# Race scope
RACE_ID = "berlin_2024_r10"

# Attack Mode constants (R10 — see build doc working assumptions)
AM_TOTAL_BUDGET_S = 240
AM_SCENARIOS = {
    1: "short-first (60s + 180s)",
    2: "even (120s + 120s)",
    3: "long-first (180s + 60s)",
}

# ----------------------------------------------------------------------------
# Time bridging: race time ↔ the 2024 race's wall clock
# ----------------------------------------------------------------------------
# BigQuery time columns are INT64 nanoseconds since epoch in the ORIGINAL
# race's wall clock (May 12, 2024) — not the replay's. To query "history up
# to now", convert current race_time_s into that 2024 clock. Never use the
# replay machine's clock for this.
#
# Green flag: 2024-05-12T13:04:05.726Z (RACE_START_UTC in the simulator's
# build_frames.ipynb, Cell 5). Exact integer — no float arithmetic.
RACE_START_EPOCH_NS = 1_715_519_045_726_000_000


def race_time_to_wall_ns(race_time_s: int) -> int:
    """Convert race-relative seconds to the 2024 race's wall-clock ns.

    Use the result as `through_time_ns` in the MCP Toolbox BigQuery tools.
    """
    return RACE_START_EPOCH_NS + race_time_s * 1_000_000_000