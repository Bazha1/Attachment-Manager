import { Switch, Route, Router as WouterRouter, useLocation } from "wouter";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useGetGameState } from "@workspace/api-client-react";
import { useEffect } from "react";
import Layout from "@/components/Layout";
import SetupPage from "@/pages/setup";
import DashboardPage from "@/pages/dashboard";
import CalendarPage from "@/pages/calendar";
import RosterPage from "@/pages/roster";
import TransfersPage from "@/pages/transfers";
import NewsPage from "@/pages/news";
import RankingsPage from "@/pages/rankings";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 10_000 },
  },
});

function AuthGuard({ children }: { children: React.ReactNode }) {
  const { data: state, isLoading } = useGetGameState();
  const [, navigate] = useLocation();

  useEffect(() => {
    if (!isLoading && state && !state.has_game) {
      navigate("/setup");
    }
  }, [state, isLoading, navigate]);

  return <>{children}</>;
}

function Router() {
  return (
    <Switch>
      <Route path="/setup" component={SetupPage} />
      <Route path="/">
        {() => (
          <AuthGuard>
            <Layout>
              <DashboardPage />
            </Layout>
          </AuthGuard>
        )}
      </Route>
      <Route path="/calendar">
        {() => (
          <AuthGuard>
            <Layout>
              <CalendarPage />
            </Layout>
          </AuthGuard>
        )}
      </Route>
      <Route path="/roster">
        {() => (
          <AuthGuard>
            <Layout>
              <RosterPage />
            </Layout>
          </AuthGuard>
        )}
      </Route>
      <Route path="/transfers">
        {() => (
          <AuthGuard>
            <Layout>
              <TransfersPage />
            </Layout>
          </AuthGuard>
        )}
      </Route>
      <Route path="/news">
        {() => (
          <AuthGuard>
            <Layout>
              <NewsPage />
            </Layout>
          </AuthGuard>
        )}
      </Route>
      <Route path="/rankings">
        {() => (
          <AuthGuard>
            <Layout>
              <RankingsPage />
            </Layout>
          </AuthGuard>
        )}
      </Route>
    </Switch>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, "")}>
        <Router />
      </WouterRouter>
    </QueryClientProvider>
  );
}

export default App;
