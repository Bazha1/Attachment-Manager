# CS Manager — Living Esports World Simulation

A Football Manager-style CS2 esports management game built in Python. Manage an organization through a full calendar-driven competitive year — regional leagues, Majors, and The International.

## How to Play

Run in the Shell:
```
cd cs_manager && python3 main.py
```

Choose **New Game** to generate the world (200 orgs, 2,000+ players across 4 regions) and pick your organization. Then use the main menu to advance time, manage your roster, and chase glory.

## Game Systems

- **Calendar-driven world** — time progresses week by week through Winter/Spring/Summer leagues → Majors → TI Qualification → The International
- **200 organizations** (50 per region: Europe, Asia, Latin America, Africa/Oceania)
- **2,000+ players** with full attributes, ratings (HLTV + Performance), mental states, playstyles
- **Academy system** — scout and develop youth players (manual promotion only)
- **Economy** — budgets, sponsor income, salaries, prize money
- **Contracts** — 1–3 year contracts, free agency, renewals
- **Transfer market** — sign free agents, AI orgs make rational moves
- **Match engine** — map-by-map simulation with round momentum, clutch moments, key events
- **HLTV-style ranking** — time-decayed world ranking updated monthly
- **Chemistry & pressure** — team chemistry and mental systems affect match outcomes
- **News system** — live esports-style headlines for transfers, upsets, results, records
- **Career dashboards** — full history for players and organizations

## Run & Operate

- `cd cs_manager && python3 main.py` — start / continue game
- `python3 -c "from main import generate_world; gs = generate_world()"` — test world generation
- Save file: `cs_manager/data/gamestate.json`

## Stack

- Pure Python 3.12, stdlib only — no external dependencies
- Multi-file architecture: `engine/`, `systems/`, `ui/`, `utils/`
- JSON persistence for all game state

## Where things live

- `cs_manager/main.py` — entry point, new game setup, world generation
- `cs_manager/game_loop.py` — main menu loop, all user interactions
- `cs_manager/config.py` — all constants, tuning values
- `cs_manager/engine/calendar_engine.py` — THE core driver; advance_time() triggers everything
- `cs_manager/engine/match_engine.py` — map-by-map CS match simulation
- `cs_manager/systems/` — player, team, chemistry, pressure, contract, academy, tournament, news
- `cs_manager/ui/` — all terminal UI: menu, calendar, match view, dashboards
- `cs_manager/data/gamestate.json` — save file (auto-created)

## Architecture decisions

- Calendar is the primary object — matches only exist inside tournaments, triggered by the calendar
- All systems interconnected: match engine depends on player attrs + chemistry + pressure + ranking
- JSON save/load for full game state persistence
- HLTV-style exponential decay ranking (half-life: 6 months)
- Academy players NEVER auto-promote — player decision only

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

- The game uses interactive `input()` — must run in a Shell, not as a background workflow
- World generation takes ~3-5 seconds (200 orgs, 2,000+ players)
- Save file at `cs_manager/data/gamestate.json` — backed up each week 4 of month
