---
name: CS Manager web bridge
description: Architecture for the React+Vite web version of CS Manager — Node api-server calls Python via spawn stdin/stdout
---

**Architecture:**
- React+Vite at `artifacts/cs-manager-web/` (preview path `/`)
- Node.js api-server at `artifacts/api-server/` routes game actions to Python
- Python bridge at `cs_manager/web_api.py` — reads JSON action from stdin, writes JSON result to stdout

**Critical fix — stdout redirect:**
The Python game modules (especially `generate_world`) print progress text to stdout.
This corrupts the JSON output channel. The fix is at the top of `web_api.py main()`:
```python
real_stdout = sys.stdout
sys.stdout = sys.stderr   # redirect prints to stderr during execution
# ... do all work ...
sys.stdout = real_stdout
print(json.dumps(result))  # only JSON goes to real stdout
```
**Without this fix, the `/api/game/orgs` endpoint always returns 500.**

**Node→Python spawn pattern (game.ts):**
Use `spawn()` with stdin piping — NOT `execFile` with `input` option (execFile doesn't support `input`).
Write payload to `child.stdin`, collect `child.stdout`, resolve on `close`.

**Save file:** `cs_manager/data/gamestate.json` — shared between console and web version.
Playing via web and then via terminal uses the same save file.

**API routes (all at `/api/game/...`):**
- GET /game/state, GET /game/orgs, GET /game/roster, GET /game/news, GET /game/rankings
- GET /game/transfers, GET /game/fixtures, GET /game/results
- POST /game/new, POST /game/advance
- POST /game/roster/release/:id, POST /game/roster/sign/:id, POST /game/academy/promote/:id

**Frontend pages:** /, /setup, /calendar, /roster, /transfers, /news, /rankings

**CSS theme:** Tailwind v4 with dark vars in :root directly (no `.dark` class needed). Do NOT use `html { @apply dark; }` — `dark` is not a utility in Tailwind v4, causes build error.
