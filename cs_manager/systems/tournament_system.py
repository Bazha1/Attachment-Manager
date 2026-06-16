"""Tournament lifecycle: scheduling, bracket, results, promotion/relegation."""
import random
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (LEAGUE_SIZE, RELEGATION_SPOTS, PROMOTION_SPOTS,
                    MAJOR_SLOTS_BY_REGION, MAJOR_TOTAL_TEAMS,
                    TI_TOTAL_TEAMS, TI_QUALIFIER_SLOTS,
                    MAJOR_PRIZE_POOL, TI_PRIZE_POOL,
                    TOURNAMENT_POINTS, REGIONS)
from utils.random_utils import generate_id

_tid_counter = [0]


def create_tournament(name: str, ttype: str, tier: str,
                      region: str | None, year: int, month: int,
                      participants: list, prize_pool: int = 0) -> dict:
    tid = generate_id("t", _tid_counter)
    return {
        "id":           tid,
        "name":         name,
        "type":         ttype,   # "regional", "major", "ti", "tier2", "tier3"
        "tier":         tier,    # "1","2","3"
        "region":       region,
        "year":         year,
        "month":        month,
        "participants": participants,   # org IDs
        "results":      {},             # org_id -> {"wins","losses","points"}
        "standings":    [],             # ordered org IDs
        "bracket":      [],             # list of match dicts
        "current_round":0,
        "status":       "upcoming",     # upcoming / ongoing / completed
        "winner":       None,
        "prize_pool":   prize_pool or _default_prize(ttype),
        "point_key":    ttype if ttype in TOURNAMENT_POINTS else "tier3",
    }


def _default_prize(ttype: str) -> int:
    return {"ti": TI_PRIZE_POOL, "major": MAJOR_PRIZE_POOL,
            "regional": 100_000, "tier2": 25_000, "tier3": 5_000}.get(ttype, 5_000)


# ─── Round Robin (regional league) ──────────────────────────────────────────

def generate_rr_schedule(participants: list) -> list:
    """Return list of (team_a, team_b) pairs for a round-robin."""
    pairs = []
    n = len(participants)
    for i in range(n):
        for j in range(i + 1, n):
            pairs.append((participants[i], participants[j]))
    random.shuffle(pairs)
    return pairs


def init_rr_results(tournament: dict) -> None:
    for oid in tournament["participants"]:
        tournament["results"][oid] = {
            "wins": 0, "losses": 0, "map_wins": 0, "map_losses": 0, "points": 0
        }
    tournament["bracket"] = [
        {"team_a": a, "team_b": b, "played": False, "winner": None, "score": ""}
        for a, b in generate_rr_schedule(tournament["participants"])
    ]
    tournament["status"] = "ongoing"


def record_rr_match(tournament: dict, team_a: str, team_b: str,
                    winner: str, score_a: int, score_b: int) -> None:
    for m in tournament["bracket"]:
        if not m["played"] and {m["team_a"], m["team_b"]} == {team_a, team_b}:
            m["played"] = True
            m["winner"] = winner
            m["score"]  = f"{score_a}-{score_b}"
            break
    loser = team_b if winner == team_a else team_a
    r = tournament["results"]
    r[winner]["wins"]      += 1
    r[winner]["points"]    += 3
    r[winner]["map_wins"]  += score_a if winner == team_a else score_b
    r[winner]["map_losses"]+= score_b if winner == team_a else score_a
    r[loser]["losses"]     += 1
    r[loser]["map_wins"]   += score_b if winner == team_a else score_a
    r[loser]["map_losses"] += score_a if winner == team_a else score_b


def finalize_rr(tournament: dict) -> dict:
    """Sort standings, return dict with promoted/relegated lists."""
    results = tournament["results"]
    standings = sorted(
        results.keys(),
        key=lambda o: (results[o]["points"],
                       results[o]["map_wins"] - results[o]["map_losses"]),
        reverse=True,
    )
    tournament["standings"] = standings
    tournament["winner"]    = standings[0] if standings else None
    tournament["status"]    = "completed"

    promoted  = []
    relegated = []
    if tournament["type"] == "regional" and len(standings) >= LEAGUE_SIZE:
        relegated = standings[-RELEGATION_SPOTS:]

    return {"standings": standings, "promoted": promoted, "relegated": relegated}


# ─── Single Elimination ──────────────────────────────────────────────────────

def generate_se_bracket(participants: list) -> list:
    """Single elimination rounds. Participants already seeded/randomized."""
    import math
    size = len(participants)
    # Pad to power of 2
    byes = (2 ** math.ceil(math.log2(size))) - size
    padded = list(participants) + [None] * byes
    random.shuffle(padded[:size])
    matches = []
    for i in range(0, len(padded), 2):
        matches.append({
            "team_a":  padded[i],
            "team_b":  padded[i + 1] if i + 1 < len(padded) else None,
            "played":  padded[i + 1] is None,  # bye
            "winner":  padded[i] if padded[i + 1] is None else None,
            "score":   "BYE" if padded[i + 1] is None else "",
            "round":   1,
        })
    return matches


def advance_se(tournament: dict) -> list:
    """
    Collect winners from current round, generate next round.
    Returns list of next-round matchups or empty if final done.
    """
    current_round = tournament.get("current_round", 1)
    winners = [m["winner"] for m in tournament["bracket"]
               if m["round"] == current_round and m["winner"]]
    if len(winners) <= 1:
        if winners:
            tournament["winner"] = winners[0]
            tournament["status"] = "completed"
        return []
    next_round = current_round + 1
    new_matches = []
    for i in range(0, len(winners), 2):
        if i + 1 < len(winners):
            new_matches.append({
                "team_a": winners[i], "team_b": winners[i + 1],
                "played": False, "winner": None, "score": "", "round": next_round,
            })
    tournament["bracket"].extend(new_matches)
    tournament["current_round"] = next_round
    return new_matches


# ─── Swiss Stage (TI group) ──────────────────────────────────────────────────

def swiss_pair(pools: dict) -> list:
    """
    pools = {record_str: [org_id, ...]}  e.g. {"0-0": [...], "1-0": [...]}
    Returns list of (team_a, team_b) pairs.
    """
    pairs = []
    for record, teams in pools.items():
        shuffled = list(teams)
        random.shuffle(shuffled)
        for i in range(0, len(shuffled) - 1, 2):
            pairs.append((shuffled[i], shuffled[i + 1]))
    return pairs


def init_swiss(tournament: dict) -> None:
    tournament["swiss_records"] = {oid: [0, 0] for oid in tournament["participants"]}
    tournament["swiss_eliminated"] = []
    tournament["swiss_advanced"]   = []
    tournament["status"] = "ongoing"
    tournament["current_round"] = 0


def record_swiss_match(tournament: dict, winner: str, loser: str) -> dict:
    sr = tournament["swiss_records"]
    sr[winner][0] += 1
    sr[loser][1]  += 1
    result = {}
    # Check advance/eliminate (3 wins = advance, 3 losses = out)
    if sr[winner][0] >= 3 and winner not in tournament["swiss_advanced"]:
        tournament["swiss_advanced"].append(winner)
        result["advanced"] = winner
    if sr[loser][1] >= 3 and loser not in tournament["swiss_eliminated"]:
        tournament["swiss_eliminated"].append(loser)
        result["eliminated"] = loser
    return result


def get_swiss_pools(tournament: dict) -> dict:
    pools: dict = {}
    sr = tournament["swiss_records"]
    for oid, (w, l) in sr.items():
        if oid in tournament["swiss_advanced"] or oid in tournament["swiss_eliminated"]:
            continue
        key = f"{w}-{l}"
        pools.setdefault(key, []).append(oid)
    return pools
