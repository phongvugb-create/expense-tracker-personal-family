import uuid
from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ReportPeriodInfo(BaseModel):
    """Thông tin khoảng thời gian báo cáo."""

    date_from: date
    date_to: date
    days_count: int


class ReportFilterInfo(BaseModel):
    """Bộ lọc áp dụng cho báo cáo."""

    scope: Literal["all", "personal", "family"]
    family_id: uuid.UUID | None = None
    family_name: str | None = None
    account_id: uuid.UUID | None = None
    account_name: str | None = None


class ReportCashFlowByCurrency(BaseModel):
    """Dòng tiền trong kỳ báo cáo theo từng loại tiền tệ."""

    currency: str
    total_income: Decimal
    total_expense: Decimal
    total_transfer_fee: Decimal
    net_cash_flow: Decimal


class ReportCategoryBreakdown(BaseModel):
    """Chi tiêu theo danh mục."""

    category_id: uuid.UUID
    category_name: str
    category_icon: str | None = None
    category_color: str | None = None
    currency: str
    total_amount: Decimal
    percentage: Decimal  # 0.00% -> 100.00%


class ReportAccountBreakdown(BaseModel):
    """Thu/chi theo ví tài khoản."""

    account_id: uuid.UUID
    account_name: str
    account_type: str
    currency: str
    scope: str
    total_income: Decimal
    total_expense: Decimal
    net_amount: Decimal


class ReportMonthlyTrendPoint(BaseModel):
    """Dữ liệu thu/chi từng tháng trong khoảng thời gian báo cáo."""

    month_key: str  # YYYY-MM
    display_label: str  # TMM/YYYY
    currency: str
    income: Decimal
    expense: Decimal
    transfer_fee: Decimal
    net: Decimal


class ReportTopExpenseItem(BaseModel):
    """Khoản chi tiêu lớn nhất trong kỳ."""

    id: uuid.UUID
    account_id: uuid.UUID
    account_name: str
    currency: str
    category_id: uuid.UUID | None = None
    category_name: str | None = None
    category_icon: str | None = None
    category_color: str | None = None
    amount: Decimal
    occurred_at: str
    description: str | None = None


class PeriodComparisonCurrency(BaseModel):
    """So sánh số liệu thu/chi/dòng tiền giữa 2 kỳ của 1 loại tiền tệ."""

    currency: str
    current_income: Decimal
    previous_income: Decimal
    income_change_amount: Decimal
    income_change_percentage: Decimal | None = None  # None nếu kỳ trước = 0

    current_expense: Decimal
    previous_expense: Decimal
    expense_change_amount: Decimal
    expense_change_percentage: Decimal | None = None  # None nếu kỳ trước = 0

    current_net: Decimal
    previous_net: Decimal
    net_change_amount: Decimal
    net_change_percentage: Decimal | None = None  # None nếu kỳ trước = 0


class ReportComparison(BaseModel):
    """So sánh kỳ báo cáo hiện tại với kỳ trước có độ dài tương đương."""

    previous_date_from: date
    previous_date_to: date
    by_currency: list[PeriodComparisonCurrency] = Field(default_factory=list)


class ReportSummaryResponse(BaseModel):
    """Toàn bộ cấu trúc response của GET /api/v1/reports/summary."""

    model_config = ConfigDict(from_attributes=True)

    period: ReportPeriodInfo
    filters: ReportFilterInfo
    cash_flow_by_currency: list[ReportCashFlowByCurrency] = Field(default_factory=list)
    category_breakdown: list[ReportCategoryBreakdown] = Field(default_factory=list)
    account_breakdown: list[ReportAccountBreakdown] = Field(default_factory=list)
    monthly_trend: list[ReportMonthlyTrendPoint] = Field(default_factory=list)
    top_expenses: list[ReportTopExpenseItem] = Field(default_factory=list)
    comparison: ReportComparison | None = None
