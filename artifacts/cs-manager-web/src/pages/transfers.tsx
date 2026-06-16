import { useState } from "react";
import {
  useGetTransfers,
  useSignPlayer,
  useGetRoster,
  getGetRosterQueryKey,
  getGetGameStateQueryKey,
  getGetTransfersQueryKey,
} from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";

const ROLES = ["all", "igl", "awper", "entry", "support", "lurker", "rifler"];

export default function TransfersPage() {
  const { data: freeAgents, isLoading } = useGetTransfers();
  const { data: roster } = useGetRoster();
  const sign = useSignPlayer();
  const qc = useQueryClient();
  const [roleFilter, setRoleFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [successId, setSuccessId] = useState<string | null>(null);

  const filtered = (freeAgents ?? []).filter((p) => {
    const matchRole = roleFilter === "all" || p.role === roleFilter;
    const matchSearch =
      !search ||
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      (p.alias ?? "").toLowerCase().includes(search.toLowerCase()) ||
      p.nationality.toLowerCase().includes(search.toLowerCase());
    return matchRole && matchSearch;
  });

  function handleSign(playerId: string) {
    setError(null);
    setSuccessId(null);
    sign.mutate(
      { playerId },
      {
        onSuccess: () => {
          setSuccessId(playerId);
          qc.invalidateQueries({ queryKey: getGetRosterQueryKey() });
          qc.invalidateQueries({ queryKey: getGetGameStateQueryKey() });
          qc.invalidateQueries({ queryKey: getGetTransfersQueryKey() });
        },
        onError: (e: unknown) => {
          const err = e as { data?: { error?: string }; message?: string };
          setError(err?.data?.error ?? err?.message ?? "Failed to sign player");
        },
      }
    );
  }

  const roleColors: Record<string, string> = {
    igl: "bg-purple-500/20 text-purple-400",
    awper: "bg-cyan-500/20 text-cyan-400",
    entry: "bg-red-500/20 text-red-400",
    support: "bg-green-500/20 text-green-400",
    lurker: "bg-orange-500/20 text-orange-400",
    rifler: "bg-zinc-500/20 text-zinc-400",
  };

  return (
    <div className="px-4 py-5 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-black">Transfer Market</h1>
        {roster && (
          <span className="text-xs text-muted-foreground">
            Squad: <span className="text-foreground font-semibold">{roster.roster.length}/10</span>
          </span>
        )}
      </div>

      <div className="space-y-2 sticky top-0 bg-background py-2 z-10">
        <input
          type="text"
          className="org-search"
          placeholder="Search players..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div className="flex gap-1.5 overflow-x-auto pb-1">
          {ROLES.map((r) => (
            <button
              key={r}
              onClick={() => setRoleFilter(r)}
              className={`shrink-0 text-xs px-3 py-1.5 rounded-full font-medium transition-colors capitalize ${
                roleFilter === r
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary text-muted-foreground hover:text-foreground"
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="bg-destructive/10 border border-destructive/30 rounded-lg px-4 py-2.5 text-sm text-destructive">
          {error}
        </div>
      )}

      {isLoading ? (
        <div className="text-center text-muted-foreground py-8">
          <div className="text-2xl mb-2">◎</div>
          <p className="text-sm">Loading free agents...</p>
        </div>
      ) : (
        <div className="space-y-2">
          <p className="text-xs text-muted-foreground">{filtered.length} available</p>
          {filtered.map((p) => (
            <div key={p.id} className="player-row">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-bold text-sm truncate">{p.alias || p.name}</span>
                  <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${roleColors[p.role] ?? roleColors.rifler}`}>
                    {p.role}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span>{p.nationality}</span>
                  <span>·</span>
                  <span>Age {p.age}</span>
                  <span>·</span>
                  <span>${(p.salary / 1000).toFixed(1)}k/mo</span>
                </div>
              </div>
              <div className="flex items-center gap-3 ml-2 flex-shrink-0">
                <div className="text-right">
                  <div className="font-bold text-primary">{p.rating.toFixed(0)}</div>
                  <div className="text-xs text-muted-foreground">RTG</div>
                </div>
                {successId === p.id ? (
                  <span className="text-green-400 text-xs font-semibold">Signed!</span>
                ) : (
                  <button
                    className="btn-success"
                    onClick={() => handleSign(p.id)}
                    disabled={sign.isPending || (roster?.roster.length ?? 0) >= 10}
                  >
                    Sign
                  </button>
                )}
              </div>
            </div>
          ))}
          {filtered.length === 0 && (
            <p className="text-center text-muted-foreground py-8 text-sm">No free agents match your filters</p>
          )}
        </div>
      )}
    </div>
  );
}
