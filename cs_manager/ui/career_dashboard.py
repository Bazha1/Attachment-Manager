"""Career dashboards for players and organizations."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SEPARATOR
from ui.menu import _c, pause, header, print_table, print_menu
from utils.stats_utils import overall_rating
from utils.time_utils import month_name


def show_player_career(player: dict, gs: dict) -> None:
    header(gs)
    p = player
    ovr = int(overall_rating(p["attributes"]))
    print(_c("bold", f"\n  ◈ PLAYER CAREER: {_c('yellow', p['nickname'].upper())}\n"))
    print(f"    {'Full Name':<25} {p['first_name']} \"{p['nickname']}\" {p['last_name']}")
    print(f"    {'Nationality':<25} {p['nationality']}")
    print(f"    {'Age':<25} {p['age']}")
    print(f"    {'Region':<25} {p['region'].title()}")
    print(f"    {'Role':<25} {p['role']}")
    print(f"    {'Overall Rating':<25} {_c('cyan', str(ovr))}")
    print(f"    {'Status':<25} {p['status'].title()}")
    if p.get("org_id"):
        org_name = gs["orgs"].get(p["org_id"], {}).get("name", "—")
        print(f"    {'Current Org':<25} {org_name}")

    # Ratings
    print(_c("dim", f"\n    {SEPARATOR}"))
    print(_c("bold", "    RATINGS"))
    hltv = p["stats"].get("hltv_rating", 1.0)
    perf = p["stats"].get("performance_rating", 5.0)
    h_color = "green" if hltv >= 1.15 else ("yellow" if hltv >= 0.95 else "red")
    print(f"    {'HLTV Rating':<25} {_c(h_color, str(hltv))}")
    print(f"    {'Performance Rating':<25} {perf}/10")

    # Core attributes
    print(_c("dim", f"\n    {SEPARATOR}"))
    print(_c("bold", "    CORE ATTRIBUTES"))
    attrs = p["attributes"]
    for attr, val in attrs.items():
        bar = _attr_bar(val)
        print(f"    {attr.title():<20} {bar} {val:>3}")

    # Mental
    print(_c("dim", f"\n    {SEPARATOR}"))
    print(_c("bold", "    MENTAL"))
    for k, v in p["mental"].items():
        bar = _attr_bar(v)
        print(f"    {k.replace('_',' ').title():<20} {bar} {v:>3}")

    # Career stats
    s = p["stats"]
    print(_c("dim", f"\n    {SEPARATOR}"))
    print(_c("bold", "    CAREER STATISTICS"))
    print(f"    {'Career Matches':<25} {s.get('career_matches', 0)}")
    print(f"    {'Career Kills':<25} {s.get('career_kills', 0)}")
    print(f"    {'Career Deaths':<25} {s.get('career_deaths', 0)}")

    # Market value
    print(_c("dim", f"\n    {SEPARATOR}"))
    print(_c("bold", "    MARKET VALUE"))
    mv   = p.get("market_value", 0)
    pmv  = p.get("peak_market_value", 0)
    print(f"    {'Current Value':<25} ${mv:,}")
    print(f"    {'Peak Value':<25} ${pmv:,}")
    print(f"    {'Salary / month':<25} ${p['contract'].get('salary', 0):,}")
    print(f"    {'Contract expires':<25} {p['contract'].get('expiry_year','—')}")

    # Playstyle
    print(_c("dim", f"\n    {SEPARATOR}"))
    print(f"    Playstyle: {_c('yellow', p.get('playstyle','—'))}")

    # Achievements
    if p.get("achievements"):
        print(_c("dim", f"\n    {SEPARATOR}"))
        print(_c("bold", "    ACHIEVEMENTS"))
        for a in p["achievements"]:
            print(f"    ★ {a}")

    # Career history
    history = p.get("career_history", [])
    if history:
        print(_c("dim", f"\n    {SEPARATOR}"))
        print(_c("bold", "    CAREER HISTORY"))
        for h in history[-8:]:
            event = h.get("event", "")
            detail = h.get("org", h.get("to", ""))
            print(f"    {h.get('year','')}-{h.get('month',''):<5} "
                  f"{event.title():<15} {detail}")

    print()
    pause()


def show_org_career(org: dict, gs: dict) -> None:
    header(gs)
    print(_c("bold", f"\n  ◈ ORG PROFILE: {_c('yellow', org['name'].upper())}\n"))
    print(f"    {'Tag':<25} [{org['tag']}]")
    print(f"    {'Region':<25} {org['region'].title()}")
    print(f"    {'Founded':<25} {org['founding_year']}")
    print(f"    {'Era':<25} {org['era'].replace('_',' ').title()}")
    print(f"    {'Identity':<25} {org.get('identity','—')}")
    print(f"    {'Reputation':<25} {org.get('reputation',0)}/100")
    print(f"    {'Global Prestige':<25} {org.get('global_prestige',0)}/100")
    print(f"    {'Regional Prestige':<25} {org.get('regional_prestige',0)}/100")
    print(f"    {'World Ranking':<25} #{org.get('ranking_position','—')}")
    print(f"    {'Ranking Points':<25} {org.get('ranking_points',0):,}")
    rank_pts = org.get("ranking_points", 0)
    print(f"    {'Budget':<25} ${org.get('budget',0):,}")
    print(f"    {'Sponsor Income/mo':<25} ${org.get('sponsor_income',0):,}")

    # Form
    form = org.get("form", [])
    form_str = " ".join(_c("green", r) if r == "W" else _c("red", r) for r in form[:5])
    print(f"    {'Recent Form':<25} {form_str}")
    print(f"    {'Chemistry':<25} {org.get('chemistry', 50)}/100")

    # Roster
    print(_c("dim", f"\n    {SEPARATOR}"))
    print(_c("bold", "    MAIN ROSTER"))
    from utils.stats_utils import overall_rating as ovr
    for pid in org.get("roster", []):
        p = gs["players"].get(pid)
        if not p: continue
        o = int(ovr(p["attributes"]))
        h_color = "green" if p["stats"]["hltv_rating"] >= 1.15 else "dim"
        print(f"    {p['nickname']:<16} {p['role']:<16} OVR:{o:>3}  "
              f"HLTV: {_c(h_color, str(p['stats']['hltv_rating']))}")
    for pid in org.get("bench", []):
        p = gs["players"].get(pid)
        if not p: continue
        o = int(ovr(p["attributes"]))
        print(f"    {p['nickname']:<16} {p['role']:<16} OVR:{o:>3}  "
              f"[BENCH]  {_c('dim', str(p['stats']['hltv_rating']))}")

    # Academy
    if org.get("academy"):
        print(_c("dim", f"\n    {SEPARATOR}"))
        print(_c("bold", "    ACADEMY ROSTER"))
        for pid in org["academy"][:5]:
            p = gs["players"].get(pid)
            if not p: continue
            o = int(ovr(p["attributes"]))
            print(f"    {p['nickname']:<16} Age:{p['age']:<5} OVR:{o:>3}  "
                  f"Potential: {'★'*(max(1,o//25))}")

    # Trophies
    trophies = org.get("trophies", [])
    if trophies:
        print(_c("dim", f"\n    {SEPARATOR}"))
        print(_c("bold", f"    TROPHY CABINET ({len(trophies)})"))
        for t in trophies[-8:]:
            print(f"    {_c('yellow', '★')} {t['name']} ({t['year']})")

    # Sponsors
    print(_c("dim", f"\n    {SEPARATOR}"))
    print(_c("bold", "    SPONSORS"))
    for sp in org.get("sponsors", []):
        if sp.get("income", 0) > 0:
            print(f"    {sp['name']:<30} ${sp['income']:,}/mo  "
                  f"[{sp['type'].upper()}]  Expires: {sp.get('expiry_year','?')}")
    print()
    pause()


def _attr_bar(val: int, width: int = 15) -> str:
    filled = int(val / 100 * width)
    empty  = width - filled
    if val >= 80: color = "green"
    elif val >= 60: color = "yellow"
    else: color = "red"
    return _c(color, "█" * filled) + _c("dim", "░" * empty)


def player_list_menu(gs: dict, org_id: str | None = None,
                     title: str = "SELECT PLAYER") -> dict | None:
    """Interactive player list; returns chosen player dict or None."""
    header(gs)
    from utils.stats_utils import overall_rating as ovr

    if org_id:
        org = gs["orgs"].get(org_id, {})
        pids = org.get("roster", []) + org.get("bench", [])
    else:
        pids = list(gs["players"].keys())

    players = [gs["players"][pid] for pid in pids if pid in gs["players"]
               and not gs["players"][pid].get("retired")]
    players.sort(key=lambda p: ovr(p["attributes"]), reverse=True)

    print(_c("bold", f"\n  ◈ {title}"))
    print(_c("dim", f"  {SEPARATOR}"))
    for i, p in enumerate(players[:20], 1):
        o = int(ovr(p["attributes"]))
        print(f"  [{_c('yellow', str(i))}] {p['nickname']:<16} {p['role']:<16} "
              f"OVR:{o:>3}  HLTV:{p['stats']['hltv_rating']}")
    print(f"  [{_c('yellow', '0')}] Back")
    raw = input(_c("cyan", "  ▶ ")).strip()
    try:
        idx = int(raw)
        if idx == 0: return None
        return players[idx - 1]
    except (ValueError, IndexError):
        return None
