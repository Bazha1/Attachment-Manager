"""Contract management — creation, expiry, renewal, free agency."""
import random
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SALARY_TIERS
from utils.stats_utils import overall_rating


def assign_contract(player: dict, current_year: int,
                    duration_years: int | None = None) -> None:
    if duration_years is None:
        duration_years = random.randint(1, 3)
    expiry_year = current_year + duration_years
    player["contract"]["expiry_year"]  = expiry_year
    player["contract"]["expiry_month"] = 12


def is_expiring_soon(player: dict, current_year: int, current_month: int,
                     months_ahead: int = 3) -> bool:
    ey = player["contract"]["expiry_year"]
    em = player["contract"]["expiry_month"]
    months_left = (ey - current_year) * 12 + (em - current_month)
    return 0 < months_left <= months_ahead


def is_expired(player: dict, current_year: int, current_month: int) -> bool:
    ey = player["contract"]["expiry_year"]
    em = player["contract"]["expiry_month"]
    return (current_year > ey) or (current_year == ey and current_month > em)


def release_player(player: dict, current_year: int, current_month: int,
                   org: dict) -> None:
    """Remove player from org and make free agent."""
    pid = player["id"]
    for lst in ("roster", "bench", "academy"):
        if pid in org.get(lst, []):
            org[lst].remove(pid)
    player["org_id"] = None
    player["status"] = "free_agent"
    # Record in career history
    player["career_history"].append({
        "year":    current_year,
        "month":   current_month,
        "event":   "released",
        "org":     org["name"],
    })


def renew_contract(player: dict, current_year: int,
                   salary_increase_pct: float = 0.10) -> bool:
    """
    Renew a player's contract for 1-3 more years.
    Returns True if the player accepts.
    """
    ovr = overall_rating(player["attributes"])
    # Probability of acceptance depends on player happiness (mental)
    confidence = player["mental"].get("confidence", 60)
    motivation  = player["mental"].get("motivation", 60)
    happiness = (confidence + motivation) / 2

    accept_prob = 0.5 + (happiness - 50) / 200
    if random.random() > accept_prob:
        return False

    new_salary = int(player["contract"]["salary"] * (1 + salary_increase_pct))
    duration   = random.randint(1, 3)
    player["contract"]["salary"]       = new_salary
    player["contract"]["expiry_year"]  = current_year + duration
    player["contract"]["expiry_month"] = 12
    return True


def process_expired_contracts(gs: dict) -> list:
    """
    Check all players for expired contracts.
    Returns list of (player_id, org_id) pairs that became free agents.
    """
    released = []
    y, m = gs["year"], gs["month"]
    for pid, p in gs["players"].items():
        if p.get("retired") or p["org_id"] is None:
            continue
        if is_expired(p, y, m):
            org = gs["orgs"].get(p["org_id"])
            if org:
                release_player(p, y, m, org)
            else:
                p["org_id"] = None
                p["status"] = "free_agent"
            released.append((pid, p.get("org_id")))
    return released
