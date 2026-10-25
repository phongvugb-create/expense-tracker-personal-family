import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict


class DashboardPeriodInfo(BaseModel):
    """Thông tin kỳ báo cáo thống kê."""

    year: int
    month: int
    start_date: str
    end_date: str


class DashboardFilterInfo(BaseModel):
    """Thông tin bộ lọc áp dụng."""

    scope: Literal["all", "personal", "family"]
    family_id: uuid.UUID | None = None
    family_name: str | None = None


class CurrencyBalanceInfo(BaseModel):
    """Số dư ví khả dụng theo từng loại tiền tệ."""

    currency: str
    total_balance: Decimal
    active_accounts_count: int


class CurrencyCashFlowInfo(BaseModel):
    """Dòng tiền trong kỳ thống kê theo từng loại tiền tệ."""

    currency: str
    total_income: Decimal
    total_expense: Decimal
    total_transfer_fee: Decimal
    net_cash_flow: Decimal


class MonthlyTrendPoint(BaseModel):
    """Điểm dữ liệu thu/chi trong 6 tháng gần nhất cho biểu đồ."""

    month_key: str  # YYYY-MM
    display_label: str  # TMM/YYYY (VD: T05/2026)
    currency: str
    income: Decimal
    expense: Decimal
    transfer_fee: Decimal
    net: Decimal


class ExpenseCategoryBreakdown(BaseModel):
    """Cơ cấu chi tiêu theo danh mục trong kỳ."""

    category_id: uuid.UUID
    category_name: str
    category_icon: str | None = None
    category_color: str | None = None
    currency: str
    total_amount: Decimal
    percentage: Decimal  # 0.00% -> 100.00%


class RecentTransactionItem(BaseModel):
    """Giao dịch thu/chi gần đây."""

    id: uuid.UUID
    account_id: uuid.UUID
    account_name: str
    currency: str
    category_id: uuid.UUID | None = None
    category_name: str | None = None
    category_icon: str | None = None
    category_color: str | None = None
    type: str  # income, expense, transfer_fee
    amount: Decimal
    note: str | None = None
    occurred_at: datetime


class RecentTransferItem(BaseModel):
    """Giao dịch chuyển tiền gần đây."""

    id: uuid.UUID
    from_account_id: uuid.UUID
    from_account_name: str
    to_account_id: uuid.UUID
    to_account_name: str
    currency: str
    amount: Decimal
    fee_amount: Decimal
    note: str | None = None
    occurred_at: datetime
    is_voided: bool


class DashboardBudgetAlert(BaseModel):
    """Ngân sách đang có cảnh báo trong kỳ."""

    id: uuid.UUID
    name: str | None
    scope: str
    category_name: str
    amount_limit: Decimal
    spent_amount: Decimal
    remaining_amount: Decimal
    overspent_amount: Decimal
    usage_percentage: Decimal
    warning_threshold: Decimal
    status: Literal["warning", "exceeded"]


class DashboardSummaryResponse(BaseModel):
    """Response đầy đủ cho Dashboard tổng hợp tài chính."""

    model_config = ConfigDict(from_attributes=True)

    period: DashboardPeriodInfo
    filters: DashboardFilterInfo
    balances_by_currency: list[CurrencyBalanceInfo]
    cash_flow_by_currency: list[CurrencyCashFlowInfo]
    monthly_trend: list[MonthlyTrendPoint]
    expense_categories: list[ExpenseCategoryBreakdown]
    recent_transactions: list[RecentTransactionItem]
    recent_transfers: list[RecentTransferItem]
    budget_alerts: list[DashboardBudgetAlert]
