export type NotificationType =
  | 'recurring_due_soon'
  | 'recurring_due_today'
  | 'recurring_overdue'
  | 'budget_warning'
  | 'budget_exceeded'
  | 'system';

export interface NotificationItem {
  id: string;
  user_id: string;
  type: NotificationType;
  title: string;
  message: string;
  source_key: string;
  entity_type?: string | null;
  entity_id?: string | null;
  action_url?: string | null;
  metadata?: Record<string, unknown> | null;
  read_at?: string | null; // ISO 8601
  archived_at?: string | null; // ISO 8601
  created_at: string; // ISO 8601
  updated_at: string; // ISO 8601
}

export interface NotificationQueryParams {
  unread_only?: boolean;
  include_archived?: boolean;
  type?: NotificationType;
  limit?: number;
  offset?: number;
}

export interface NotificationSyncResponse {
  created_count: number;
  updated_count: number;
  unread_count: number;
  message: string;
}

export interface NotificationUnreadCountResponse {
  unread_count: number;
}
