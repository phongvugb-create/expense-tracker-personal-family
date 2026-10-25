import { apiClient } from './apiClient';
import type { DashboardQueryParams, DashboardSummaryResponse } from '../types/dashboard';

export const dashboardService = {
  /**
   * Lấy báo cáo tổng quan tài chính thời gian thực từ backend
   */
  async getSummary(params?: DashboardQueryParams): Promise<DashboardSummaryResponse> {
    const response = await apiClient.get<DashboardSummaryResponse>('/dashboard/summary', {
      params: {
        ...(params?.year !== undefined ? { year: params.year } : {}),
        ...(params?.month !== undefined ? { month: params.month } : {}),
        ...(params?.scope ? { scope: params.scope } : {}),
        ...(params?.family_id ? { family_id: params.family_id } : {}),
      },
    });
    return response.data;
  },
};
