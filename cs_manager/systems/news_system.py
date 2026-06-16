"""Dynamic news generation."""
import random
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import NEWS_MAX_ITEMS


def _push(gs: dict, headline: str, category: str,
          year: int, month: int) -> None:
    item = {"headline": headline, "category": category,
            "year": year, "month": month}
    gs["news"].insert(0, item)
    gs["news"] = gs["news"][:NEWS_MAX_ITEMS]


def news_transfer(gs, player_nick: str, from_org: str, to_org: str) -> None:
    templates = [
        f"{player_nick} makes the move from {from_org} to {to_org}",
        f"BREAKING: {player_nick} signs with {to_org} from {from_org}",
        f"{to_org} acquires {player_nick} in major roster move",
        f"{from_org} parts ways with {player_nick} — joins {to_org}",
    ]
    _push(gs, random.choice(templates), "transfer", gs["year"], gs["month"])


def news_match_upset(gs, underdog: str, favourite: str, tournament: str) -> None:
    templates = [
        f"{underdog} shocks {favourite} in stunning {tournament} upset",
        f"GIANT KILLER: {underdog} eliminates top seed {favourite}",
        f"{tournament}: Nobody saw this coming — {underdog} over {favourite}",
    ]
    _push(gs, random.choice(templates), "upset", gs["year"], gs["month"])


def news_tournament_winner(gs, org_name: str, tournament_name: str) -> None:
    templates = [
        f"{org_name} claims the {tournament_name} championship",
        f"CHAMPIONS: {org_name} wins {tournament_name}",
        f"{org_name} crowned {tournament_name} winners after dominant run",
    ]
    _push(gs, random.choice(templates), "result", gs["year"], gs["month"])


def news_roster_change(gs, org_name: str, player_nick: str, action: str) -> None:
    if action == "dropped":
        msg = f"{org_name} drops {player_nick} from main roster"
    elif action == "promoted":
        msg = f"{player_nick} promoted to {org_name} main lineup from academy"
    else:
        msg = f"{org_name} announces roster change involving {player_nick}"
    _push(gs, msg, "roster", gs["year"], gs["month"])


def news_record(gs, record_type: str, subject: str, value: str) -> None:
    _push(gs,
          f"NEW RECORD: {subject} — {record_type} ({value})",
          "record", gs["year"], gs["month"])


def news_relegation(gs, org_name: str, region: str) -> None:
    _push(gs,
          f"{org_name} relegated from {region.title()} regional league",
          "relegation", gs["year"], gs["month"])


def news_promotion(gs, org_name: str, region: str) -> None:
    _push(gs,
          f"{org_name} earns promotion to {region.title()} regional league",
          "promotion", gs["year"], gs["month"])


def news_free_agent(gs, player_nick: str, org_name: str) -> None:
    _push(gs,
          f"{player_nick} becomes free agent after leaving {org_name}",
          "transfer", gs["year"], gs["month"])


def news_major_qualified(gs, org_name: str, major_name: str) -> None:
    _push(gs,
          f"{org_name} qualifies for {major_name}",
          "qualification", gs["year"], gs["month"])


def news_injury(gs, player_nick: str, org_name: str) -> None:
    _push(gs,
          f"{player_nick} ({org_name}) sidelined with injury",
          "injury", gs["year"], gs["month"])


def news_winning_streak(gs, org_name: str, count: int) -> None:
    _push(gs,
          f"{org_name} extends winning streak to {count} matches",
          "streak", gs["year"], gs["month"])


def latest_news(gs: dict, n: int = 10) -> list:
    return gs["news"][:n]
