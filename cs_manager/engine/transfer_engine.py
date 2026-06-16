"""Transfer market — AI transfers, free agency, negotiations."""
import random
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.stats_utils import overall_rating
from engine.economy_engine import transfer_fee, spend, can_afford
from systems.player_system import short_name
from systems.contract_system import assign_contract
from systems.news_system import news_transfer, news_free_agent


def find_available_players(gs: dict, region: str | None = None,
                            role: str | None = None,
                            max_age: int = 35) -> list:
    """Return free agents matching criteria."""
    result = []
    for p in gs["players"].values():
        if p.get("retired") or p.get("is_academy"):
            continue
        if p["org_id"] is not None:
            continue
        if region and p["region"] != region:
            continue
        if role and p["role"] != role:
            continue
        if p["age"] > max_age:
            continue
        result.append(p)
    result.sort(key=lambda p: overall_rating(p["attributes"]), reverse=True)
    return result


def sign_player(org: dict, player: dict, gs: dict,
                duration: int | None = None) -> bool:
    """
    Sign a free agent to the org. Returns True on success.
    Handles budget, roster cap.
    """
    fee = transfer_fee(player)
    if not can_afford(org, fee // 4):   # signing bonus = 25% of value
        return False
    spend(org, fee // 4)
    assign_contract(player, gs["year"], duration)
    player["org_id"] = org["id"]
    if len(org["roster"]) < 5:
        org["roster"].append(player["id"])
        player["status"] = "starter"
    elif len(org.get("bench", [])) < 2:
        org.setdefault("bench", []).append(player["id"])
        player["status"] = "bench"
    else:
        return False   # no room
    player["career_history"].append({
        "year":  gs["year"], "month": gs["month"],
        "event": "signed", "org": org["name"],
    })
    return True


def transfer_player(from_org: dict, to_org: dict,
                    player: dict, gs: dict) -> bool:
    """
    Transfer player between two orgs. Returns True on success.
    """
    fee = transfer_fee(player)
    if not can_afford(to_org, fee):
        return False
    spend(to_org, fee)
    from_org["budget"] = from_org.get("budget", 0) + fee

    pid = player["id"]
    for lst in ("roster", "bench", "academy"):
        if pid in from_org.get(lst, []):
            from_org[lst].remove(pid)

    player["org_id"] = to_org["id"]
    if len(to_org["roster"]) < 5:
        to_org["roster"].append(pid)
        player["status"] = "starter"
    else:
        to_org.setdefault("bench", []).append(pid)
        player["status"] = "bench"

    player["career_history"].append({
        "year": gs["year"], "month": gs["month"],
        "event": "transferred",
        "from": from_org["name"], "to": to_org["name"],
    })
    news_transfer(gs, short_name(player), from_org["name"], to_org["name"])
    return True


def ai_transfers(gs: dict) -> None:
    """
    AI-controlled orgs make rational roster decisions:
    - Replace declining veterans
    - Sign free agents to fill roster gaps
    - Attempt renewals before expiry
    """
    for org in gs["orgs"].values():
        if org["id"] == gs.get("player_org_id"):
            continue   # skip human-controlled org
        _ai_fill_roster(org, gs)
        _ai_replace_weak(org, gs)


def _ai_fill_roster(org: dict, gs: dict) -> None:
    """Fill any empty roster slots from free agents in the same region."""
    while len(org.get("roster", [])) < 5:
        candidates = find_available_players(gs, region=org["region"])
        if not candidates:
            break
        target = candidates[0]
        if not sign_player(org, target, gs):
            break


def _ai_replace_weak(org: dict, gs: dict) -> None:
    """Replace the weakest starter if a significantly better free agent exists."""
    roster = [gs["players"][pid] for pid in org.get("roster", [])
              if pid in gs["players"]]
    if not roster:
        return
    weakest = min(roster, key=lambda p: overall_rating(p["attributes"]))
    weak_ovr = overall_rating(weakest["attributes"])
    candidates = find_available_players(gs, region=org["region"])
    for cand in candidates:
        if overall_rating(cand["attributes"]) > weak_ovr + 10:
            if can_afford(org, transfer_fee(cand) // 4):
                # Release weakest
                weakest["org_id"] = None
                weakest["status"] = "free_agent"
                org["roster"].remove(weakest["id"])
                news_free_agent(gs, short_name(weakest), org["name"])
                sign_player(org, cand, gs)
                break
