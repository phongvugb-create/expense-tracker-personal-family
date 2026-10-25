import { apiClient } from './apiClient';
import type { ReportQueryParams, ReportSummaryResponse } from '../types/report';

export const reportService = {
  /**
   * Lấy dữ liệu báo cáo tài chính tổng hợp
   */
  async getSummary(params: ReportQueryParams): Promise<ReportSummaryResponse> {
    const response = await apiClient.get<ReportSummaryResponse>('/reports/summary', {
      params,
    });
    return response.data;
  },

  /**
   * Tải tệp CSV báo cáo giao dịch chi tiết
   */
  async downloadCsv(params: ReportQueryParams): Promise<void> {
    const response = await apiClient.get('/reports/export.csv', {
      params,
      responseType: 'blob',
    });

    const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `bao-cao-tai-chinh_${params.date_from}_${params.date_to}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  },
};
