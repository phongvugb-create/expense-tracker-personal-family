import { apiClient } from './apiClient';
import type {
  Budget,
  BudgetCreateRequest,
  BudgetUpdateRequest,
  BudgetQueryParams,
} from '../types/budget';

export const budgetService = {
  /**
   * Lấy danh sách ngân sách có quyền truy cập
   */
  async getBudgets(params?: BudgetQueryParams): Promise<Budget[]> {
    const response = await apiClient.get<Budget[]>('/budgets', {
      params: {
        ...(params?.scope ? { scope: params.scope } : {}),
        ...(params?.family_id ? { family_id: params.family_id } : {}),
        ...(params?.category_id ? { category_id: params.category_id } : {}),
        ...(params?.include_archived !== undefined
          ? { include_archived: params.include_archived }
          : {}),
        ...(params?.active_on ? { active_on: params.active_on } : {}),
        ...(params?.limit !== undefined ? { limit: params.limit } : {}),
        ...(params?.offset !== undefined ? { offset: params.offset } : {}),
      },
    });
    return response.data;
  },

  /**
   * Lấy chi tiết một ngân sách theo ID
   */
  async getBudgetById(budgetId: string): Promise<Budget> {
    const response = await apiClient.get<Budget>(`/budgets/${budgetId}`);
    return response.data;
  },

  /**
   * Tạo ngân sách mới (cá nhân hoặc gia đình)
   */
  async createBudget(payload: BudgetCreateRequest): Promise<Budget> {
    const response = await apiClient.post<Budget>('/budgets', payload);
    return response.data;
  },

  /**
   * Chỉnh sửa thông tin ngân sách
   */
  async updateBudget(budgetId: string, payload: BudgetUpdateRequest): Promise<Budget> {
    const response = await apiClient.patch<Budget>(`/budgets/${budgetId}`, payload);
    return response.data;
  },

  /**
   * Lưu trữ ngân sách (is_archived = true)
   */
  async archiveBudget(budgetId: string): Promise<Budget> {
    const response = await apiClient.post<Budget>(`/budgets/${budgetId}/archive`);
    return response.data;
  },

  /**
   * Khôi phục ngân sách từ lưu trữ (is_archived = false)
   */
  async restoreBudget(budgetId: string): Promise<Budget> {
    const response = await apiClient.post<Budget>(`/budgets/${budgetId}/restore`);
    return response.data;
  },
};
