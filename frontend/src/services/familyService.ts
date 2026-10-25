import { apiClient } from './apiClient';
import type {
  Family,
  FamilyMember,
  FamilyInvitation,
  FamilyCreateRequest,
  FamilyUpdateRequest,
  FamilyMemberRoleUpdateRequest,
  FamilyInvitationCreateRequest,
  FamilyInvitationAcceptRequest,
} from '../types/family';

export const familyService = {
  /**
   * Lấy danh sách nhóm gia đình mà người dùng có quyền truy cập
   */
  async getFamilies(): Promise<Family[]> {
    const response = await apiClient.get<Family[]>('/families');
    return response.data;
  },

  /**
   * Tạo nhóm gia đình mới
   */
  async createFamily(payload: FamilyCreateRequest): Promise<Family> {
    const response = await apiClient.post<Family>('/families', payload);
    return response.data;
  },

  /**
   * Xem thông tin chi tiết một nhóm gia đình
   */
  async getFamilyDetail(familyId: string): Promise<Family> {
    const response = await apiClient.get<Family>(`/families/${familyId}`);
    return response.data;
  },

  /**
   * Đổi tên nhóm gia đình (chỉ Owner)
   */
  async updateFamily(familyId: string, payload: FamilyUpdateRequest): Promise<Family> {
    const response = await apiClient.patch<Family>(`/families/${familyId}`, payload);
    return response.data;
  },

  /**
   * Lấy danh sách thành viên trong nhóm gia đình
   */
  async getFamilyMembers(familyId: string): Promise<FamilyMember[]> {
    const response = await apiClient.get<FamilyMember[]>(`/families/${familyId}/members`);
    return response.data;
  },

  /**
   * Thay đổi vai trò thành viên (chỉ Owner)
   */
  async updateMemberRole(
    familyId: string,
    memberId: string,
    payload: FamilyMemberRoleUpdateRequest
  ): Promise<FamilyMember> {
    const response = await apiClient.patch<FamilyMember>(
      `/families/${familyId}/members/${memberId}/role`,
      payload
    );
    return response.data;
  },

  /**
   * Rời nhóm (thành viên tự rời) hoặc loại thành viên (Owner kick)
   */
  async leaveFamily(familyId: string, memberId: string): Promise<{ message: string }> {
    const response = await apiClient.post<{ message: string }>(
      `/families/${familyId}/members/${memberId}/leave`
    );
    return response.data;
  },

  /**
   * Tạo lời mời thành viên tham gia nhóm (Owner hoặc Editor)
   */
  async createInvitation(
    familyId: string,
    payload: FamilyInvitationCreateRequest
  ): Promise<FamilyInvitation> {
    const response = await apiClient.post<FamilyInvitation>(
      `/families/${familyId}/invitations`,
      payload
    );
    return response.data;
  },

  /**
   * Lấy danh sách lời mời của nhóm gia đình (Owner hoặc Editor)
   */
  async getFamilyInvitations(familyId: string): Promise<FamilyInvitation[]> {
    const response = await apiClient.get<FamilyInvitation[]>(`/families/${familyId}/invitations`);
    return response.data;
  },

  /**
   * Thu hồi lời mời chưa được chấp nhận (Owner hoặc Editor)
   */
  async revokeInvitation(familyId: string, invitationId: string): Promise<{ message: string }> {
    const response = await apiClient.post<{ message: string }>(
      `/families/${familyId}/invitations/${invitationId}/revoke`
    );
    return response.data;
  },

  /**
   * Chấp nhận lời mời tham gia nhóm bằng token
   */
  async acceptInvitation(payload: FamilyInvitationAcceptRequest): Promise<FamilyMember> {
    const response = await apiClient.post<FamilyMember>('/families/invitations/accept', payload);
    return response.data;
  },
};
