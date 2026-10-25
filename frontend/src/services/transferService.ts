import { apiClient } from './apiClient';
import type {
  Transfer,
  TransferCreateRequest,
  TransferQueryParams,
} from '../types/transfer';

export const transferService = {
  /**
   * Lấy danh sách giao dịch chuyển tiền (có lọc và phân trang)
   */
  async getTransfers(params?: TransferQueryParams): Promise<Transfer[]> {
    const response = await apiClient.get<Transfer[]>('/transfers', {
      params: {
        ...(params?.account_id ? { account_id: params.account_id } : {}),
        ...(params?.date_from ? { date_from: params.date_from } : {}),
        ...(params?.date_to ? { date_to: params.date_to } : {}),
        ...(params?.include_voided !== undefined
          ? { include_voided: params.include_voided }
          : {}),
        ...(params?.limit !== undefined ? { limit: params.limit } : {}),
        ...(params?.offset !== undefined ? { offset: params.offset } : {}),
      },
    });
    return response.data;
  },

  /**
   * Xem chi tiết một giao dịch chuyển tiền
   */
  async getTransferById(transferId: string): Promise<Transfer> {
    const response = await apiClient.get<Transfer>(`/transfers/${transferId}`);
    return response.data;
  },

  /**
   * Tạo giao dịch chuyển tiền giữa 2 ví (hạch toán kép nguyên tử)
   */
  async createTransfer(data: TransferCreateRequest): Promise<Transfer> {
    const response = await apiClient.post<Transfer>('/transfers', data);
    return response.data;
  },

  /**
   * Hủy hiệu lực (void) giao dịch chuyển tiền
   */
  async voidTransfer(transferId: string): Promise<Transfer> {
    const response = await apiClient.post<Transfer>(`/transfers/${transferId}/void`);
    return response.data;
  },
};
