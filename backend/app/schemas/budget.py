import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class BudgetBase(BaseModel):
    """Base schema cho dữ liệu ngân sách chi tiêu."""

    name: str | None = Field(
        default=None,
        max_length=100,
        description="Tên gợi nhớ cho ngân sách (tùy chọn)",
    )
    category_id: uuid.UUID = Field(
        ...,
        description="ID danh mục chi tiêu cần quản lý hạn mức",
    )
    amount_limit: Decimal = Field(
        ...,
        gt=Decimal("0.00"),
        decimal_places=2,
        max_digits=15,
        description="Hạn mức chi tiêu tối đa trong kỳ (phải > 0)",
    )
    period_start: date = Field(
        ...,
        description="Ngày bắt đầu kỳ ngân sách",
    )
    period_end: date = Field(
        ...,
        description="Ngày kết thúc kỳ ngân sách (phải >= period_start)",
    )
    warning_threshold: Decimal = Field(
        default=Decimal("80.00"),
        gt=Decimal("0.00"),
        le=Decimal("100.00"),
        decimal_places=2,
        max_digits=5,
        description="Ngưỡng cảnh báo chi tiêu (0 < threshold <= 100, mặc định 80%)",
    )

    @field_validator("period_end")
    @classmethod
    def validate_period_range(cls, v: date, info) -> date:
        if "period_start" in info.data and v < info.data["period_start"]:
            raise ValueError("Ngày kết thúc ngân sách (period_end) không được trước ngày bắt đầu (period_start).")
        return v


class BudgetCreateRequest(BudgetBase):
    """Schema tạo mới ngân sách cá nhân hoặc gia đình."""

    scope: Literal["personal", "family"] = Field(
        ...,
        description="Phạm vi ngân sách: 'personal' hoặc 'family'",
    )
    family_id: uuid.UUID | None = Field(
        default=None,
        description="ID nhóm gia đình (bắt buộc khi scope = 'family', không được có khi scope = 'personal')",
    )

    @field_validator("family_id")
    @classmethod
    def validate_scope_ownership(cls, v: uuid.UUID | None, info) -> uuid.UUID | None:
        scope = info.data.get("scope")
        if scope == "family" and v is None:
            raise ValueError("Ngân sách gia đình (scope='family') bắt buộc phải có 'family_id'.")
        if scope == "personal" and v is not None:
            raise ValueError("Ngân sách cá nhân (scope='personal') không được truyền 'family_id'.")
        return v


class BudgetUpdateRequest(BaseModel):
    """Schema cập nhật thông tin ngân sách (không cho phép thay đổi scope, user_id, family_id)."""

    name: str | None = Field(
        default=None,
        max_length=100,
        description="Tên gợi nhớ cho ngân sách",
    )
    category_id: uuid.UUID | None = Field(
        default=None,
        description="ID danh mục chi tiêu mới",
    )
    amount_limit: Decimal | None = Field(
        default=None,
        gt=Decimal("0.00"),
        decimal_places=2,
        max_digits=15,
        description="Hạn mức chi tiêu tối đa mới (phải > 0)",
    )
    period_start: date | None = Field(
        default=None,
        description="Ngày bắt đầu kỳ mới",
    )
    period_end: date | None = Field(
        default=None,
        description="Ngày kết thúc kỳ mới",
    )
    warning_threshold: Decimal | None = Field(
        default=None,
        gt=Decimal("0.00"),
        le=Decimal("100.00"),
        decimal_places=2,
        max_digits=5,
        description="Ngưỡng cảnh báo chi tiêu mới (0 < threshold <= 100)",
    )

    @field_validator("period_end")
    @classmethod
    def validate_period_range(cls, v: date | None, info) -> date | None:
        if (
            v is not None
            and "period_start" in info.data
            and info.data["period_start"] is not None
            and v < info.data["period_start"]
        ):
            raise ValueError("Ngày kết thúc ngân sách (period_end) không được trước ngày bắt đầu (period_start).")
        return v


class BudgetResponse(BaseModel):
    """Schema chi tiết ngân sách trả về client, kèm số tiền đã chi và trạng thái cảnh báo theo thời gian thực."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str | None
    scope: Literal["personal", "family"]
    user_id: uuid.UUID | None
    family_id: uuid.UUID | None
    category_id: uuid.UUID
    category_name: str | None = None
    category_icon: str | None = None
    category_color: str | None = None
    amount_limit: Decimal
    period_start: date
    period_end: date
    warning_threshold: Decimal
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    # Các trường tính toán động (dynamic computed fields)
    spent_amount: Decimal = Field(
        ...,
        description="Tổng số tiền đã chi tiêu thực tế trong kỳ (chỉ tính giao dịch hợp lệ)",
    )
    remaining_amount: Decimal = Field(
        ...,
        description="Số tiền còn lại trong hạn mức ngân sách (max(limit - spent, 0))",
    )
    overspent_amount: Decimal = Field(
        ...,
        description="Số tiền vượt quá hạn mức ngân sách (max(spent - limit, 0))",
    )
    usage_percentage: Decimal = Field(
        ...,
        description="Tỷ lệ phần trăm đã sử dụng so với hạn mức (spent / limit * 100)",
    )
    status: Literal["normal", "warning", "exceeded"] = Field(
        ...,
        description="Trạng thái cảnh báo: 'normal' (< threshold), 'warning' (>= threshold và < 100%), 'exceeded' (>= 100%)",
    )
