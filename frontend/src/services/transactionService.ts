import { apiClient } from './apiClient';
import type {
  Transaction,
  TransactionCreateRequest,
  TransactionUpdateRequest,
  TransactionQueryParams,
} from '../types/transaction';

export const transactionService = {
  /**
   * Lấy danh sách giao dịch thu/chi có lọc và phân trang
   */
  async getTransactions(params?: TransactionQueryParams): Promise<Transaction[]> {
    const response = await apiClient.get<Transaction[]>('/transactions', {
      params: {
        ...(params?.account_id ? { account_id: params.account_id } : {}),
        ...(params?.category_id ? { category_id: params.category_id } : {}),
        ...(params?.type ? { type: params.type } : {}),
        ...(params?.date_from ? { date_from: params.date_from } : {}),
        ...(params?.date_to ? { date_to: params.date_to } : {}),
        ...(params?.limit !== undefined ? { limit: params.limit } : {}),
        ...(params?.offset !== undefined ? { offset: params.offset } : {}),
      },
    });
    return response.data;
  },

  /**
   * Lấy chi tiết một giao dịch
   */
  async getTransactionById(transactionId: string): Promise<Transaction> {
    const response = await apiClient.get<Transaction>(`/transactions/${transactionId}`);
    return response.data;
  },

  /**
   * Tạo giao dịch thu/chi mới
   */
  async createTransaction(data: TransactionCreateRequest): Promise<Transaction> {
    const response = await apiClient.post<Transaction>('/transactions', data);
    return response.data;
  },

  /**
   * Cập nhật thông tin giao dịch thu/chi (amount, category, type, note, occurred_at)
   */
  async updateTransaction(
    transactionId: string,
    data: TransactionUpdateRequest,
  ): Promise<Transaction> {
    const response = await apiClient.patch<Transaction>(
      `/transactions/${transactionId}`,
      data,
    );
    return response.data;
  },

  /**
   * Xóa mềm giao dịch (loại khỏi danh sách hoạt động và số dư ví)
   */
  async deleteTransaction(transactionId: string): Promise<{ message: string }> {
    const response = await apiClient.delete<{ message: string }>(
      `/transactions/${transactionId}`,
    );
    return response.data;
  },
};
