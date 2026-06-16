import { Link, useLocation } from "wouter";
import { useGetGameState } from "@workspace/api-client-react";

const NAV = [
  { path: "/", label: "Home", icon: "⌂" },
  { path: "/calendar", label: "Calendar", icon: "◷" },
  { path: "/roster", label: "Roster", icon: "◈" },
  { path: "/transfers", label: "Market", icon: "⇄" },
  { path: "/news", label: "News", icon: "◉" },
  { path: "/rankings", label: "Ranks", icon: "▲" },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const [location] = useLocation();
  const { data: state } = useGetGameState();

  return (
    <div className="min-h-screen bg-background flex flex-col max-w-2xl mx-auto">
      {/* Top bar */}
      <header className="sticky top-0 z-50 bg-background/95 backdrop-blur border-b border-border px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-primary font-black text-lg tracking-tight">CS MANAGER</span>
          {state?.has_game && (
            <span className="text-xs text-muted-foreground ml-1">{state.week_label}</span>
          )}
        </div>
        {state?.has_game && (
          <div className="flex items-center gap-3 text-xs">
            <span className="text-muted-foreground">
              <span className="text-primary font-bold">{state.org_tag}</span>
            </span>
            <span className="text-muted-foreground">
              ${(state.budget / 1000).toFixed(0)}k
            </span>
            <Link href="/setup">
              <span className="text-[10px] font-medium bg-primary/10 text-primary hover:bg-primary/20 px-2 py-1 rounded transition-colors cursor-pointer">
                + New Game
              </span>
            </Link>
          </div>
        )}
      </header>

      {/* Content */}
      <main className="flex-1 overflow-auto pb-20">
        {children}
      </main>

      {/* Bottom nav */}
      {state?.has_game && (
        <nav className="fixed bottom-0 left-0 right-0 z-50 bg-card/95 backdrop-blur border-t border-border max-w-2xl mx-auto">
          <div className="flex items-center">
            {NAV.map((item) => {
              const active = location === item.path;
              return (
                <Link key={item.path} href={item.path} className="flex-1">
                  <div className={`flex flex-col items-center py-2.5 gap-0.5 transition-colors ${
                    active ? "text-primary" : "text-muted-foreground"
                  }`}>
                    <span className="text-base leading-none">{item.icon}</span>
                    <span className="text-[10px] font-medium">{item.label}</span>
                  </div>
                </Link>
              );
            })}
          </div>
        </nav>
      )}
    </div>
  );
}
