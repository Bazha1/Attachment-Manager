"""
Main game loop.
advance_calendar() → process_tournaments() → simulate_matches()
→ update_players() → update_teams() → update_rankings()
→ update_economy() → generate_news() → save_state()
"""
import json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import SAVE_FILE, DATA_DIR
from engine.calendar_engine import advance_time
from engine.simulation_engine import simulate_world_week
from ui.menu import main_menu, header, pause, _c, print_news_item
from ui.calendar_view import show_calendar
from ui.match_view import show_match_result, show_pre_match
from ui.season_dashboard import show_season_dashboard
from ui.career_dashboard import (show_player_career, show_org_career,
                                  player_list_menu)
from systems.news_system import latest_news
from engine.ranking_engine import compute_rankings


def run(gs: dict) -> None:
    """Enter the main game loop."""
    while True:
        choice = main_menu(gs)

        if choice == "1":
            _advance_one_week(gs, verbose=True)
        elif choice == "2":
            _advance_to_next_event(gs)
        elif choice == "3":
            show_calendar(gs)
        elif choice == "4":
            _team_overview(gs)
        elif choice == "5":
            _player_overview(gs)
        elif choice == "6":
            _transfers_menu(gs)
        elif choice == "7":
            _academy_menu(gs)
        elif choice == "8":
            _rankings_menu(gs)
        elif choice == "9":
            _news_menu(gs)
        elif choice == "0":
            _career_menu(gs)
        elif choice == "s":
            show_season_dashboard(gs)
        elif choice == "q":
            save_state(gs)
            print(_c("green", "\n  Game saved. Goodbye!\n"))
            sys.exit(0)
        else:
            pass  # invalid choice, loop again


# ─── Week Advancement ─────────────────────────────────────────────────────

def _advance_one_week(gs: dict, verbose: bool = True) -> list:
    """Core game loop step — advance one week and process all events."""
    # 1–8: calendar + simulation
    events = advance_time(gs)
    simulate_world_week(gs)

    # Show player-org match results
    player_org_id = gs.get("player_org_id")
    player_results = [e for e in events
                      if isinstance(e, dict)
                      and (e.get("team_a") == player_org_id
                           or e.get("team_b") == player_org_id)]

    if verbose and player_results:
        header(gs)
        for r in player_results:
            show_match_result(r, gs, player_org_id)
        pause()
    elif verbose and events:
        header(gs)
        _print_event_summary(events, gs)
        pause()

    # Auto-save every 4 weeks
    if gs["week"] == 4:
        save_state(gs)

    return events


def _advance_to_next_event(gs: dict) -> None:
    """Advance weeks until a meaningful event occurs for the player's org."""
    player_org_id = gs.get("player_org_id")
    max_weeks = 52
    for _ in range(max_weeks):
        events = _advance_one_week(gs, verbose=False)
        player_events = [e for e in events
                         if isinstance(e, dict)
                         and (e.get("team_a") == player_org_id
                              or e.get("team_b") == player_org_id)]
        if player_events:
            header(gs)
            for r in player_events:
                show_match_result(r, gs, player_org_id)
            pause()
            return
        # Also stop at notable world events
        notable = [e for e in events
                   if isinstance(e, dict) and e.get("type") == "league_end"]
        if notable:
            header(gs)
            _print_event_summary(events, gs)
            pause()
            return


def _print_event_summary(events: list, gs: dict) -> None:
    print(_c("bold", f"\n  This week — {gs['current_date']}\n"))
    shown = 0
    for e in events:
        if not isinstance(e, dict):
            continue
        if e.get("type") == "league_end":
            print(_c("cyan", f"  ✓ League concluded: {e.get('tournament')}"))
            shown += 1
        elif "winner" in e and "team_a_name" in e:
            w = e["team_a_name"] if e["winner"] == e["team_a"] else e["team_b_name"]
            l = e["team_b_name"] if e["winner"] == e["team_a"] else e["team_a_name"]
            print(f"  {_c('green', w):<30} def. {_c('red', l):<30} {e['score']}")
            shown += 1
        if shown >= 8:
            remaining = len(events) - shown
            if remaining > 0:
                print(_c("dim", f"  ... and {remaining} more matches"))
            break


# ─── Team Overview ─────────────────────────────────────────────────────────

def _team_overview(gs: dict) -> None:
    from ui.menu import header, pause, print_table, _c
    header(gs)
    poid = gs.get("player_org_id")
    if not poid:
        pause()
        return
    org = gs["orgs"][poid]
    show_org_career(org, gs)


# ─── Player Overview ───────────────────────────────────────────────────────

def _player_overview(gs: dict) -> None:
    poid = gs.get("player_org_id")
    p = player_list_menu(gs, poid, "YOUR ROSTER — SELECT PLAYER")
    if p:
        show_player_career(p, gs)


# ─── Transfers ─────────────────────────────────────────────────────────────

def _transfers_menu(gs: dict) -> None:
    from ui.menu import header, pause, print_menu, print_table, _c
    from engine.transfer_engine import find_available_players, sign_player
    from engine.economy_engine import transfer_fee, can_afford
    from utils.stats_utils import overall_rating as ovr

    while True:
        header(gs)
        poid = gs.get("player_org_id")
        org  = gs["orgs"].get(poid)
        choice = print_menu("TRANSFERS", [
            ("1", "Browse free agents"),
            ("2", "Release a player"),
            ("3", "View incoming interest"),
            ("0", "Back"),
        ])
        if choice == "0":
            return
        elif choice == "1":
            header(gs)
            fas = find_available_players(gs)[:20]
            if not fas:
                print("  No free agents available.")
                pause()
                continue
            print(_c("bold", "\n  FREE AGENTS\n"))
            for i, p in enumerate(fas, 1):
                fee = transfer_fee(p)
                o   = int(ovr(p["attributes"]))
                can = _c("green", "✓") if can_afford(org, fee // 4) else _c("red", "✗")
                print(f"  [{_c('yellow', str(i))}] {p['nickname']:<16} "
                      f"{p['role']:<16} OVR:{o:>3}  "
                      f"Value:${fee:>8,}  Signing:${fee//4:>7,} {can}")
            print(f"  [{_c('yellow', '0')}] Back")
            raw = input(_c("cyan", "  ▶ Sign player #: ")).strip()
            try:
                idx = int(raw)
                if idx == 0: continue
                target = fas[idx - 1]
                if sign_player(org, target, gs):
                    print(_c("green", f"\n  {target['nickname']} signed!"))
                else:
                    print(_c("red", "\n  Could not sign — insufficient budget or no roster space."))
                pause()
            except (ValueError, IndexError):
                pass

        elif choice == "2":
            p = player_list_menu(gs, poid, "RELEASE PLAYER")
            if p:
                from systems.contract_system import release_player
                release_player(p, gs["year"], gs["month"], org)
                from systems.news_system import news_free_agent
                news_free_agent(gs, p["nickname"], org["name"])
                print(_c("yellow", f"\n  {p['nickname']} released."))
                pause()


# ─── Academy ───────────────────────────────────────────────────────────────

def _academy_menu(gs: dict) -> None:
    from ui.menu import header, pause, print_menu, _c
    from systems.academy_system import (fill_academy, top_prospects,
                                         promote_player, scout_prospect)
    from utils.stats_utils import overall_rating as ovr

    while True:
        header(gs)
        poid = gs.get("player_org_id")
        org  = gs["orgs"].get(poid)
        acad = org.get("academy", [])
        print(_c("bold", f"\n  ACADEMY  ({len(acad)} / 5 players)\n"))
        for pid in acad:
            p = gs["players"].get(pid)
            if not p: continue
            o = int(ovr(p["attributes"]))
            print(f"    {p['nickname']:<16} Age:{p['age']}  OVR:{o:>3}  "
                  f"{p['role']:<16}  {p.get('playstyle','')}")

        choice = print_menu("ACADEMY OPTIONS", [
            ("1", "Promote player"),
            ("2", "Scout new prospect"),
            ("3", "Fill academy (auto)"),
            ("0", "Back"),
        ])
        if choice == "0": return
        elif choice == "1":
            pids = [gs["players"][pid] for pid in acad if pid in gs["players"]]
            if not pids:
                print("  No academy players.")
                pause()
                continue
            for i, ap in enumerate(pids, 1):
                print(f"  [{_c('yellow', str(i))}] {ap['nickname']}  "
                      f"OVR:{int(ovr(ap['attributes']))}  {ap['role']}")
            raw = input(_c("cyan", "  Promote #: ")).strip()
            try:
                idx = int(raw) - 1
                target = pids[idx]
                dest_choice = input(_c("cyan", "  To [1] Starter  [2] Bench: ")).strip()
                dest = "starter" if dest_choice == "1" else "bench"
                if promote_player(target, org, dest):
                    print(_c("green", f"\n  {target['nickname']} promoted to {dest}!"))
                else:
                    print(_c("red", "\n  Promotion failed."))
            except (ValueError, IndexError):
                pass
            pause()
        elif choice == "2":
            p = scout_prospect(org["region"], org.get("budget", 0),
                               gs["players"], gs["year"])
            if p:
                org["academy"].append(p["id"])
                print(_c("green", f"\n  Scouted: {p['nickname']} (Age {p['age']})"))
            else:
                print(_c("red", "\n  No suitable prospect found or insufficient budget."))
            pause()
        elif choice == "3":
            fill_academy(org, gs["players"], gs["year"])
            print(_c("green", "\n  Academy filled."))
            pause()


# ─── Rankings ──────────────────────────────────────────────────────────────

def _rankings_menu(gs: dict) -> None:
    from ui.menu import header, pause, print_table, _c
    header(gs)
    print(_c("bold", "\n  ◈ WORLD RANKINGS (Top 30)\n"))
    ranking = compute_rankings(gs)
    headers = ["#", "Organization", "Region", "Points", "Rep"]
    rows = []
    for rank, (oid, pts) in enumerate(ranking[:30], 1):
        org = gs["orgs"].get(oid)
        if not org: continue
        rows.append([rank, org["name"][:28], org["region"].title(),
                     f"{int(pts):,}", org.get("reputation", 0)])
    print_table(headers, rows, col_widths=[4, 30, 18, 12, 6])
    print()
    pause()


# ─── News ──────────────────────────────────────────────────────────────────

def _news_menu(gs: dict) -> None:
    from ui.menu import header, pause, print_news_item, _c
    header(gs)
    print(_c("bold", "\n  ◈ LATEST NEWS\n"))
    items = latest_news(gs, 20)
    if not items:
        print("  No news yet.")
    for item in items:
        print_news_item(item)
    print()
    pause()


# ─── Career ────────────────────────────────────────────────────────────────

def _career_menu(gs: dict) -> None:
    from ui.menu import print_menu, header, _c
    while True:
        header(gs)
        choice = print_menu("CAREER DASHBOARD", [
            ("1", "Your organization history"),
            ("2", "Browse any player career"),
            ("3", "Browse any organization"),
            ("0", "Back"),
        ])
        if choice == "0": return
        elif choice == "1":
            poid = gs.get("player_org_id")
            if poid:
                show_org_career(gs["orgs"][poid], gs)
        elif choice == "2":
            p = player_list_menu(gs, title="ALL PLAYERS")
            if p:
                show_player_career(p, gs)
        elif choice == "3":
            _pick_org_career(gs)


def _pick_org_career(gs: dict) -> None:
    from ui.menu import header, _c, pause
    from utils.stats_utils import overall_rating as ovr
    header(gs)
    orgs = sorted(gs["orgs"].values(),
                  key=lambda o: o.get("ranking_points", 0), reverse=True)[:30]
    for i, o in enumerate(orgs, 1):
        print(f"  [{_c('yellow', str(i))}] {o['name']:<30} "
              f"{o['region'].title():<18}  Rank #{o.get('ranking_position','—')}")
    print(f"  [{_c('yellow', '0')}] Back")
    raw = input(_c("cyan", "  ▶ ")).strip()
    try:
        idx = int(raw)
        if idx == 0: return
        show_org_career(orgs[idx - 1], gs)
    except (ValueError, IndexError):
        pass


# ─── State Persistence ─────────────────────────────────────────────────────

def save_state(gs: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SAVE_FILE, "w") as f:
        json.dump(gs, f, indent=2)


def load_state() -> dict | None:
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE) as f:
            return json.load(f)
    return None
