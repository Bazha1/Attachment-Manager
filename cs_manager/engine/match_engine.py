"""
Core match simulation engine.
Matches are ONLY triggered by the calendar — never by direct user calls.
"""
import random
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ROUNDS_PER_HALF, MAX_ROUNDS, TOURNAMENT_POINTS
from utils.stats_utils import overall_rating, chemistry_bonus, pressure_modifier
from systems.player_system import record_match_stats
from systems.pressure_system import apply_pressure_to_player, update_mental_after_result
from systems.chemistry_system import evolve_chemistry


def _team_strength(org: dict, players: dict, pressure: int,
                   chemistry: int) -> float:
    roster_ids = org.get("roster", [])
    if not roster_ids:
        return 30.0
    squad = [players[pid] for pid in roster_ids if pid in players]
    if not squad:
        return 30.0
    base = sum(overall_rating(p["attributes"]) for p in squad) / len(squad)
    chem_mult = chemistry_bonus(chemistry)
    # Average pressure modifier across squad
    press_mult = sum(apply_pressure_to_player(p, pressure) for p in squad) / len(squad)
    return base * chem_mult * press_mult


def simulate_map(team_a_str: float, team_b_str: float) -> tuple[int, int, list]:
    """
    Simulate one CS map (up to 30 rounds + possible OT).
    Returns (score_a, score_b, key_events[]).
    """
    score_a = 0
    score_b = 0
    events = []
    total_rounds = 0
    # CT/T sides for first half; swap at half-time
    for half in range(2):
        rounds_this_half = 0
        while rounds_this_half < ROUNDS_PER_HALF and not _map_over(score_a, score_b, half):
            rounds_this_half += 1
            total_rounds += 1
            # Add momentum from round history
            momentum_a = min(1.15, 1.0 + (score_a - score_b) * 0.005)
            momentum_b = min(1.15, 1.0 + (score_b - score_a) * 0.005)
            eff_a = team_a_str * momentum_a
            eff_b = team_b_str * momentum_b
            prob_a = eff_a / (eff_a + eff_b)
            if random.random() < prob_a:
                score_a += 1
                if score_a in (15, 20, 25, 30) or abs(score_a - score_b) == 1:
                    events.append(f"R{total_rounds}: Team A wins crucial round ({score_a}-{score_b})")
            else:
                score_b += 1
                if score_b in (15, 20, 25, 30) or abs(score_b - score_a) == 1:
                    events.append(f"R{total_rounds}: Team B wins crucial round ({score_a}-{score_b})")
        # Swap sides
        team_a_str, team_b_str = team_b_str, team_a_str

    # Overtime if tied at 15-15
    if score_a == score_b:
        for _ in range(3):  # max 3 OT pairs (each OT = 6 rounds: first to 4)
            ot_a, ot_b = 0, 0
            for _ in range(6):
                prob_a = team_a_str / (team_a_str + team_b_str)
                if random.random() < prob_a:
                    ot_a += 1
                else:
                    ot_b += 1
                if ot_a == 4 or ot_b == 4:
                    break
            score_a += ot_a
            score_b += ot_b
            events.append(f"OVERTIME: {score_a}-{score_b}")
            if score_a != score_b:
                break
    return score_a, score_b, events


def _map_over(score_a: int, score_b: int, half: int) -> bool:
    if half == 0:
        return score_a >= ROUNDS_PER_HALF or score_b >= ROUNDS_PER_HALF
    return score_a >= 16 or score_b >= 16


def _gen_player_stats(squad: list, maps_played: int,
                      won: bool) -> list[dict]:
    """Generate per-player stats for a match."""
    stats = []
    for p in squad:
        ovr    = overall_rating(p["attributes"])
        rounds = maps_played * 24
        base_kpr = (ovr / 100) * 0.85
        kpr    = max(0.2, random.gauss(base_kpr, 0.12))
        dpr    = max(0.1, random.gauss(0.65, 0.1))
        kills  = int(kpr * rounds)
        deaths = int(dpr * rounds)
        adr    = random.gauss(75 + ovr * 0.3, 12)
        impact = random.gauss(0.7 + ovr / 200, 0.1)
        from utils.stats_utils import hltv_from_stats, performance_rating, clamp
        hltv   = hltv_from_stats(kills, deaths, rounds, adr, impact)
        clutches = random.randint(0, 3)
        op_kills = random.randint(0, 5)
        perf   = performance_rating(clutches, op_kills, random.randint(0, 4),
                                    1.0 + (0.5 if won else 0))
        perf   = float(clamp(perf, 0.0, 10.0))
        stats.append({
            "player_id":  p["id"],
            "nickname":   p["nickname"],
            "role":       p["role"],
            "kills":      kills,
            "deaths":     deaths,
            "adr":        round(adr, 1),
            "hltv":       hltv,
            "perf":       perf,
            "clutches":   clutches,
            "opening_k":  op_kills,
        })
    stats.sort(key=lambda s: s["hltv"], reverse=True)
    return stats


def simulate_match(org_a: dict, org_b: dict, players: dict,
                   match_format: str = "bo3",
                   tournament_tier: str = "tier2",
                   pressure_a: int = 30, pressure_b: int = 30,
                   verbose: bool = False) -> dict:
    """
    Full match simulation.  Returns a rich result dict.
    ONLY called from calendar/tournament events — never directly.
    """
    chemistry_a = org_a.get("chemistry", 50)
    chemistry_b = org_b.get("chemistry", 50)

    str_a = _team_strength(org_a, players, pressure_a, chemistry_a)
    str_b = _team_strength(org_b, players, pressure_b, chemistry_b)

    maps_to_play  = {"bo1": 1, "bo3": 2, "bo5": 3}.get(match_format, 2)
    maps_needed   = {"bo1": 1, "bo3": 2, "bo5": 3}.get(match_format, 2)

    maps_won_a, maps_won_b = 0, 0
    map_results   = []
    all_events    = []
    maps_played   = 0

    while maps_won_a < maps_needed and maps_won_b < maps_needed:
        sa, sb, evts = simulate_map(str_a, str_b)
        if sa > sb:
            maps_won_a += 1
        else:
            maps_won_b += 1
        map_results.append({"score_a": sa, "score_b": sb})
        all_events.extend(evts)
        maps_played += 1

    winner_id  = org_a["id"] if maps_won_a > maps_won_b else org_b["id"]
    loser_id   = org_b["id"] if winner_id == org_a["id"] else org_a["id"]
    winner_won = winner_id == org_a["id"]

    # Generate player stats
    squad_a = [players[pid] for pid in org_a.get("roster", []) if pid in players]
    squad_b = [players[pid] for pid in org_b.get("roster", []) if pid in players]
    stats_a = _gen_player_stats(squad_a, maps_played, winner_won)
    stats_b = _gen_player_stats(squad_b, maps_played, not winner_won)

    # Update player career stats
    for s in stats_a:
        p = players.get(s["player_id"])
        if p: record_match_stats(p, s["kills"], s["deaths"],
                                  maps_played * 24, s["hltv"], s["perf"])
    for s in stats_b:
        p = players.get(s["player_id"])
        if p: record_match_stats(p, s["kills"], s["deaths"],
                                  maps_played * 24, s["hltv"], s["perf"])

    # Update mental states
    result_a = "W" if winner_won else "L"
    result_b = "L" if winner_won else "W"
    for pid in org_a.get("roster", []):
        p = players.get(pid)
        if p: update_mental_after_result(p, result_a, tournament_tier)
    for pid in org_b.get("roster", []):
        p = players.get(pid)
        if p: update_mental_after_result(p, result_b, tournament_tier)

    # Update chemistry
    evolve_chemistry(org_a, result_a)
    evolve_chemistry(org_b, result_b)

    # Score string like "2-1"
    score_str = f"{maps_won_a}-{maps_won_b}"

    pts_table = TOURNAMENT_POINTS.get(tournament_tier, TOURNAMENT_POINTS["tier3"])
    if winner_won:
        rp_a = pts_table.get("win", 0)
        rp_b = pts_table.get("group", 0)
    else:
        rp_a = pts_table.get("group", 0)
        rp_b = pts_table.get("win", 0)

    return {
        "team_a":       org_a["id"],
        "team_a_name":  org_a["name"],
        "team_b":       org_b["id"],
        "team_b_name":  org_b["name"],
        "winner":       winner_id,
        "loser":        loser_id,
        "score":        score_str,
        "map_results":  map_results,
        "maps_played":  maps_played,
        "events":       all_events,
        "stats_a":      stats_a,
        "stats_b":      stats_b,
        "ranking_pts_a":rp_a,
        "ranking_pts_b":rp_b,
        "tournament_tier": tournament_tier,
    }


def mvp_of_match(result: dict) -> dict | None:
    """Return the player stat dict with highest HLTV from the winning team."""
    winner = result["winner"]
    stats  = result["stats_a"] if result["team_a"] == winner else result["stats_b"]
    return stats[0] if stats else None
