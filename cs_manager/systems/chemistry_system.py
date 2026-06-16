"""Team chemistry calculation and evolution."""
import random
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.stats_utils import clamp


def compute_chemistry(org: dict, players: dict) -> int:
    """
    Compute a 0-100 chemistry score for the given org's main roster.
    Considers: time together, shared nationality, language similarity, recent form.
    """
    roster_ids = org.get("roster", [])
    if len(roster_ids) < 2:
        return 50

    squad = [players[pid] for pid in roster_ids if pid in players]
    if not squad:
        return 50

    base = 50

    # Shared nationalities
    nats = [p["nationality"] for p in squad]
    most_common_nat = max(set(nats), key=nats.count)
    nat_share = nats.count(most_common_nat) / len(nats)
    base += int(nat_share * 20)

    # Shared region (same region as org)
    region_match = sum(1 for p in squad if p["region"] == org["region"])
    base += int((region_match / len(squad)) * 10)

    # Existing chemistry stored in org
    stored = org.get("chemistry", base)

    # Blend stored with freshly computed
    result = int(stored * 0.7 + base * 0.3)
    return clamp(result, 0, 100)


def evolve_chemistry(org: dict, result: str, roster_changed: bool = False) -> None:
    """Update org chemistry after a match/event."""
    current = org.get("chemistry", 50)
    if roster_changed:
        # Roster change hurts chemistry
        delta = -random.randint(5, 15)
    elif result == "W":
        delta = random.randint(1, 4)
    else:
        delta = random.randint(-3, 0)
    org["chemistry"] = clamp(current + delta, 0, 100)


def chemistry_from_roster_change(org: dict) -> None:
    """Called whenever the roster is modified."""
    org["chemistry"] = max(0, org.get("chemistry", 50) - random.randint(5, 12))


def passive_chemistry_gain(org: dict) -> None:
    """Called monthly — long-term stability bonus."""
    current = org.get("chemistry", 50)
    if current < 80:
        org["chemistry"] = min(100, current + random.randint(0, 2))
