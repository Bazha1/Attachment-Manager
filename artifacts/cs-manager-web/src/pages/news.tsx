import { useState } from "react";
import { useGetNews } from "@workspace/api-client-react";

const CATEGORIES = ["all", "upset", "transfer", "record", "result", "general"];

const categoryClass: Record<string, string> = {
  upset: "nc-upset",
  transfer: "nc-transfer",
  record: "nc-record",
  result: "nc-result",
  general: "nc-default",
};

export default function NewsPage() {
  const { data: news, isLoading } = useGetNews();
  const [filter, setFilter] = useState("all");

  const filtered = (news ?? []).filter(
    (n) => filter === "all" || n.category === filter
  );

  return (
    <div className="px-4 py-5 space-y-4">
      <h1 className="text-lg font-black">News Feed</h1>

      <div className="flex gap-1.5 overflow-x-auto pb-1">
        {CATEGORIES.map((c) => (
          <button
            key={c}
            onClick={() => setFilter(c)}
            className={`shrink-0 text-xs px-3 py-1.5 rounded-full font-medium transition-colors capitalize ${
              filter === c
                ? "bg-primary text-primary-foreground"
                : "bg-secondary text-muted-foreground hover:text-foreground"
            }`}
          >
            {c}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="text-center text-muted-foreground py-8">
          <div className="text-2xl mb-2">◎</div>
          <p className="text-sm">Loading news...</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.length === 0 && (
            <p className="text-center text-muted-foreground py-8 text-sm">
              No news yet — advance some weeks to generate news
            </p>
          )}
          {filtered.map((n) => (
            <div key={n.id} className="stat-card py-3">
              <div className="flex items-start gap-2">
                <span className={`news-category shrink-0 mt-0.5 ${categoryClass[n.category] ?? "nc-default"}`}>
                  {n.category}
                </span>
                <div className="min-w-0">
                  <p className="text-sm leading-snug">{n.headline}</p>
                  <p className="text-xs text-muted-foreground mt-1">{n.timestamp}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
