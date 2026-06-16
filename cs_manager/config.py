"""
CS Manager - Global Configuration
All constants, tuning values and world parameters.
"""

GAME_TITLE = "CS Manager - Living Esports World Simulation"
VERSION = "1.0.0"

# ─── Calendar ───────────────────────────────────────────────────────────────
MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]
WEEKS_PER_MONTH = 4
START_YEAR = 2025
START_MONTH = 1   # January

# Season phases
SEASON_PHASES = {
    "winter":  {"months": [1, 2, 3],        "label": "Winter League"},
    "spring":  {"months": [4, 5, 6],        "label": "Spring League"},
    "summer":  {"months": [8, 9, 10],       "label": "Summer League"},
    "ti_qual": {"months": [11],             "label": "TI Qualification"},
    "ti":      {"months": [12],             "label": "The International"},
    "break":   {"months": [7],              "label": "July Break"},
}

# ─── Regions ────────────────────────────────────────────────────────────────
REGIONS = ["europe", "asia", "latin_america", "africa_oceania"]
REGION_LABELS = {
    "europe":         "Europe",
    "asia":           "Asia",
    "latin_america":  "Latin America",
    "africa_oceania": "Africa/Oceania",
}

ORGS_PER_REGION = 50   # target
LEAGUE_SIZE     = 16   # teams per regional league
RELEGATION_SPOTS = 3
PROMOTION_SPOTS  = 3

# ─── Major / TI ─────────────────────────────────────────────────────────────
MAJOR_SLOTS_BY_REGION = {
    "europe":         6,
    "asia":           4,
    "latin_america":  3,
    "africa_oceania": 3,
}
MAJOR_TOTAL_TEAMS = 16
TI_TOTAL_TEAMS    = 20
TI_QUALIFIER_SLOTS = 4   # one per region
MAJOR_PRIZE_POOL  = 500_000      # USD
TI_PRIZE_POOL     = 1_500_000    # at least 2.5× major

# Major schedule: after which season
MAJORS = [
    {"name": "Major 1", "after_phase": "winter", "month": 4, "week": 1},
    {"name": "Major 2", "after_phase": "spring", "month": 7, "week": 2},
    {"name": "Major 3", "after_phase": "summer", "month": 11, "week": 1},
]

# ─── Player Roles ────────────────────────────────────────────────────────────
ROLES = ["IGL", "AWPer", "Entry Fragger", "Lurker", "Support"]
ROLE_WEIGHTS = [1, 1, 2, 1, 2]  # relative frequency

# ─── Player Age Bands ────────────────────────────────────────────────────────
AGE_ACADEMY_MIN  = 14
AGE_ACADEMY_MAX  = 19
AGE_PRO_MIN      = 18
AGE_RETIRE_START = 30
AGE_RETIRE_HARD  = 36

# Development speed by age
def dev_speed(age):
    if age < 18:  return 3.5
    if age < 22:  return 2.5
    if age < 26:  return 1.2
    if age < 30:  return 0.3
    return -0.8   # decline

# ─── Attribute Ranges ────────────────────────────────────────────────────────
ATTRIBUTE_NAMES = ["aim", "game_sense", "positioning", "clutch", "leadership"]
HIDDEN_NAMES    = ["aggression", "discipline", "adaptability", "consistency"]
MENTAL_NAMES    = ["confidence", "motivation", "tilt_resistance"]

# ─── Organization Eras ───────────────────────────────────────────────────────
ORG_ERAS = [
    "emerging", "regional_contender", "international_challenger",
    "golden_era", "established_elite", "declining_power", "rebuilding",
]

# ─── Team Identity ───────────────────────────────────────────────────────────
TEAM_IDENTITIES = ["Aggressive", "Tactical", "Balanced", "Disciplined", "Chaos"]

# ─── Sponsor Types ───────────────────────────────────────────────────────────
SPONSOR_TYPES = {
    "conservative":  {"income_base": 50_000,  "expectations": "low"},
    "ambitious":     {"income_base": 150_000, "expectations": "medium"},
    "premium":       {"income_base": 400_000, "expectations": "high"},
    "developmental": {"income_base": 30_000,  "expectations": "minimal"},
}

# ─── Economy ─────────────────────────────────────────────────────────────────
SALARY_TIERS = {          # monthly salary in USD
    "star":    15_000,
    "regular": 5_000,
    "prospect":2_000,
    "academy": 500,
}
BUDGET_TIERS = {
    "elite":    3_000_000,
    "mid":      800_000,
    "small":    200_000,
    "micro":    50_000,
}

# ─── Ranking System ──────────────────────────────────────────────────────────
RANKING_DECAY_MONTHS = 3       # full weight window
RANKING_HALF_LIFE    = 6       # months before points halve
TOP_RANKING_SIZE     = 50

# Tournament point values
TOURNAMENT_POINTS = {
    "ti":          {"win": 5000, "final": 3000, "semi": 1500, "quarter": 700, "group": 200},
    "major":       {"win": 2000, "final": 1200, "semi":  600, "quarter": 300, "group":  80},
    "tier2":       {"win":  300, "final":  150, "semi":   80, "quarter":  40, "group":  10},
    "tier3":       {"win":   50, "final":   25, "semi":   10, "quarter":   5, "group":   2},
    "regional":    {"win":  800, "final":  400, "semi":  200, "quarter": 100, "group":  30},
}

# ─── Match Engine ────────────────────────────────────────────────────────────
ROUNDS_PER_HALF    = 12
MAX_ROUNDS         = 30   # OT possible
MATCH_FORMATS      = {
    "bo1": 1,
    "bo3": 3,
    "bo5": 5,
}

# ─── News ────────────────────────────────────────────────────────────────────
NEWS_MAX_ITEMS = 50   # keep last N news items

# ─── UI ──────────────────────────────────────────────────────────────────────
TERMINAL_WIDTH = 80
SEPARATOR      = "─" * TERMINAL_WIDTH
THICK_SEP      = "═" * TERMINAL_WIDTH

# Colors (ANSI) — gracefully degrade if unsupported
ANSI = {
    "reset":  "\033[0m",
    "bold":   "\033[1m",
    "dim":    "\033[2m",
    "red":    "\033[91m",
    "green":  "\033[92m",
    "yellow": "\033[93m",
    "blue":   "\033[94m",
    "magenta":"\033[95m",
    "cyan":   "\033[96m",
    "white":  "\033[97m",
}

# ─── Save paths ──────────────────────────────────────────────────────────────
import os
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DATA_DIR  = os.path.join(BASE_DIR, "data")
SAVE_FILE = os.path.join(DATA_DIR, "gamestate.json")
