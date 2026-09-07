export interface AuthStatus {
  connected: boolean;
  configured: boolean;
  scopes: string | null;
}

export interface SyncStatus {
  status: "idle" | "running" | "done" | "error";
  step: string;
  error: string | null;
  counts: Record<string, number>;
  last_sync: string | null;
  has_data: boolean;
}

export interface AttentionItem {
  level: "critical" | "warning" | "info";
  title: string;
  detail: string;
}

export interface DashboardSummary {
  year: number;
  company_name: string;
  currency: string;
  revenue_ytd: number;
  costs_ytd: number;
  profit_ytd: number;
  cash: number;
  outstanding_total: number;
  outstanding_count: number;
  overdue_total: number;
  overdue_count: number;
  monthly: { months: string[]; revenue: number[]; costs: number[] };
  attention: AttentionItem[];
  last_sync: string | null;
}

export interface PnlAccount {
  number: number;
  name: string;
  monthly: number[];
  total: number;
}

export interface PnlGroup {
  key: string;
  name: string;
  monthly: number[];
  total: number;
  accounts: PnlAccount[];
}

export interface Pnl {
  year: number;
  months: string[];
  groups: PnlGroup[];
  revenue_total: number;
  costs_total: number;
  financial_net: number;
  profit_before_tax: number;
  profit_monthly: number[];
}

export interface AccountTxn {
  date: string;
  series: string;
  voucher_number: number;
  description: string;
  amount: number;
  running: number;
}

export interface AccountDetail {
  year: number;
  number: number;
  name: string;
  explain: string | null;
  group: string;
  is_balance_account: boolean;
  ib: number;
  ub: number | null;
  period_total: number;
  monthly_average: number;
  months: string[];
  monthly: number[];
  transaction_count: number;
  transactions: AccountTxn[];
}

export interface CostCategory {
  label: string;
  account: number | null;
  total: number;
  share: number;
}

export interface RecurringCost {
  label: string;
  account: number | string;
  frequency: "Monthly" | "Quarterly";
  per_month: number;
  trend: number;
}

export interface OneOff {
  date: string;
  account: number;
  description: string;
  amount: number;
  series: string;
  voucher_number: number;
}

export interface CostStructure {
  year: number;
  months: string[];
  elapsed_months: number;
  total_costs: number;
  monthly_costs: number[];
  categories: CostCategory[];
  recurring: RecurringCost[];
  burn_per_month: number;
  cash: number;
  runway_months: number | null;
  oneoff_total: number;
  oneoffs: OneOff[];
}

export interface ClientRow {
  name: string;
  invoiced_fy: number;
  invoiced_alltime: number;
  count_fy: number;
  outstanding: number;
  share_fy: number;
  avg_days_to_pay: number | null;
  last_invoice_date: string | null;
  last_invoice_number: string;
  active: boolean;
}

export interface ClientInvoice {
  document_number: string;
  customer_name: string;
  invoice_date: string | null;
  due_date: string | null;
  final_pay_date: string | null;
  total: number;
  balance: number;
  status: "paid" | "open" | "overdue";
}

export interface ClientsOverview {
  year: number;
  invoiced_total: number;
  invoice_count: number;
  outstanding_total: number;
  outstanding_count: number;
  avg_days_to_pay: number | null;
  active_clients: number;
  top_client_share: number;
  clients: ClientRow[];
  invoices: ClientInvoice[];
}

export interface PayrollBucket {
  key: string;
  label: string;
  monthly: number[];
  total: number;
}

export interface Payroll {
  year: number;
  months: string[];
  buckets: PayrollBucket[];
  total: number;
  avg_month: Record<string, number>;
  multiplier: number | null;
  monthly_total: number[];
}

export interface ProjectionBaseline {
  year: number;
  months: string[];
  elapsed_months: number;
  actual_revenue: number[];
  actual_costs: number[];
  revenue_ytd: number;
  costs_ytd: number;
  financial_net: number;
  defaults: { revenue_per_month: number; costs_per_month: number; oneoff_costs: number };
  tax_rate: number;
}

export interface VoucherRow {
  account: number;
  name: string;
  debit: number | null;
  credit: number | null;
}

export interface Voucher {
  series: string;
  number: number;
  date: string;
  description: string;
  rows: VoucherRow[];
}
