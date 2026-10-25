import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ==============================================================================
# Family Schemas
# ==============================================================================
class FamilyCreateRequest(BaseModel):
    """Schema dữ liệu tạo nhóm gia đình mới."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Tên nhóm gia đình (ví dụ: Gia đình Hạnh Phúc, Quỹ chung Nhà Bờm)",
    )


class FamilyUpdateRequest(BaseModel):
    """Schema cập nhật tên nhóm gia đình."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Tên mới của nhóm gia đình",
    )


class FamilyResponse(BaseModel):
    """Schema phản hồi thông tin nhóm gia đình kèm vai trò của user hiện tại."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    owner_user_id: uuid.UUID
    my_role: Literal["owner", "editor", "viewer"]
    member_count: int
    created_at: datetime
    updated_at: datetime


# ==============================================================================
# Family Member Schemas
# ==============================================================================
class FamilyMemberResponse(BaseModel):
    """Schema thông tin thành viên trong nhóm gia đình."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    display_name: str
    email: str
    avatar_url: str | None = None
    role: Literal["owner", "editor", "viewer"]
    joined_at: datetime
    is_owner: bool


class FamilyMemberRoleUpdateRequest(BaseModel):
    """Schema thay đổi vai trò của thành viên."""

    role: Literal["editor", "viewer"] = Field(
        ...,
        description="Vai trò mới chỉ gồm editor hoặc viewer (không thể gán role owner)",
    )


# ==============================================================================
# Family Invitation Schemas
# ==============================================================================
class FamilyInvitationCreateRequest(BaseModel):
    """Schema tạo lời mời tham gia nhóm gia đình."""

    invited_email: EmailStr = Field(
        ...,
        description="Email của người được mời",
    )
    role: Literal["editor", "viewer"] = Field(
        default="viewer",
        description="Vai trò đề xuất cho thành viên khi tham gia (editor hoặc viewer)",
    )


class FamilyInvitationResponse(BaseModel):
    """Schema thông tin lời mời tham gia nhóm gia đình."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    family_id: uuid.UUID
    inviter_id: uuid.UUID
    inviter_name: str | None = None
    invited_email: str
    role: Literal["editor", "viewer"]
    expires_at: datetime
    created_at: datetime
    status: Literal["pending", "accepted", "declined", "revoked", "expired"]
    # raw_token chỉ được trả về một lần duy nhất lúc vừa tạo khi bật chế độ dev/demo
    invitation_token: str | None = None


class FamilyInvitationAcceptRequest(BaseModel):
    """Schema chấp nhận lời mời tham gia nhóm bằng token."""

    token: str = Field(
        ...,
        min_length=10,
        description="Mã token của lời mời nhận được",
    )
