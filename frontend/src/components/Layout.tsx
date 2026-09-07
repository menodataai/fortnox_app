import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { api } from "../api";
import { ChatDrawer } from "./ChatDrawer";
import { SelectionAsk } from "./SelectionAsk";

export function Layout() {
  const [company, setCompany] = useState("");
  const [lastSync, setLastSync] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    fetch("/api/company")
      .then((r) => r.json())
      .then((c) => setCompany(c.CompanyName ?? ""))
      .catch(() => {});
    api
      .syncStatus()
      .then((s) => {
        setLastSync(s.last_sync);
        setSyncing(s.status === "running");
      })
      .catch(() => {});
  }, []);

  const resync = async () => {
    setSyncing(true);
    await api.startSync();
    const poll = setInterval(async () => {
      const s = await api.syncStatus().catch(() => null);
      if (s && s.status !== "running") {
        clearInterval(poll);
        setSyncing(false);
        setLastSync(s.last_sync);
        location.reload();
      }
    }, 1500);
  };

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="logo">
          <div className="logo-mark">Fi</div>
          <div className="logo-name">
            Fortnox Insights
            <small>{company || "…"}</small>
          </div>
        </div>
        <nav className="nav" aria-label="Main">
          <NavLink to="/" end>
            <span className="icon">◈</span>Overview
          </NavLink>
          <NavLink to="/pnl">
            <span className="icon">≣</span>Profit &amp; loss
          </NavLink>
          <NavLink to="/costs">
            <span className="icon">◔</span>Cost structure
          </NavLink>
          <NavLink to="/clients">
            <span className="icon">▣</span>Clients &amp; invoices
          </NavLink>
          <NavLink to="/payroll">
            <span className="icon">◉</span>Payroll
          </NavLink>
          <NavLink to="/projection">
            <span className="icon">↗</span>Year projection
          </NavLink>
          <div className="nav-label">Assistant</div>
          <button
            className="nav-chat"
            onClick={() => window.dispatchEvent(new CustomEvent("fi:open-chat"))}
          >
            <span className="icon">✦</span>Ask the AI
          </button>
        </nav>
        <div className="sidebar-foot">
          <div className="conn">
            <span className="conn-dot" aria-hidden="true" />
            <span>
              Connected to Fortnox
              <small>
                {syncing
                  ? "Syncing…"
                  : lastSync
                    ? `Synced ${new Date(lastSync).toLocaleString()}`
                    : "Not synced yet"}
              </small>
            </span>
          </div>
          <button className="link-button" onClick={resync} disabled={syncing}>
            Sync now
          </button>
          <button
            className="link-button"
            style={{ marginLeft: 12 }}
            onClick={async () => {
              await api.logout();
              location.href = "/";
            }}
          >
            Disconnect
          </button>
        </div>
      </aside>
      <main className="main">
        <Outlet />
      </main>
      <ChatDrawer />
      <SelectionAsk />
    </div>
  );
}
