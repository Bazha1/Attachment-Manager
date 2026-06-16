"""
Calendar Engine — THE core driver of the simulation.
advance_week() is the single entry point that triggers everything.
"""
import random
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (SEASON_PHASES, LEAGUE_SIZE, REGIONS, MAJORS,
                    MAJOR_SLOTS_BY_REGION, TI_TOTAL_TEAMS, TI_QUALIFIER_SLOTS,
                    MAJOR_PRIZE_POOL, TI_PRIZE_POOL, MAJOR_TOTAL_TEAMS,
                    SEASON_CYCLES)
from utils.time_utils import (advance_week, is_league_month,
                               league_round_for_week, phase_for_month, date_str)
from systems.tournament_system import (
    create_tournament, init_rr_results, record_rr_match, finalize_rr,
    generate_se_bracket, advance_se, init_swiss, swiss_pair,
    record_swiss_match, get_swiss_pools
)
from engine.match_engine import simulate_match
from engine.ranking_engine import update_ranking_points, update_org_ranking_points
from engine.economy_engine import apply_monthly_financials, prize_distribution, renew_sponsor
from engine.season_engine import (
    init_season_state, record_league_result, record_playoff_result,
    record_major_result, record_ti_qual_result, record_ti_result,
    get_season, get_season_progress
)
from systems.team_system import record_result, update_reputation, update_era, reset_season
from systems.news_system import (news_tournament_winner, news_match_upset,
                                 news_relegation, news_promotion, news_major_qualified)


# ─── Week Advancement ─────────────────────────────────────────────────────

def advance_time(gs: dict) -> list:
    """
    Advance one week. Triggers all calendar events for that week.
    Returns list of result dicts (match results, announcements, etc.)
    """
    events_log = []

    # 1. Ensure season state exists
    y = gs.get("year", 2025)
    if not gs.get("seasons"):
        init_season_state(gs, y)
        gs["current_season"] = y
    # If year changed and current season isn't complete, keep current_season
    # pointing to the active season year. This prevents season data from
    # resetting when the calendar rolls into January.

    # 2. Advance calendar
    gs["year"], gs["month"], gs["week"] = advance_week(
        gs["year"], gs["month"], gs["week"])

    y, m, w = gs["year"], gs["month"], gs["week"]
    gs["current_date"] = date_str(y, m, w)

    # 3. Check and trigger scheduled events
    events_log += _check_calendar_events(gs)

    # 4. Monthly tasks (first week of each month)
    if w == 1:
        _monthly_tasks(gs)

    return events_log


def _check_calendar_events(gs: dict) -> list:
    y, m, w = gs["year"], gs["month"], gs["week"]
    log = []

    phase = phase_for_month(m)

    # ── Regional League matches ────────────────────────────────────────────
    if phase in ("winter", "spring", "summer"):
        for region in REGIONS:
            key = f"league_{region}_{phase}_{y}"
            tourn = gs["tournaments"].get(key)
            if tourn is None:
                tourn = _create_league(gs, region, phase, y, m)
                gs["tournaments"][key] = tourn
            if tourn["status"] == "upcoming":
                init_rr_results(tourn)
            if tourn["status"] == "ongoing":
                log += _run_league_week(gs, tourn, region)

        # Finalise league at last week of last month in phase
        phase_months = SEASON_PHASES[phase]["months"]
        if m == phase_months[-1] and w == 4:
            for region in REGIONS:
                key = f"league_{region}_{phase}_{y}"
                tourn = gs["tournaments"].get(key)
                if tourn and tourn["status"] == "ongoing":
                    log += _finalise_league(gs, tourn, region)

    # ── Regional Playoffs (auto-created by season pipeline after league) ──
    for tourn in list(gs["tournaments"].values()):
        if tourn.get("type") == "tier2" and "Playoffs" in tourn.get("name", ""):
            if tourn["status"] == "ongoing":
                log += _run_se_tournament(gs, tourn)

    # ── Majors (auto-created by season pipeline after playoffs) ────────────
    for tourn in list(gs["tournaments"].values()):
        if tourn.get("type") == "major" and tourn["status"] == "ongoing":
            log += _run_se_tournament(gs, tourn)

    # ── Legacy: create majors from schedule if pipeline hasn't created them ──
    for major_def in MAJORS:
        if m == major_def["month"] and w == major_def["week"]:
            # Check if pipeline already created this major
            pipeline_major = None
            for t in gs["tournaments"].values():
                if t.get("type") == "major" and str(y) in t.get("name", ""):
                    pipeline_major = t
                    break
            if pipeline_major:
                log += _run_se_tournament(gs, pipeline_major)
            else:
                key = f"major_{major_def['name'].replace(' ','_')}_{y}"
                if key not in gs["tournaments"]:
                    tourn = _create_major(gs, major_def, y)
                    if tourn:
                        gs["tournaments"][key] = tourn
                        log += _run_se_tournament(gs, tourn)

    # ── TI Qualifiers (auto-created by season pipeline after all cycles) ──
    for tourn in list(gs["tournaments"].values()):
        if tourn.get("type") == "tier2" and "Qualifier" in tourn.get("name", ""):
            if tourn["status"] == "ongoing":
                log += _run_se_tournament(gs, tourn)

    # ── Legacy TI Qualification (Nov W1) ──────────────────────────────────
    qual_exists = any(
        t.get("type") == "tier2" and "Qualifier" in t.get("name", "")
        for t in gs["tournaments"].values()
    )
    if m == 11 and w == 1 and not qual_exists:
        key = f"ti_qual_{y}"
        if key not in gs["tournaments"]:
            log += _run_ti_qualifiers(gs, y)

    # ── The International (auto-created by season pipeline after qualifiers) ─
    for tourn in list(gs["tournaments"].values()):
        if tourn.get("type") == "ti" and tourn["status"] == "ongoing":
            if "Playoffs" in tourn.get("name", ""):
                log += _run_se_tournament(gs, tourn)
            else:
                log += _run_ti_swiss(gs, tourn)

    # ── Legacy: The International (Dec W2) ───────────────────────────────
    ti_exists = any(
        t.get("type") == "ti" and not "Playoffs" in t.get("name", "")
        for t in gs["tournaments"].values()
    )
    if m == 12 and w == 2 and not ti_exists:
        key = f"ti_{y}"
        if key not in gs["tournaments"]:
            log += _run_ti(gs, y)

    # ── Tier 2 filler events ──────────────────────────────────────────────
    if phase == "break" and w in (1, 3):
        log += _run_tier2_events(gs, y, m)

    return log


def _monthly_tasks(gs: dict) -> None:
    """Tasks that happen at the start of each month."""
    for org in gs["orgs"].values():
        apply_monthly_financials(org, gs["players"])
        renew_sponsor(org, gs["year"])
        update_era(org)
    update_org_ranking_points(gs)


# ─── Regional League ──────────────────────────────────────────────────────

def _create_league(gs: dict, region: str, phase: str,
                   year: int, month: int) -> dict:
    from engine.ranking_engine import regional_rankings
    ranked = regional_rankings(gs, region)
    # Top 16 by ranking (or all if fewer than 16)
    participants = [o["id"] for o in ranked[:LEAGUE_SIZE]]
    # Pad with random eligible orgs if needed
    all_region = [o["id"] for o in gs["orgs"].values()
                  if o["region"] == region and o["id"] not in participants]
    random.shuffle(all_region)
    while len(participants) < LEAGUE_SIZE and all_region:
        participants.append(all_region.pop())
    # Ensure player team is included in their region's league
    player_org_id = gs.get("player_org_id")
    if player_org_id:
        player_org = gs["orgs"].get(player_org_id)
        if player_org and player_org.get("region") == region:
            if player_org_id not in participants:
                if len(participants) >= LEAGUE_SIZE:
                    # Remove the lowest-ranked team to make room
                    participants = participants[:LEAGUE_SIZE - 1]
                participants.append(player_org_id)
    # Mark them as in league
    for oid in participants:
        gs["orgs"][oid]["in_league"] = True
    tourn = create_tournament(
        f"{region.title()} {phase.title()} League {year}",
        "regional", "1", region, year, month, participants
    )
    return tourn


def _run_league_week(gs: dict, tourn: dict, region: str) -> list:
    log = []
    unplayed = [m for m in tourn["bracket"] if not m["played"]]
    if not unplayed:
        return log
    # Play up to 4 matches per week
    matches_this_week = unplayed[:4]
    for m in matches_this_week:
        oid_a, oid_b = m["team_a"], m["team_b"]
        org_a = gs["orgs"].get(oid_a)
        org_b = gs["orgs"].get(oid_b)
        if not org_a or not org_b:
            m["played"] = True
            continue
        result = simulate_match(org_a, org_b, gs["players"],
                                match_format="bo3",
                                tournament_tier="regional",
                                year=gs["year"], month=gs["month"])
        w_id = result["winner"]
        l_id = result["loser"]
        sa = int(result["score"].split("-")[0])
        sb = int(result["score"].split("-")[1])
        record_rr_match(tourn, oid_a, oid_b, w_id,
                        sa if w_id == oid_a else sb,
                        sb if w_id == oid_a else sa)
        update_ranking_points(gs, w_id, 80, gs["year"], gs["month"])
        update_ranking_points(gs, l_id, 20, gs["year"], gs["month"])
        w_org = gs["orgs"][w_id]
        l_org = gs["orgs"][l_id]
        # Winner's score from result dict (parts[0] for winner, parts[1] for loser)
        score_parts = result["score"].split("-")
        w_score = score_parts[0]
        l_score = score_parts[1] if len(score_parts) > 1 else "0"
        record_result(w_org, "W", gs["orgs"][l_id]["name"],
                      f"{w_score}-{l_score}", gs["year"], gs["month"])
        record_result(l_org, "L", gs["orgs"][w_id]["name"],
                      f"{l_score}-{w_score}", gs["year"], gs["month"])
        update_reputation(w_org, "W", "regional")
        update_reputation(l_org, "L", "regional")
        # Detect upset (lower-ranked team beats higher)
        if w_org.get("ranking_position", 99) > l_org.get("ranking_position", 1) + 10:
            news_match_upset(gs, w_org["name"], l_org["name"],
                             tourn["name"])
        result["tournament_name"] = tourn["name"]
        log.append(result)
    return log


def _finalise_league(gs: dict, tourn: dict, region: str) -> list:
    log = []
    info = finalize_rr(tourn)
    standings = info["standings"]
    # Prize distribution
    prize_distribution(tourn, standings, gs["orgs"])
    # Ranking bonus for top performers
    for i, oid in enumerate(standings[:3]):
        pts = [800, 400, 200][i]
        update_ranking_points(gs, oid, pts, gs["year"], gs["month"])
    # Trophies for winner
    winner_id = standings[0] if standings else None
    if winner_id:
        gs["orgs"][winner_id]["trophies"].append({
            "name": tourn["name"], "year": gs["year"]})
        news_tournament_winner(gs, gs["orgs"][winner_id]["name"], tourn["name"])
    # Relegation
    player_org_id = gs.get("player_org_id")
    for oid in standings[-3:]:
        # Skip player team from relegation
        if oid == player_org_id:
            continue
        gs["orgs"][oid]["in_league"] = False
        news_relegation(gs, gs["orgs"][oid]["name"], region)
    # Qualification for next Major (top N teams)
    slots = MAJOR_SLOTS_BY_REGION.get(region, 3)
    gs.setdefault("major_qualified", {})
    phase = _current_phase(gs)
    major_key = f"major_{phase}_{gs['year']}"
    gs["major_qualified"].setdefault(major_key, [])
    for oid in standings[:slots]:
        if oid not in gs["major_qualified"][major_key]:
            gs["major_qualified"][major_key].append(oid)
            news_major_qualified(gs, gs["orgs"][oid]["name"],
                                  f"Major ({phase.title()})")
    # Reset season stats
    for oid in tourn["participants"]:
        org = gs["orgs"].get(oid)
        if org:
            reset_season(org)
    log.append({"type": "league_end", "tournament": tourn["name"],
                "standings": standings[:5]})

    # Season pipeline: record league result and trigger next stage
    pipeline_log = record_league_result(gs, tourn)
    log.extend(pipeline_log)

    return log


# ─── Major ────────────────────────────────────────────────────────────────

def _create_major(gs: dict, major_def: dict, year: int) -> dict | None:
    # Gather qualified teams from the just-finished league cycle
    phase_map = {4: "winter", 7: "spring", 11: "summer"}
    phase = phase_map.get(major_def["month"], "winter")
    major_key = f"major_{phase}_{year}"
    qualified = gs.get("major_qualified", {}).get(major_key, [])
    # Fill remaining slots randomly from region rankings
    if len(qualified) < MAJOR_TOTAL_TEAMS:
        from engine.ranking_engine import compute_rankings
        ranked = compute_rankings(gs)
        for oid, _ in ranked:
            if oid not in qualified:
                qualified.append(oid)
            if len(qualified) >= MAJOR_TOTAL_TEAMS:
                break
    if len(qualified) < 4:
        return None
    tourn = create_tournament(
        major_def["name"] + f" {year}", "major", "1", None,
        year, major_def["month"], qualified[:MAJOR_TOTAL_TEAMS],
        prize_pool=MAJOR_PRIZE_POOL
    )
    tourn["bracket"] = generate_se_bracket(tourn["participants"])
    tourn["current_round"] = 1
    tourn["status"] = "ongoing"
    return tourn


def _run_se_tournament(gs: dict, tourn: dict) -> list:
    """Run an entire SE tournament to completion."""
    log = []
    max_rounds = 8
    for _ in range(max_rounds):
        pending = [m for m in tourn["bracket"]
                   if m.get("round") == tourn.get("current_round") and not m["played"]]
        if not pending:
            new_matches = advance_se(tourn)
            if not new_matches:
                break
            pending = new_matches
        for m in pending:
            if not m["team_a"] or not m["team_b"]:
                m["played"] = True
                m["winner"] = m["team_a"] or m["team_b"]
                continue
            org_a = gs["orgs"].get(m["team_a"])
            org_b = gs["orgs"].get(m["team_b"])
            if not org_a or not org_b:
                continue
            result = simulate_match(org_a, org_b, gs["players"],
                                    match_format="bo3",
                                    tournament_tier=tourn["type"],
                                    year=gs["year"], month=gs["month"])
            m["played"] = True
            m["winner"] = result["winner"]
            m["loser"]  = result["loser"]
            m["score"]  = result["score"]
            w_org = gs["orgs"][result["winner"]]
            l_org = gs["orgs"][result["loser"]]
            # Store scores from each org's perspective
            score_parts = result["score"].split("-")
            w_score = score_parts[0]
            l_score = score_parts[1] if len(score_parts) > 1 else "0"
            record_result(w_org, "W", l_org["name"],
                          f"{w_score}-{l_score}", gs["year"], gs["month"])
            record_result(l_org, "L", w_org["name"],
                          f"{l_score}-{w_score}", gs["year"], gs["month"])
            pts_table = {
                "ti": (2000, 300), "major": (1200, 200), "tier2": (150, 30)
            }.get(tourn["type"], (50, 10))
            update_ranking_points(gs, result["winner"], pts_table[0],
                                   gs["year"], gs["month"])
            update_ranking_points(gs, result["loser"], pts_table[1],
                                   gs["year"], gs["month"])
            result["tournament_name"] = tourn["name"]
            log.append(result)
        if tourn["status"] == "completed":
            break

    if tourn.get("winner"):
        w_org = gs["orgs"].get(tourn["winner"])
        if w_org:
            w_org["trophies"].append({"name": tourn["name"], "year": gs["year"]})
            w_org["achievements"] = w_org.get("achievements", [])
            news_tournament_winner(gs, w_org["name"], tourn["name"])
    # Prize distribution
    finished = [m["loser"] for m in tourn["bracket"] if m.get("played") and m.get("loser")]
    standings = [tourn["winner"]] + list(reversed(finished)) if tourn.get("winner") else []
    prize_distribution(tourn, standings, gs["orgs"])

    # Season pipeline: record tournament completion
    if tourn["type"] == "major" and tourn["status"] == "completed":
        pipeline_log = record_major_result(gs, tourn)
        log.extend(pipeline_log)
    elif tourn["type"] == "tier2" and "Qualifier" in tourn.get("name", ""):
        pipeline_log = record_ti_qual_result(gs, tourn)
        log.extend(pipeline_log)
    elif tourn["type"] == "tier2" and "Playoffs" in tourn.get("name", ""):
        pipeline_log = record_playoff_result(gs, tourn)
        log.extend(pipeline_log)
    elif tourn["type"] == "ti" and "Playoffs" in tourn.get("name", "") and tourn["status"] == "completed":
        # TI playoff finished — record final TI result and mark main TI as completed
        record_ti_result(gs, tourn)
        # The main TI tournament is stored separately; mark it completed too
        for main_t in gs["tournaments"].values():
            if main_t.get("type") == "ti" and not "Playoffs" in main_t.get("name", ""):
                main_t["status"] = "completed"
        log.append({"type": "ti_completed", "tournament": tourn["name"]})

    return log


# ─── TI Qualifiers ────────────────────────────────────────────────────────

def _run_ti_qualifiers(gs: dict, year: int) -> list:
    log = []
    gs.setdefault("ti_qualified", [])
    # Add top 16 from season rankings as direct invites
    from engine.ranking_engine import compute_rankings
    ranked = compute_rankings(gs)
    direct = [oid for oid, _ in ranked[:16]]
    gs["ti_qualified"] = direct[:]
    # One qualifier per region
    for region in REGIONS:
        region_orgs = [o for o in gs["orgs"].values()
                       if o["region"] == region and o["id"] not in gs["ti_qualified"]]
        region_orgs.sort(key=lambda o: o.get("ranking_points", 0), reverse=True)
        candidates = [o["id"] for o in region_orgs[:8]]
        if len(candidates) < 2:
            continue
        tourn = create_tournament(
            f"TI {year} {region.title()} Qualifier",
            "tier2", "2", region, year, 11, candidates
        )
        tourn["bracket"] = generate_se_bracket(candidates)
        tourn["current_round"] = 1
        tourn["status"] = "ongoing"
        qual_log = _run_se_tournament(gs, tourn)
        log.extend(qual_log)
        if tourn.get("winner") and tourn["winner"] not in gs["ti_qualified"]:
            gs["ti_qualified"].append(tourn["winner"])
            news_major_qualified(gs, gs["orgs"][tourn["winner"]]["name"],
                                  f"The International {year}")
        gs["tournaments"][f"ti_qual_{region}_{year}"] = tourn
    gs["tournaments"][f"ti_qual_{year}"] = {"status": "completed"}
    return log


# ─── The International ───────────────────────────────────

def _run_ti_swiss(gs: dict, tourn: dict) -> list:
    """Run Swiss stage for TI. Returns updated log."""
    log = []
    year = tourn["year"]
    if tourn.get("swiss_init"):
        return log
    init_swiss(tourn)
    tourn["swiss_init"] = True
    for _ in range(8):
        pools = get_swiss_pools(tourn)
        if not pools:
            break
        pairs = swiss_pair(pools)
        for a_id, b_id in pairs:
            org_a = gs["orgs"].get(a_id)
            org_b = gs["orgs"].get(b_id)
            if not org_a or not org_b:
                continue
            result = simulate_match(org_a, org_b, gs["players"],
                                    match_format="bo3",
                                    tournament_tier="ti",
                                    pressure_a=70, pressure_b=70,
                                    year=gs["year"], month=gs["month"])
            rec = record_swiss_match(tourn, result["winner"], result["loser"])
            record_result(gs["orgs"][result["winner"]], "W",
                          gs["orgs"][result["loser"]]["name"],
                          result["score"], gs["year"], gs["month"])
            record_result(gs["orgs"][result["loser"]], "L",
                          gs["orgs"][result["winner"]]["name"],
                          result["score"], gs["year"], gs["month"])
            result["tournament_name"] = tourn["name"]
            log.append(result)
        tourn["current_round"] += 1
    playoff_teams = tourn.get("swiss_advanced", [])
    if len(playoff_teams) >= 2:
        playoff = create_tournament(
            f"TI {year} Playoffs", "ti", "1", None,
            year, 12, playoff_teams, prize_pool=TI_PRIZE_POOL
        )
        playoff["bracket"] = generate_se_bracket(playoff_teams)
        playoff["current_round"] = 1
        playoff["status"] = "ongoing"
        gs["tournaments"][f"ti_{year}_playoffs"] = playoff
    return log


def _run_ti(gs: dict, year: int) -> list:
    """Legacy full TI run."""
    log = []
    qualified = gs.get("ti_qualified", [])[:TI_TOTAL_TEAMS]
    if len(qualified) < 4:
        return log
    tourn = create_tournament(
        f"The International {year}", "ti", "1", None,
        year, 12, qualified, prize_pool=TI_PRIZE_POOL
    )
    log += _run_ti_swiss(gs, tourn)
    gs["tournaments"][f"ti_{year}"] = tourn
    playoff = gs["tournaments"].get(f"ti_{year}_playoffs")
    if playoff and playoff["status"] == "ongoing":
        log += _run_se_tournament(gs, playoff)
        winner_id = playoff.get("winner")
    else:
        winner_id = None
    if winner_id:
        w_org = gs["orgs"].get(winner_id)
        if w_org:
            w_org["trophies"].append({"name": f"The International {year}", "year": year})
            news_tournament_winner(gs, w_org["name"], f"The International {year}")
        tourn["winner"] = winner_id
    record_ti_result(gs, tourn)
    all_teams = (tourn.get("swiss_advanced", []) +
                 list(reversed(tourn.get("swiss_eliminated", []))))
    standings = [winner_id] + [t for t in all_teams if t != winner_id] if winner_id else all_teams
    prize_distribution(tourn, standings, gs["orgs"])
    return log

# ─── Tier 2 Filler Events ─────────────────────────────────────────────────

def _run_tier2_events(gs: dict, year: int, month: int) -> list:
    log = []
    for region in REGIONS:
        # Pick 8 orgs that aren't in the main league
        candidates = [o for o in gs["orgs"].values()
                      if o["region"] == region and not o.get("in_league")]
        candidates.sort(key=lambda o: o.get("ranking_points", 0), reverse=True)
        candidates = candidates[:8]
        if len(candidates) < 2:
            continue
        tourn = create_tournament(
            f"{region.title()} Invitational {year}-{month}",
            "tier2", "2", region, year, month,
            [o["id"] for o in candidates]
        )
        tourn["bracket"] = generate_se_bracket(tourn["participants"])
        tourn["current_round"] = 1
        tourn["status"] = "ongoing"
        log += _run_se_tournament(gs, tourn)
        gs["tournaments"][f"t2_{region}_{year}_{month}"] = tourn
    return log


# ─── Helpers ──────────────────────────────────────────────────────────────

def _current_phase(gs: dict) -> str:
    from utils.time_utils import phase_for_month
    return phase_for_month(gs["month"]) or "break"


def upcoming_events(gs: dict, weeks_ahead: int = 4) -> list:
    """Return a list of expected upcoming event descriptions."""
    y, m, w = gs["year"], gs["month"], gs["week"]
    events = []
    phase = _current_phase(gs)
    if phase in ("winter", "spring", "summer"):
        events.append(f"Regional Leagues active ({SEASON_PHASES[phase]['label']})")
    for major_def in MAJORS:
        if m == major_def["month"] and w <= major_def["week"]:
            events.append(f"→ {major_def['name']} begins W{major_def['week']}")
    if m == 11:
        events.append("→ TI Qualification phase")
    if m == 12:
        events.append("→ The International")
    return events
