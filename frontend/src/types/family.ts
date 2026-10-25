export type FamilyRole = 'owner' | 'editor' | 'viewer';

export interface Family {
  id: string;
  name: string;
  owner_user_id: string;
  my_role: FamilyRole;
  member_count: number;
  created_at: string;
  updated_at: string;
}

export interface FamilyMember {
  id: string;
  user_id: string;
  display_name: string;
  email: string;
  avatar_url?: string | null;
  role: FamilyRole;
  joined_at: string;
  is_owner: boolean;
}

export type InvitationStatus = 'pending' | 'accepted' | 'declined' | 'revoked' | 'expired';

export interface FamilyInvitation {
  id: string;
  family_id: string;
  inviter_id: string;
  inviter_name?: string | null;
  invited_email: string;
  role: 'editor' | 'viewer';
  expires_at: string;
  created_at: string;
  status: InvitationStatus;
  invitation_token?: string | null;
}

export interface FamilyCreateRequest {
  name: string;
}

export interface FamilyUpdateRequest {
  name: string;
}

export interface FamilyMemberRoleUpdateRequest {
  role: 'editor' | 'viewer';
}

export interface FamilyInvitationCreateRequest {
  invited_email: string;
  role: 'editor' | 'viewer';
}

export interface FamilyInvitationAcceptRequest {
  token: string;
}
