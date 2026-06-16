"""
Python bridge for the CS Manager web API.
Called by the Node.js api-server via child_process.
Reads a JSON action from stdin, performs it, writes JSON result to stdout.
"""
import sys
import os
import json
import uuid
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "gamestate.json")
os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)


def load_state():
    if not os.path.exists(STATE_FILE):
        return None
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state(gs):
    with open(STATE_FILE, "w") as f:
        json.dump(gs, f)


def org_summary(org, org_id):
    roster = org.get("roster", [])
    return {
        "id": org_id,
        "name": org.get("name", ""),
        "tag": org.get("tag", ""),
        "region": org.get("region", ""),
        "tier": org.get("tier", 1),
        "rating": round(org.get("rating", 70.0), 1),
        "budget": org.get("budget", 1000000),
        "roster_size": len(roster),
    }


def build_game_state(gs):
    if gs is None:
        return {"has_game": False, "week": 0, "month": 1, "year": 2025,
                "season_phase": "", "budget": 0, "roster_size": 0, "form": []}

    org_id = gs.get("player_org_id")
    org = gs["orgs"].get(org_id, {}) if org_id else {}

    # Compute world rank
    world_rank = None
    try:
        from engine.ranking_engine import compute_rankings
        rankings = compute_rankings(gs)
        for i, (oid, _) in enumerate(rankings):
            if oid == org_id:
                world_rank = i + 1
                break
    except Exception:
        pass

    # Chemistry & pressure
    try:
        from systems.chemistry_system import team_chemistry
        chem = round(team_chemistry(gs, org_id), 1)
    except Exception:
        chem = 50.0

    try:
        from systems.pressure_system import org_pressure
        pres = round(org_pressure(gs, org_id), 1)
    except Exception:
        pres = 0.0

    week = gs.get("week", 1)
    month = gs.get("month", 1)
    year = gs.get("year", 2025)

    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    month_name = month_names[month - 1] if 1 <= month <= 12 else "?"
    week_label = f"Week {week}, {month_name} {year}"

    # Season phase
    phase_map = {
        1: "Winter League", 2: "Winter League", 3: "Winter League",
        4: "Spring League", 5: "Spring League", 6: "Spring League",
        7: "Major I", 8: "Summer League", 9: "Summer League",
        10: "Summer League", 11: "Major II", 12: "TI Season"
    }
    season_phase = phase_map.get(month, "Off-Season")

    return {
        "has_game": True,
        "manager_name": gs.get("player_name", "Manager"),
        "week": week,
        "month": month,
        "year": year,
        "season_phase": season_phase,
        "org_id": org_id or "",
        "org_name": org.get("name", ""),
        "org_tag": org.get("tag", ""),
        "region": org.get("region", ""),
        "tier": org.get("tier", 1),
        "budget": org.get("budget", 0),
        "roster_size": len(org.get("roster", [])),
        "academy_size": len(org.get("academy", [])),
        "form": org.get("form", [])[-10:],
        "world_rank": world_rank,
        "chemistry": chem,
        "pressure": pres,
        "news_count": len(gs.get("news", [])),
        "week_label": week_label,
    }


def mental_label(mental) -> str:
    """Convert mental dict {confidence, motivation, tilt_resistance} to a readable label."""
    if isinstance(mental, str):
        return mental
    if not isinstance(mental, dict):
        return "stable"
    conf = mental.get("confidence", 50)
    motiv = mental.get("motivation", 50)
    tilt = mental.get("tilt_resistance", 50)
    avg = (conf + motiv + tilt) / 3
    if avg >= 75:
        return "confident"
    if avg >= 60:
        return "motivated"
    if avg >= 40:
        return "stable"
    if tilt < 30:
        return "tilted"
    if conf < 30:
        return "nervous"
    return "stable"


def build_player_card(gs, player_id, is_academy=False):
    p = gs["players"].get(player_id, {})
    if not p:
        return None
    attrs = p.get("attributes", {})
    return {
        "id": player_id,
        "name": p.get("name", ""),
        "alias": p.get("alias", ""),
        "age": p.get("age", 18),
        "nationality": p.get("nationality", ""),
        "role": p.get("role", "rifler"),
        "rating": round(p.get("rating", 70.0), 1),
        "hltv_rating": round(p.get("hltv_rating", 1.0), 3),
        "salary": p.get("salary", 5000),
        "contract_years": p.get("contract_years", 1),
        "form": p.get("form", [])[-5:],
        "mental": mental_label(p.get("mental", "stable")),
        "is_academy": is_academy,
        "org_id": p.get("org_id"),
        "attributes": {k: round(float(v), 1) for k, v in attrs.items()},
    }


def handle_list_orgs(gs):
    if gs is None:
        return {"error": "No game state"}
    orgs = []
    for org_id, org in gs["orgs"].items():
        orgs.append(org_summary(org, org_id))
    orgs.sort(key=lambda x: (-x["rating"], x["name"]))
    return orgs


def handle_new_game(data):
    from main import generate_world
    from engine.simulation_engine import simulate_world_week
    org_id = data.get("org_id")
    manager_name = data.get("manager_name", "Manager")
    year = data.get("year", 2025)

    gs = generate_world(year)
    if org_id not in gs["orgs"]:
        return {"error": f"Unknown org: {org_id}"}

    gs["player_org_id"] = org_id
    gs["player_name"] = manager_name
    gs["week"] = 1
    gs["month"] = 1
    gs["year"] = year
    gs["match_history"] = []
    gs["news"] = []
    gs["save_id"] = str(uuid.uuid4())[:8]

    save_state(gs)
    return build_game_state(gs)


def handle_get_state():
    gs = load_state()
    if gs is None:
        return {"has_game": False, "week": 0, "month": 1, "year": 2025,
                "season_phase": "", "budget": 0, "roster_size": 0, "form": []}
    return build_game_state(gs)


def handle_advance_week():
    gs = load_state()
    if gs is None:
        return {"error": "No active game"}

    from engine.calendar_engine import advance_time
    from engine.simulation_engine import simulate_world_week

    news_before = len(gs.get("news", []))
    events = advance_time(gs)
    simulate_world_week(gs)

    # Collect new news
    all_news = gs.get("news", [])
    new_news_raw = all_news[news_before:] if news_before < len(all_news) else all_news[-5:]

    # Find player org match results this week
    org_id = gs.get("player_org_id")
    player_results = []
    other_results = []
    for e in events:
        if not isinstance(e, dict) or "winner" not in e:
            continue
        is_player = (e.get("team_a_id") == org_id or e.get("team_b_id") == org_id)
        result = {
            "tournament_name": e.get("tournament_name", ""),
            "team_a": e.get("team_a_name", ""),
            "team_b": e.get("team_b_name", ""),
            "score_a": e.get("score_a", 0),
            "score_b": e.get("score_b", 0),
            "winner": e.get("winner_name", ""),
            "is_player_match": is_player,
            "maps": e.get("maps", []),
            "week": gs.get("week", 1),
        }
        if is_player:
            player_results.append(result)
        else:
            other_results.append(result)

    all_results = player_results + other_results[:10]

    # Build news items
    new_news = []
    for i, n in enumerate(new_news_raw[:20]):
        new_news.append({
            "id": f"n{gs.get('week',1)}-{i}",
            "headline": n.get("headline", ""),
            "category": n.get("category", "general"),
            "week": n.get("week", gs.get("week", 1)),
            "month": n.get("month", gs.get("month", 1)),
            "year": n.get("year", gs.get("year", 2025)),
            "timestamp": f"Week {n.get('week',1)}, {n.get('year',2025)}",
        })

    # Build summary
    if player_results:
        r = player_results[0]
        if r["winner"] == r["team_a"] and gs["orgs"].get(org_id, {}).get("name") == r["team_a"]:
            outcome = f"Victory! {r['team_a']} {r['score_a']}-{r['score_b']} {r['team_b']}"
        elif r["winner"] == r["team_b"] and gs["orgs"].get(org_id, {}).get("name") == r["team_b"]:
            outcome = f"Victory! {r['team_b']} {r['score_b']}-{r['score_a']} {r['team_a']}"
        else:
            outcome = f"Defeat. {r['team_a']} {r['score_a']}-{r['score_b']} {r['team_b']}"
        week_summary = outcome
    else:
        week_summary = f"Week {gs.get('week', 1)} complete. {len(all_results)} matches played worldwide."

    save_state(gs)
    return {
        "state": build_game_state(gs),
        "match_results": all_results,
        "new_news": new_news,
        "week_summary": week_summary,
    }


def handle_get_roster():
    gs = load_state()
    if gs is None:
        return {"error": "No active game"}

    org_id = gs.get("player_org_id")
    org = gs["orgs"].get(org_id, {})

    roster_ids = org.get("roster", [])
    academy_ids = org.get("academy", [])

    roster = [build_player_card(gs, pid, False) for pid in roster_ids]
    academy = [build_player_card(gs, pid, True) for pid in academy_ids]
    roster = [p for p in roster if p]
    academy = [p for p in academy if p]

    roster.sort(key=lambda p: -p["rating"])
    academy.sort(key=lambda p: -p["rating"])

    try:
        from systems.chemistry_system import team_chemistry
        chem = round(team_chemistry(gs, org_id), 1)
    except Exception:
        chem = 50.0

    try:
        from systems.pressure_system import org_pressure
        pres = round(org_pressure(gs, org_id), 1)
    except Exception:
        pres = 0.0

    return {
        "roster": roster,
        "academy": academy,
        "budget": org.get("budget", 0),
        "chemistry": chem,
        "pressure": pres,
    }


def handle_release_player(player_id):
    gs = load_state()
    if gs is None:
        return {"error": "No active game"}

    org_id = gs.get("player_org_id")
    org = gs["orgs"].get(org_id, {})
    roster = org.get("roster", [])

    if player_id not in roster:
        return {"error": "Player not in roster"}
    if len(roster) <= 5:
        return {"error": "Cannot release — minimum 5 players required"}

    roster.remove(player_id)
    org["roster"] = roster
    p = gs["players"].get(player_id, {})
    if p:
        p["org_id"] = None
    save_state(gs)
    return handle_get_roster()


def handle_sign_player(player_id):
    gs = load_state()
    if gs is None:
        return {"error": "No active game"}

    org_id = gs.get("player_org_id")
    org = gs["orgs"].get(org_id, {})
    roster = org.get("roster", [])

    if len(roster) >= 10:
        return {"error": "Roster full (max 10 players)"}

    p = gs["players"].get(player_id, {})
    if not p:
        return {"error": "Player not found"}
    if p.get("org_id"):
        return {"error": "Player is already on a team"}

    # Check salary budget
    monthly_salary = p.get("salary", 5000)
    budget = org.get("budget", 0)
    if budget < monthly_salary * 3:
        return {"error": f"Insufficient budget (need ${monthly_salary*3:,}, have ${budget:,})"}

    p["org_id"] = org_id
    p["contract_years"] = 1
    roster.append(player_id)
    org["roster"] = roster
    org["budget"] = budget - monthly_salary

    save_state(gs)
    return handle_get_roster()


def handle_promote_player(player_id):
    gs = load_state()
    if gs is None:
        return {"error": "No active game"}

    org_id = gs.get("player_org_id")
    org = gs["orgs"].get(org_id, {})
    roster = org.get("roster", [])
    academy = org.get("academy", [])

    if player_id not in academy:
        return {"error": "Player not in academy"}
    if len(roster) >= 10:
        return {"error": "Roster full (max 10 players)"}

    academy.remove(player_id)
    roster.append(player_id)
    org["academy"] = academy
    org["roster"] = roster

    p = gs["players"].get(player_id, {})
    if p:
        p["is_academy"] = False

    save_state(gs)
    return handle_get_roster()


def handle_get_news():
    gs = load_state()
    if gs is None:
        return []

    all_news = gs.get("news", [])
    result = []
    for i, n in enumerate(reversed(all_news[-50:])):
        result.append({
            "id": f"news-{i}",
            "headline": n.get("headline", ""),
            "category": n.get("category", "general"),
            "week": n.get("week", 1),
            "month": n.get("month", 1),
            "year": n.get("year", 2025),
            "timestamp": f"Week {n.get('week',1)}, {n.get('year',2025)}",
        })
    return result


def handle_get_rankings():
    gs = load_state()
    if gs is None:
        return []

    org_id = gs.get("player_org_id")
    try:
        from engine.ranking_engine import compute_rankings
        rankings = compute_rankings(gs)
    except Exception:
        return []

    result = []
    for i, (oid, pts) in enumerate(rankings[:30]):
        org = gs["orgs"].get(oid, {})
        result.append({
            "rank": i + 1,
            "org_id": oid,
            "name": org.get("name", ""),
            "tag": org.get("tag", ""),
            "region": org.get("region", ""),
            "points": int(pts),
            "is_player_org": oid == org_id,
        })
    return result


def handle_get_transfers():
    gs = load_state()
    if gs is None:
        return []

    # Find free agents (players with no org_id)
    free_agents = []
    for pid, p in gs["players"].items():
        if not p.get("org_id") and not p.get("is_academy", False):
            card = build_player_card(gs, pid, False)
            if card:
                free_agents.append(card)

    free_agents.sort(key=lambda p: -p["rating"])
    return free_agents[:50]


def handle_get_fixtures():
    gs = load_state()
    if gs is None:
        return []

    org_id = gs.get("player_org_id")
    org = gs["orgs"].get(org_id, {})
    org_name = org.get("name", "")

    fixtures = []
    current_week = gs.get("week", 1)

    for tid, t in gs.get("tournaments", {}).items():
        if not isinstance(t, dict):
            continue
        if t.get("status") != "ongoing":
            continue

        participants = t.get("participants", [])
        if org_id not in participants:
            continue

        # Look at schedule
        schedule = t.get("schedule", [])
        for match in schedule:
            if match.get("played"):
                continue
            if match.get("team_a") == org_id or match.get("team_b") == org_id:
                opp_id = match["team_b"] if match["team_a"] == org_id else match["team_a"]
                opp = gs["orgs"].get(opp_id, {})
                fixtures.append({
                    "tournament_id": tid,
                    "tournament_name": t.get("name", ""),
                    "opponent_name": opp.get("name", ""),
                    "opponent_tag": opp.get("tag", ""),
                    "week": match.get("week", current_week + 1),
                    "month": gs.get("month", 1),
                    "is_home": match.get("team_a") == org_id,
                    "round": match.get("round", "Group Stage"),
                })

    fixtures.sort(key=lambda f: (f["week"],))
    return fixtures[:10]


def handle_get_results():
    gs = load_state()
    if gs is None:
        return []

    org_id = gs.get("player_org_id")
    history = gs.get("match_history", [])
    results = []
    for r in reversed(history[-20:]):
        if r.get("team_a_id") == org_id or r.get("team_b_id") == org_id:
            results.append({
                "tournament_name": r.get("tournament_name", ""),
                "team_a": r.get("team_a_name", ""),
                "team_b": r.get("team_b_name", ""),
                "score_a": r.get("score_a", 0),
                "score_b": r.get("score_b", 0),
                "winner": r.get("winner_name", ""),
                "is_player_match": True,
                "maps": r.get("maps", []),
                "week": r.get("week", 1),
            })
    return results[:10]


def handle_list_orgs_initial():
    """Generate a mini world just for org selection (no full simulation)."""
    from main import generate_world
    gs = generate_world(2025)
    orgs = []
    for org_id, org in gs["orgs"].items():
        orgs.append(org_summary(org, org_id))
    orgs.sort(key=lambda x: (-x["rating"], x["name"]))
    return orgs


def main():
    raw = sys.stdin.read()

    # Redirect stdout to stderr so any print() calls from game modules
    # don't pollute our JSON output channel
    real_stdout = sys.stdout
    sys.stdout = sys.stderr

    try:
        payload = json.loads(raw)
    except Exception as e:
        sys.stdout = real_stdout
        print(json.dumps({"error": f"Invalid JSON input: {e}"}))
        return

    action = payload.get("action")
    data = payload.get("data", {})

    try:
        if action == "list_orgs":
            gs = load_state()
            if gs:
                result = handle_list_orgs(gs)
            else:
                result = handle_list_orgs_initial()

        elif action == "new_game":
            result = handle_new_game(data)

        elif action == "get_state":
            result = handle_get_state()

        elif action == "advance_week":
            result = handle_advance_week()

        elif action == "get_roster":
            result = handle_get_roster()

        elif action == "release_player":
            result = handle_release_player(data.get("player_id", ""))

        elif action == "sign_player":
            result = handle_sign_player(data.get("player_id", ""))

        elif action == "promote_player":
            result = handle_promote_player(data.get("player_id", ""))

        elif action == "get_news":
            result = handle_get_news()

        elif action == "get_rankings":
            result = handle_get_rankings()

        elif action == "get_transfers":
            result = handle_get_transfers()

        elif action == "get_fixtures":
            result = handle_get_fixtures()

        elif action == "get_results":
            result = handle_get_results()

        else:
            result = {"error": f"Unknown action: {action}"}

    except Exception as e:
        result = {"error": str(e), "trace": traceback.format_exc()}

    sys.stdout = real_stdout
    print(json.dumps(result))


if __name__ == "__main__":
    main()
