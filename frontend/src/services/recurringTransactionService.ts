import { apiClient } from './apiClient';
import type {
  RecurringTransaction,
  RecurringTransactionCreateRequest,
  RecurringTransactionUpdateRequest,
  RecurringTransactionQueryParams,
  RecurringTransactionGenerateResponse,
} from '../types/recurringTransaction';

export const recurringTransactionService = {
  /**
   * Lấy danh sách quy tắc định kỳ
   */
  async getRecurringTransactions(params?: RecurringTransactionQueryParams): Promise<RecurringTransaction[]> {
    const response = await apiClient.get<RecurringTransaction[]>('/recurring-transactions', {
      params: {
        ...(params?.scope ? { scope: params.scope } : {}),
        ...(params?.family_id ? { family_id: params.family_id } : {}),
        ...(params?.type ? { type: params.type } : {}),
        ...(params?.is_active !== undefined ? { is_active: params.is_active } : {}),
        ...(params?.is_archived !== undefined ? { is_archived: params.is_archived } : {}),
        ...(params?.due_before ? { due_before: params.due_before } : {}),
        ...(params?.limit !== undefined ? { limit: params.limit } : {}),
        ...(params?.offset !== undefined ? { offset: params.offset } : {}),
      },
    });
    return response.data;
  },

  /**
   * Xem chi tiết một quy tắc định kỳ
   */
  async getRecurringTransactionById(id: string): Promise<RecurringTransaction> {
    const response = await apiClient.get<RecurringTransaction>(`/recurring-transactions/${id}`);
    return response.data;
  },

  /**
   * Tạo mới quy tắc định kỳ
   */
  async createRecurringTransaction(payload: RecurringTransactionCreateRequest): Promise<RecurringTransaction> {
    const response = await apiClient.post<RecurringTransaction>('/recurring-transactions', payload);
    return response.data;
  },

  /**
   * Chỉnh sửa quy tắc định kỳ
   */
  async updateRecurringTransaction(id: string, payload: RecurringTransactionUpdateRequest): Promise<RecurringTransaction> {
    const response = await apiClient.patch<RecurringTransaction>(`/recurring-transactions/${id}`, payload);
    return response.data;
  },

  /**
   * Tạm dừng quy tắc định kỳ
   */
  async pauseRecurringTransaction(id: string): Promise<RecurringTransaction> {
    const response = await apiClient.post<RecurringTransaction>(`/recurring-transactions/${id}/pause`);
    return response.data;
  },

  /**
   * Kích hoạt lại quy tắc định kỳ
   */
  async resumeRecurringTransaction(id: string): Promise<RecurringTransaction> {
    const response = await apiClient.post<RecurringTransaction>(`/recurring-transactions/${id}/resume`);
    return response.data;
  },

  /**
   * Lưu trữ quy tắc định kỳ
   */
  async archiveRecurringTransaction(id: string): Promise<RecurringTransaction> {
    const response = await apiClient.post<RecurringTransaction>(`/recurring-transactions/${id}/archive`);
    return response.data;
  },

  /**
   * Tạo một giao dịch thực tế từ kỳ đến hạn hiện tại
   */
  async generateTransaction(id: string): Promise<RecurringTransactionGenerateResponse> {
    const response = await apiClient.post<RecurringTransactionGenerateResponse>(`/recurring-transactions/${id}/generate`);
    return response.data;
  },
};
