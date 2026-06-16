import { useState } from "react";
import {
  useGetGameState,
  useAdvanceWeek,
  useGetFixtures,
  useGetResults,
  getGetGameStateQueryKey,
  getGetNewsQueryKey,
  getGetRankingsQueryKey,
  getGetRosterQueryKey,
  getGetResultsQueryKey,
  getGetFixturesQueryKey,
} from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";

export default function CalendarPage() {
  const { data: state } = useGetGameState();
  const { data: fixtures } = useGetFixtures();
  const { data: results } = useGetResults();
  const advance = useAdvanceWeek();
  const qc = useQueryClient();
  const [lastResult, setLastResult] = useState<{
    week_summary: string;
    match_results: Array<{
      tournament_name: string;
      team_a: string;
      team_b: string;
      score_a: number;
      score_b: number;
      winner: string;
      is_player_match: boolean;
    }>;
    new_news: Array<{ id: string; headline: string; category: string }>;
  } | null>(null);

  function handleAdvance() {
    setLastResult(null);
    advance.mutate(undefined, {
      onSuccess: (data) => {
        setLastResult(data as typeof lastResult);
        qc.invalidateQueries({ queryKey: getGetGameStateQueryKey() });
        qc.invalidateQueries({ queryKey: getGetNewsQueryKey() });
        qc.invalidateQueries({ queryKey: getGetRankingsQueryKey() });
        qc.invalidateQueries({ queryKey: getGetRosterQueryKey() });
        qc.invalidateQueries({ queryKey: getGetResultsQueryKey() });
        qc.invalidateQueries({ queryKey: getGetFixturesQueryKey() });
      },
    });
  }

  const categoryClass: Record<string, string> = {
    upset: "nc-upset",
    transfer: "nc-transfer",
    record: "nc-record",
    result: "nc-result",
  };

  return (
    <div className="px-4 py-5 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-black">Calendar</h1>
          {state?.has_game && (
            <p className="text-muted-foreground text-xs">{state.week_label} · {state.season_phase}</p>
          )}
        </div>
        <button
          className="btn-primary px-5 py-2.5"
          onClick={handleAdvance}
          disabled={advance.isPending || !state?.has_game}
        >
          {advance.isPending ? "Simulating..." : "Advance Week"}
        </button>
      </div>

      {advance.isPending && (
        <div className="stat-card text-center py-6">
          <div className="text-2xl mb-2 animate-spin inline-block">◎</div>
          <p className="text-sm text-muted-foreground">Simulating week...</p>
        </div>
      )}

      {lastResult && (
        <div className="space-y-4">
          <div className={`stat-card border-l-4 ${
            lastResult.week_summary.startsWith("Victory")
              ? "border-green-500 bg-green-500/5"
              : lastResult.week_summary.startsWith("Defeat")
              ? "border-red-500 bg-red-500/5"
              : "border-primary"
          }`}>
            <div className="text-xs text-muted-foreground mb-1 uppercase tracking-wide font-medium">Week Summary</div>
            <div className="font-semibold">{lastResult.week_summary}</div>
          </div>

          {lastResult.match_results.filter((r) => r.is_player_match).length > 0 && (
            <div>
              <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Your Match</h2>
              <div className="space-y-2">
                {lastResult.match_results.filter((r) => r.is_player_match).map((r, i) => {
                  const won = r.winner === r.team_a ? "a" : "b";
                  return (
                    <div key={i} className="match-result-row">
                      <div className="text-xs text-muted-foreground">{r.tournament_name}</div>
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

          {lastResult.new_news.length > 0 && (
            <div>
              <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Breaking News</h2>
              <div className="space-y-2">
                {lastResult.new_news.slice(0, 5).map((n) => (
                  <div key={n.id} className="stat-card py-2.5">
                    <div className="flex items-start gap-2">
                      <span className={`news-category shrink-0 ${categoryClass[n.category] ?? "nc-default"}`}>
                        {n.category}
                      </span>
                      <span className="text-sm leading-snug">{n.headline}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {lastResult.match_results.filter((r) => !r.is_player_match).length > 0 && (
            <div>
              <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">Other Results</h2>
              <div className="space-y-2">
                {lastResult.match_results.filter((r) => !r.is_player_match).slice(0, 8).map((r, i) => {
                  const won = r.winner === r.team_a ? "a" : "b";
                  return (
                    <div key={i} className="match-result-row">
                      <div className="text-xs text-muted-foreground truncate max-w-[100px]">{r.tournament_name}</div>
                      <div className="flex items-center gap-2 text-sm">
                        <span className={won === "a" ? "font-bold text-foreground" : "text-muted-foreground"}>
                          {r.team_a}
                        </span>
                        <span className="font-mono font-bold text-muted-foreground">
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
        </div>
      )}

      {/* Upcoming fixtures */}
      {fixtures && fixtures.length > 0 && (
        <div>
          <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
            Upcoming Fixtures
          </h2>
          <div className="space-y-2">
            {fixtures.map((f, i) => (
              <div key={i} className="stat-card py-3">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-xs text-muted-foreground">{f.tournament_name}</div>
                    <div className="font-semibold mt-0.5">
                      vs <span className="text-primary">{f.opponent_name}</span>
                    </div>
                    <div className="text-xs text-muted-foreground mt-0.5">{f.round}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-xs text-muted-foreground">Week {f.week}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Past results */}
      {results && results.length > 0 && (
        <div>
          <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
            Past Results
          </h2>
          <div className="space-y-2">
            {results.map((r, i) => {
              const won = r.winner === r.team_a ? "a" : "b";
              return (
                <div key={i} className="match-result-row">
                  <div className="text-xs text-muted-foreground truncate max-w-[100px]">{r.tournament_name}</div>
                  <div className="flex items-center gap-2 text-sm">
                    <span className={won === "a" ? "font-bold text-foreground" : "text-muted-foreground"}>
                      {r.team_a}
                    </span>
                    <span className="font-mono font-bold text-primary">{r.score_a}:{r.score_b}</span>
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
    </div>
  );
}
