import { useState } from "react";
import {
  useGetGameState,
  useAdvanceWeek,
  useGetCalendar,
  useGetFixtures,
  useGetResults,
  getGetGameStateQueryKey,
  getGetNewsQueryKey,
  getGetRankingsQueryKey,
  getGetRosterQueryKey,
  getGetResultsQueryKey,
  getGetFixturesQueryKey,
  getGetCalendarQueryKey,
} from "@workspace/api-client-react";
import { useQueryClient } from "@tanstack/react-query";

type AdvanceResultLocal = {
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
};

const CATEGORY_CLASS: Record<string, string> = {
  upset: "nc-upset",
  transfer: "nc-transfer",
  record: "nc-record",
  result: "nc-result",
};

function ProgressBar({ value }: { value: number }) {
  return (
    <div className="h-1.5 bg-secondary rounded-full overflow-hidden">
      <div
        className="h-full bg-primary rounded-full transition-all"
        style={{ width: `${Math.round(value * 100)}%` }}
      />
    </div>
  );
}

function StandingsTable({ league }: {
  league: NonNullable<ReturnType<typeof useGetCalendar>["data"]>["player_league"];
}) {
  if (!league) return null;
  const { standings, player_record, played_matches, total_matches } = league;

  return (
    <div className="stat-card space-y-2">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
            {league.name || "Regional League"}
          </div>
          <div className="text-xs text-muted-foreground mt-0.5">
            {played_matches}/{total_matches} matches played
          </div>
        </div>
        {player_record && (
          <div className="text-right">
            <span className="text-xs font-bold text-foreground">
              {player_record.wins}W–{player_record.losses}L
            </span>
            <div className="text-xs text-muted-foreground">{player_record.points} pts</div>
          </div>
        )}
      </div>

      <div className="space-y-0.5">
        {/* Header */}
        <div className="grid grid-cols-[20px_1fr_32px_32px_32px] gap-1 px-1 py-1 text-[10px] text-muted-foreground uppercase tracking-wide font-medium">
          <span>#</span>
          <span>Team</span>
          <span className="text-center">W</span>
          <span className="text-center">L</span>
          <span className="text-center">Pts</span>
        </div>
        {standings.map((s) => (
          <div
            key={s.org_id}
            className={`grid grid-cols-[20px_1fr_32px_32px_32px] gap-1 px-1 py-1.5 rounded text-xs items-center ${
              s.is_player
                ? "bg-primary/10 border border-primary/20"
                : "hover:bg-secondary/50"
            }`}
          >
            <span className={`text-center font-bold ${
              s.rank <= 3 ? "text-primary" : "text-muted-foreground"
            }`}>{s.rank}</span>
            <span className={`font-medium truncate ${s.is_player ? "text-primary" : ""}`}>
              {s.tag || s.name}
            </span>
            <span className="text-center text-green-400 font-semibold">{s.wins}</span>
            <span className="text-center text-red-400">{s.losses}</span>
            <span className={`text-center font-bold ${s.is_player ? "text-primary" : "text-foreground"}`}>
              {s.points}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function CalendarPage() {
  const { data: state }    = useGetGameState();
  const { data: cal }      = useGetCalendar();
  const { data: fixtures } = useGetFixtures();
  const { data: results }  = useGetResults();
  const advance = useAdvanceWeek();
  const qc = useQueryClient();
  const [lastResult, setLastResult] = useState<AdvanceResultLocal | null>(null);

  function handleAdvance() {
    setLastResult(null);
    advance.mutate(undefined, {
      onSuccess: (data) => {
        setLastResult(data as AdvanceResultLocal);
        qc.invalidateQueries({ queryKey: getGetGameStateQueryKey() });
        qc.invalidateQueries({ queryKey: getGetNewsQueryKey() });
        qc.invalidateQueries({ queryKey: getGetRankingsQueryKey() });
        qc.invalidateQueries({ queryKey: getGetRosterQueryKey() });
        qc.invalidateQueries({ queryKey: getGetResultsQueryKey() });
        qc.invalidateQueries({ queryKey: getGetFixturesQueryKey() });
        qc.invalidateQueries({ queryKey: getGetCalendarQueryKey() });
      },
    });
  }

  const playerMatches  = lastResult?.match_results.filter((r) => r.is_player_match)  ?? [];
  const otherMatches   = lastResult?.match_results.filter((r) => !r.is_player_match) ?? [];

  return (
    <div className="px-4 py-5 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-black">Calendar</h1>
          {state?.has_game && (
            <p className="text-muted-foreground text-xs">
              {state.week_label} · {state.season_phase}
            </p>
          )}
        </div>
        <button
          className="btn-primary px-5 py-2.5"
          onClick={handleAdvance}
          disabled={advance.isPending || !state?.has_game}
        >
          {advance.isPending ? "Simulating…" : "Advance Week"}
        </button>
      </div>

      {/* Season phase bar */}
      {cal && (
        <div className="stat-card space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              {cal.current_phase}
            </span>
            <span className="text-xs text-muted-foreground">
              {Math.round(cal.phase_progress * 100)}% complete
            </span>
          </div>
          <ProgressBar value={cal.phase_progress} />
          {cal.upcoming_events && cal.upcoming_events.length > 0 && (
            <ul className="text-xs text-muted-foreground space-y-0.5 mt-1">
              {cal.upcoming_events.slice(0, 3).map((ev, i) => (
                <li key={i} className="flex items-start gap-1.5">
                  <span className="text-primary mt-0.5">›</span>
                  <span>{ev}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Pipeline stage */}
      {cal?.pipeline_stage && (
        <div className="stat-card">
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
            Tournament Pipeline
          </div>
          <div className="flex items-center gap-1 text-xs">
            {[
              { label: "League", status: cal.pipeline_stage.league_status },
              { label: "Playoffs", status: cal.pipeline_stage.playoff_status },
              { label: "Major", status: cal.pipeline_stage.major_status },
            ].map((stage, i) => (
              <span key={i} className="flex items-center gap-1">
                <span
                  className={`px-2 py-0.5 rounded font-medium ${
                    stage.status === "completed"
                      ? "bg-green-500/20 text-green-400"
                      : stage.status === "ongoing"
                      ? "bg-primary/20 text-primary"
                      : "bg-secondary text-muted-foreground"
                  }`}
                >
                  {stage.label}
                </span>
                {i < 2 && <span className="text-muted-foreground">→</span>}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Season overall progress */}
      {cal?.season && (
        <div className="stat-card">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              Season {cal.season.year}
            </span>
            <span className="text-xs text-muted-foreground">
              {cal.season.cycles_completed}/{cal.season.cycles_total} cycles
            </span>
          </div>
          <ProgressBar
            value={(cal.season.cycles_completed || 0) / (cal.season.cycles_total || 3)}
          />
          {cal.season.ti_qual_status && (
            <div className="flex items-center gap-2 mt-2 text-xs">
              <span className="text-muted-foreground">TI Qual:</span>
              <span
                className={`font-medium ${
                  cal.season.ti_qual_status === "completed"
                    ? "text-green-400"
                    : cal.season.ti_qual_status === "ongoing"
                    ? "text-primary"
                    : "text-muted-foreground"
                }`}
              >
                {cal.season.ti_qual_status}
              </span>
              <span className="text-muted-foreground">· TI:</span>
              <span
                className={`font-medium ${
                  cal.season.ti_status === "completed"
                    ? "text-green-400"
                    : cal.season.ti_status === "ongoing"
                    ? "text-primary"
                    : "text-muted-foreground"
                }`}
              >
                {cal.season.ti_status}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Advancing spinner */}
      {advance.isPending && (
        <div className="stat-card text-center py-6">
          <div className="text-2xl mb-2 animate-spin inline-block">◎</div>
          <p className="text-sm text-muted-foreground">Simulating week…</p>
        </div>
      )}

      {/* Week results */}
      {lastResult && (
        <div className="space-y-3">
          <div className={`stat-card border-l-4 ${
            lastResult.week_summary.startsWith("Victory")
              ? "border-green-500 bg-green-500/5"
              : lastResult.week_summary.startsWith("Defeat")
              ? "border-red-500 bg-red-500/5"
              : "border-primary"
          }`}>
            <div className="text-xs text-muted-foreground mb-1 uppercase tracking-wide font-medium">
              Week Summary
            </div>
            <div className="font-semibold">{lastResult.week_summary}</div>
          </div>

          {playerMatches.length > 0 && (
            <div>
              <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
                Your Match
              </h2>
              <div className="space-y-2">
                {playerMatches.map((r, i) => (
                  <MatchRow key={i} r={r} />
                ))}
              </div>
            </div>
          )}

          {lastResult.new_news.length > 0 && (
            <div>
              <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
                Breaking News
              </h2>
              <div className="space-y-2">
                {lastResult.new_news.slice(0, 5).map((n) => (
                  <div key={n.id} className="stat-card py-2.5">
                    <div className="flex items-start gap-2">
                      <span className={`news-category shrink-0 ${CATEGORY_CLASS[n.category] ?? "nc-default"}`}>
                        {n.category}
                      </span>
                      <span className="text-sm leading-snug">{n.headline}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {otherMatches.length > 0 && (
            <div>
              <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
                Other Results
              </h2>
              <div className="space-y-2">
                {otherMatches.slice(0, 8).map((r, i) => (
                  <MatchRow key={i} r={r} dim />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* League standings */}
      {cal?.player_league && (
        <div>
          <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
            League Standings
          </h2>
          <StandingsTable league={cal.player_league} />
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
                      vs <span className="text-primary">{f.opponent_name}</span>{" "}
                      <span className="text-xs text-muted-foreground">({f.opponent_tag})</span>
                    </div>
                    <div className="text-xs text-muted-foreground mt-0.5">{f.round}</div>
                  </div>
                  <div className="text-right">
                    <span className="text-[10px] text-muted-foreground">
                      {f.is_home ? "HOME" : "AWAY"}
                    </span>
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
            Match History
          </h2>
          <div className="space-y-2">
            {results.map((r, i) => (
              <MatchRow key={i} r={r} />
            ))}
          </div>
        </div>
      )}

      {/* Active global tournaments */}
      {cal?.active_tournaments && cal.active_tournaments.length > 0 && (
        <div>
          <h2 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2">
            Active Tournaments
          </h2>
          <div className="space-y-2">
            {cal.active_tournaments.map((t) => (
              <div key={t.id} className="stat-card py-2.5 flex items-center justify-between">
                <div>
                  <div className="text-sm font-semibold">{t.name}</div>
                  <div className="text-xs text-muted-foreground capitalize">{t.type}</div>
                </div>
                {t.winner && (
                  <span className="text-xs text-primary font-bold">🏆 {t.winner}</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function MatchRow({
  r,
  dim,
}: {
  r: { tournament_name: string; team_a: string; team_b: string; score_a: number; score_b: number; winner: string };
  dim?: boolean;
}) {
  const aWon = r.score_a > r.score_b;
  return (
    <div className="match-result-row">
      <div className={`text-xs truncate max-w-[110px] ${dim ? "text-muted-foreground/60" : "text-muted-foreground"}`}>
        {r.tournament_name}
      </div>
      <div className="flex items-center gap-2 text-sm">
        <span className={aWon ? "font-bold text-foreground" : "text-muted-foreground"}>
          {r.team_a}
        </span>
        <span className={`font-mono font-bold ${dim ? "text-muted-foreground" : "text-primary"}`}>
          {r.score_a}:{r.score_b}
        </span>
        <span className={!aWon ? "font-bold text-foreground" : "text-muted-foreground"}>
          {r.team_b}
        </span>
      </div>
    </div>
  );
}
