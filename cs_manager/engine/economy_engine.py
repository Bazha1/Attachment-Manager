"""Economy — budgets, salaries, sponsorships, prize money."""
import random
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SPONSOR_TYPES


def monthly_income(org: dict) -> int:
    return org.get("sponsor_income", 0)


def monthly_expenses(org: dict, players: dict) -> int:
    total = 0
    for pid in org.get("roster", []) + org.get("bench", []) + org.get("academy", []):
        p = players.get(pid)
        if p:
            total += p["contract"].get("salary", 0)
    # Coaching staff placeholder
    total += 3_000
    return total


def apply_monthly_financials(org: dict, players: dict) -> int:
    income  = monthly_income(org)
    expense = monthly_expenses(org, players)
    net = income - expense
    org["budget"] = org.get("budget", 0) + net
    return net


def award_prize(org: dict, amount: int) -> None:
    org["budget"] = org.get("budget", 0) + amount
    org.setdefault("prize_money_total", 0)
    org["prize_money_total"] += amount


def prize_distribution(tournament: dict, standings: list, orgs: dict) -> dict:
    """
    Distribute prize pool to top finishers.
    Returns {org_id: amount} dict.
    """
    pool = tournament.get("prize_pool", 0)
    if not pool or not standings:
        return {}
    # Split: 40% to winner, 20% to 2nd, 15% to 3rd/4th, rest split among rest
    splits = [0.40, 0.20, 0.10, 0.10]
    remaining = 1.0 - sum(splits)
    rest_each = remaining / max(len(standings) - len(splits), 1)
    distribution: dict = {}
    for i, oid in enumerate(standings):
        pct = splits[i] if i < len(splits) else rest_each
        amt = int(pool * pct)
        distribution[oid] = amt
        org = orgs.get(oid)
        if org:
            award_prize(org, amt)
    return distribution


def renew_sponsor(org: dict, current_year: int) -> bool:
    """Check and renew expiring sponsors; possibly attract new ones."""
    sponsors = org.get("sponsors", [])
    renewed = False
    for sp in sponsors:
        if sp.get("expiry_year", 9999) <= current_year:
            # 60% chance to renew with a raise
            if random.random() < 0.60:
                sp["income"] = int(sp["income"] * random.uniform(1.0, 1.20))
                sp["expiry_year"] = current_year + random.randint(1, 3)
                renewed = True
            else:
                sp["income"] = 0  # lost sponsor
    # Recalculate total sponsor income
    org["sponsor_income"] = sum(sp["income"] for sp in sponsors)
    # Chance to attract a new sponsor for high-reputation orgs
    if org.get("reputation", 50) >= 70 and random.random() < 0.15:
        stype = random.choice(["conservative", "ambitious"])
        income = int(random.gauss(SPONSOR_TYPES[stype]["income_base"],
                                   SPONSOR_TYPES[stype]["income_base"] * 0.2))
        sponsors.append({
            "name": f"New Sponsor {current_year}",
            "type": stype,
            "income": max(0, income),
            "expectations": SPONSOR_TYPES[stype]["expectations"],
            "expiry_year": current_year + random.randint(1, 2),
        })
        org["sponsor_income"] += max(0, income)
    return renewed


def transfer_fee(player: dict) -> int:
    return player.get("market_value", 50_000)


def can_afford(org: dict, amount: int) -> bool:
    return org.get("budget", 0) >= amount


def spend(org: dict, amount: int) -> bool:
    if can_afford(org, amount):
        org["budget"] -= amount
        return True
    return False
