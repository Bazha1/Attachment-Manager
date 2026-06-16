import { useGetRankings } from "@workspace/api-client-react";

const REGION_LABELS: Record<string, string> = {
  europe: "EU",
  asia: "AS",
  latin_america: "LA",
  africa_oceania: "AO",
};

export default function RankingsPage() {
  const { data: rankings, isLoading } = useGetRankings();

  return (
    <div className="px-4 py-5 space-y-4">
      <div>
        <h1 className="text-lg font-black">World Rankings</h1>
        <p className="text-xs text-muted-foreground">HLTV-style time-decayed ranking</p>
      </div>

      {isLoading ? (
        <div className="text-center text-muted-foreground py-8">
          <div className="text-2xl mb-2">◎</div>
          <p className="text-sm">Calculating rankings...</p>
        </div>
      ) : (
        <div className="space-y-1.5">
          {(rankings ?? []).map((r) => (
            <div
              key={r.org_id}
              className={`rank-row ${r.is_player_org ? "rank-row-player" : "rank-row-normal"}`}
            >
              <div className={`text-sm font-black w-7 flex-shrink-0 ${
                r.rank <= 3 ? "text-primary" : "text-muted-foreground"
              }`}>
                {r.rank <= 3 ? ["", "①", "②", "③"][r.rank] : `#${r.rank}`}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="tag-badge text-xs">{r.tag}</span>
                  <span className="font-semibold text-sm truncate">{r.name}</span>
                  {r.is_player_org && (
                    <span className="text-[10px] bg-primary/20 text-primary px-1.5 py-0.5 rounded font-bold">YOU</span>
                  )}
                </div>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-xs text-muted-foreground">
                    {REGION_LABELS[r.region] ?? r.region.toUpperCase()}
                  </span>
                </div>
              </div>
              <div className="text-right flex-shrink-0">
                <div className="font-bold text-sm">{r.points.toLocaleString()}</div>
                <div className="text-xs text-muted-foreground">pts</div>
              </div>
            </div>
          ))}
          {(!rankings || rankings.length === 0) && (
            <p className="text-center text-muted-foreground py-8 text-sm">
              Rankings will appear after matches are played
            </p>
          )}
        </div>
      )}
    </div>
  );
}
