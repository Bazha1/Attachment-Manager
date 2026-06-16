"""Season Dashboard — macro overview of the current year."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import REGIONS, SEPARATOR
from ui.menu import _c, pause, header, print_table


def show_season_dashboard(gs: dict) -> None:
    header(gs)
    y = gs["year"]
    print(_c("bold", f"\n  ◈ SEASON {y} DASHBOARD\n"))

    # ── Phases ──────────────────────────────────────────────────────────
    phases = [
        ("Winter League",    "winter"),
        ("Spring League",    "spring"),
        ("Summer League",    "summer"),
        ("TI Qualification", "ti_qual"),
        ("The International","ti"),
    ]
    print(_c("dim", f"  {SEPARATOR}"))
    print(_c("bold", "  SEASON FLOW"))
    print(_c("dim", f"  {SEPARATOR}"))
    for label, phase_key in phases:
        # Find any completed tournament for this phase
        completed = [t for t in gs["tournaments"].values()
                     if isinstance(t, dict)
                     and t.get("year") == y
                     and _phase_matches(t, phase_key)
                     and t.get("status") == "completed"]
        if completed:
            t = completed[0]
            winner_name = gs["orgs"].get(t.get("winner"), {}).get("name", "—") if t.get("winner") else "—"
            status = _c("green", f"✓ {winner_name}")
        else:
            ongoing = [t for t in gs["tournaments"].values()
                       if isinstance(t, dict)
                       and t.get("year") == y
                       and _phase_matches(t, phase_key)
                       and t.get("status") == "ongoing"]
            status = _c("yellow", "Ongoing") if ongoing else _c("dim", "Not yet")
        print(f"    {label:<30} {status}")

    # ── Regional League Tables ────────────────────────────────────────────
    current_phase = _current_season_phase(gs)
    if current_phase:
        print(_c("dim", f"\n  {SEPARATOR}"))
        print(_c("bold", f"  REGIONAL LEAGUE STANDINGS  ({current_phase.upper()})"))
        for region in REGIONS:
            key = f"league_{region}_{current_phase}_{y}"
            tourn = gs["tournaments"].get(key)
            if not tourn or not tourn.get("results"):
                continue
            print(_c("dim", f"\n    ── {region.upper()} ──"))
            standings = sorted(
                tourn["results"].items(),
                key=lambda x: (x[1]["wins"], x[1]["map_wins"]),
                reverse=True,
            )
            headers = ["#", "Team", "W", "L", "Maps+", "Maps-"]
            rows = []
            for rank, (oid, rec) in enumerate(standings[:8], 1):
                org = gs["orgs"].get(oid)
                name = org["name"][:22] if org else oid
                rows.append([rank, name, rec["wins"], rec["losses"],
                              rec["map_wins"], rec["map_losses"]])
            print_table(headers, rows, col_widths=[4, 25, 5, 5, 8, 8])

    # ── Major results this year ──────────────────────────────────────────
    majors = [t for t in gs["tournaments"].values()
              if isinstance(t, dict) and t.get("type") == "major"
              and t.get("year") == y and t.get("status") == "completed"]
    if majors:
        print(_c("dim", f"\n  {SEPARATOR}"))
        print(_c("bold", "  MAJOR RESULTS"))
        for t in majors:
            winner = gs["orgs"].get(t.get("winner"), {}).get("name", "—") if t.get("winner") else "—"
            print(f"    {t['name']:<40} Champion: {_c('yellow', winner)}")

    # ── TI status ───────────────────────────────────────────────────────
    ti_qualified = gs.get("ti_qualified", [])
    if ti_qualified:
        print(_c("dim", f"\n  {SEPARATOR}"))
        print(_c("bold", f"  TI {y} QUALIFIED TEAMS ({len(ti_qualified)})"))
        for i, oid in enumerate(ti_qualified[:10], 1):
            name = gs["orgs"].get(oid, {}).get("name", oid)
            print(f"    {i:>2}. {name}")

    print()
    pause()


def _phase_matches(tourn: dict, phase_key: str) -> bool:
    t = tourn.get("type", "")
    n = tourn.get("name", "").lower()
    if phase_key == "winter":   return t == "regional" and "winter" in n
    if phase_key == "spring":   return t == "regional" and "spring" in n
    if phase_key == "summer":   return t == "regional" and "summer" in n
    if phase_key == "ti_qual":  return "qual" in n and t in ("tier2",)
    if phase_key == "ti":       return t == "ti" and "international" in n
    return False


def _current_season_phase(gs: dict) -> str | None:
    from utils.time_utils import phase_for_month
    p = phase_for_month(gs["month"])
    return p if p in ("winter", "spring", "summer") else None
