import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RecurringTransactionCreateRequest(BaseModel):
    """Schema tạo mới quy tắc giao dịch định kỳ."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Tên quy tắc định kỳ (ví dụ: Tiền thuê nhà, Tiền điện, Nhận lương)",
    )
    type: Literal["income", "expense"] = Field(
        ...,
        description="Loại giao dịch: 'income' (thu nhập) hoặc 'expense' (chi tiêu)",
    )
    scope: Literal["personal", "family"] = Field(
        default="personal",
        description="Phạm vi: 'personal' (cá nhân) hoặc 'family' (gia đình)",
    )
    family_id: uuid.UUID | None = Field(
        default=None,
        description="ID nhóm gia đình (bắt buộc khi scope='family', cấm khi scope='personal')",
    )
    account_id: uuid.UUID = Field(
        ...,
        description="ID ví tài khoản áp dụng",
    )
    category_id: uuid.UUID = Field(
        ...,
        description="ID danh mục thu/chi tương thích",
    )
    amount: Decimal = Field(
        ...,
        gt=Decimal(0),
        decimal_places=2,
        description="Số tiền phát sinh định kỳ (phải lớn hơn 0)",
    )
    start_date: date = Field(
        ...,
        description="Ngày bắt đầu hiệu lực (YYYY-MM-DD)",
    )
    frequency: Literal["daily", "weekly", "monthly", "yearly"] = Field(
        ...,
        description="Chu kỳ lặp: 'daily', 'weekly', 'monthly', 'yearly'",
    )
    interval_value: int = Field(
        default=1,
        ge=1,
        description="Khoảng lặp (ví dụ 1 tháng/lần, 2 tuần/lần, 3 tháng/lần)",
    )
    end_date: date | None = Field(
        default=None,
        description="Ngày kết thúc quy tắc tùy chọn (nếu có, phải >= start_date)",
    )
    note: str | None = Field(
        default=None,
        max_length=500,
        description="Ghi chú thêm về quy tắc",
    )

    @field_validator("end_date")
    @classmethod
    def validate_end_date(cls, v: date | None, info) -> date | None:
        start_date = info.data.get("start_date")
        if v is not None and start_date is not None and v < start_date:
            raise ValueError("Ngày kết thúc (end_date) không được trước ngày bắt đầu (start_date).")
        return v


class RecurringTransactionUpdateRequest(BaseModel):
    """Schema cập nhật quy tắc giao dịch định kỳ."""

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Tên quy tắc",
    )
    category_id: uuid.UUID | None = Field(
        default=None,
        description="ID danh mục thu/chi mới",
    )
    amount: Decimal | None = Field(
        default=None,
        gt=Decimal(0),
        decimal_places=2,
        description="Số tiền định kỳ mới",
    )
    frequency: Literal["daily", "weekly", "monthly", "yearly"] | None = Field(
        default=None,
        description="Chu kỳ lặp mới",
    )
    interval_value: int | None = Field(
        default=None,
        ge=1,
        description="Khoảng lặp mới",
    )
    end_date: date | None = Field(
        default=None,
        description="Ngày kết thúc mới",
    )
    note: str | None = Field(
        default=None,
        max_length=500,
        description="Ghi chú",
    )


class RecurringTransactionResponse(BaseModel):
    """Schema dữ liệu trả về cho 1 quy tắc giao dịch định kỳ."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    type: Literal["income", "expense"]
    scope: Literal["personal", "family"]
    user_id: uuid.UUID | None
    family_id: uuid.UUID | None
    created_by: uuid.UUID
    account_id: uuid.UUID
    account_name: str
    currency: str
    category_id: uuid.UUID
    category_name: str
    category_icon: str | None
    category_color: str | None
    amount: Decimal
    start_date: date
    next_due_date: date
    frequency: Literal["daily", "weekly", "monthly", "yearly"]
    interval_value: int
    end_date: date | None
    note: str | None
    is_active: bool
    is_archived: bool
    is_completed: bool = False
    is_due: bool = False
    created_at: datetime
    updated_at: datetime


class RecurringTransactionGenerateResponse(BaseModel):
    """Kết quả tạo giao dịch thực tế từ một kỳ đến hạn."""

    message: str
    transaction_id: uuid.UUID
    recurrence_date: date
    next_due_date: date | None
    rule: RecurringTransactionResponse
