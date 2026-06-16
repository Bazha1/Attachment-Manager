import { Router, type IRouter } from "express";
import { spawn } from "child_process";
import path from "path";

const router: IRouter = Router();

const PYTHON = "python3";
const BRIDGE = path.resolve("/home/runner/workspace/cs_manager/web_api.py");
const CS_MANAGER_DIR = path.resolve("/home/runner/workspace/cs_manager");

const TIMEOUT_MS = 90_000;

function callPython(action: string, data: Record<string, unknown> = {}): Promise<unknown> {
  return new Promise((resolve, reject) => {
    const payload = JSON.stringify({ action, data });
    let stdout = "";
    let stderr = "";

    const child = spawn(PYTHON, [BRIDGE], {
      cwd: CS_MANAGER_DIR,
      env: { ...process.env, PYTHONPATH: CS_MANAGER_DIR },
    });

    const timer = setTimeout(() => {
      child.kill();
      reject(new Error("Python bridge timed out after 90s"));
    }, TIMEOUT_MS);

    child.stdout.on("data", (chunk: Buffer) => { stdout += chunk.toString(); });
    child.stderr.on("data", (chunk: Buffer) => { stderr += chunk.toString(); });

    child.on("close", (code: number | null) => {
      clearTimeout(timer);
      if (stderr && !stderr.includes("DeprecationWarning") && !stderr.includes("Generating world")) {
        console.error("[game bridge stderr]", stderr.slice(0, 800));
      }
      if (!stdout.trim()) {
        reject(new Error(`Python bridge returned no output (exit ${code}): ${stderr.slice(0, 200)}`));
        return;
      }
      try {
        resolve(JSON.parse(stdout.trim()));
      } catch {
        reject(new Error(`Invalid JSON from Python: ${stdout.slice(0, 200)}`));
      }
    });

    child.on("error", (err: Error) => {
      clearTimeout(timer);
      reject(err);
    });

    child.stdin.write(payload);
    child.stdin.end();
  });
}

function gameRoute(action: string, dataFn?: (req: import("express").Request) => Record<string, unknown>) {
  return async (req: import("express").Request, res: import("express").Response) => {
    try {
      const data = dataFn ? dataFn(req) : {};
      const result = await callPython(action, data);
      const r = result as Record<string, unknown>;
      if (r && typeof r === "object" && r.error) {
        res.status(400).json(r);
      } else {
        res.json(r);
      }
    } catch (e: unknown) {
      res.status(500).json({ error: String(e) });
    }
  };
}

router.get("/game/orgs", gameRoute("list_orgs"));
router.post("/game/new", gameRoute("new_game", (req) => req.body));
router.get("/game/state", gameRoute("get_state"));
router.post("/game/advance", gameRoute("advance_week"));
router.get("/game/roster", gameRoute("get_roster"));
router.post("/game/roster/release/:playerId", gameRoute("release_player", (req) => ({ player_id: req.params.playerId })));
router.post("/game/roster/sign/:playerId", gameRoute("sign_player", (req) => ({ player_id: req.params.playerId })));
router.post("/game/academy/promote/:playerId", gameRoute("promote_player", (req) => ({ player_id: req.params.playerId })));
router.get("/game/news", gameRoute("get_news"));
router.get("/game/rankings", gameRoute("get_rankings"));
router.get("/game/transfers", gameRoute("get_transfers"));
router.get("/game/fixtures", gameRoute("get_fixtures"));
router.get("/game/results", gameRoute("get_results"));

export default router;
