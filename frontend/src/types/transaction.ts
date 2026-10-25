export type TransactionType = 'income' | 'expense';

export interface Transaction {
  id: string;
  account_id: string;
  account_name?: string | null;
  category_id: string;
  category_name?: string | null;
  transfer_id?: string | null;
  user_id: string;
  creator_name?: string | null;
  type: TransactionType;
  amount: string; // Decimal string (ví dụ: "150000.00") để tránh sai số float JavaScript
  note?: string | null;
  occurred_at: string; // ISO 8601 string
  created_at: string;
  updated_at: string;
}

export interface TransactionCreateRequest {
  account_id: string;
  category_id: string;
  type: TransactionType;
  amount: string; // Decimal string, amount > 0
  note?: string | null;
  occurred_at: string; // ISO 8601 string
}

export interface TransactionUpdateRequest {
  category_id?: string;
  type?: TransactionType;
  amount?: string;
  note?: string | null;
  occurred_at?: string;
}

export interface TransactionQueryParams {
  account_id?: string;
  category_id?: string;
  type?: TransactionType;
  date_from?: string; // ISO 8601 string
  date_to?: string;   // ISO 8601 string
  limit?: number;
  offset?: number;
}
