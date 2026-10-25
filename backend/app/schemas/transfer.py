import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ==============================================================================
# Transfer Request Schemas
# ==============================================================================
class TransferCreateRequest(BaseModel):
    """Schema yêu cầu tạo giao dịch chuyển tiền giữa 2 ví."""

    from_account_id: uuid.UUID = Field(
        ...,
        description="ID ví nguồn (tiền chuyển đi)",
    )
    to_account_id: uuid.UUID = Field(
        ...,
        description="ID ví đích (tiền chuyển đến)",
    )
    amount: Decimal = Field(
        ...,
        gt=Decimal(0),
        decimal_places=2,
        max_digits=15,
        description="Số tiền chuyển (phải lớn hơn 0)",
    )
    fee_amount: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal(0),
        decimal_places=2,
        max_digits=15,
        description="Phí chuyển tiền (mặc định 0.00, không được âm)",
    )
    fee_category_id: uuid.UUID | None = Field(
        default=None,
        description="ID danh mục chi phí (bắt buộc khi fee_amount > 0)",
    )
    note: str | None = Field(
        default=None,
        max_length=500,
        description="Ghi chú chuyển khoản tùy chọn",
    )
    occurred_at: datetime | None = Field(
        default=None,
        description="Thời điểm phát sinh giao dịch chuyển khoản (mặc định là hiện tại UTC)",
    )

    @model_validator(mode="after")
    def validate_accounts_and_fee(self) -> "TransferCreateRequest":
        if self.from_account_id == self.to_account_id:
            raise ValueError("Ví nguồn và ví đích phải khác nhau.")
        if self.fee_amount > Decimal(0) and self.fee_category_id is None:
            raise ValueError("Vui lòng chọn danh mục chi phí khi có phát sinh phí chuyển tiền.")
        return self


# ==============================================================================
# Transfer Response Schemas
# ==============================================================================
class TransferResponse(BaseModel):
    """Schema phản hồi thông tin chi tiết một lượt chuyển tiền."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    from_account_id: uuid.UUID
    from_account_name: str | None = None
    to_account_id: uuid.UUID
    to_account_name: str | None = None
    created_by: uuid.UUID
    creator_name: str | None = None
    amount: Decimal
    fee_amount: Decimal
    fee_category_id: uuid.UUID | None = None
    currency: str | None = None
    note: str | None = None
    occurred_at: datetime
    created_at: datetime
    updated_at: datetime
    voided_at: datetime | None = None
    is_voided: bool = False
