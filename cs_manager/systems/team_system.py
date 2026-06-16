"""
Organization generation, roster management, era tracking.
"""
import random
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (ORG_ERAS, TEAM_IDENTITIES, BUDGET_TIERS, REGIONS,
                    SPONSOR_TYPES, SALARY_TIERS, LEAGUE_SIZE)
from utils.random_utils import generate_id, roll, weighted_randint

_oid_counter = [0]

# ─── Org name building blocks ─────────────────────────────────────────────
_PREFIXES = [
    "Team","Club","Org","Squad","Force","Legion","Alliance","Union","Core",
    "Nexus","Apex","Vortex","Storm","Blaze","Shadow","Phantom","Infinity",
    "Nova","Pulse","Edge","Peak","Prime","Elite","Origin","Ember","Titan",
]
_WORDS = [
    "Aurora","Eclipse","Horizon","Zenith","Cipher","Phantom","Rogue","Viper",
    "Cobra","Lynx","Hydra","Tempest","Surge","Radiant","Spectral","Crimson",
    "Azure","Obsidian","Ivory","Midnight","Dawn","Dusk","Flare","Glacier",
    "Thunder","Quake","Forge","Aegis","Bastion","Citadel","Sentinel","Rampart",
    "Vandal","Havoc","Chaos","Fury","Wrath","Valor","Honor","Glory","Crest",
    "Overture","Pinnacle","Summit","Apex","Vertex","Zenith","Nadir","Quasar",
]
_USED_ORG_NAMES: set = set()


def _random_org_name() -> tuple[str, str]:
    for _ in range(50):
        if roll(0.6):
            name = f"{random.choice(_PREFIXES)} {random.choice(_WORDS)}"
        else:
            name = random.choice(_WORDS)
        tag  = _make_tag(name)
        if name not in _USED_ORG_NAMES:
            _USED_ORG_NAMES.add(name)
            return name, tag
    # Fallback: append number
    base = random.choice(_WORDS)
    name = f"{base}{random.randint(1,999)}"
    return name, _make_tag(name)


def _make_tag(name: str) -> str:
    parts = name.upper().split()
    if len(parts) >= 2:
        return (parts[0][:2] + parts[1][:2])[:4]
    return name.upper()[:4]


def create_org(region: str, tier: str = "mid",
               founding_year: int | None = None) -> dict:
    oid  = generate_id("org", _oid_counter)
    name, tag = _random_org_name()
    if founding_year is None:
        founding_year = random.randint(2010, 2024)

    budget_map = {"elite": "elite", "top": "mid", "mid": "mid",
                  "lower": "small", "bottom": "micro"}
    budget_key = budget_map.get(tier, "small")
    budget = int(random.gauss(BUDGET_TIERS[budget_key],
                              BUDGET_TIERS[budget_key] * 0.2))

    rep = {"elite": 85, "top": 70, "mid": 50, "lower": 35, "bottom": 20}.get(tier, 50)
    rep = weighted_randint(rep - 15, rep + 15, rep, 8)

    sponsor = _gen_sponsor(tier)

    return {
        "id":               oid,
        "name":             name,
        "tag":              tag,
        "region":           region,
        "founding_year":    founding_year,
        "budget":           budget,
        "reputation":       rep,
        "global_prestige":  max(0, rep - random.randint(5, 20)),
        "regional_prestige":min(100, rep + random.randint(0, 10)),
        "era":              _initial_era(rep),
        "identity":         random.choice(TEAM_IDENTITIES),
        "roster":           [],    # player IDs
        "bench":            [],
        "academy":          [],
        "coach_id":         None,
        "sponsors":         [sponsor],
        "sponsor_income":   sponsor["income"],
        "trophies":         [],
        "history":          [],    # [{year, era, notable}]
        "in_league":        False,
        "league_division":  None,
        "ranking_points":   random.randint(0, int(rep * 30)),
        "form":             [random.choice(["W", "L"]) for _ in range(5)],
        "wins":             0,
        "losses":           0,
        "season_wins":      0,
        "season_losses":    0,
        "match_history":    [],    # [{"year","month","opp","result","score"}]
    }


def _initial_era(rep: int) -> str:
    if rep >= 85: return "established_elite"
    if rep >= 70: return "international_challenger"
    if rep >= 55: return "regional_contender"
    if rep >= 40: return "emerging"
    return "rebuilding"


def _gen_sponsor(tier: str) -> dict:
    type_map = {"elite": "premium", "top": "ambitious",
                "mid": "ambitious", "lower": "conservative",
                "bottom": "developmental"}
    stype = type_map.get(tier, "conservative")
    income = int(random.gauss(SPONSOR_TYPES[stype]["income_base"],
                               SPONSOR_TYPES[stype]["income_base"] * 0.2))
    return {
        "name":         f"{random.choice(_WORDS)} Sponsor",
        "type":         stype,
        "income":       max(0, income),
        "expectations": SPONSOR_TYPES[stype]["expectations"],
        "expiry_year":  2025 + random.randint(1, 3),
    }


def update_era(org: dict) -> None:
    """Re-evaluate era based on reputation and recent results."""
    rep = org["reputation"]
    wins = org.get("wins", 0)
    losses = org.get("losses", 0)
    trophy_cnt = len(org["trophies"])

    if rep >= 85 and trophy_cnt >= 3:
        org["era"] = "golden_era"
    elif rep >= 75:
        org["era"] = "established_elite"
    elif rep >= 60:
        org["era"] = "international_challenger"
    elif rep >= 45:
        org["era"] = "regional_contender"
    elif rep >= 30:
        org["era"] = "emerging"
    elif wins < losses * 0.5:
        org["era"] = "declining_power"
    else:
        org["era"] = "rebuilding"


def update_reputation(org: dict, result: str, tournament_tier: str) -> None:
    """Adjust org reputation after a match result."""
    delta_map = {
        ("W", "ti"):      +4, ("L", "ti"):      -2,
        ("W", "major"):   +3, ("L", "major"):   -1,
        ("W", "regional"):+2, ("L", "regional"):-1,
        ("W", "tier2"):   +1, ("L", "tier2"):    0,
        ("W", "tier3"):   +0, ("L", "tier3"):    0,
    }
    delta = delta_map.get((result, tournament_tier), 0)
    org["reputation"] = max(0, min(100, org["reputation"] + delta))


def record_result(org: dict, result: str, opponent_name: str,
                  score: str, year: int, month: int) -> None:
    org["form"] = ([result] + org.get("form", []))[:5]
    if result == "W":
        org["wins"] += 1
        org["season_wins"] += 1
    else:
        org["losses"] += 1
        org["season_losses"] += 1
    org["match_history"] = ([{
        "year": year, "month": month, "opponent": opponent_name,
        "result": result, "score": score
    }] + org.get("match_history", []))[:50]


def reset_season(org: dict) -> None:
    org["season_wins"]   = 0
    org["season_losses"] = 0


def get_squad(org: dict, players: dict) -> list:
    """Return list of player dicts for this org's main roster."""
    return [players[pid] for pid in org["roster"] if pid in players]


def get_academy(org: dict, players: dict) -> list:
    return [players[pid] for pid in org["academy"] if pid in players]


def team_overall(org: dict, players: dict) -> float:
    from utils.stats_utils import overall_rating
    squad = get_squad(org, players)
    if not squad:
        return 40.0
    return sum(overall_rating(p["attributes"]) for p in squad) / len(squad)
