---
name: CS Manager game
description: Football Manager-style CS2 esports manager game — pure Python, stdlib only, lives in cs_manager/
---

**How to run:** `cd cs_manager && python3 main.py`

**Why pure Python stdlib:** No pip install needed; the prompt required no external dependencies and terminal-only UI.

**Key architecture rule:** Matches are ONLY triggered by the calendar engine (calendar_engine.py `advance_time()`). Never call match_engine.simulate_match() directly from UI — it violates the calendar-first design.

**Academy promotion rule:** Academy players NEVER auto-promote. Only the human player can call `academy_system.promote_player()`.

**Save file:** `cs_manager/data/gamestate.json` — written every week 4. The entire game state is a single JSON dict (`gs`).

**How to add:** Add new systems in `cs_manager/systems/`, new engines in `engine/`. Wire them into `simulation_engine.simulate_world_week()` (monthly tasks) or `calendar_engine._monthly_tasks()` (always-on monthly tasks).

**World generation:** ~3-5 seconds; produces 200 orgs (50/region × 4 regions) and 2,000+ players. Called once in `main.new_game()`.

**Python version:** Requires Python 3.12 (installed via installProgrammingLanguage). Uses `str | None` union syntax which requires 3.10+.
