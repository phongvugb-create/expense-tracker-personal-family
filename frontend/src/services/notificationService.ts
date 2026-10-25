import { apiClient } from './apiClient';
import type {
  NotificationItem,
  NotificationQueryParams,
  NotificationSyncResponse,
  NotificationUnreadCountResponse,
} from '../types/notification';

export const notificationService = {
  /**
   * Đồng bộ thông báo tài chính từ các khoản định kỳ và ngân sách (idempotent)
   */
  async syncNotifications(): Promise<NotificationSyncResponse> {
    const response = await apiClient.post<NotificationSyncResponse>('/notifications/sync');
    return response.data;
  },

  /**
   * Lấy danh sách thông báo của người dùng
   */
  async getNotifications(params?: NotificationQueryParams): Promise<NotificationItem[]> {
    const response = await apiClient.get<NotificationItem[]>('/notifications', {
      params: {
        ...(params?.unread_only !== undefined ? { unread_only: params.unread_only } : {}),
        ...(params?.include_archived !== undefined ? { include_archived: params.include_archived } : {}),
        ...(params?.type ? { type: params.type } : {}),
        ...(params?.limit !== undefined ? { limit: params.limit } : {}),
        ...(params?.offset !== undefined ? { offset: params.offset } : {}),
      },
    });
    return response.data;
  },

  /**
   * Đếm số lượng thông báo chưa đọc
   */
  async getUnreadCount(): Promise<number> {
    const response = await apiClient.get<NotificationUnreadCountResponse>('/notifications/unread-count');
    return response.data.unread_count;
  },

  /**
   * Đánh dấu một thông báo là đã đọc
   */
  async markAsRead(notificationId: string): Promise<NotificationItem> {
    const response = await apiClient.patch<NotificationItem>(`/notifications/${notificationId}/read`);
    return response.data;
  },

  /**
   * Đánh dấu tất cả thông báo chưa đọc là đã đọc
   */
  async markAllAsRead(): Promise<{ marked_count: number }> {
    const response = await apiClient.post<{ marked_count: number }>('/notifications/mark-all-read');
    return response.data;
  },

  /**
   * Lưu trữ một thông báo
   */
  async archiveNotification(notificationId: string): Promise<NotificationItem> {
    const response = await apiClient.post<NotificationItem>(`/notifications/${notificationId}/archive`);
    return response.data;
  },
};
