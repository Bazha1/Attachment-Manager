"""Calendar and time helpers."""
from config import MONTHS, WEEKS_PER_MONTH, SEASON_PHASES


def month_name(month: int) -> str:
    """1-indexed month number → name."""
    return MONTHS[month - 1]


def phase_for_month(month: int) -> str | None:
    for phase, info in SEASON_PHASES.items():
        if month in info["months"]:
            return phase
    return None


def phase_label(month: int) -> str:
    p = phase_for_month(month)
    if p:
        return SEASON_PHASES[p]["label"]
    return ""


def advance_week(year: int, month: int, week: int):
    """Return (year, month, week) after advancing one week."""
    week += 1
    if week > WEEKS_PER_MONTH:
        week = 1
        month += 1
        if month > 12:
            month = 1
            year += 1
    return year, month, week


def weeks_between(y1, m1, w1, y2, m2, w2) -> int:
    def total(y, m, w):
        return y * 12 * WEEKS_PER_MONTH + (m - 1) * WEEKS_PER_MONTH + (w - 1)
    return total(y2, m2, w2) - total(y1, m1, w1)


def date_str(year: int, month: int, week: int) -> str:
    return f"{month_name(month)} W{week}, {year}"


def is_league_month(month: int) -> bool:
    return phase_for_month(month) in ("winter", "spring", "summer")


def league_round_for_week(month: int, week: int) -> int | None:
    """
    Each league season spans 3 months × 4 weeks = 12 weeks.
    Return 1-based round number within that season.
    """
    phase = phase_for_month(month)
    if phase not in ("winter", "spring", "summer"):
        return None
    months_in_phase = SEASON_PHASES[phase]["months"]
    month_idx = months_in_phase.index(month)
    return month_idx * WEEKS_PER_MONTH + week  # 1–12
