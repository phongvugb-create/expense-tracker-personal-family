export type CategoryType = 'income' | 'expense';
export type CategoryScope = 'system' | 'personal' | 'family';

export interface Category {
  id: string;
  name: string;
  type: CategoryType;
  scope: CategoryScope;
  user_id?: string | null;
  family_id?: string | null;
  parent_id?: string | null;
  icon?: string | null;
  color?: string | null;
  is_default: boolean;
  is_archived: boolean;
  created_at: string;
  updated_at: string;
}

export interface CategoryQueryParams {
  type?: CategoryType;
  scope?: CategoryScope;
  family_id?: string;
  include_archived?: boolean;
}
