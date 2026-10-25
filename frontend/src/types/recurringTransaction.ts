export type RecurringTransactionType = 'income' | 'expense';
export type RecurrenceFrequency = 'daily' | 'weekly' | 'monthly' | 'yearly';
export type RecurringScope = 'personal' | 'family' | 'all';

export interface RecurringTransaction {
  id: string;
  name: string;
  type: RecurringTransactionType;
  account_id: string;
  account_name?: string | null;
  currency: string;
  category_id: string;
  category_name?: string | null;
  user_id: string;
  creator_name?: string | null;
  scope: 'personal' | 'family';
  family_id?: string | null;
  amount: string; // Decimal string ví dụ "4500000.00"
  frequency: RecurrenceFrequency;
  interval_value: number;
  start_date: string; // YYYY-MM-DD
  next_due_date: string; // YYYY-MM-DD
  end_date?: string | null; // YYYY-MM-DD
  note?: string | null;
  is_active: boolean;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface RecurringTransactionCreateRequest {
  name: string;
  type: RecurringTransactionType;
  account_id: string;
  category_id: string;
  amount: string; // Decimal string > 0
  frequency: RecurrenceFrequency;
  interval_value?: number;
  start_date: string;
  end_date?: string | null;
  note?: string | null;
  scope?: 'personal' | 'family';
  family_id?: string | null;
}

export interface RecurringTransactionUpdateRequest {
  name?: string;
  category_id?: string;
  amount?: string;
  frequency?: RecurrenceFrequency;
  interval_value?: number;
  end_date?: string | null;
  note?: string | null;
  is_active?: boolean;
}

export interface RecurringTransactionQueryParams {
  scope?: RecurringScope;
  family_id?: string;
  type?: RecurringTransactionType;
  is_active?: boolean;
  is_archived?: boolean;
  due_before?: string; // YYYY-MM-DD
  limit?: number;
  offset?: number;
}

export interface RecurringTransactionGenerateResponse {
  message: string;
  transaction_id: string;
  recurrence_date: string;
  next_due_date: string | null;
  rule: RecurringTransaction;
}
