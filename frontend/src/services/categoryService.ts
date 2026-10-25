import { apiClient } from './apiClient';
import type { Category, CategoryQueryParams } from '../types/category';

export const categoryService = {
  /**
   * Lấy danh sách danh mục thu/chi mà người dùng có quyền xem
   */
  async getCategories(params?: CategoryQueryParams): Promise<Category[]> {
    const response = await apiClient.get<Category[]>('/categories', {
      params: {
        ...(params?.type ? { type: params.type } : {}),
        ...(params?.scope ? { scope: params.scope } : {}),
        ...(params?.family_id ? { family_id: params.family_id } : {}),
        ...(params?.include_archived !== undefined
          ? { include_archived: params.include_archived }
          : {}),
      },
    });
    return response.data;
  },
};
