export interface ReportPeriodInfo {
  date_from: string;
  date_to: string;
  days_count: number;
}

export interface ReportFilterInfo {
  scope: 'all' | 'personal' | 'family';
  family_id: string | null;
  family_name: string | null;
  account_id: string | null;
  account_name: string | null;
}

export interface ReportCashFlowByCurrency {
  currency: string;
  total_income: string;
  total_expense: string;
  total_transfer_fee: string;
  net_cash_flow: string;
}

export interface ReportCategoryBreakdown {
  category_id: string;
  category_name: string;
  category_icon: string | null;
  category_color: string | null;
  currency: string;
  total_amount: string;
  percentage: string;
}

export interface ReportAccountBreakdown {
  account_id: string;
  account_name: string;
  account_type: string;
  currency: string;
  scope: string;
  total_income: string;
  total_expense: string;
  net_amount: string;
}

export interface ReportMonthlyTrendPoint {
  month_key: string;
  display_label: string;
  currency: string;
  income: string;
  expense: string;
  transfer_fee: string;
  net: string;
}

export interface ReportTopExpenseItem {
  id: string;
  account_id: string;
  account_name: string;
  currency: string;
  category_id: string | null;
  category_name: string | null;
  category_icon: string | null;
  category_color: string | null;
  amount: string;
  occurred_at: string;
  description: string | null;
}

export interface PeriodComparisonCurrency {
  currency: string;
  current_income: string;
  previous_income: string;
  income_change_amount: string;
  income_change_percentage: string | null;

  current_expense: string;
  previous_expense: string;
  expense_change_amount: string;
  expense_change_percentage: string | null;

  current_net: string;
  previous_net: string;
  net_change_amount: string;
  net_change_percentage: string | null;
}

export interface ReportComparison {
  previous_date_from: string;
  previous_date_to: string;
  by_currency: PeriodComparisonCurrency[];
}

export interface ReportSummaryResponse {
  period: ReportPeriodInfo;
  filters: ReportFilterInfo;
  cash_flow_by_currency: ReportCashFlowByCurrency[];
  category_breakdown: ReportCategoryBreakdown[];
  account_breakdown: ReportAccountBreakdown[];
  monthly_trend: ReportMonthlyTrendPoint[];
  top_expenses: ReportTopExpenseItem[];
  comparison: ReportComparison | null;
}

export interface ReportQueryParams {
  date_from: string;
  date_to: string;
  scope?: 'all' | 'personal' | 'family';
  family_id?: string;
  account_id?: string;
}
