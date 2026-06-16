"""
Season Engine — Pipeline for tournament progression.

Pipeline: League → Regional Playoffs → Major → (repeat 3x) → TI Qual → TI

Each stage automatically triggers the next when completed.
Season performance is tracked across all stages for TI qualification.
"""
import random
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    SEASON_LEAGUE_POINTS, SEASON_PLAYOFF_POINTS, SEASON_MAJOR_POINTS,
    SEASON_TI_POINTS, REGIONAL_PLAYOFF_SIZE, REGIONS, MAJORS,
    MAJOR_TOTAL_TEAMS, MAJOR_SLOTS_BY_REGION, TI_TOTAL_TEAMS,
    SEASON_CYCLES, MAJOR_PRIZE_POOL, TI_PRIZE_POOL
)
from systems.tournament_system import (
    create_tournament, generate_se_bracket, finalize_rr
)
from systems.news_system import news_major_qualified


# ─── Season State Management ─────────────────────────────────────────────────

def init_season_state(gs: dict, year: int) -> None:
    """Initialize season tracking for a new year."""
    gs.setdefault("seasons", {})
    gs["seasons"][year] = {
        "year": year,
        "cycles": {
            "cycle_1": {"status": "upcoming", "league": None, "playoffs": {}, "major": None},
            "cycle_2": {"status": "upcoming", "league": None, "playoffs": {}, "major": None},
            "cycle_3": {"status": "upcoming", "league": None, "playoffs": {}, "major": None},
        },
        "ti_qual": {"status": "upcoming", "tournament": None},
        "ti": {"status": "upcoming", "tournament": None},
        "org_totals": {},   # org_id → {league:0, playoff:0, major:0, ti:0, total:0}
    }
    gs.setdefault("current_season", year)


def get_season(gs: dict, year: int | None = None) -> dict | None:
    """Get season state for a year, or current season."""
    year = year or gs.get("current_season", gs.get("year", 2025))
    seasons = gs.get("seasons", {})
    # JSON keys may be strings after save/load
    if year in seasons:
        return seasons[year]
    return seasons.get(str(year))


def get_current_cycle(gs: dict) -> tuple[str, dict]:
    """Return (cycle_id, cycle_info) for the current in-progress cycle."""
    season = get_season(gs)
    if not season:
        return "", {}
    for cid, cycle in season["cycles"].items():
        if cycle["status"] in ("ongoing", "upcoming"):
            return cid, cycle
    # All cycles done, check TI
    if season["ti_qual"]["status"] in ("ongoing", "upcoming"):
        return "ti_qual", season["ti_qual"]
    if season["ti"]["status"] in ("ongoing", "upcoming"):
        return "ti", season["ti"]
    return "", {}


def _season_total_key(tournament: dict) -> str:
    """Infer cycle id from tournament name or id."""
    name = tournament.get("name", "").lower()
    tid = tournament.get("id", "").lower()
    combined = name + " " + tid
    if "winter" in combined or "cycle_1" in combined:
        return "cycle_1"
    if "spring" in combined or "cycle_2" in combined:
        return "cycle_2"
    if "summer" in combined or "cycle_3" in combined:
        return "cycle_3"
    return ""


# ─── Stage 1: Regional League Results ─────────────────────────────────

def record_league_result(gs: dict, tournament: dict) -> list:
    """
    Called when a regional league is finalized.
    Records standings, awards season points, and triggers playoffs.
    Returns list of news/announcements.
    """
    log = []
    year = tournament["year"]
    season = get_season(gs, year)
    if not season:
        return log

    region = tournament.get("region", "")
    standings = tournament.get("standings", [])
    cycle_id = _season_total_key(tournament)
    if not cycle_id:
        return log

    # Store league reference
    cycle = season["cycles"][cycle_id]
    if cycle["league"] is None:
        cycle["league"] = {}
    cycle["league"][region] = {
        "tournament_id": tournament["id"],
        "standings": standings,
        "status": "completed",
    }
    cycle["status"] = "ongoing"

    # Award season points
    for i, oid in enumerate(standings):
        points = SEASON_LEAGUE_POINTS[i] if i < len(SEASON_LEAGUE_POINTS) else 0
        season["org_totals"].setdefault(oid, {
            "league": 0, "playoff": 0, "major": 0, "ti": 0, "total": 0
        })
        season["org_totals"][oid]["league"] += points
        season["org_totals"][oid]["total"] += points

    # Check if all regional leagues for this cycle are done
    if len(cycle["league"]) >= len(REGIONS):
        all_done = all(l.get("status") == "completed" for l in cycle["league"].values())
        if all_done:
            # Auto-create regional playoffs
            for reg in REGIONS:
                league_info = cycle["league"].get(reg)
                if league_info:
                    playoff = create_regional_playoffs(gs, reg, cycle_id, year)
                    if playoff:
                        cycle["playoffs"][reg] = {
                            "tournament_id": playoff["id"],
                            "status": "ongoing",
                        }
                        gs["tournaments"][playoff["id"]] = playoff
                        log.append({
                            "type": "playoff_created",
                            "region": reg,
                            "cycle": cycle_id,
                            "tournament_id": playoff["id"],
                        })
    return log


# ─── Stage 2: Regional Playoffs ─────────────────────────────────────────

def create_regional_playoffs(gs: dict, region: str, cycle_id: str, year: int) -> dict | None:
    """
    Create a regional playoff after the league completes.
    Top 8 teams from the league advance.
    """
    season = get_season(gs, year)
    if not season:
        return None
    cycle = season["cycles"][cycle_id]
    league_info = cycle["league"].get(region)
    if not league_info:
        return None

    standings = league_info.get("standings", [])
    playoff_teams = standings[:REGIONAL_PLAYOFF_SIZE]
    if len(playoff_teams) < 2:
        return None

    phase_name = cycle_id.replace("cycle_", "Cycle ")
    tourn = create_tournament(
        f"{region.title()} {phase_name} Playoffs {year}",
        "tier2", "2", region, year, _playoff_month_for_cycle(cycle_id),
        playoff_teams, prize_pool=50_000
    )
    tourn["bracket"] = generate_se_bracket(playoff_teams)
    tourn["current_round"] = 1
    tourn["status"] = "ongoing"
    return tourn


def _playoff_month_for_cycle(cycle_id: str) -> int:
    """Return the month when playoffs should happen."""
    cycle_map = {"cycle_1": 4, "cycle_2": 7, "cycle_3": 11}
    return cycle_map.get(cycle_id, 1)


def record_playoff_result(gs: dict, tournament: dict) -> list:
    """
    Called when a regional playoff is completed.
    Records top performers, awards season points.
    """
    log = []
    year = tournament["year"]
    season = get_season(gs, year)
    if not season:
        return log

    # Find which cycle this belongs to
    cycle_id = ""
    for cid, cycle in season["cycles"].items():
        for reg, info in cycle.get("playoffs", {}).items():
            if info.get("tournament_id") == tournament["id"]:
                cycle_id = cid
                info["status"] = "completed"
                info["standings"] = _extract_se_standings(tournament)
                break
        if cycle_id:
            break

    if not cycle_id:
        return log

    # Award season points for playoff performance
    standings = _extract_se_standings(tournament)
    for i, oid in enumerate(standings):
        points = SEASON_PLAYOFF_POINTS[i] if i < len(SEASON_PLAYOFF_POINTS) else 0
        season["org_totals"].setdefault(oid, {
            "league": 0, "playoff": 0, "major": 0, "ti": 0, "total": 0
        })
        season["org_totals"][oid]["playoff"] += points
        season["org_totals"][oid]["total"] += points

    # Check if all regional playoffs for this cycle are done
    cycle = season["cycles"][cycle_id]
    all_done = all(p.get("status") == "completed" for p in cycle["playoffs"].values())
    if all_done and len(cycle["playoffs"]) >= len(REGIONS):
        # Auto-create major
        major = create_major_from_playoffs(gs, cycle_id, year)
        if major:
            cycle["major"] = {
                "tournament_id": major["id"],
                "status": "ongoing",
            }
            gs["tournaments"][major["id"]] = major
            log.append({
                "type": "major_created",
                "cycle": cycle_id,
                "tournament_id": major["id"],
                "name": major["name"],
            })
    return log


def _extract_se_standings(tournament: dict) -> list:
    """Extract standings from a single-elimination tournament."""
    winner = tournament.get("winner")
    if not winner:
        return []
    # Build standings from bracket: winner first, then losers in reverse round order
    standings = [winner]
    # Collect losers by round (higher round = later elimination = better standing)
    round_losers: dict[int, list] = {}
    for m in tournament.get("bracket", []):
        if m.get("played") and m.get("loser"):
            rd = m.get("round", 1)
            round_losers.setdefault(rd, []).append(m["loser"])
    # Add in reverse round order (last round losers first)
    for rd in sorted(round_losers.keys(), reverse=True):
        for loser in round_losers[rd]:
            if loser not in standings:
                standings.append(loser)
    return standings


# ─── Stage 3: Major Tournament ─────────────────────────────────────────────

def create_major_from_playoffs(gs: dict, cycle_id: str, year: int) -> dict | None:
    """
    Create a Major tournament from regional playoff winners.
    Top 4 from each regional playoff qualify.
    """
    season = get_season(gs, year)
    if not season:
        return None
    cycle = season["cycles"][cycle_id]

    qualified = []
    for reg, info in cycle.get("playoffs", {}).items():
        t = gs["tournaments"].get(info.get("tournament_id", ""))
        if t:
            standings = _extract_se_standings(t)
            qualified.extend(standings[:4])

    # Remove duplicates, fill from global rankings if needed
    seen = set()
    unique = []
    for oid in qualified:
        if oid and oid not in seen:
            seen.add(oid)
            unique.append(oid)
    qualified = unique

    if len(qualified) < MAJOR_TOTAL_TEAMS:
        from engine.ranking_engine import compute_rankings
        ranked = compute_rankings(gs)
        for oid, _ in ranked:
            if oid not in seen:
                seen.add(oid)
                qualified.append(oid)
            if len(qualified) >= MAJOR_TOTAL_TEAMS:
                break

    if len(qualified) < 4:
        return None

    # Find major definition
    major_def = None
    for md in MAJORS:
        cycle_map = {"cycle_1": "winter", "cycle_2": "spring", "cycle_3": "summer"}
        if md.get("after_phase") == cycle_map.get(cycle_id):
            major_def = md
            break

    if not major_def:
        return None

    tourn = create_tournament(
        major_def["name"] + f" {year}",
        "major", "1", None,
        year, major_def["month"], qualified[:MAJOR_TOTAL_TEAMS],
        prize_pool=MAJOR_PRIZE_POOL
    )
    tourn["bracket"] = generate_se_bracket(tourn["participants"])
    tourn["current_round"] = 1
    tourn["status"] = "ongoing"
    return tourn


def record_major_result(gs: dict, tournament: dict) -> list:
    """
    Called when a Major is completed.
    Records results, awards season points, triggers next cycle.
    """
    log = []
    year = tournament["year"]
    season = get_season(gs, year)
    if not season:
        return log

    # Find which cycle this major belongs to
    cycle_id = ""
    for cid, cycle in season["cycles"].items():
        major_info = cycle.get("major")
        if major_info and major_info.get("tournament_id") == tournament["id"]:
            cycle_id = cid
            major_info["status"] = "completed"
            major_info["standings"] = _extract_se_standings(tournament)
            break

    if not cycle_id:
        return log

    # Award season points
    standings = _extract_se_standings(tournament)
    for i, oid in enumerate(standings):
        points = SEASON_MAJOR_POINTS[i] if i < len(SEASON_MAJOR_POINTS) else 0
        season["org_totals"].setdefault(oid, {
            "league": 0, "playoff": 0, "major": 0, "ti": 0, "total": 0
        })
        season["org_totals"][oid]["major"] += points
        season["org_totals"][oid]["total"] += points

    # Mark cycle as completed
    season["cycles"][cycle_id]["status"] = "completed"

    # Check if all 3 cycles are done
    all_cycles_done = all(c["status"] == "completed" for c in season["cycles"].values())
    if all_cycles_done:
        # Trigger TI qualification
        ti_qual = create_ti_qual_from_season(gs, year)
        if ti_qual:
            season["ti_qual"]["status"] = "ongoing"
            season["ti_qual"]["tournament"] = ti_qual
            for t in ti_qual:
                gs["tournaments"][t["id"]] = t
            log.append({
                "type": "ti_qual_created",
                "year": year,
            })

    return log


# ─── Stage 4: TI Qualification ─────────────────────────────────────────────

def create_ti_qual_from_season(gs: dict, year: int) -> list:
    """
    Create TI qualification based on season performance.
    Top 16 by season total points get direct invites.
    Regional qualifiers for 4 additional spots.
    """
    season = get_season(gs, year)
    if not season:
        return []

    # Calculate standings by season total points
    totals = sorted(
        season["org_totals"].items(),
        key=lambda x: x[1]["total"],
        reverse=True
    )

    # Direct invites (top 16)
    direct = [oid for oid, _ in totals[:16]]
    gs["ti_qualified"] = direct[:]

    tournaments = []
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
        tournaments.append(tourn)
    return tournaments


def record_ti_qual_result(gs: dict, tournament: dict) -> list:
    """Record a TI qualifier result."""
    log = []
    year = tournament["year"]
    season = get_season(gs, year)
    if not season:
        return log

    winner = tournament.get("winner")
    if winner and winner not in gs.get("ti_qualified", []):
        gs["ti_qualified"].append(winner)
        news_major_qualified(gs, gs["orgs"][winner]["name"],
                             f"The International {year}")

    # Check if all qualifiers are done
    qual_tourns = [t for t in gs["tournaments"].values()
                   if t.get("name", "").startswith(f"TI {year}") and "Qualifier" in t.get("name", "")]
    if all(t.get("status") == "completed" for t in qual_tourns):
        # Trigger TI — only if not already created
        ti_exists = any(
            t.get("type") == "ti" and not "Playoffs" in t.get("name", "")
            for t in gs["tournaments"].values()
        )
        if not ti_exists:
            ti = create_ti_from_qual(gs, year)
            if ti:
                season["ti"]["status"] = "ongoing"
                season["ti"]["tournament"] = ti
                gs["tournaments"][ti["id"]] = ti
                log.append({
                    "type": "ti_created",
                    "year": year,
                    "tournament_id": ti["id"],
                })
    return log


# ─── Stage 5: The International ─────────────────────────────────────────────

def create_ti_from_qual(gs: dict, year: int) -> dict | None:
    """Create The International tournament."""
    from config import TI_TOTAL_TEAMS, TI_PRIZE_POOL
    qualified = gs.get("ti_qualified", [])[:TI_TOTAL_TEAMS]
    if len(qualified) < 4:
        return None
    tourn = create_tournament(
        f"The International {year}", "ti", "1", None,
        year, 12, qualified, prize_pool=TI_PRIZE_POOL
    )
    return tourn


def record_ti_result(gs: dict, tournament: dict) -> None:
    """Record TI results and award season points."""
    year = tournament["year"]
    season = get_season(gs, year)
    if not season:
        return

    season["ti"]["status"] = "completed"
    season["ti"]["standings"] = _extract_se_standings(tournament)

    # Award TI season points
    standings = _extract_se_standings(tournament)
    for i, oid in enumerate(standings):
        points = SEASON_TI_POINTS[i] if i < len(SEASON_TI_POINTS) else 0
        season["org_totals"].setdefault(oid, {
            "league": 0, "playoff": 0, "major": 0, "ti": 0, "total": 0
        })
        season["org_totals"][oid]["ti"] += points
        season["org_totals"][oid]["total"] += points


# ─── Helpers ──────────────────────────────────────────────────────────────

def get_season_standings(gs: dict, year: int | None = None) -> list:
    """Return orgs sorted by season total points for a year."""
    season = get_season(gs, year)
    if not season:
        return []
    totals = sorted(
        season["org_totals"].items(),
        key=lambda x: x[1]["total"],
        reverse=True
    )
    return [(oid, data["total"]) for oid, data in totals]


def get_org_season_performance(gs: dict, org_id: str, year: int | None = None) -> dict:
    """Return season performance breakdown for a single org."""
    season = get_season(gs, year)
    if not season:
        return {"league": 0, "playoff": 0, "major": 0, "ti": 0, "total": 0}
    return season["org_totals"].get(org_id, {
        "league": 0, "playoff": 0, "major": 0, "ti": 0, "total": 0
    })


def get_season_progress(gs: dict, year: int | None = None) -> dict:
    """Return overall season progress for UI display."""
    season = get_season(gs, year)
    if not season:
        return {}

    cycles_done = sum(1 for c in season["cycles"].values() if c["status"] == "completed")
    total_cycles = len(season["cycles"])

    return {
        "year": season["year"],
        "cycles_completed": cycles_done,
        "cycles_total": total_cycles,
        "ti_qual_status": season["ti_qual"]["status"],
        "ti_status": season["ti"]["status"],
        "current_phase": _get_phase_label(season),
    }


def _get_phase_label(season: dict) -> str:
    """Get human-readable current phase."""
    for cid, cycle in season["cycles"].items():
        if cycle["status"] in ("ongoing", "upcoming"):
            # Check sub-stages
            if cycle.get("league"):
                all_league_done = all(l.get("status") == "completed"
                                       for l in cycle["league"].values())
                if not all_league_done:
                    return f"{cid.replace('_', ' ').title()} League"
            if cycle.get("playoffs"):
                all_playoff_done = all(p.get("status") == "completed"
                                       for p in cycle["playoffs"].values())
                if not all_playoff_done:
                    return f"{cid.replace('_', ' ').title()} Playoffs"
            if cycle.get("major"):
                if cycle["major"].get("status") != "completed":
                    return f"{cid.replace('_', ' ').title()} Major"
            return f"{cid.replace('_', ' ').title()} League"
    if season["ti_qual"]["status"] in ("ongoing", "upcoming"):
        return "TI Qualification"
    if season["ti"]["status"] in ("ongoing", "upcoming"):
        return "The International"
    return "Season Complete"
