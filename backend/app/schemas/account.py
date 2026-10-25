import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AccountCreateRequest(BaseModel):
    """Schema dữ liệu tạo tài khoản ví mới."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Tên ví (ví dụ: Tiền mặt, Techcombank, Ví MoMo)",
    )
    scope: Literal["personal", "family"] = Field(
        ...,
        description="Phạm vi sở hữu ví: 'personal' hoặc 'family'",
    )
    account_type: Literal["cash", "bank", "e_wallet", "credit_card", "other"] = Field(
        default="cash",
        description="Phân loại ví tài chính",
    )
    currency: str = Field(
        default="VND",
        min_length=3,
        max_length=3,
        description="Mã tiền tệ chuẩn ISO 4217 (mặc định VND)",
    )
    initial_balance: Decimal = Field(
        default=Decimal("0.00"),
        description="Số dư khởi tạo ban đầu",
    )
    family_id: uuid.UUID | None = Field(
        default=None,
        description="ID nhóm gia đình (bắt buộc đối với ví gia đình, phải null với ví cá nhân)",
    )


class AccountUpdateRequest(BaseModel):
    """Schema dữ liệu cập nhật thông tin ví."""

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Tên ví mới",
    )
    account_type: Literal["cash", "bank", "e_wallet", "credit_card", "other"] | None = Field(
        default=None,
        description="Phân loại ví tài chính",
    )


class AccountResponse(BaseModel):
    """Schema dữ liệu phản hồi thông tin ví kèm số dư hiện tại."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    scope: str
    account_type: str
    currency: str
    initial_balance: Decimal
    current_balance: Decimal
    is_archived: bool
    family_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime
