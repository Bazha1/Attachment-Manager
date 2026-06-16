"""Statistical helpers for rating calculations."""
import math


def clamp(val, lo=0, hi=100):
    return max(lo, min(hi, val))


def lerp(a, b, t):
    return a + (b - a) * t


def weighted_avg(values: list, weights: list) -> float:
    total_w = sum(weights)
    if total_w == 0:
        return 0.0
    return sum(v * w for v, w in zip(values, weights)) / total_w


def overall_rating(attrs: dict) -> float:
    """0-100 overall from core attributes dict."""
    keys = ["aim", "game_sense", "positioning", "clutch", "leadership"]
    weights = [3, 2, 2, 2, 1]
    vals = [attrs.get(k, 50) for k in keys]
    return weighted_avg(vals, weights)


def hltv_from_stats(kills: int, deaths: int, rounds: int,
                    adr: float, impact: float) -> float:
    """Simplified HLTV 2.0 approximation."""
    if rounds == 0:
        return 1.0
    kpr   = kills / rounds
    dpr   = deaths / rounds
    kast  = clamp(0.5 + (kills - deaths) / (2 * max(rounds, 1)), 0.0, 1.0)
    rating = (0.0073 * kast
              + 0.3591 * kpr
              - 0.5329 * dpr
              + 0.2372 * impact
              + 0.0032 * adr
              + 0.1587)
    return round(clamp(rating, 0.5, 2.5), 2)


def performance_rating(clutches: int, opening_kills: int, mvp_rounds: int,
                       match_importance: float) -> float:
    """0-10 contextual contribution score."""
    raw = (clutches * 1.5 + opening_kills * 0.8 + mvp_rounds * 0.5) * match_importance
    return round(clamp(raw / 5.0, 0.0, 10.0), 1)


def market_value(overall: float, age: int, hltv: float, role: str,
                 achievements: int) -> int:
    """Rough market value in USD."""
    base = overall * 15_000
    age_factor = 1.0
    if age < 22:
        age_factor = 1.1
    elif age > 28:
        age_factor = max(0.3, 1.0 - (age - 28) * 0.12)
    hltv_bonus  = max(0, (hltv - 1.0) * 200_000)
    trophy_bonus = achievements * 25_000
    return int((base * age_factor + hltv_bonus + trophy_bonus))


def chemistry_bonus(chemistry: int) -> float:
    """Return a multiplier (0.85–1.15) based on team chemistry."""
    return 0.85 + 0.30 * (chemistry / 100.0)


def pressure_modifier(pressure: int) -> float:
    """Return a multiplier based on pressure level (0–100)."""
    # Very low or very high pressure can hurt; moderate is best
    p = pressure / 100.0
    return 1.0 - 0.2 * (p - 0.5) ** 2 * 4
