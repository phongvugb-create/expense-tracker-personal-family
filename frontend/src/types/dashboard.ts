export type DashboardScope = 'all' | 'personal' | 'family';

export interface DashboardPeriodInfo {
  year: number;
  month: number;
  start_date: string;
  end_date: string;
}

export interface DashboardFilterInfo {
  scope: DashboardScope;
  family_id?: string | null;
  family_name?: string | null;
}

export interface CurrencyBalanceInfo {
  currency: string;
  total_balance: string;
  active_accounts_count: number;
}

export interface CurrencyCashFlowInfo {
  currency: string;
  total_income: string;
  total_expense: string;
  total_transfer_fee: string;
  net_cash_flow: string;
}

export interface MonthlyTrendPoint {
  month_key: string;
  display_label: string;
  currency: string;
  income: string;
  expense: string;
  transfer_fee: string;
  net: string;
}

export interface ExpenseCategoryBreakdown {
  category_id: string;
  category_name: string;
  category_icon?: string | null;
  category_color?: string | null;
  currency: string;
  total_amount: string;
  percentage: string;
}

export interface RecentTransactionItem {
  id: string;
  account_id: string;
  account_name: string;
  currency: string;
  category_id?: string | null;
  category_name?: string | null;
  category_icon?: string | null;
  category_color?: string | null;
  type: string;
  amount: string;
  note?: string | null;
  occurred_at: string;
}

export interface RecentTransferItem {
  id: string;
  from_account_id: string;
  from_account_name: string;
  to_account_id: string;
  to_account_name: string;
  currency: string;
  amount: string;
  fee_amount: string;
  note?: string | null;
  occurred_at: string;
  is_voided: boolean;
}

export interface DashboardBudgetAlert {
  id: string;
  name?: string | null;
  scope: string;
  category_name: string;
  amount_limit: string;
  spent_amount: string;
  remaining_amount: string;
  overspent_amount: string;
  usage_percentage: string;
  warning_threshold: string;
  status: 'warning' | 'exceeded';
}

export interface DashboardSummaryResponse {
  period: DashboardPeriodInfo;
  filters: DashboardFilterInfo;
  balances_by_currency: CurrencyBalanceInfo[];
  cash_flow_by_currency: CurrencyCashFlowInfo[];
  monthly_trend: MonthlyTrendPoint[];
  expense_categories: ExpenseCategoryBreakdown[];
  recent_transactions: RecentTransactionItem[];
  recent_transfers: RecentTransferItem[];
  budget_alerts: DashboardBudgetAlert[];
}

export interface DashboardQueryParams {
  year?: number;
  month?: number;
  scope?: DashboardScope;
  family_id?: string;
}
