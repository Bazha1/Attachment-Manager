"""Academy system — youth development and scouting."""
import random
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import AGE_ACADEMY_MIN, AGE_ACADEMY_MAX
from systems.player_system import create_player, develop_player
from systems.contract_system import assign_contract
from utils.stats_utils import overall_rating


def fill_academy(org: dict, players: dict, current_year: int,
                 target_size: int = 5) -> None:
    """Ensure the org has `target_size` academy players."""
    region = org["region"]
    while len(org["academy"]) < target_size:
        quality = random.randint(25, 55)
        p = create_player(org["id"], region, quality=quality, is_academy=True)
        assign_contract(p, current_year, duration_years=random.randint(1, 3))
        players[p["id"]] = p
        org["academy"].append(p["id"])


def develop_academy(org: dict, players: dict, months: int = 1) -> list:
    """
    Develop all academy players. Returns list of breakthrough players
    (those who jumped in overall rating by >= 5 points).
    """
    breakthroughs = []
    for pid in list(org["academy"]):
        p = players.get(pid)
        if not p:
            continue
        old_ovr = overall_rating(p["attributes"])
        develop_player(p, months)
        new_ovr = overall_rating(p["attributes"])
        if new_ovr - old_ovr >= 5:
            breakthroughs.append(p)
    return breakthroughs


def promote_player(player: dict, org: dict, target: str = "bench") -> bool:
    """
    Human-controlled promotion. target = 'bench' or 'starter'.
    Academy players NEVER auto-promote (rule enforced here).
    Returns True on success.
    """
    pid = player["id"]
    if pid not in org.get("academy", []):
        return False
    org["academy"].remove(pid)
    if target == "starter" and len(org["roster"]) < 5:
        org["roster"].append(pid)
        player["status"] = "starter"
        player["is_academy"] = False
    else:
        org["bench"].append(pid)
        player["status"] = "bench"
        player["is_academy"] = False
    return True


def scout_prospect(region: str, budget: int, players: dict,
                   current_year: int) -> dict | None:
    """
    Spend budget to scout a free-agent youth prospect.
    Returns a new player if budget is sufficient, else None.
    """
    cost = random.randint(5_000, 20_000)
    if budget < cost:
        return None
    quality = random.randint(30, 60)
    p = create_player(None, region, quality=quality, is_academy=True)
    assign_contract(p, current_year, duration_years=2)
    players[p["id"]] = p
    return p


def top_prospects(org: dict, players: dict, n: int = 3) -> list:
    """Return top n academy players by overall rating."""
    acad = [players[pid] for pid in org["academy"] if pid in players]
    acad.sort(key=lambda p: overall_rating(p["attributes"]), reverse=True)
    return acad[:n]
