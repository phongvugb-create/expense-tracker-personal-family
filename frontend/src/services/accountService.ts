import { apiClient } from './apiClient';
import type {
  Account,
  AccountCreateRequest,
  AccountUpdateRequest,
  AccountQueryParams,
} from '../types/account';

export const accountService = {
  /**
   * Lấy danh sách ví tài khoản mà người dùng có quyền truy cập
   */
  async getAccounts(params?: AccountQueryParams): Promise<Account[]> {
    const response = await apiClient.get<Account[]>('/accounts', {
      params: {
        ...(params?.scope ? { scope: params.scope } : {}),
        ...(params?.family_id ? { family_id: params.family_id } : {}),
        ...(params?.include_archived !== undefined
          ? { include_archived: params.include_archived }
          : {}),
      },
    });
    return response.data;
  },

  /**
   * Lấy chi tiết thông tin ví và số dư khả dụng
   */
  async getAccountById(accountId: string): Promise<Account> {
    const response = await apiClient.get<Account>(`/accounts/${accountId}`);
    return response.data;
  },

  /**
   * Tạo ví mới (cá nhân hoặc gia đình)
   */
  async createAccount(data: AccountCreateRequest): Promise<Account> {
    const response = await apiClient.post<Account>('/accounts', data);
    return response.data;
  },

  /**
   * Cập nhật thông tin ví được phép (tên ví, loại ví)
   */
  async updateAccount(accountId: string, data: AccountUpdateRequest): Promise<Account> {
    const response = await apiClient.patch<Account>(`/accounts/${accountId}`, data);
    return response.data;
  },

  /**
   * Lưu trữ ví (is_archived = true)
   */
  async archiveAccount(accountId: string): Promise<Account> {
    const response = await apiClient.post<Account>(`/accounts/${accountId}/archive`);
    return response.data;
  },

  /**
   * Khôi phục ví đã lưu trữ (is_archived = false)
   */
  async restoreAccount(accountId: string): Promise<Account> {
    const response = await apiClient.post<Account>(`/accounts/${accountId}/restore`);
    return response.data;
  },
};
