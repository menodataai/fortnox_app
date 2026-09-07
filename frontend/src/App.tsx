import { useCallback, useEffect, useRef, useState } from "react";
import { Route, Routes } from "react-router-dom";
import { api } from "./api";
import { Layout } from "./components/Layout";
import { Account } from "./pages/Account";
import { Clients } from "./pages/Clients";
import { CostStructure } from "./pages/CostStructure";
import { Overview } from "./pages/Overview";
import { PayrollPage } from "./pages/PayrollPage";
import { ProfitLoss } from "./pages/ProfitLoss";
import { Projection } from "./pages/Projection";

type Phase =
  | { kind: "loading" }
  | { kind: "connect"; configured: boolean }
  | { kind: "syncing"; step: string }
  | { kind: "ready" }
  | { kind: "error"; message: string };

const SYNC_STEPS = ["starting", "company information", "financial years", "ledger", "invoices", "supplier invoices"];

function stepProgress(step: string): number {
  const idx = SYNC_STEPS.findIndex((s) => step.startsWith(s.split(" ")[0]) || step.includes(s));
  return idx < 0 ? 10 : Math.round(((idx + 1) / (SYNC_STEPS.length + 1)) * 100);
}

export default function App() {
  const [phase, setPhase] = useState<Phase>({ kind: "loading" });
  const pollRef = useRef<number | null>(null);

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  const pollSync = useCallback(() => {
    stopPolling();
    pollRef.current = window.setInterval(async () => {
      const s = await api.syncStatus().catch(() => null);
      if (!s) return;
      if (s.status === "running") {
        setPhase({ kind: "syncing", step: s.step });
      } else if (s.has_data) {
        stopPolling();
        setPhase({ kind: "ready" });
      } else if (s.status === "error") {
        stopPolling();
        setPhase({ kind: "error", message: s.error ?? "Sync failed" });
      }
    }, 1200);
  }, []);

  const boot = useCallback(async () => {
    setPhase({ kind: "loading" });
    try {
      const auth = await api.authStatus();
      if (!auth.connected) {
        setPhase({ kind: "connect", configured: auth.configured });
        return;
      }
      const sync = await api.syncStatus();
      if (sync.has_data && sync.status !== "running") {
        setPhase({ kind: "ready" });
        return;
      }
      if (sync.status !== "running") await api.startSync();
      setPhase({ kind: "syncing", step: "starting" });
      pollSync();
    } catch (e) {
      setPhase({ kind: "error", message: e instanceof Error ? e.message : String(e) });
    }
  }, [pollSync]);

  useEffect(() => {
    boot();
    return stopPolling;
  }, [boot]);

  if (phase.kind === "loading") {
    return (
      <div className="center-screen">
        <div className="panel">
          <h1>Fortnox Insights</h1>
          <p>Loading…</p>
        </div>
      </div>
    );
  }

  if (phase.kind === "connect") {
    return (
      <div className="center-screen">
        <div className="panel">
          <h1>Connect your Fortnox account</h1>
          {phase.configured ? (
            <>
              <p>
                Authorize this app to read your company's financial data. You'll be
                redirected to Fortnox to sign in and approve access. The app never
                writes anything to Fortnox.
              </p>
              <a className="button" href="/auth/login">
                Connect to Fortnox
              </a>
            </>
          ) : (
            <p>
              Add <code>FORTNOX_CLIENT_ID</code> and <code>FORTNOX_CLIENT_SECRET</code>{" "}
              to the <code>.env</code> file in the project root, then restart the backend.
            </p>
          )}
        </div>
      </div>
    );
  }

  if (phase.kind === "syncing") {
    return (
      <div className="center-screen">
        <div className="panel">
          <h1>Fetching your data from Fortnox</h1>
          <p>
            Building your local mirror — ledger, invoices and balances. This takes
            under a minute.
          </p>
          <div className="progress-track">
            <div className="progress-fill" style={{ width: `${stepProgress(phase.step)}%` }} />
          </div>
          <p style={{ fontSize: 12.5, color: "var(--ink-3)" }}>
            {phase.step ? `Syncing: ${phase.step}…` : "Starting…"}
          </p>
        </div>
      </div>
    );
  }

  if (phase.kind === "error") {
    return (
      <div className="center-screen">
        <div className="panel">
          <h1>Something went wrong</h1>
          <div className="error-banner">{phase.message}</div>
          <button className="button" onClick={boot}>
            Try again
          </button>
        </div>
      </div>
    );
  }

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Overview />} />
        <Route path="/pnl" element={<ProfitLoss />} />
        <Route path="/accounts/:number" element={<Account />} />
        <Route path="/costs" element={<CostStructure />} />
        <Route path="/clients" element={<Clients />} />
        <Route path="/payroll" element={<PayrollPage />} />
        <Route path="/projection" element={<Projection />} />
      </Route>
    </Routes>
  );
}
