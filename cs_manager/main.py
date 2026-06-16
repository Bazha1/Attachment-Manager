"""
CS Manager — Entry Point
Handles new game setup and world generation.
"""
import os, sys, json, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (REGIONS, ORGS_PER_REGION, LEAGUE_SIZE, START_YEAR,
                    START_MONTH, GAME_TITLE, DATA_DIR, SAVE_FILE)
from systems.player_system import create_player
from systems.team_system import create_org
from systems.academy_system import fill_academy
from systems.contract_system import assign_contract
from engine.ranking_engine import update_org_ranking_points
from systems.chemistry_system import compute_chemistry
from ui.menu import _c, clear, THICK_SEP, TERMINAL_WIDTH
from game_loop import run, save_state, load_state


# ─── World Generation ──────────────────────────────────────────────────────

def generate_world(year: int = START_YEAR) -> dict:
    print(_c("cyan", "\n  Generating world..."))

    orgs: dict  = {}
    players: dict = {}
    ranking_history: dict = {}

    tier_dist = {
        "elite":  3,
        "top":    5,
        "mid":    18,
        "lower":  14,
        "bottom": 10,
    }

    for region in REGIONS:
        print(f"    {region.title()}...", end="", flush=True)
        region_orgs = []

        for tier, count in tier_dist.items():
            for _ in range(count):
                org = create_org(region, tier=tier)
                orgs[org["id"]] = org
                region_orgs.append(org)

        # Assign rosters
        for org in region_orgs:
            tier = _org_tier_from_rep(org["reputation"])
            quality_map = {"elite": 82, "top": 72, "mid": 58,
                           "lower": 44, "bottom": 30}
            quality = quality_map.get(tier, 50) + random.randint(-8, 8)

            # 5 starters
            for i in range(5):
                p = create_player(org["id"], region, quality=quality)
                assign_contract(p, year, random.randint(1, 3))
                players[p["id"]] = p
                org["roster"].append(p["id"])

            # 0-1 bench
            if random.random() < 0.5:
                p = create_player(org["id"], region, quality=max(30, quality - 10))
                assign_contract(p, year, random.randint(1, 2))
                players[p["id"]] = p
                org["bench"].append(p["id"])

            # Academy
            fill_academy(org, players, year, target_size=random.randint(3, 5))

            # Seed chemistry
            org["chemistry"] = compute_chemistry(org, players)
            org["morale"] = random.randint(45, 75)

        # Mark top LEAGUE_SIZE as in-league
        region_orgs_sorted = sorted(region_orgs,
                                     key=lambda o: o["reputation"], reverse=True)
        for org in region_orgs_sorted[:LEAGUE_SIZE]:
            org["in_league"] = True

        # Seed ranking points based on reputation
        for org in region_orgs:
            pts = int(org["reputation"] ** 2 * 2.5 + random.randint(0, 500))
            ranking_history.setdefault(org["id"], [])
            ranking_history[org["id"]].append({
                "year": year - 1, "month": 12, "points": pts
            })
            org["ranking_points"] = pts

        print(_c("green", " ✓"))

    # ── Coaches (simplified — just IDs attached to orgs) ──────────────
    for org in orgs.values():
        org["coach_id"] = _gen_coach()

    # ── Free agents (5% of player pool) ──────────────────────────────
    fa_count = max(10, len(players) // 20)
    for region in REGIONS:
        for _ in range(fa_count // len(REGIONS)):
            p = create_player(None, region, quality=random.randint(30, 70))
            assign_contract(p, year, random.randint(1, 2))
            p["status"] = "free_agent"
            players[p["id"]] = p

    gs = {
        "year":           year,
        "month":          START_MONTH,
        "week":           1,
        "current_date":   f"January Week 1, {year}",
        "orgs":           orgs,
        "players":        players,
        "tournaments":    {},
        "ranking_history":ranking_history,
        "major_qualified":{},
        "ti_qualified":   [],
        "news":           [],
        "records":        {
            "highest_hltv_season": None,
            "most_mvps":           None,
            "longest_win_streak":  None,
        },
        "player_org_id":  None,
    }

    update_org_ranking_points(gs)
    return gs


def _org_tier_from_rep(rep: int) -> str:
    if rep >= 88: return "elite"
    if rep >= 74: return "top"
    if rep >= 55: return "mid"
    if rep >= 38: return "lower"
    return "bottom"


def _gen_coach() -> dict:
    from utils.random_utils import random_name, random_nationality
    region = random.choice(REGIONS)
    fn, ln = random_name(region)
    return {
        "id":         f"c_{random.randint(1000,9999)}",
        "name":       f"{fn} {ln}",
        "age":        random.randint(28, 52),
        "nationality":random_nationality(region),
        "leadership": random.randint(40, 95),
        "tactical_iq":random.randint(40, 95),
        "mental_coaching": random.randint(40, 95),
    }


# ─── New Game Setup ────────────────────────────────────────────────────────

def new_game() -> dict:
    clear()
    print(_c("cyan", THICK_SEP))
    print(_c("bold", "  NEW GAME SETUP".center(80)))
    print(_c("cyan", THICK_SEP))

    player_name = input(_c("yellow", "\n  Your name (manager): ")).strip() or "Manager"

    print(_c("bold", "\n  Select a region:"))
    for i, r in enumerate(REGIONS, 1):
        print(f"    [{_c('yellow', str(i))}] {r.replace('_', ' ').title()}")
    region_choice = input(_c("cyan", "  ▶ ")).strip()
    try:
        region = REGIONS[int(region_choice) - 1]
    except (ValueError, IndexError):
        region = REGIONS[0]

    print(_c("bold", "\n  Generating the world (this may take a moment)..."))
    gs = generate_world()

    # Show orgs in chosen region sorted by reputation
    region_orgs = sorted(
        [o for o in gs["orgs"].values() if o["region"] == region],
        key=lambda o: o["reputation"], reverse=True
    )
    print(_c("bold", f"\n  Select your organization in {region.replace('_',' ').title()}:"))
    print(_c("dim", f"  {'#':<4} {'Name':<30} {'Tier':<20} {'Rep':>5} {'In League?':>12}"))
    print(_c("dim", "  " + "─" * 72))
    for i, org in enumerate(region_orgs[:20], 1):
        tier   = _org_tier_from_rep(org["reputation"])
        in_l   = _c("green", "Yes") if org["in_league"] else _c("dim", "No")
        print(f"  [{_c('yellow', str(i))}]  {org['name']:<30} {tier:<20} "
              f"{org['reputation']:>5}  {in_l}")
    print(f"\n  [{_c('yellow', '21')}]  Random organization")

    raw = input(_c("cyan", "\n  ▶ ")).strip()
    try:
        idx = int(raw)
        if idx == 21 or idx < 1:
            chosen_org = random.choice(region_orgs)
        else:
            chosen_org = region_orgs[idx - 1]
    except (ValueError, IndexError):
        chosen_org = region_orgs[0]

    gs["player_org_id"] = chosen_org["id"]
    gs["player_name"]   = player_name

    print(_c("green", f"\n  Welcome, {player_name}!"))
    print(_c("green", f"  You are now managing: {chosen_org['name']} [{chosen_org['tag']}]"))
    print(_c("green", f"  Region: {region.replace('_',' ').title()}"))
    input(_c("dim", "\n  Press Enter to begin your career..."))

    save_state(gs)
    return gs


# ─── Entry Point ───────────────────────────────────────────────────────────

def main() -> None:
    clear()
    print(_c("cyan", THICK_SEP))
    print(_c("bold", f"\n  {GAME_TITLE}\n".center(82)))
    print(_c("dim",  "  A living esports world. Your career starts now.\n".center(82)))
    print(_c("cyan", THICK_SEP))
    print(f"\n  [{_c('yellow', '1')}] New Game")
    print(f"  [{_c('yellow', '2')}] Continue Saved Game")
    print(f"  [{_c('yellow', '3')}] Exit")
    choice = input(_c("cyan", "\n  ▶ ")).strip()

    if choice == "1":
        gs = new_game()
        run(gs)
    elif choice == "2":
        gs = load_state()
        if gs is None:
            print(_c("red", "\n  No saved game found. Starting new game...\n"))
            import time; time.sleep(1)
            gs = new_game()
        else:
            print(_c("green", f"\n  Save loaded — {gs.get('current_date', 'Unknown date')}"))
            import time; time.sleep(0.8)
        run(gs)
    elif choice == "3":
        sys.exit(0)
    else:
        main()


if __name__ == "__main__":
    main()
