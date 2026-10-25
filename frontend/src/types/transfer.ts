export interface Transfer {
  id: string;
  from_account_id: string;
  from_account_name?: string | null;
  to_account_id: string;
  to_account_name?: string | null;
  created_by: string;
  creator_name?: string | null;
  amount: string; // Decimal string (ví dụ: "500000.00")
  fee_amount: string; // Decimal string (ví dụ: "2000.00")
  fee_category_id?: string | null;
  currency?: string | null;
  note?: string | null;
  occurred_at: string; // ISO 8601 string
  created_at: string;
  updated_at: string;
  voided_at?: string | null;
  is_voided: boolean;
}

export interface TransferCreateRequest {
  from_account_id: string;
  to_account_id: string;
  amount: string; // Decimal string, amount > 0
  fee_amount?: string; // Decimal string, fee_amount >= 0, default "0.00"
  fee_category_id?: string | null; // Bắt buộc khi fee_amount > 0
  note?: string | null;
  occurred_at?: string | null; // ISO 8601 string
}

export interface TransferQueryParams {
  account_id?: string;
  date_from?: string; // ISO 8601 string
  date_to?: string;   // ISO 8601 string
  include_voided?: boolean;
  limit?: number;
  offset?: number;
}
