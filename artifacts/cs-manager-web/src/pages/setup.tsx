import { useState, useMemo } from "react";
import { useLocation } from "wouter";
import { useListOrgs, useNewGame } from "@workspace/api-client-react";

const REGIONS = ["all", "europe", "asia", "latin_america", "africa_oceania"];
const REGION_LABELS: Record<string, string> = {
  all: "All Regions",
  europe: "Europe",
  asia: "Asia",
  latin_america: "Latin America",
  africa_oceania: "Africa & Oceania",
};

export default function SetupPage() {
  const [, navigate] = useLocation();
  const { data: orgs, isLoading } = useListOrgs();
  const newGame = useNewGame();

  const [search, setSearch] = useState("");
  const [region, setRegion] = useState("all");
  const [selectedOrgId, setSelectedOrgId] = useState<string | null>(null);
  const [managerName, setManagerName] = useState("");
  const [step, setStep] = useState<"pick" | "name">("pick");

  const filtered = useMemo(() => {
    if (!orgs) return [];
    return orgs.filter((o) => {
      const matchRegion = region === "all" || o.region === region;
      const matchSearch =
        !search ||
        o.name.toLowerCase().includes(search.toLowerCase()) ||
        o.tag.toLowerCase().includes(search.toLowerCase());
      return matchRegion && matchSearch;
    });
  }, [orgs, region, search]);

  const selectedOrg = orgs?.find((o) => o.id === selectedOrgId);

  function handleSelectOrg(id: string) {
    setSelectedOrgId(id);
    setStep("name");
  }

  function handleStart() {
    if (!selectedOrgId || !managerName.trim()) return;
    newGame.mutate(
      { data: { org_id: selectedOrgId, manager_name: managerName.trim() } },
      {
        onSuccess: () => navigate("/"),
      }
    );
  }

  if (step === "name" && selectedOrg) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center px-6 py-12">
        <div className="w-full max-w-sm">
          <button
            onClick={() => setStep("pick")}
            className="text-muted-foreground text-sm mb-6 flex items-center gap-1 hover:text-foreground"
          >
            ← Back
          </button>

          <div className="text-center mb-8">
            <div className="tag-badge text-lg px-4 py-2 mb-3">{selectedOrg.tag}</div>
            <h1 className="text-2xl font-black">{selectedOrg.name}</h1>
            <div className={`region-badge region-${selectedOrg.region} mt-2 mx-auto w-fit`}>
              {REGION_LABELS[selectedOrg.region] ?? selectedOrg.region}
            </div>
            <div className="flex items-center justify-center gap-4 mt-3 text-sm text-muted-foreground">
              <span>Tier {selectedOrg.tier}</span>
              <span>Rating {selectedOrg.rating.toFixed(0)}</span>
              <span>${(selectedOrg.budget / 1_000_000).toFixed(1)}M budget</span>
            </div>
          </div>

          <div className="space-y-4">
            <div>
              <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-2 block">
                Your Manager Name
              </label>
              <input
                type="text"
                className="org-search"
                placeholder="Enter your name..."
                value={managerName}
                onChange={(e) => setManagerName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleStart()}
                autoFocus
              />
            </div>

            <button
              className="btn-primary w-full py-3 text-base"
              onClick={handleStart}
              disabled={!managerName.trim() || newGame.isPending}
            >
              {newGame.isPending ? "Generating world..." : "Start Career"}
            </button>

            {newGame.isPending && (
              <p className="text-xs text-center text-muted-foreground">
                Simulating 200 orgs and 2,000+ players... this takes ~10 seconds
              </p>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background flex flex-col px-4 py-8">
      <div className="max-w-2xl mx-auto w-full">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-black text-primary mb-1">CS MANAGER</h1>
          <p className="text-muted-foreground text-sm">Pick your organization to begin</p>
        </div>

        <div className="space-y-3 mb-4 sticky top-0 bg-background py-3 z-10">
          <input
            type="text"
            className="org-search"
            placeholder="Search orgs..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <div className="flex gap-2 overflow-x-auto pb-1 no-scrollbar">
            {REGIONS.map((r) => (
              <button
                key={r}
                onClick={() => setRegion(r)}
                className={`shrink-0 text-xs px-3 py-1.5 rounded-full font-medium transition-colors ${
                  region === r
                    ? "bg-primary text-primary-foreground"
                    : "bg-secondary text-muted-foreground hover:text-foreground"
                }`}
              >
                {REGION_LABELS[r]}
              </button>
            ))}
          </div>
        </div>

        {isLoading ? (
          <div className="text-center text-muted-foreground py-12">
            <div className="text-2xl mb-2">◎</div>
            <p className="text-sm">Generating world...</p>
          </div>
        ) : (
          <div className="space-y-2">
            {filtered.slice(0, 60).map((org) => (
              <button
                key={org.id}
                onClick={() => handleSelectOrg(org.id)}
                className="w-full text-left p-4 rounded-lg bg-card border border-border hover:border-primary/50 hover:bg-card/80 transition-all"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="tag-badge">{org.tag}</span>
                    <div>
                      <div className="font-semibold text-sm">{org.name}</div>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className={`region-badge region-${org.region}`}>
                          {REGION_LABELS[org.region] ?? org.region}
                        </span>
                        <span className="text-xs text-muted-foreground">T{org.tier}</span>
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-primary font-bold text-sm">{org.rating.toFixed(0)}</div>
                    <div className="text-xs text-muted-foreground">rating</div>
                  </div>
                </div>
              </button>
            ))}
            {filtered.length === 0 && (
              <p className="text-center text-muted-foreground py-8 text-sm">No orgs match your search</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
