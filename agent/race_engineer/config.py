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
