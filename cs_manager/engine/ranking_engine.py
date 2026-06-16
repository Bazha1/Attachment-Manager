"""
HLTV-style world ranking system.
Updated monthly with time-decay on older results.
"""
import math
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import RANKING_HALF_LIFE, TOP_RANKING_SIZE


def _decay(months_ago: int) -> float:
    """Point decay factor for results `months_ago` months in the past."""
    return math.exp(-math.log(2) * months_ago / RANKING_HALF_LIFE)


def update_ranking_points(gs: dict, org_id: str, raw_points: int,
                          year: int, month: int) -> None:
    """Add a ranking points entry for the org."""
    rp = gs["ranking_history"].setdefault(org_id, [])
    rp.append({"year": year, "month": month, "points": raw_points})


def compute_rankings(gs: dict) -> list:
    """
    Compute current rankings for all orgs.
    Returns sorted list of (org_id, total_points) tuples.
    """
    cy, cm = gs["year"], gs["month"]
    scores: dict = {}
    for org_id, entries in gs["ranking_history"].items():
        total = 0.0
        for e in entries:
            ey, em = e["year"], e["month"]
            months_ago = (cy - ey) * 12 + (cm - em)
            if months_ago < 0:
                continue
            total += e["points"] * _decay(months_ago)
        scores[org_id] = total

    # Also include orgs with no points yet
    for oid in gs["orgs"]:
        scores.setdefault(oid, gs["orgs"][oid].get("ranking_points", 0))

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return ranked[:TOP_RANKING_SIZE]


def get_rank(gs: dict, org_id: str) -> int | None:
    """Return 1-based rank of org, or None if outside top 50."""
    ranking = compute_rankings(gs)
    for i, (oid, _) in enumerate(ranking):
        if oid == org_id:
            return i + 1
    return None


def update_org_ranking_points(gs: dict) -> None:
    """
    Called monthly — recompute and store each org's ranking_points.
    """
    ranking = compute_rankings(gs)
    for rank, (oid, pts) in enumerate(ranking, 1):
        org = gs["orgs"].get(oid)
        if org:
            org["ranking_points"] = int(pts)
            org["ranking_position"] = rank


def regional_rankings(gs: dict, region: str) -> list:
    """Return top orgs in a region, sorted by ranking_points."""
    orgs = [o for o in gs["orgs"].values() if o["region"] == region]
    orgs.sort(key=lambda o: o.get("ranking_points", 0), reverse=True)
    return orgs
