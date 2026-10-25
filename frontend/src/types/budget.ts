export type BudgetScope = 'personal' | 'family';
export type BudgetStatus = 'normal' | 'warning' | 'exceeded';

export interface Budget {
  id: string;
  name?: string | null;
  scope: BudgetScope;
  user_id?: string | null;
  family_id?: string | null;
  category_id: string;
  category_name?: string | null;
  category_icon?: string | null;
  category_color?: string | null;
  amount_limit: string;
  period_start: string;
  period_end: string;
  warning_threshold: string;
  is_archived: boolean;
  created_at: string;
  updated_at: string;

  // Dynamic computed fields from backend
  spent_amount: string;
  remaining_amount: string;
  overspent_amount: string;
  usage_percentage: string;
  status: BudgetStatus;
}

export interface BudgetCreateRequest {
  name?: string | null;
  scope: BudgetScope;
  family_id?: string | null;
  category_id: string;
  amount_limit: string;
  period_start: string;
  period_end: string;
  warning_threshold?: string;
}

export interface BudgetUpdateRequest {
  name?: string | null;
  category_id?: string | null;
  amount_limit?: string | null;
  period_start?: string | null;
  period_end?: string | null;
  warning_threshold?: string | null;
}

export interface BudgetQueryParams {
  scope?: BudgetScope;
  family_id?: string;
  category_id?: string;
  include_archived?: boolean;
  active_on?: string;
  limit?: number;
  offset?: number;
}
