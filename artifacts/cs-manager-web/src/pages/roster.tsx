import { useState } from "react";
import {
  useGetRoster,
  useReleasePlayer,
  usePromotePlayer,
  getGetRosterQueryKey,
  getGetGameStateQueryKey,
} from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";

function RoleTag({ role }: { role: string }) {
  const colors: Record<string, string> = {
    igl: "bg-purple-500/20 text-purple-400",
    awper: "bg-cyan-500/20 text-cyan-400",
    entry: "bg-red-500/20 text-red-400",
    support: "bg-green-500/20 text-green-400",
    lurker: "bg-orange-500/20 text-orange-400",
    rifler: "bg-zinc-500/20 text-zinc-400",
  };
  return (
    <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${colors[role] ?? colors.rifler}`}>
      {role}
    </span>
  );
}

function MentalTag({ mental }: { mental: string }) {
  const colors: Record<string, string> = {
    confident: "text-green-400",
    motivated: "text-green-400",
    stable: "text-muted-foreground",
    nervous: "text-yellow-400",
    tilted: "text-red-400",
    depressed: "text-red-400",
  };
  return (
    <span className={`text-[10px] capitalize ${colors[mental] ?? "text-muted-foreground"}`}>
      {mental}
    </span>
  );
}

export default function RosterPage() {
  const { data: roster, isLoading } = useGetRoster();
  const release = useReleasePlayer();
  const promote = usePromotePlayer();
  const qc = useQueryClient();
  const [tab, setTab] = useState<"active" | "academy">("active");
  const [error, setError] = useState<string | null>(null);

  function handleRelease(playerId: string) {
    setError(null);
    release.mutate(
      { playerId },
      {
        onSuccess: () => {
          qc.invalidateQueries({ queryKey: getGetRosterQueryKey() });
          qc.invalidateQueries({ queryKey: getGetGameStateQueryKey() });
        },
        onError: (e: unknown) => {
          const err = e as { data?: { error?: string }; message?: string };
          setError(err?.data?.error ?? err?.message ?? "Failed to release player");
        },
      }
    );
  }

  function handlePromote(playerId: string) {
    setError(null);
    promote.mutate(
      { playerId },
      {
        onSuccess: () => {
          qc.invalidateQueries({ queryKey: getGetRosterQueryKey() });
          qc.invalidateQueries({ queryKey: getGetGameStateQueryKey() });
        },
        onError: (e: unknown) => {
          const err = e as { data?: { error?: string }; message?: string };
          setError(err?.data?.error ?? err?.message ?? "Failed to promote player");
        },
      }
    );
  }

  const players = tab === "active" ? (roster?.roster ?? []) : (roster?.academy ?? []);

  return (
    <div className="px-4 py-5 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-black">Roster</h1>
        {roster && (
          <span className="text-xs text-muted-foreground">
            Budget: <span className="text-foreground font-semibold">${(roster.budget / 1000).toFixed(0)}k</span>
          </span>
        )}
      </div>

      {roster && (
        <div className="flex gap-4 text-sm">
          <div className="stat-card flex-1 text-center py-2">
            <div className="font-bold text-foreground">{roster.chemistry.toFixed(0)}%</div>
            <div className="text-xs text-muted-foreground">Chemistry</div>
          </div>
          <div className="stat-card flex-1 text-center py-2">
            <div className="font-bold text-foreground">{roster.pressure.toFixed(0)}</div>
            <div className="text-xs text-muted-foreground">Pressure</div>
          </div>
        </div>
      )}

      <div className="flex border-b border-border">
        <button
          onClick={() => setTab("active")}
          className={`flex-1 py-2.5 text-sm font-semibold transition-colors ${
            tab === "active"
              ? "text-primary border-b-2 border-primary"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          Active ({roster?.roster.length ?? 0})
        </button>
        <button
          onClick={() => setTab("academy")}
          className={`flex-1 py-2.5 text-sm font-semibold transition-colors ${
            tab === "academy"
              ? "text-primary border-b-2 border-primary"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          Academy ({roster?.academy.length ?? 0})
        </button>
      </div>

      {error && (
        <div className="bg-destructive/10 border border-destructive/30 rounded-lg px-4 py-2.5 text-sm text-destructive">
          {error}
        </div>
      )}

      {isLoading ? (
        <div className="text-center text-muted-foreground py-8">
          <div className="text-2xl mb-2">◎</div>
          <p className="text-sm">Loading roster...</p>
        </div>
      ) : (
        <div className="space-y-2">
          {players.map((p) => (
            <div key={p.id} className="player-row">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-bold text-sm truncate">{p.alias || p.name}</span>
                  <RoleTag role={p.role} />
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs text-muted-foreground">{p.nationality}</span>
                  <span className="text-xs text-muted-foreground">Age {p.age}</span>
                  <MentalTag mental={p.mental} />
                </div>
                <div className="flex items-center gap-2 mt-1.5">
                  {(p.form ?? []).slice(-5).map((f, i) => (
                    <span
                      key={i}
                      className={`inline-flex w-4 h-4 rounded text-[9px] font-bold items-center justify-center ${
                        f === "W" ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"
                      }`}
                    >
                      {f}
                    </span>
                  ))}
                </div>
              </div>
              <div className="flex items-center gap-3 ml-2 flex-shrink-0">
                <div className="text-right">
                  <div className="font-bold text-primary">{p.rating.toFixed(0)}</div>
                  <div className="text-xs text-muted-foreground">${(p.salary / 1000).toFixed(1)}k/mo</div>
                </div>
                {tab === "active" ? (
                  <button
                    className="btn-danger"
                    onClick={() => handleRelease(p.id)}
                    disabled={release.isPending}
                  >
                    Release
                  </button>
                ) : (
                  <button
                    className="btn-success"
                    onClick={() => handlePromote(p.id)}
                    disabled={promote.isPending}
                  >
                    Promote
                  </button>
                )}
              </div>
            </div>
          ))}
          {players.length === 0 && (
            <p className="text-center text-muted-foreground py-8 text-sm">
              {tab === "academy" ? "Academy is empty" : "No players on roster"}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
