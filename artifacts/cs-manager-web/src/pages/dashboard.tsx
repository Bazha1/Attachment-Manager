import { Link } from "wouter";
import { useGetGameState, useGetFixtures, useGetResults } from "@workspace/api-client-react";

function FormPip({ result }: { result: string }) {
  return (
    <span className={`form-pip ${result === "W" ? "form-pip-w" : "form-pip-l"}`}>
      {result}
    </span>
  );
}

function StatBlock({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="stat-card">
      <div className="text-xs text-muted-foreground mb-1 uppercase tracking-wide font-medium">{label}</div>
      <div className="text-xl font-bold text-foreground">{value}</div>
      {sub && <div className="text-xs text-muted-foreground mt-0.5">{sub}</div>}
    </div>
  );
}

export default function DashboardPage() {
  const { data: state, isLoading } = useGetGameState();
  const { data: fixtures } = useGetFixtures();
  const { data: results } = useGetResults();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center text-muted-foreground">
          <div className="text-3xl mb-2">◎</div>
          <p className="text-sm">Loading...</p>
        </div>
      </div>
    );
  }

  if (!state?.has_game) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center px-6">
          <div className="text-4xl font-black text-primary mb-3">CS MANAGER</div>
          <p className="text-muted-foreground text-sm mb-6">Living Esports World Simulation</p>
          <Link href="/setup">
            <button className="btn-primary text-base px-8 py-3">New Career</button>
          </Link>
        </div>
      </div>
    );
  }

  const winRate = (() => {
    const form = state.form ?? [];
    if (!form.length) return null;
    const wins = form.filter((f) => f === "W").length;
    return `${Math.round((wins / form.length) * 100)}%`;
  })();

  const phaseMap: Record<string, string> = {
    "Winter League": "bg-blue-500/20 text-blue-400",
    "Spring League": "bg-green-500/20 text-green-400",
    "Summer League": "bg-orange-500/20 text-orange-400",
    "Major I": "bg-yellow-500/20 text-yellow-400",
    "Major II": "bg-yellow-500/20 text-yellow-400",
    "TI Season": "bg-red-500/20 text-red-400",
  };
  const phaseClass = phaseMap[state.season_phase] ?? "bg-zinc-500/20 text-zinc-400";

  return (
    <div className="px-4 py-5 space-y-5">
      {/* Org header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="tag-badge text-base px-3 py-1">{state.org_tag}</span>
            <span className={`text-xs px-2 py-0.5 rounded font-semibold ${phaseClass}`}>
              {state.season_phase}
            </span>
          </div>
          <h1 className="text-xl font-black">{state.org_name}</h1>
          <p className="text-muted-foreground text-xs mt-0.5">
            {state.manager_name} · {state.week_label}
          </p>
        </div>
        <div className="text-right">
          {state.world_rank ? (
            <div>
              <div className="text-primary font-black text-2xl">#{state.world_rank}</div>
              <div className="text-xs text-muted-foreground">World Rank</div>
            </div>
          ) : (
            <div className="text-xs text-muted-foreground">Unranked</div>
          )}
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-3">
        <StatBlock
          label="Budget"
          value={`$${(state.budget / 1000).toFixed(0)}k`}
          sub="available"
        />
        <StatBlock
          label="Squad"
          value={state.roster_size}
          sub={`+${state.academy_size} academy`}
        />
        <StatBlock
          label="Chemistry"
          value={`${state.chemistry.toFixed(0)}%`}
          sub="team synergy"
        />
        <StatBlock
          label="Pressure"
          value={`${state.pressure.toFixed(0)}`}
          sub={state.pressure > 60 ? "high pressure" : state.pressure > 30 ? "moderate" : "calm"}
        />
      </div>

      {/* Form */}
      {state.form.length > 0 && (
        <div className="stat-card">
          <div className="text-xs text-muted-foreground mb-2 uppercase tracking-wide font-medium">
            Recent Form {winRate && <span className="text-foreground ml-1">({winRate} win rate)</span>}
          </div>
          <div className="flex gap-1 flex-wrap">
            {state.form.slice(-10).map((f, i) => (
              <FormPip key={i} result={f} />
            ))}
          </div>
        </div>
      )}

      {/* Next fixture */}
      {fixtures && fixtures.length > 0 && (
        <div className="stat-card">
          <div className="text-xs text-muted-foreground mb-2 uppercase tracking-wide font-medium">Next Match</div>
          <div className="flex items-center justify-between">
            <div>
              <div className="font-semibold">{fixtures[0].tournament_name}</div>
              <div className="text-sm text-muted-foreground mt-0.5">
                vs <span className="text-foreground font-medium">{fixtures[0].opponent_name}</span>
                <span className="ml-1">({fixtures[0].opponent_tag})</span>
              </div>
              <div className="text-xs text-muted-foreground mt-0.5">{fixtures[0].round}</div>
            </div>
            <Link href="/calendar">
              <button className="btn-secondary text-xs px-3 py-1.5">Calendar →</button>
            </Link>
          </div>
        </div>
      )}

      {/* Recent results */}
      {results && results.length > 0 && (
        <div>
          <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
            Recent Results
          </h2>
          <div className="space-y-2">
            {results.slice(0, 3).map((r, i) => {
              const won = r.winner === r.team_a ? "a" : "b";
              return (
                <div key={i} className="match-result-row">
                  <div className="text-xs text-muted-foreground flex-shrink-0">{r.tournament_name}</div>
                  <div className="flex items-center gap-2 text-sm">
                    <span className={won === "a" ? "font-bold text-foreground" : "text-muted-foreground"}>
                      {r.team_a}
                    </span>
                    <span className="font-mono font-bold text-primary">
                      {r.score_a}:{r.score_b}
                    </span>
                    <span className={won === "b" ? "font-bold text-foreground" : "text-muted-foreground"}>
                      {r.team_b}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Quick nav */}
      <div className="grid grid-cols-2 gap-3 pt-2">
        <Link href="/calendar">
          <button className="btn-primary w-full py-3">Advance Week</button>
        </Link>
        <Link href="/roster">
          <button className="btn-secondary w-full py-3">Manage Roster</button>
        </Link>
      </div>
    </div>
  );
}
