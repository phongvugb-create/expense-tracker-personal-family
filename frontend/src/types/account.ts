export type AccountScope = 'personal' | 'family';

export type AccountType = 'cash' | 'bank' | 'e_wallet' | 'credit_card' | 'other';

export interface Account {
  id: string;
  name: string;
  scope: AccountScope;
  account_type: AccountType;
  currency: string;
  initial_balance: string; // Decimal serialized as string/number
  current_balance: string; // Calculated Decimal balance from PostgreSQL
  is_archived: boolean;
  family_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface AccountCreateRequest {
  name: string;
  scope: AccountScope;
  account_type?: AccountType;
  currency?: string;
  initial_balance?: string;
  family_id?: string | null;
}

export interface AccountUpdateRequest {
  name?: string;
  account_type?: AccountType;
}

export interface AccountQueryParams {
  scope?: AccountScope;
  family_id?: string;
  include_archived?: boolean;
}
