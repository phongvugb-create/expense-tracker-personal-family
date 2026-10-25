import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegisterRequest(BaseModel):
    """Schema dữ liệu yêu cầu đăng ký tài khoản mới."""

    email: EmailStr = Field(..., description="Địa chỉ email hợp lệ của người dùng")
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="Mật khẩu bảo mật có độ dài từ 8 đến 128 ký tự",
    )
    display_name: str = Field(
        ...,
        min_length=2,
        max_length=150,
        description="Tên hiển thị người dùng từ 2 đến 150 ký tự",
    )


class UserLoginRequest(BaseModel):
    """Schema dữ liệu yêu cầu đăng nhập."""

    email: EmailStr = Field(..., description="Địa chỉ email đã đăng ký")
    password: str = Field(..., min_length=1, max_length=128, description="Mật khẩu tài khoản")


class UserResponse(BaseModel):
    """Schema phản hồi thông tin người dùng an toàn (không bao gồm password_hash)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    display_name: str
    avatar_url: str | None = None
    email_verified_at: datetime | None = None
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    """Schema thông điệp phản hồi chung."""

    message: str
