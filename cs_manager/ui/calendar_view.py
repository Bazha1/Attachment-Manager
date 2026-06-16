"""Calendar interface — displays current month and upcoming events."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TERMINAL_WIDTH, SEPARATOR, MONTHS, SEASON_PHASES
from utils.time_utils import month_name, phase_label
from ui.menu import _c, pause, header


def show_calendar(gs: dict) -> None:
    header(gs)
    y, m, w = gs["year"], gs["month"], gs["week"]

    print(_c("bold", "\n  ◈ CALENDAR VIEW\n"))
    print(f"  Current date : {_c('yellow', f'{month_name(m)} Week {w}, {y}')}")
    print(f"  Season phase : {_c('cyan', phase_label(m) or 'Off-season / Break')}")

    # ── Year timeline ────────────────────────────────────────────────────
    print(_c("dim", f"\n  {SEPARATOR}"))
    print(_c("bold", "  SEASON YEAR OVERVIEW"))
    print(_c("dim", f"  {SEPARATOR}"))
    timeline = [
        ("Jan–Mar", "Winter Regional Leagues"),
        ("Apr",     "Major 1"),
        ("Apr–Jun", "Spring Regional Leagues"),
        ("Jul",     "Major 2  |  Transfer Window"),
        ("Aug–Oct", "Summer Regional Leagues"),
        ("Nov",     "Major 3  |  TI Qualification"),
        ("Dec",     "The International"),
    ]
    for months_label, description in timeline:
        arrow = "►" if _in_current_range(m, months_label) else " "
        color = "yellow" if arrow == "►" else "white"
        print(f"  {_c('green', arrow)} {_c(color, months_label):<12} {description}")

    # ── Active tournaments ───────────────────────────────────────────────
    active = [t for t in gs["tournaments"].values()
              if isinstance(t, dict) and t.get("status") == "ongoing"]
    if active:
        print(_c("dim", f"\n  {SEPARATOR}"))
        print(_c("bold", f"  ACTIVE TOURNAMENTS ({len(active)})"))
        print(_c("dim", f"  {SEPARATOR}"))
        for t in active[:8]:
            print(f"    • {_c('cyan', t['name'])} "
                  f"[{t['type'].upper()}] "
                  f"Teams: {len(t.get('participants', []))}")

    # ── Upcoming events ──────────────────────────────────────────────────
    from engine.calendar_engine import upcoming_events
    upcoming = upcoming_events(gs)
    if upcoming:
        print(_c("dim", f"\n  {SEPARATOR}"))
        print(_c("bold", "  UPCOMING THIS MONTH"))
        print(_c("dim", f"  {SEPARATOR}"))
        for ev in upcoming:
            print(f"    {_c('yellow', '→')} {ev}")

    # ── Recent results ───────────────────────────────────────────────────
    porg = gs["orgs"].get(gs.get("player_org_id", ""))
    if porg:
        history = porg.get("match_history", [])[:5]
        if history:
            print(_c("dim", f"\n  {SEPARATOR}"))
            print(_c("bold", f"  {porg['name']} — RECENT RESULTS"))
            print(_c("dim", f"  {SEPARATOR}"))
            for h in history:
                color = "green" if h["result"] == "W" else "red"
                print(f"    {_c(color, h['result'])}  vs {h['opponent']:<30} "
                      f"{h['score']}  {month_name(h['month'])} {h['year']}")

    print()
    pause()


def _in_current_range(month: int, label: str) -> bool:
    ranges = {
        "Jan–Mar": (1, 3), "Apr": (4, 4), "Apr–Jun": (4, 6),
        "Jul": (7, 7), "Aug–Oct": (8, 10), "Nov": (11, 11), "Dec": (12, 12),
    }
    r = ranges.get(label)
    if r:
        return r[0] <= month <= r[1]
    return False
