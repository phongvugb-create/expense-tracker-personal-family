import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ==============================================================================
# Transaction Request Schemas
# ==============================================================================
class TransactionCreateRequest(BaseModel):
    """Schema tạo giao dịch thu/chi mới."""

    account_id: uuid.UUID = Field(
        ...,
        description="ID của ví tài khoản liên quan",
    )
    category_id: uuid.UUID = Field(
        ...,
        description="ID danh mục thu chi (phải cùng loại với giao dịch)",
    )
    type: Literal["income", "expense"] = Field(
        ...,
        description="Loại giao dịch: 'income' (thu nhập) hoặc 'expense' (chi tiêu)",
    )
    amount: Decimal = Field(
        ...,
        gt=0,
        max_digits=15,
        decimal_places=2,
        description="Số tiền giao dịch (phải lớn hơn 0, tối đa 2 chữ số thập phân)",
    )
    note: str | None = Field(
        default=None,
        max_length=500,
        description="Ghi chú chi tiết cho giao dịch",
    )
    occurred_at: datetime | None = Field(
        default=None,
        description="Thời điểm phát sinh giao dịch (mặc định là thời điểm tạo nếu để trống)",
    )


class TransactionUpdateRequest(BaseModel):
    """Schema cập nhật giao dịch thu/chi."""

    category_id: uuid.UUID | None = Field(
        default=None,
        description="ID danh mục mới (phải cùng loại với giao dịch và hợp lệ với ví)",
    )
    type: Literal["income", "expense"] | None = Field(
        default=None,
        description="Loại giao dịch mới",
    )
    amount: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=15,
        decimal_places=2,
        description="Số tiền giao dịch mới (phải lớn hơn 0)",
    )
    note: str | None = Field(
        default=None,
        max_length=500,
        description="Ghi chú chi tiết mới",
    )
    occurred_at: datetime | None = Field(
        default=None,
        description="Thời điểm phát sinh giao dịch mới",
    )


# ==============================================================================
# Transaction Response Schema
# ==============================================================================
class TransactionResponse(BaseModel):
    """Schema phản hồi thông tin giao dịch."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    account_name: str | None = None
    account_currency: str | None = None
    category_id: uuid.UUID | None = None
    category_name: str | None = None
    category_icon: str | None = None
    category_color: str | None = None
    user_id: uuid.UUID
    creator_name: str | None = None
    type: Literal["income", "expense", "transfer_in", "transfer_out", "transfer_fee"]
    amount: Decimal
    note: str | None = None
    occurred_at: datetime
    created_at: datetime
    updated_at: datetime
