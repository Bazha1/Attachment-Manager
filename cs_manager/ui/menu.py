"""Main menu and shared UI helpers."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import TERMINAL_WIDTH, SEPARATOR, THICK_SEP, ANSI, GAME_TITLE
from utils.time_utils import month_name, phase_label


def _c(code: str, text: str) -> str:
    """Wrap text in ANSI colour code, then reset."""
    return ANSI.get(code, "") + str(text) + ANSI["reset"]


def clear() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def header(gs: dict) -> None:
    clear()
    print(_c("cyan", THICK_SEP))
    title_line = f"  {GAME_TITLE}  "
    print(_c("bold", title_line.center(TERMINAL_WIDTH)))
    # Date + org info
    y, m, w = gs["year"], gs["month"], gs["week"]
    date_str = f"{month_name(m)} Week {w}, {y}  |  Phase: {phase_label(m) or 'Off-season'}"
    print(_c("yellow", f"  {date_str}"))
    # Player org
    porg = gs["orgs"].get(gs.get("player_org_id", ""))
    if porg:
        rep  = porg.get("reputation", 0)
        rank = porg.get("ranking_position", "—")
        budget = porg.get("budget", 0)
        print(_c("green", f"  Org: {porg['name']} [{porg['tag']}]  "
                           f"Rep: {rep}/100  Rank: #{rank}  "
                           f"Budget: ${budget:,}"))
    print(_c("cyan", THICK_SEP))


def print_menu(title: str, options: list[tuple[str, str]]) -> str:
    """Print a numbered menu and return the chosen key."""
    print(_c("bold", f"\n  {title}"))
    print(_c("dim", f"  {SEPARATOR}"))
    for i, (key, label) in enumerate(options, 1):
        print(f"  [{_c('yellow', key)}] {label}")
    print(_c("dim", f"  {SEPARATOR}"))
    return input(_c("cyan", "  ▶ ")).strip().lower()


def main_menu(gs: dict) -> str:
    header(gs)
    options = [
        ("1", "Continue (advance 1 week)"),
        ("2", "Continue Season (advance to next event)"),
        ("3", "View Calendar"),
        ("4", "Team Overview"),
        ("5", "Player Overview"),
        ("6", "Transfers / Free Agents"),
        ("7", "Academy"),
        ("8", "Rankings"),
        ("9", "News"),
        ("0", "Career Dashboard"),
        ("s", "Season Dashboard"),
        ("q", "Save & Exit"),
    ]
    return print_menu("MAIN MENU", options)


def pause(prompt: str = "  Press Enter to continue...") -> None:
    input(_c("dim", prompt))


def print_table(headers: list, rows: list, col_widths: list | None = None) -> None:
    if col_widths is None:
        col_widths = [max(len(str(h)), max((len(str(r[i])) for r in rows), default=0)) + 2
                      for i, h in enumerate(headers)]
    header_row = "  " + "".join(str(h).ljust(w) for h, w in zip(headers, col_widths))
    print(_c("bold", header_row))
    print(_c("dim", "  " + "─" * sum(col_widths)))
    for row in rows:
        line = "  " + "".join(str(v).ljust(w) for v, w in zip(row, col_widths))
        print(line)


def prompt_choice(options: list[str], prompt: str = "Choice: ") -> str:
    for i, opt in enumerate(options, 1):
        print(f"  [{_c('yellow', str(i))}] {opt}")
    raw = input(_c("cyan", f"  {prompt}")).strip()
    try:
        idx = int(raw) - 1
        if 0 <= idx < len(options):
            return options[idx]
    except ValueError:
        pass
    return ""


def print_news_item(item: dict) -> None:
    cat_colors = {
        "transfer":      "cyan",
        "upset":         "red",
        "result":        "green",
        "roster":        "yellow",
        "record":        "magenta",
        "relegation":    "red",
        "promotion":     "green",
        "qualification": "blue",
        "injury":        "red",
        "streak":        "yellow",
    }
    color = cat_colors.get(item.get("category", ""), "white")
    tag   = f"[{item.get('category','NEWS').upper()[:8]}]"
    date  = f"{month_name(item['month'])} {item['year']}"
    print(f"  {_c(color, tag):<20} {_c('dim', date):<20} {item['headline']}")
