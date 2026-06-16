"""
World simulation step — called each week.
Drives player development, AI decisions, and world state updates.
"""
import random
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from systems.player_system import develop_player, should_retire
from systems.academy_system import develop_academy
from systems.contract_system import process_expired_contracts
from systems.chemistry_system import passive_chemistry_gain
from engine.transfer_engine import ai_transfers
from systems.news_system import news_free_agent


def simulate_world_week(gs: dict) -> None:
    """
    Called every week — updates all living systems in the world.
    The calendar engine handles match/tournament triggers;
    this function handles everything else.
    """
    # Ensure season state exists
    year = gs.get("year", 2025)
    from engine.season_engine import init_season_state
    if not gs.get("seasons"):
        init_season_state(gs, year)
        gs["current_season"] = year
    # Don't overwrite current_season when the calendar year advances to a new year
    # The active season spans across the calendar year boundary
    # 1. Player development (once per month — on week 1)
    if gs["week"] == 1:
        _develop_all_players(gs)
        _retire_veterans(gs)
        _evolve_chemistry(gs)

    # 2. Process expired contracts (monthly)
    if gs["week"] == 1:
        released = process_expired_contracts(gs)
        for pid, oid in released:
            p = gs["players"].get(pid)
            org = gs["orgs"].get(oid) if oid else None
            if p and org:
                news_free_agent(gs, p["nickname"], org["name"])

    # 3. AI roster management (every 4 weeks = monthly)
    if gs["week"] == 2:
        ai_transfers(gs)

    # 4. Academy development (monthly)
    if gs["week"] == 3:
        for org in gs["orgs"].values():
            develop_academy(org, gs["players"], months=1)


def _develop_all_players(gs: dict) -> None:
    for p in gs["players"].values():
        if not p.get("retired"):
            develop_player(p, months_passed=1)


def _retire_veterans(gs: dict) -> None:
    for p in list(gs["players"].values()):
        if p.get("retired"):
            continue
        if should_retire(p):
            p["retired"] = True
            org_id = p.get("org_id")
            if org_id:
                org = gs["orgs"].get(org_id)
                if org:
                    pid = p["id"]
                    for lst in ("roster", "bench", "academy"):
                        if pid in org.get(lst, []):
                            org[lst].remove(pid)
            p["org_id"] = None
            p["career_history"].append({
                "year": gs["year"], "month": gs["month"], "event": "retired"
            })


def _evolve_chemistry(gs: dict) -> None:
    for org in gs["orgs"].values():
        passive_chemistry_gain(org)
