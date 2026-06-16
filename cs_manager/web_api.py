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


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _tier_from_rep(rep: float) -> int:
    if rep >= 85: return 1
    if rep >= 70: return 2
    if rep >= 50: return 3
    if rep >= 35: return 4
    return 5


def org_summary(org, org_id):
    rep = org.get("reputation", 50)
    return {
        "id": org_id,
        "name": org.get("name", ""),
        "tag": org.get("tag", ""),
        "region": org.get("region", ""),
        "tier": _tier_from_rep(rep),
        "rating": round(float(rep), 1),
        "budget": org.get("budget", 0),
        "roster_size": len(org.get("roster", [])),
    }


def _rating_from_attrs(attrs: dict) -> float:
    try:
        from utils.stats_utils import overall_rating
        return round(overall_rating(attrs), 1)
    except Exception:
        if attrs:
            return round(sum(attrs.values()) / len(attrs), 1)
        return 50.0


def mental_label(mental) -> str:
    """Convert mental dict {confidence, motivation, tilt_resistance} to a readable label."""
    if isinstance(mental, str):
        return mental
    if not isinstance(mental, dict):
        return "stable"
    conf  = mental.get("confidence", 50)
    motiv = mental.get("motivation", 50)
    tilt  = mental.get("tilt_resistance", 50)
    avg   = (conf + motiv + tilt) / 3
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

    attrs    = p.get("attributes", {})
    rating   = _rating_from_attrs(attrs)
    stats    = p.get("stats", {})
    contract = p.get("contract", {})
    salary   = contract.get("salary", p.get("salary", 5000))
    expiry   = contract.get("expiry_year", gs.get("year", 2025) + 1)
    contract_years = max(0, expiry - gs.get("year", 2025))
    nickname = p.get("nickname", "Unknown")
    fn       = p.get("first_name", "")
    ln       = p.get("last_name", "")
    full_name = f"{fn} {ln}".strip() or nickname
    hltv     = stats.get("hltv_rating", 1.0)
    if not isinstance(hltv, (int, float)):
        hltv = 1.0

    # Match history from player stats
    raw_history = stats.get("match_history", [])
    match_history = []
    for m in raw_history:
        if isinstance(m, dict):
            match_history.append({
                "year":     m.get("year", 0),
                "month":    m.get("month", 0),
                "opponent": m.get("opponent", ""),
                "won":      m.get("won", False),
                "kills":    m.get("kills", 0),
                "deaths":   m.get("deaths", 0),
                "hltv":     m.get("hltv", 0),
                "perf":     m.get("perf", 0),
            })
    match_history.reverse()  # newest first

    return {
        "id":             player_id,
        "name":           full_name,
        "alias":          nickname,
        "age":            p.get("age", 18),
        "nationality":    p.get("nationality", ""),
        "role":           p.get("role", "Rifler"),
        "rating":         rating,
        "hltv_rating":    round(float(hltv), 3),
        "salary":         salary,
        "contract_years": contract_years,
        "form":           [],   # individual player form not tracked; org form used instead
        "mental":         mental_label(p.get("mental", "stable")),
        "is_academy":     is_academy,
        "org_id":         p.get("org_id"),
        "attributes":     {k: round(float(v), 1) for k, v in attrs.items()
                           if isinstance(v, (int, float))},
        "match_history":  match_history[:10],
    }


def build_game_state(gs):
    if gs is None:
        return {"has_game": False, "week": 0, "month": 1, "year": 2025,
                "season_phase": "", "budget": 0, "roster_size": 0,
                "academy_size": 0, "form": []}

    org_id = gs.get("player_org_id")
    org    = gs["orgs"].get(org_id, {}) if org_id else {}

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

    week  = gs.get("week", 1)
    month = gs.get("month", 1)
    year  = gs.get("year", 2025)

    month_names = ["Jan","Feb","Mar","Apr","May","Jun",
                   "Jul","Aug","Sep","Oct","Nov","Dec"]
    month_name  = month_names[month - 1] if 1 <= month <= 12 else "?"
    week_label  = f"Week {week}, {month_name} {year}"

    phase_map = {
        1:"Winter League", 2:"Winter League", 3:"Winter League",
        4:"Spring League", 5:"Spring League", 6:"Spring League",
        7:"Major I",       8:"Summer League", 9:"Summer League",
        10:"Summer League",11:"Major II",      12:"TI Season"
    }
    season_phase = phase_map.get(month, "Off-Season")

    # Season progress (use current_season, not calendar year)
    season_info = None
    try:
        from engine.season_engine import get_season_progress, get_org_season_performance
        season_info = get_season_progress(gs, None)
        player_season = get_org_season_performance(gs, org_id, None)
        if season_info:
            season_info["player_points"] = player_season
    except Exception:
        pass

    return {
        "has_game":      True,
        "manager_name":  gs.get("player_name", "Manager"),
        "week":          week,
        "month":         month,
        "year":          year,
        "season_phase":  season_phase,
        "org_id":        org_id or "",
        "org_name":      org.get("name", ""),
        "org_tag":       org.get("tag", ""),
        "region":        org.get("region", ""),
        "tier":          _tier_from_rep(org.get("reputation", 50)),
        "budget":        org.get("budget", 0),
        "roster_size":   len(org.get("roster", [])),
        "academy_size":  len(org.get("academy", [])),
        "form":          org.get("form", [])[-10:],
        "world_rank":    world_rank,
        "chemistry":     chem,
        "pressure":      pres,
        "news_count":    len(gs.get("news", [])),
        "week_label":    week_label,
        "season":        season_info,
    }


# ─── Handlers ─────────────────────────────────────────────────────────────────

def handle_list_orgs(gs):
    if gs is None:
        return {"error": "No game state"}
    orgs = [org_summary(org, oid) for oid, org in gs["orgs"].items()]
    orgs.sort(key=lambda x: (-x["rating"], x["name"]))
    return orgs


def handle_new_game(data):
    from main import generate_world
    org_id       = data.get("org_id")
    manager_name = data.get("manager_name", "Manager")
    year         = data.get("year", 2025)

    gs = generate_world(year)
    if org_id not in gs["orgs"]:
        return {"error": f"Unknown org: {org_id}"}

    gs["player_org_id"] = org_id
    gs["player_name"]   = manager_name
    gs["week"]          = 1
    gs["month"]         = 1
    gs["year"]          = year
    gs["news"]          = []
    gs["save_id"]       = str(uuid.uuid4())[:8]

    save_state(gs)
    return build_game_state(gs)


def handle_get_state():
    gs = load_state()
    if gs is None:
        return {"has_game": False, "week": 0, "month": 1, "year": 2025,
                "season_phase": "", "budget": 0, "roster_size": 0,
                "academy_size": 0, "form": [], "season": None}
    return build_game_state(gs)


def handle_advance_week():
    gs = load_state()
    if gs is None:
        return {"error": "No active game"}

    from engine.calendar_engine import advance_time
    from engine.simulation_engine import simulate_world_week

    news_before = len(gs.get("news", []))
    events      = advance_time(gs)
    simulate_world_week(gs)

    # Collect new news items
    all_news     = gs.get("news", [])
    new_news_raw = all_news[news_before:] if news_before < len(all_news) else all_news[-5:]

    org_id         = gs.get("player_org_id")
    player_results = []
    other_results  = []

    for e in events:
        if not isinstance(e, dict) or "winner" not in e:
            continue
        team_a_id = e.get("team_a", "")
        team_b_id = e.get("team_b", "")
        is_player = (team_a_id == org_id or team_b_id == org_id)

        score_str = e.get("score", "0-0")
        parts     = score_str.split("-")
        try:
            score_a = int(parts[0])
            score_b = int(parts[1]) if len(parts) > 1 else 0
        except (ValueError, IndexError):
            score_a, score_b = 0, 0

        # Resolve team names — the match result includes them directly
        team_a_name = e.get("team_a_name",
                            gs["orgs"].get(team_a_id, {}).get("name", team_a_id))
        team_b_name = e.get("team_b_name",
                            gs["orgs"].get(team_b_id, {}).get("name", team_b_id))
        winner_id   = e.get("winner", "")

        result = {
            "tournament_name": e.get("tournament_name", ""),
            "team_a":          team_a_name,
            "team_b":          team_b_name,
            "team_a_id":       team_a_id,
            "team_b_id":       team_b_id,
            "score_a":         score_a,
            "score_b":         score_b,
            "winner":          winner_id,
            "is_player_match": is_player,
            "maps":            [],
            "week":            gs.get("week", 1),
        }
        if is_player:
            player_results.append(result)
        else:
            other_results.append(result)

    all_results = player_results + other_results[:12]

    new_news = []
    for i, n in enumerate(new_news_raw[:20]):
        new_news.append({
            "id":        f"n{gs.get('week',1)}-{i}",
            "headline":  n.get("headline", ""),
            "category":  n.get("category", "general"),
            "week":      n.get("week",  gs.get("week",  1)),
            "month":     n.get("month", gs.get("month", 1)),
            "year":      n.get("year",  gs.get("year",  2025)),
            "timestamp": f"Week {n.get('week',1)}, {n.get('year',2025)}",
        })

    org     = gs["orgs"].get(org_id, {})
    org_name = org.get("name", "")
    if player_results:
        r        = player_results[0]
        score_str = f"{r['score_a']}-{r['score_b']}"
        won = (r["winner"] == org_id)
        opp = r["team_b"] if r["team_a_id"] == org_id else r["team_a"]
        if won:
            week_summary = f"Victory! {org_name} {score_str} {opp}"
        else:
            week_summary = f"Defeat. {org_name} {score_str} {opp}"
    else:
        week_summary = (f"Week {gs.get('week', 1)} complete — "
                        f"{len(all_results)} matches played worldwide.")

    save_state(gs)
    return {
        "state":         build_game_state(gs),
        "match_results": all_results,
        "new_news":      new_news,
        "week_summary":  week_summary,
    }


def handle_get_roster():
    gs = load_state()
    if gs is None:
        return {"error": "No active game"}

    org_id = gs.get("player_org_id")
    org    = gs["orgs"].get(org_id, {})

    roster  = [build_player_card(gs, pid, False)
               for pid in org.get("roster", [])]
    academy = [build_player_card(gs, pid, True)
               for pid in org.get("academy", [])]
    roster  = [p for p in roster  if p]
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
        "roster":    roster,
        "academy":   academy,
        "budget":    org.get("budget", 0),
        "chemistry": chem,
        "pressure":  pres,
    }


def handle_release_player(player_id):
    gs = load_state()
    if gs is None:
        return {"error": "No active game"}

    org_id = gs.get("player_org_id")
    org    = gs["orgs"].get(org_id, {})
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
        p["status"] = "free_agent"

    save_state(gs)
    return handle_get_roster()


def handle_sign_player(player_id):
    gs = load_state()
    if gs is None:
        return {"error": "No active game"}

    org_id = gs.get("player_org_id")
    org    = gs["orgs"].get(org_id, {})
    roster = org.get("roster", [])

    if len(roster) >= 10:
        return {"error": "Roster full (max 10 players)"}

    p = gs["players"].get(player_id, {})
    if not p:
        return {"error": "Player not found"}
    if p.get("org_id"):
        return {"error": "Player is already on a team — use Transfer instead"}

    # Use the engine's sign logic
    from engine.transfer_engine import sign_player
    success = sign_player(org, p, gs)
    if not success:
        from engine.economy_engine import transfer_fee
        fee = transfer_fee(p)
        budget = org.get("budget", 0)
        return {"error": (f"Cannot sign — need ${fee // 4:,} signing bonus "
                          f"(budget: ${budget:,}) or roster is full")}

    save_state(gs)
    return handle_get_roster()


def handle_transfer_player(player_id):
    """Buy a player from another org (club-to-club transfer)."""
    gs = load_state()
    if gs is None:
        return {"error": "No active game"}

    org_id  = gs.get("player_org_id")
    to_org  = gs["orgs"].get(org_id)
    p       = gs["players"].get(player_id)

    if not p:
        return {"error": "Player not found"}
    if p.get("org_id") == org_id:
        return {"error": "Player is already on your team"}
    if not p.get("org_id"):
        return {"error": "Player is a free agent — use Sign instead"}

    from_org = gs["orgs"].get(p["org_id"])
    if not from_org:
        return {"error": "Player's current org not found"}

    from engine.transfer_engine import transfer_player as do_transfer
    from engine.economy_engine import transfer_fee

    fee    = transfer_fee(p)
    budget = to_org.get("budget", 0)
    if budget < fee:
        return {"error": f"Insufficient budget — transfer fee is ${fee:,}, you have ${budget:,}"}

    success = do_transfer(from_org, to_org, p, gs)
    if not success:
        return {"error": "Transfer failed — roster may be full"}

    save_state(gs)
    return {
        "success":     True,
        "player_name": p.get("nickname", ""),
        "fee":         fee,
        "roster":      handle_get_roster(),
    }


def handle_promote_player(player_id):
    gs = load_state()
    if gs is None:
        return {"error": "No active game"}

    org_id  = gs.get("player_org_id")
    org     = gs["orgs"].get(org_id, {})
    roster  = org.get("roster", [])
    academy = org.get("academy", [])

    if player_id not in academy:
        return {"error": "Player not in academy"}
    if len(roster) >= 10:
        return {"error": "Roster full (max 10 players)"}

    academy.remove(player_id)
    roster.append(player_id)
    org["academy"] = academy
    org["roster"]  = roster

    p = gs["players"].get(player_id, {})
    if p:
        p["is_academy"] = False
        p["status"]     = "starter"

    save_state(gs)
    return handle_get_roster()


def handle_get_news():
    gs = load_state()
    if gs is None:
        return []

    result = []
    for i, n in enumerate(reversed(gs.get("news", [])[-50:])):
        result.append({
            "id":        f"news-{i}",
            "headline":  n.get("headline", ""),
            "category":  n.get("category", "general"),
            "week":      n.get("week",  1),
            "month":     n.get("month", 1),
            "year":      n.get("year",  2025),
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
    player_rank = None
    for i, (oid, pts) in enumerate(rankings[:30]):
        org = gs["orgs"].get(oid, {})
        result.append({
            "rank":          i + 1,
            "org_id":        oid,
            "name":          org.get("name", ""),
            "tag":           org.get("tag", ""),
            "region":        org.get("region", ""),
            "points":        int(pts),
            "is_player_org": oid == org_id,
        })
        if oid == org_id:
            player_rank = i + 1

    # If player org is outside top 30, append it
    if player_rank is None and org_id:
        from engine.ranking_engine import get_rank
        player_rank = get_rank(gs, org_id)
        if player_rank:
            player_org = gs["orgs"].get(org_id, {})
            pts = 0
            for oid, p in rankings:
                if oid == org_id:
                    pts = p
                    break
            result.append({
                "rank":          player_rank,
                "org_id":        org_id,
                "name":          player_org.get("name", ""),
                "tag":           player_org.get("tag", ""),
                "region":        player_org.get("region", ""),
                "points":        int(pts),
                "is_player_org": True,
            })
    return result


def handle_get_transfers():
    """Return free agents and contracted players for the transfer market."""
    gs = load_state()
    if gs is None:
        return {"free_agents": [], "contracted": []}

    org_id  = gs.get("player_org_id")
    my_org  = gs["orgs"].get(org_id, {})

    from engine.economy_engine import transfer_fee

    free_agents = []
    contracted  = []

    for pid, p in gs["players"].items():
        if p.get("retired") or p.get("is_academy", False):
            continue
        p_org = p.get("org_id")
        if p_org == org_id:
            continue

        card = build_player_card(gs, pid, False)
        if not card:
            continue

        if not p_org:
            free_agents.append(card)
        else:
            from_org = gs["orgs"].get(p_org, {})
            fee      = transfer_fee(p)
            card["current_org"]     = from_org.get("name", "")
            card["current_org_tag"] = from_org.get("tag", "")
            card["transfer_fee"]    = fee
            card["can_afford"]      = my_org.get("budget", 0) >= fee
            contracted.append(card)

    free_agents.sort(key=lambda p: -p["rating"])
    contracted.sort(key=lambda p: -p["rating"])

    return {
        "free_agents": free_agents[:50],
        "contracted":  contracted[:40],
    }


def handle_get_fixtures():
    """Return upcoming unplayed matches involving the player's org."""
    gs = load_state()
    if gs is None:
        return []

    org_id   = gs.get("player_org_id")
    fixtures = []

    for tid, t in gs.get("tournaments", {}).items():
        if not isinstance(t, dict):
            continue
        if t.get("status") not in ("ongoing", "upcoming"):
            continue
        if org_id not in t.get("participants", []):
            continue

        for match in t.get("bracket", []):
            if match.get("played"):
                continue
            if match.get("team_a") != org_id and match.get("team_b") != org_id:
                continue

            opp_id   = match["team_b"] if match["team_a"] == org_id else match["team_a"]
            opp      = gs["orgs"].get(opp_id, {})
            rnd      = match.get("round")
            rnd_label = f"Round {rnd}" if rnd else "Group Stage"
            fixtures.append({
                "tournament_id":   tid,
                "tournament_name": t.get("name", ""),
                "opponent_name":   opp.get("name", "Unknown"),
                "opponent_tag":    opp.get("tag", "?"),
                "week":            gs.get("week", 1) + 1,
                "month":           gs.get("month", 1),
                "is_home":         match.get("team_a") == org_id,
                "round":           rnd_label,
            })

    fixtures.sort(key=lambda f: f["week"])
    return fixtures[:10]


def handle_get_results():
    """Return past match results for the player's org from org match_history."""
    gs = load_state()
    if gs is None:
        return []

    org_id   = gs.get("player_org_id")
    org      = gs["orgs"].get(org_id, {})
    org_name = org.get("name", "")
    history  = org.get("match_history", [])   # newest-first list

    results = []
    for r in history[:12]:
        score_str = r.get("score", "0-0")
        parts     = score_str.split("-")
        is_win    = r.get("result") == "W"
        try:
            maps_won  = int(parts[0])
            maps_lost = int(parts[1]) if len(parts) > 1 else 0
        except (ValueError, IndexError):
            maps_won, maps_lost = 0, 0

        opponent = r.get("opponent", "?")
        # Score is always stored from org's perspective (our score first)
        # So parts[0] is our score, parts[1] is opponent's score
        results.append({
            "tournament_name": f"Week {r.get('month', 1)}/{r.get('year', 2025)}",
            "team_a":          org_name,
            "team_b":          opponent,
            "score_a":         maps_won,
            "score_b":         maps_lost,
            "winner":          org_name if is_win else opponent,
            "is_player_match": True,
            "maps":            [],
            "week":            r.get("month", 1),
        })
    return results[:10]


def handle_get_calendar():
    """Return calendar data: active league standings, upcoming events, season phase."""
    gs = load_state()
    if gs is None:
        return {"error": "No active game"}

    from config import SEASON_PHASES
    from utils.time_utils import phase_for_month
    from engine.calendar_engine import upcoming_events

    org_id = gs.get("player_org_id")
    org    = gs["orgs"].get(org_id, {})
    region = org.get("region", "europe")
    year   = gs.get("year", 2025)
    month  = gs.get("month", 1)
    week   = gs.get("week", 1)

    phase       = phase_for_month(month) or "break"
    phase_label = SEASON_PHASES.get(phase, {}).get("label", phase.title())

    # ── Phase progress ─────────────────────────────────────────────────────
    phase_months = SEASON_PHASES.get(phase, {}).get("months", [month])
    if phase_months and len(phase_months) > 1:
        elapsed       = (month - phase_months[0]) * 4 + week
        total_weeks   = len(phase_months) * 4
        phase_progress = round(min(1.0, elapsed / total_weeks), 2)
    else:
        phase_progress = 0.5

    # ── Player's active regional league ───────────────────────────────────
    player_league = None
    league_key    = f"league_{region}_{phase}_{year}"
    league        = gs["tournaments"].get(league_key)

    if league and isinstance(league, dict) and league.get("status") != "completed":
        results_map     = league.get("results", {})
        standings_order = league.get("standings", [])

        if not standings_order:
            standings_order = sorted(
                results_map.keys(),
                key=lambda o: (-results_map[o].get("points", 0),
                               -results_map[o].get("wins", 0))
            ) or league.get("participants", [])

        standings = []
        for rank, oid in enumerate(standings_order[:16], 1):
            r  = results_map.get(oid, {"wins": 0, "losses": 0, "points": 0})
            o  = gs["orgs"].get(oid, {})
            standings.append({
                "rank":      rank,
                "org_id":    oid,
                "name":      o.get("name", ""),
                "tag":       o.get("tag", ""),
                "wins":      r.get("wins", 0),
                "losses":    r.get("losses", 0),
                "map_diff":  r.get("map_wins", 0) - r.get("map_losses", 0),
                "points":    r.get("points", 0),
                "is_player": oid == org_id,
            })

        # Also show orgs in league not yet in results (haven't played)
        for oid in league.get("participants", []):
            if not any(s["org_id"] == oid for s in standings):
                o = gs["orgs"].get(oid, {})
                standings.append({
                    "rank": len(standings) + 1,
                    "org_id": oid,
                    "name": o.get("name", ""),
                    "tag": o.get("tag", ""),
                    "wins": 0, "losses": 0, "map_diff": 0, "points": 0,
                    "is_player": oid == org_id,
                })

        standings.sort(key=lambda s: (-s["points"], -s["map_diff"]))
        for i, s in enumerate(standings):
            s["rank"] = i + 1

        my_record = results_map.get(org_id, {"wins": 0, "losses": 0, "points": 0})

        # Upcoming matches for player in this league
        upcoming_matches = []
        for m in league.get("bracket", []):
            if m.get("played"):
                continue
            if m.get("team_a") == org_id or m.get("team_b") == org_id:
                opp_id = m["team_b"] if m["team_a"] == org_id else m["team_a"]
                opp    = gs["orgs"].get(opp_id, {})
                upcoming_matches.append({
                    "opponent_name": opp.get("name", "Unknown"),
                    "opponent_tag":  opp.get("tag", "?"),
                })

        player_league = {
            "id":               league_key,
            "name":             league.get("name", ""),
            "status":           league.get("status", ""),
            "standings":        standings[:16],
            "player_record":    my_record,
            "upcoming_matches": upcoming_matches[:3],
            "total_matches":    len(league.get("bracket", [])),
            "played_matches":   sum(1 for m in league.get("bracket", []) if m.get("played")),
        }

    # ── Global upcoming events text ────────────────────────────────────────
    try:
        upcoming_list = upcoming_events(gs)
    except Exception:
        upcoming_list = []

    # ── Active non-regional tournaments ───────────────────────────────────
    active_tournaments = []
    for tid, t in gs.get("tournaments", {}).items():
        if not isinstance(t, dict):
            continue
        if t.get("status") == "ongoing" and t.get("type") not in ("regional",):
            active_tournaments.append({
                "id":     tid,
                "name":   t.get("name", ""),
                "type":   t.get("type", ""),
                "winner": t.get("winner"),
            })

    # Season progress
    season_data = None
    try:
        from engine.season_engine import get_season_progress
        season_data = get_season_progress(gs, None)
    except Exception:
        pass

    # Pipeline stage info
    pipeline_stage = None
    try:
        from engine.season_engine import get_current_cycle
        cid, cycle = get_current_cycle(gs)
        if cycle:
            league_status = "upcoming"
            if cycle.get("league") and isinstance(cycle["league"], dict):
                league_status = "completed" if all(
                    l.get("status") == "completed" for l in cycle["league"].values()
                ) else "ongoing"
            pipeline_stage = {
                "cycle": cid,
                "cycle_status": cycle["status"],
                "league_status": league_status,
                "playoff_status": "upcoming",
                "major_status": "upcoming",
            }
            if cycle.get("playoffs"):
                pipeline_stage["playoff_status"] = "completed" if all(
                    p.get("status") == "completed" for p in cycle["playoffs"].values()
                ) else "ongoing"
            if cycle.get("major") and isinstance(cycle["major"], dict):
                pipeline_stage["major_status"] = cycle["major"].get("status", "upcoming")
    except Exception:
        pass

    return {
        "current_phase":       phase_label,
        "phase_key":           phase,
        "phase_progress":      phase_progress,
        "upcoming_events":     upcoming_list,
        "player_league":       player_league,
        "active_tournaments":  active_tournaments[:5],
        "week_label":          gs.get("current_date",
                                      f"Week {week}, {year}"),
        "season":              season_data,
        "pipeline_stage":      pipeline_stage,
    }


def handle_list_orgs_initial():
    """Generate a mini world just for org selection."""
    from main import generate_world
    gs   = generate_world(2025)
    orgs = [org_summary(org, oid) for oid, org in gs["orgs"].items()]
    orgs.sort(key=lambda x: (-x["rating"], x["name"]))
    return orgs


# ─── Main dispatcher ──────────────────────────────────────────────────────────

def main():
    raw = sys.stdin.read()

    # Redirect stdout → stderr so game module prints don't corrupt JSON output
    real_stdout = sys.stdout
    sys.stdout  = sys.stderr

    try:
        payload = json.loads(raw)
    except Exception as e:
        sys.stdout = real_stdout
        print(json.dumps({"error": f"Invalid JSON input: {e}"}))
        return

    action = payload.get("action")
    data   = payload.get("data", {})

    try:
        if action == "list_orgs":
            gs     = load_state()
            result = handle_list_orgs(gs) if gs else handle_list_orgs_initial()

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

        elif action == "transfer_player":
            result = handle_transfer_player(data.get("player_id", ""))

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

        elif action == "get_calendar":
            result = handle_get_calendar()

        else:
            result = {"error": f"Unknown action: {action}"}

    except Exception as e:
        result = {"error": str(e), "trace": traceback.format_exc()}

    sys.stdout = real_stdout
    print(json.dumps(result))


if __name__ == "__main__":
    main()
