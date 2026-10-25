import { apiClient } from './apiClient';
import type { LoginRequest, MessageResponse, RegisterRequest, User } from '../types/auth';

export const authService = {
  async register(data: RegisterRequest): Promise<User> {
    const response = await apiClient.post<User>('/auth/register', data);
    return response.data;
  },

  async login(data: LoginRequest): Promise<User> {
    const response = await apiClient.post<User>('/auth/login', data);
    return response.data;
  },

  async getMe(): Promise<User> {
    const response = await apiClient.get<User>('/auth/me');
    return response.data;
  },

  async logout(): Promise<MessageResponse> {
    const response = await apiClient.post<MessageResponse>('/auth/logout');
    return response.data;
  },
};
