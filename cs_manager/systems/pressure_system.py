"""Mental pressure and morale system."""
import random
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.stats_utils import clamp


def compute_pressure(org: dict, tournament_tier: str, is_playoff: bool = False) -> int:
    """
    Return a 0-100 pressure score for the org in a given situation.
    High pressure can hurt performance.
    """
    base = 30
    tier_bonus = {"ti": 40, "major": 25, "regional": 15, "tier2": 5, "tier3": 0}
    base += tier_bonus.get(tournament_tier, 0)
    if is_playoff:
        base += 10
    # Sponsor expectations
    expectations = org.get("sponsors", [{}])[0].get("expectations", "low")
    exp_bonus = {"high": 15, "medium": 8, "low": 3, "minimal": 0}
    base += exp_bonus.get(expectations, 0)
    # Reputation — high reputation orgs feel more pressure
    base += int(org.get("reputation", 50) / 10)
    return clamp(base, 0, 100)


def apply_pressure_to_player(player: dict, pressure: int) -> float:
    """
    Returns a performance multiplier (0.80–1.10) based on the player's
    tilt_resistance vs the situation pressure.
    """
    resistance = player["mental"].get("tilt_resistance", 60)
    net = pressure - resistance  # positive = hurts, negative = helps
    # Each 10 points of net pressure costs 2% performance
    modifier = 1.0 - (net / 10) * 0.02
    return clamp(modifier, 0.80, 1.10)


def update_mental_after_result(player: dict, result: str,
                                tournament_tier: str) -> None:
    """Adjust player mental stats after a match result."""
    delta_conf = {"W": random.randint(1, 4), "L": random.randint(-4, -1)}[result]
    delta_mot  = {"W": random.randint(0, 3), "L": random.randint(-3,  0)}[result]
    tier_mult  = {"ti": 2, "major": 1.5, "regional": 1.2, "tier2": 0.8, "tier3": 0.5}
    mult = tier_mult.get(tournament_tier, 1.0)
    player["mental"]["confidence"]    = clamp(
        int(player["mental"]["confidence"]    + delta_conf * mult), 0, 100)
    player["mental"]["motivation"]    = clamp(
        int(player["mental"]["motivation"]    + delta_mot * mult),  0, 100)


def update_org_morale(org: dict, result: str) -> None:
    morale = org.get("morale", 60)
    if result == "W":
        morale = min(100, morale + random.randint(2, 5))
    else:
        morale = max(0, morale - random.randint(2, 5))
    org["morale"] = morale
