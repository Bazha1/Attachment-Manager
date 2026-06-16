"""
Player generation, development, retirement and career tracking.
"""
import random
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (ROLES, ROLE_WEIGHTS, ATTRIBUTE_NAMES, HIDDEN_NAMES,
                    MENTAL_NAMES, AGE_ACADEMY_MIN, AGE_ACADEMY_MAX,
                    AGE_PRO_MIN, AGE_RETIRE_START, AGE_RETIRE_HARD,
                    dev_speed, REGIONS, SALARY_TIERS)
from utils.random_utils import (random_nickname, random_name, random_nationality,
                                 random_age, weighted_randint, generate_id, roll)
from utils.stats_utils import overall_rating, market_value

_pid_counter = [0]


def _gen_attrs(quality: int, role: str) -> dict:
    """Generate core attributes biased toward role."""
    base = {
        "aim":         weighted_randint(20, 99, quality, 15),
        "game_sense":  weighted_randint(20, 99, quality, 15),
        "positioning": weighted_randint(20, 99, quality, 15),
        "clutch":      weighted_randint(20, 99, quality, 15),
        "leadership":  weighted_randint(20, 99, quality, 15),
    }
    # Boost relevant attributes per role
    boost = {
        "IGL":           ["game_sense", "leadership"],
        "AWPer":         ["aim", "positioning"],
        "Entry Fragger": ["aim", "clutch"],
        "Lurker":        ["game_sense", "positioning"],
        "Support":       ["game_sense", "leadership"],
    }.get(role, [])
    for attr in boost:
        base[attr] = min(99, base[attr] + random.randint(5, 15))
    return base


def create_player(org_id: str | None, region: str, quality: int = 60,
                  is_academy: bool = False) -> dict:
    pid = generate_id("p", _pid_counter)
    role = random.choices(ROLES, weights=ROLE_WEIGHTS, k=1)[0]
    fn, ln = random_name(region)
    nick  = random_nickname(region)
    nat   = random_nationality(region)
    if is_academy:
        age = random.randint(AGE_ACADEMY_MIN, AGE_ACADEMY_MAX)
        quality = max(10, quality - 30)
    else:
        age = random_age(AGE_PRO_MIN, 32)

    attrs   = _gen_attrs(quality, role)
    ovr     = overall_rating(attrs)
    hltv    = round(random.gauss(0.8 + ovr / 200, 0.1), 2)
    mv      = market_value(ovr, age, hltv, role, 0)
    salary  = _salary_for_quality(quality)

    return {
        "id":         pid,
        "nickname":   nick,
        "first_name": fn,
        "last_name":  ln,
        "age":        age,
        "nationality":nat,
        "region":     region,
        "org_id":     org_id,
        "role":       role,
        "status":     "academy" if is_academy else "starter",
        "attributes": attrs,
        "hidden": {
            "aggression":   weighted_randint(20, 90, 55, 20),
            "discipline":   weighted_randint(20, 90, 55, 20),
            "adaptability": weighted_randint(20, 90, 55, 20),
            "consistency":  weighted_randint(20, 90, 55, 20),
        },
        "mental": {
            "confidence":    weighted_randint(40, 90, 65, 15),
            "motivation":    weighted_randint(40, 90, 70, 15),
            "tilt_resistance": weighted_randint(30, 90, 60, 15),
        },
        "stats": {
            "hltv_rating":        hltv,
            "performance_rating": round(random.gauss(5.0, 1.5), 1),
            "career_kills":       0,
            "career_deaths":      0,
            "career_matches":     0,
            "career_rounds":      0,
            "season_kills":       0,
            "season_deaths":      0,
            "season_matches":     0,
        },
        "contract": {
            "salary":       salary,
            "expiry_year":  0,   # set externally
            "expiry_month": 12,
        },
        "market_value":      mv,
        "peak_market_value": mv,
        "career_history":    [],   # [{year, org, role, hltv}]
        "achievements":      [],   # ["Major win 2025", ...]
        "playstyle": _random_playstyle(role),
        "is_academy": is_academy,
    }


def _salary_for_quality(q: int) -> int:
    if q >= 80: return SALARY_TIERS["star"]
    if q >= 60: return SALARY_TIERS["regular"]
    if q >= 40: return SALARY_TIERS["prospect"]
    return SALARY_TIERS["academy"]


def _random_playstyle(role: str) -> str:
    styles = {
        "IGL":           ["Excels in structured calls", "Struggles under unexpected aggression",
                          "Thrives when team morale is high"],
        "AWPer":         ["Dominant from distance", "Struggles in close-range", "Peeks under pressure"],
        "Entry Fragger": ["Explosive opening impact", "Inconsistent in slow rounds",
                          "Thrives in fast executes"],
        "Lurker":        ["Creates chaos from unexpected angles", "Struggles in passive setups",
                          "Reads opponent patterns well"],
        "Support":       ["Keeps team stable", "Rarely star performer", "Elevates teammates"],
    }
    return random.choice(styles.get(role, ["Balanced performer"]))


def develop_player(player: dict, months_passed: int = 1) -> None:
    """Age and develop a player's attributes in-place."""
    age = player["age"]
    speed = dev_speed(age) * months_passed / 12
    for attr in ATTRIBUTE_NAMES:
        delta = random.gauss(speed, abs(speed) * 0.5)
        player["attributes"][attr] = max(1, min(99,
            int(player["attributes"][attr] + delta)))
    # Mental fluctuation
    for m in MENTAL_NAMES:
        player["mental"][m] = max(1, min(99,
            int(player["mental"][m] + random.gauss(0, 2))))
    # Age player once per 12 months advance
    player["_age_acc"] = player.get("_age_acc", 0) + months_passed
    if player["_age_acc"] >= 12:
        player["age"] += 1
        player["_age_acc"] -= 12
    # Recalculate market value
    ovr = overall_rating(player["attributes"])
    player["market_value"] = market_value(
        ovr, player["age"], player["stats"]["hltv_rating"],
        player["role"], len(player["achievements"])
    )
    if player["market_value"] > player["peak_market_value"]:
        player["peak_market_value"] = player["market_value"]


def should_retire(player: dict) -> bool:
    age = player["age"]
    if age < AGE_RETIRE_START: return False
    if age >= AGE_RETIRE_HARD: return True
    prob = (age - AGE_RETIRE_START) / (AGE_RETIRE_HARD - AGE_RETIRE_START) * 0.25
    return roll(prob)


def free_agent_pool(players: list, org_id: str | None = None) -> list:
    return [p for p in players if p["org_id"] is None and not p.get("retired")]


def reset_season_stats(player: dict) -> None:
    player["stats"]["season_kills"]   = 0
    player["stats"]["season_deaths"]  = 0
    player["stats"]["season_matches"] = 0


def record_match_stats(player: dict, kills: int, deaths: int,
                       rounds: int, hltv: float, perf: float,
                       year: int = 0, month: int = 0,
                       opponent: str = "", won: bool = False) -> None:
    s = player["stats"]
    s["career_kills"]   += kills
    s["career_deaths"]  += deaths
    s["career_matches"] += 1
    s["career_rounds"]  += rounds
    s["season_kills"]   += kills
    s["season_deaths"]  += deaths
    s["season_matches"] += 1
    # Exponential moving average for ratings
    alpha = 0.15
    s["hltv_rating"] = round(s["hltv_rating"] * (1 - alpha) + hltv * alpha, 2)
    s["performance_rating"] = round(
        s["performance_rating"] * (1 - alpha) + perf * alpha, 1)
    # Match-by-match history
    s.setdefault("match_history", [])
    s["match_history"].append({
        "year":     year,
        "month":    month,
        "opponent": opponent,
        "won":      won,
        "kills":    kills,
        "deaths":   deaths,
        "hltv":     round(hltv, 2),
        "perf":     round(perf, 1),
    })
    # Keep last 50 matches
    s["match_history"] = s["match_history"][-50:]
    # Update career history
    if opponent:
        player.setdefault("career_history", [])
        player["career_history"].append({
            "year":     year,
            "month":    month,
            "event":    "match",
            "opponent": opponent,
            "won":      won,
        })


def get_display_name(player: dict) -> str:
    return f"{player['nickname']} ({player['first_name']} '{player['nickname']}' {player['last_name']})"


def short_name(player: dict) -> str:
    return player["nickname"]
