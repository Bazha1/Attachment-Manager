"""Match display — pre-match, live simulation summary, post-match stats."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TERMINAL_WIDTH, SEPARATOR
from ui.menu import _c, pause, header, print_table


def show_pre_match(org_a: dict, org_b: dict, gs: dict,
                   tournament_name: str = "") -> None:
    print(_c("dim", f"\n  {SEPARATOR}"))
    print(_c("bold", f"  PRE-MATCH: {_c('cyan', org_a['name'])} vs "
                     f"{_c('yellow', org_b['name'])}"))
    if tournament_name:
        print(_c("dim", f"  Tournament: {tournament_name}"))
    print(_c("dim", f"  {SEPARATOR}"))

    def _org_line(org: dict) -> None:
        rank = org.get("ranking_position", "—")
        rep  = org.get("reputation", 0)
        form = " ".join(
            _c("green", r) if r == "W" else _c("red", r)
            for r in org.get("form", [])[:5]
        )
        chem = org.get("chemistry", 50)
        print(f"    {org['name']:<30} Rank: #{rank:<5} Rep: {rep:>3}  "
              f"Chemistry: {chem}  Form: {form}")

    _org_line(org_a)
    _org_line(org_b)


def show_match_result(result: dict, gs: dict,
                      player_org_id: str | None = None) -> None:
    """Display live summary + post-match stats for a completed match."""
    w_name = result["team_a_name"] if result["winner"] == result["team_a"] else result["team_b_name"]
    l_name = result["team_b_name"] if result["winner"] == result["team_a"] else result["team_a_name"]

    print(_c("dim", f"\n  {SEPARATOR}"))
    print(_c("bold", f"  MATCH RESULT: {_c('green', w_name)} "
                     f"defeats {_c('red', l_name)} "
                     f"  {_c('yellow', result['score'])}"))
    if result.get("tournament_name"):
        print(_c("dim", f"  [{result['tournament_name']}]"))

    # Map-by-map
    if result.get("map_results"):
        print(_c("dim", f"\n  Map Scores:"))
        for i, mr in enumerate(result["map_results"], 1):
            print(f"    Map {i}: {mr['score_a']} – {mr['score_b']}")

    # Key events (first 4)
    events = result.get("events", [])[:4]
    if events:
        print(_c("dim", f"\n  Key Moments:"))
        for ev in events:
            print(f"    {_c('yellow', '•')} {ev}")

    # Player stats for both teams
    _show_player_stats(result["stats_a"], result["team_a_name"],
                       result["winner"] == result["team_a"])
    _show_player_stats(result["stats_b"], result["team_b_name"],
                       result["winner"] == result["team_b"])

    # Advanced metrics
    _show_advanced_metrics(result)

    print(_c("dim", f"  {SEPARATOR}"))


def _show_player_stats(stats: list, team_name: str, won: bool) -> None:
    if not stats:
        return
    color = "green" if won else "red"
    print(_c("dim", f"\n  ── {_c(color, team_name)} ──"))
    headers = ["Player", "Role", "K", "D", "ADR", "HLTV", "Perf", "Clutches"]
    rows = []
    for s in stats:
        rows.append([
            s["nickname"], s["role"],
            s["kills"], s["deaths"], s["adr"],
            s["hltv"], s["perf"], s["clutches"]
        ])
    print_table(headers, rows, col_widths=[14, 15, 5, 5, 7, 7, 7, 9])


def _show_advanced_metrics(result: dict) -> None:
    print(_c("dim", f"\n  Advanced Metrics"))
    print(_c("dim", f"  {SEPARATOR}"))
    all_stats = result["stats_a"] + result["stats_b"]
    if not all_stats:
        return
    total_clutches     = sum(s.get("clutches", 0) for s in all_stats)
    total_opening_k    = sum(s.get("opening_k", 0) for s in all_stats)
    avg_adr_a = sum(s["adr"] for s in result["stats_a"]) / max(len(result["stats_a"]), 1)
    avg_adr_b = sum(s["adr"] for s in result["stats_b"]) / max(len(result["stats_b"]), 1)
    print(f"    {'Opening Kills Total':<35} {total_opening_k}")
    print(f"    {'Clutch Situations Total':<35} {total_clutches}")
    print(f"    {result['team_a_name'][:20] + ' Avg ADR':<35} {avg_adr_a:.1f}")
    print(f"    {result['team_b_name'][:20] + ' Avg ADR':<35} {avg_adr_b:.1f}")
    # Ranking impact
    print(f"\n    {'Ranking Points Earned:':<35}")
    print(f"    {result['team_a_name']:<35} +{result.get('ranking_pts_a', 0)}")
    print(f"    {result['team_b_name']:<35} +{result.get('ranking_pts_b', 0)}")


def prompt_match_mode() -> str:
    """Ask player whether to simulate quickly or watch in detail."""
    print(f"\n  [{_c('yellow', '1')}] Quick Simulation (instant result)")
    print(f"  [{_c('yellow', '2')}] Detailed Simulation (see key moments)")
    print(f"  [{_c('yellow', '3')}] Skip match")
    return input(_c("cyan", "  ▶ ")).strip()
