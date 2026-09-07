import type {
  AccountDetail,
  AuthStatus,
  ClientsOverview,
  CostStructure,
  DashboardSummary,
  Payroll,
  Pnl,
  ProjectionBaseline,
  SyncStatus,
  Voucher,
} from "./types";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public needsSync = false,
  ) {
    super(message);
  }
}

async function getJson<T>(url: string): Promise<T> {
  const resp = await fetch(url);
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}) as Record<string, unknown>);
    throw new ApiError(
      resp.status,
      typeof body.detail === "string" ? body.detail : resp.statusText,
      body.needs_sync === true,
    );
  }
  return resp.json();
}

export const api = {
  authStatus: () => getJson<AuthStatus>("/auth/status"),
  logout: () => fetch("/auth/logout", { method: "POST" }),
  startSync: () => fetch("/api/sync", { method: "POST" }),
  syncStatus: () => getJson<SyncStatus>("/api/sync/status"),
  summary: (year?: number) =>
    getJson<DashboardSummary>(`/api/dashboard/summary${year ? `?year=${year}` : ""}`),
  pnl: (year?: number) => getJson<Pnl>(`/api/pnl${year ? `?year=${year}` : ""}`),
  account: (number: number, year?: number) =>
    getJson<AccountDetail>(`/api/accounts/${number}${year ? `?year=${year}` : ""}`),
  voucher: (series: string, number: number, year?: number) =>
    getJson<Voucher>(`/api/vouchers/${series}/${number}${year ? `?year=${year}` : ""}`),
  costs: (year?: number) => getJson<CostStructure>(`/api/costs${year ? `?year=${year}` : ""}`),
  clients: (year?: number) => getJson<ClientsOverview>(`/api/clients${year ? `?year=${year}` : ""}`),
  payroll: (year?: number) => getJson<Payroll>(`/api/payroll${year ? `?year=${year}` : ""}`),
  projection: (year?: number) =>
    getJson<ProjectionBaseline>(`/api/projection${year ? `?year=${year}` : ""}`),
};

export const kr = (n: number) =>
  `${Math.round(n).toLocaleString("en-US")} kr`;

export const krPlain = (n: number) => Math.round(n).toLocaleString("en-US");

export const MONTH_NAMES = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

export const monthLabel = (ym: string) => MONTH_NAMES[parseInt(ym.slice(5), 10) - 1] ?? ym;
