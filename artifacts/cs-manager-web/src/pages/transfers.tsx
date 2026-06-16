import { useState } from "react";
import {
  useGetTransfers,
  useSignPlayer,
  useBuyPlayer,
  useGetRoster,
  getGetRosterQueryKey,
  getGetGameStateQueryKey,
  getGetTransfersQueryKey,
} from "@workspace/api-client-react";
import type { PlayerCard, ContractedPlayer } from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";

const ROLES = ["all", "igl", "awper", "entry", "support", "lurker", "rifler"];

const roleColors: Record<string, string> = {
  igl:     "bg-purple-500/20 text-purple-400",
  awper:   "bg-cyan-500/20 text-cyan-400",
  entry:   "bg-red-500/20 text-red-400",
  support: "bg-green-500/20 text-green-400",
  lurker:  "bg-orange-500/20 text-orange-400",
  rifler:  "bg-zinc-500/20 text-zinc-400",
};

function PlayerRow({
  p,
  onAction,
  actionLabel,
  actionClass,
  actionDisabled,
  succeeded,
  subText,
  subTextClass,
}: {
  p: PlayerCard;
  onAction: (id: string) => void;
  actionLabel: string;
  actionClass: string;
  actionDisabled: boolean;
  succeeded: boolean;
  subText?: string;
  subTextClass?: string;
}) {
  return (
    <div className="player-row">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-bold text-sm truncate">{p.alias || p.name}</span>
          <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${roleColors[p.role] ?? roleColors.rifler}`}>
            {p.role}
          </span>
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground flex-wrap">
          <span>{p.nationality}</span>
          <span>·</span>
          <span>Age {p.age}</span>
          <span>·</span>
          <span>${(p.salary / 1000).toFixed(1)}k/mo</span>
        </div>
        {subText && (
          <div className={`text-xs mt-0.5 ${subTextClass ?? "text-muted-foreground"}`}>
            {subText}
          </div>
        )}
      </div>
      <div className="flex items-center gap-3 ml-2 flex-shrink-0">
        <div className="text-right">
          <div className="font-bold text-primary">{p.rating.toFixed(0)}</div>
          <div className="text-xs text-muted-foreground">RTG</div>
        </div>
        {succeeded ? (
          <span className="text-green-400 text-xs font-semibold">Done!</span>
        ) : (
          <button
            className={actionClass}
            onClick={() => onAction(p.id)}
            disabled={actionDisabled}
          >
            {actionLabel}
          </button>
        )}
      </div>
    </div>
  );
}

export default function TransfersPage() {
  const { data: market, isLoading } = useGetTransfers();
  const { data: roster }            = useGetRoster();
  const sign  = useSignPlayer();
  const buy   = useBuyPlayer();
  const qc    = useQueryClient();

  const [tab,        setTab]        = useState<"free" | "contracted">("free");
  const [roleFilter, setRoleFilter] = useState("all");
  const [search,     setSearch]     = useState("");
  const [error,      setError]      = useState<string | null>(null);
  const [successId,  setSuccessId]  = useState<string | null>(null);

  const freeAgents = market?.free_agents ?? [];
  const contracted = market?.contracted  ?? [];

  function matchesFilter(p: PlayerCard) {
    const matchRole   = roleFilter === "all" || p.role.toLowerCase() === roleFilter;
    const q           = search.toLowerCase();
    const matchSearch = !q
      || p.name.toLowerCase().includes(q)
      || p.alias.toLowerCase().includes(q)
      || p.nationality.toLowerCase().includes(q);
    return matchRole && matchSearch;
  }

  const filteredFree       = freeAgents.filter(matchesFilter);
  const filteredContracted = contracted.filter(matchesFilter);
  const displayed          = tab === "free" ? filteredFree : filteredContracted;

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

  function handleBuy(playerId: string) {
    setError(null);
    setSuccessId(null);
    buy.mutate(
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
          setError(err?.data?.error ?? err?.message ?? "Transfer failed");
        },
      }
    );
  }

  const rosterFull  = (roster?.roster.length ?? 0) >= 10;
  const isPending   = sign.isPending || buy.isPending;

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

      {/* Tab switcher */}
      <div className="flex border-b border-border">
        <button
          onClick={() => setTab("free")}
          className={`flex-1 py-2.5 text-sm font-semibold transition-colors ${
            tab === "free"
              ? "text-primary border-b-2 border-primary"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          Free Agents ({freeAgents.length})
        </button>
        <button
          onClick={() => setTab("contracted")}
          className={`flex-1 py-2.5 text-sm font-semibold transition-colors ${
            tab === "contracted"
              ? "text-primary border-b-2 border-primary"
              : "text-muted-foreground hover:text-foreground"
          }`}
        >
          Buy Out ({contracted.length})
        </button>
      </div>

      {tab === "contracted" && (
        <p className="text-xs text-muted-foreground -mt-1 leading-snug">
          Purchase players from other orgs. Transfer fees are deducted from your budget.
        </p>
      )}

      {/* Search + role filter */}
      <div className="space-y-2 sticky top-0 bg-background py-2 z-10">
        <input
          type="text"
          className="org-search"
          placeholder="Search players…"
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
          <p className="text-sm">Loading transfer market…</p>
        </div>
      ) : (
        <div className="space-y-2">
          <p className="text-xs text-muted-foreground">{displayed.length} available</p>

          {tab === "free" ? (
            filteredFree.map((p) => (
              <PlayerRow
                key={p.id}
                p={p}
                onAction={handleSign}
                actionLabel="Sign"
                actionClass="btn-success"
                actionDisabled={isPending || rosterFull}
                succeeded={successId === p.id}
              />
            ))
          ) : (
            filteredContracted.map((cp) => {
              const p = cp as ContractedPlayer;
              return (
                <div key={p.id} className="player-row">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-bold text-sm truncate">{p.alias || p.name}</span>
                      <span className={`text-[10px] font-bold uppercase px-1.5 py-0.5 rounded ${roleColors[p.role] ?? roleColors.rifler}`}>
                        {p.role}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-muted-foreground flex-wrap">
                      <span>{p.nationality}</span>
                      <span>·</span>
                      <span>Age {p.age}</span>
                      <span>·</span>
                      <span>${(p.salary / 1000).toFixed(1)}k/mo</span>
                    </div>
                    <div className="flex items-center gap-1.5 mt-1 text-xs">
                      <span className="text-muted-foreground">From:</span>
                      <span className="tag-badge text-[10px] px-1.5 py-0.5">
                        {p.current_org_tag}
                      </span>
                      <span className="text-muted-foreground">{p.current_org}</span>
                    </div>
                    <div className="mt-0.5">
                      <span className={`text-xs font-semibold ${p.can_afford ? "text-yellow-400" : "text-red-400"}`}>
                        Fee: ${(p.transfer_fee / 1000).toFixed(0)}k
                      </span>
                      {!p.can_afford && (
                        <span className="text-xs text-muted-foreground ml-1">(over budget)</span>
                      )}
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
                        className={p.can_afford ? "btn-primary text-xs px-3 py-1.5" : "btn-secondary text-xs px-3 py-1.5 opacity-50"}
                        onClick={() => handleBuy(p.id)}
                        disabled={isPending || rosterFull || !p.can_afford}
                      >
                        Buy
                      </button>
                    )}
                  </div>
                </div>
              );
            })
          )}

          {displayed.length === 0 && !isLoading && (
            <p className="text-center text-muted-foreground py-8 text-sm">
              {tab === "free"
                ? "No free agents match your filters"
                : "No contracted players match your filters"}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
