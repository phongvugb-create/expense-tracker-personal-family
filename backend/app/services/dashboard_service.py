import calendar
import logging
import uuid
from datetime import UTC, date, datetime, time
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.account import Account
from app.models.category import Category
from app.models.family import Family
from app.models.family_member import FamilyMember
from app.models.transaction import Transaction
from app.models.transfer import Transfer
from app.models.user import User
from app.schemas.dashboard import (
    CurrencyBalanceInfo,
    CurrencyCashFlowInfo,
    DashboardBudgetAlert,
    DashboardFilterInfo,
    DashboardPeriodInfo,
    DashboardSummaryResponse,
    ExpenseCategoryBreakdown,
    MonthlyTrendPoint,
    RecentTransactionItem,
    RecentTransferItem,
)
from app.services.account_service import AccountService
from app.services.budget_service import BudgetService

logger = logging.getLogger(__name__)


class DashboardService:
    """Service xử lý dữ liệu tổng hợp cho trang Dashboard."""

    @staticmethod
    def _get_accessible_family_ids(db: Session, user: User) -> set[uuid.UUID]:
        """Lấy danh sách family_id mà user có quyền truy cập."""
        stmt = (
            select(Family.id)
            .where(
                Family.owner_user_id == user.id,
                Family.deleted_at.is_(None),
            )
            .union(
                select(FamilyMember.family_id)
                .join(Family, FamilyMember.family_id == Family.id)
                .where(
                    FamilyMember.user_id == user.id,
                    FamilyMember.left_at.is_(None),
                    Family.deleted_at.is_(None),
                )
            )
        )
        return set(db.scalars(stmt).all())

    @staticmethod
    def get_summary(
        db: Session,
        current_user: User,
        year: int | None = None,
        month: int | None = None,
        scope: str = "all",
        family_id: uuid.UUID | None = None,
    ) -> DashboardSummaryResponse:
        """
        Tính toán toàn bộ số liệu thống kê thời gian thực cho Dashboard:
        1. Số dư ví khả dụng theo từng currency.
        2. Tổng thu, chi, phí chuyển tiền và dòng tiền thuần trong kỳ theo currency.
        3. Xu hướng thu/chi 6 tháng gần nhất cho biểu đồ.
        4. Cơ cấu chi tiêu theo danh mục.
        5. Giao dịch thu/chi gần nhất (5-10 bản ghi).
        6. Chuyển tiền gần nhất (5-10 bản ghi).
        7. Danh sách ngân sách cảnh báo (warning / exceeded).
        """
        now = datetime.now(UTC)
        # Xác thực năm và tháng
        if year is None and month is None:
            sel_year = now.year
            sel_month = now.month
        elif year is not None and month is not None:
            if month < 1 or month > 12:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Tháng (month) phải nằm trong khoảng từ 1 đến 12.",
                )
            if year < 2000 or year > 2100:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Năm (year) không hợp lệ.",
                )
            sel_year = year
            sel_month = month
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cần truyền đồng thời cả 'year' và 'month' hoặc bỏ trống cả hai để dùng tháng hiện tại.",
            )

        if scope not in ("all", "personal", "family"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phạm vi (scope) chỉ chấp nhận 'all', 'personal' hoặc 'family'.",
            )

        # Kiểm tra quyền với family_id nếu có
        accessible_family_ids = DashboardService._get_accessible_family_ids(db, current_user)
        selected_family_name = None

        if family_id is not None:
            if family_id not in accessible_family_ids:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Nhóm gia đình không tồn tại hoặc bạn không có quyền truy cập.",
                )
            fam = db.get(Family, family_id)
            if fam:
                selected_family_name = fam.name

        # Xác định danh sách ví hợp lệ theo scope
        acc_stmt = select(Account).where(Account.deleted_at.is_(None))
        if scope == "personal":
            acc_stmt = acc_stmt.where(Account.scope == "personal", Account.user_id == current_user.id)
        elif scope == "family":
            if family_id is not None:
                acc_stmt = acc_stmt.where(Account.scope == "family", Account.family_id == family_id)
            else:
                acc_stmt = acc_stmt.where(Account.scope == "family", Account.family_id.in_(accessible_family_ids))
        else:  # all
            acc_stmt = acc_stmt.where(
                or_(
                    (Account.scope == "personal") & (Account.user_id == current_user.id),
                    (Account.scope == "family") & (Account.family_id.in_(accessible_family_ids)),
                )
            )

        all_accounts = list(db.scalars(acc_stmt).all())
        active_accounts = [a for a in all_accounts if not a.is_archived]
        account_ids = [a.id for a in all_accounts]
        active_account_ids = [a.id for a in active_accounts]

        # 1. Tính toán số dư khả dụng theo từng loại tiền tệ (không cộng gộp chéo currency)
        # Sử dụng AccountService._compute_current_balances để có số dư chính xác
        current_balances = AccountService._compute_current_balances(db, active_account_ids)
        balances_map: dict[str, dict[str, Any]] = {}
        for acc in active_accounts:
            curr = acc.currency.upper()
            if curr not in balances_map:
                balances_map[curr] = {"total_balance": Decimal("0.00"), "count": 0}
            bal = acc.initial_balance + current_balances.get(acc.id, Decimal("0.00"))
            balances_map[curr]["total_balance"] += bal
            balances_map[curr]["count"] += 1

        balances_by_currency = [
            CurrencyBalanceInfo(
                currency=curr,
                total_balance=data["total_balance"],
                active_accounts_count=data["count"],
            )
            for curr, data in sorted(balances_map.items())
        ]

        # Xác định khoảng thời gian của tháng đã chọn (period_start đến period_end)
        num_days = calendar.monthrange(sel_year, sel_month)[1]
        start_date = date(sel_year, sel_month, 1)
        end_date = date(sel_year, sel_month, num_days)
        start_dt = datetime.combine(start_date, time.min, tzinfo=UTC)
        end_dt = datetime.combine(end_date, time.max, tzinfo=UTC)

        period_info = DashboardPeriodInfo(
            year=sel_year,
            month=sel_month,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )
        filter_info = DashboardFilterInfo(
            scope=scope,  # type: ignore[arg-type]
            family_id=family_id,
            family_name=selected_family_name,
        )

        if not account_ids:
            return DashboardSummaryResponse(
                period=period_info,
                filters=filter_info,
                balances_by_currency=[],
                cash_flow_by_currency=[],
                monthly_trend=[],
                expense_categories=[],
                recent_transactions=[],
                recent_transfers=[],
                budget_alerts=[],
            )

        # 2. Dòng tiền trong kỳ theo currency: Thu, Chi, Phí chuyển tiền, Net
        # Lọc giao dịch: thuộc account_ids, deleted_at IS NULL, occurred_at trong kỳ, transfer chưa void
        cf_stmt = (
            select(
                Account.currency,
                func.coalesce(
                    func.sum(case((Transaction.type == "income", Transaction.amount), else_=Decimal("0.00"))),
                    Decimal("0.00"),
                ).label("income"),
                func.coalesce(
                    func.sum(case((Transaction.type == "expense", Transaction.amount), else_=Decimal("0.00"))),
                    Decimal("0.00"),
                ).label("expense"),
                func.coalesce(
                    func.sum(case((Transaction.type == "transfer_fee", Transaction.amount), else_=Decimal("0.00"))),
                    Decimal("0.00"),
                ).label("transfer_fee"),
            )
            .select_from(Transaction)
            .join(Account, Transaction.account_id == Account.id)
            .outerjoin(Transfer, Transaction.transfer_id == Transfer.id)
            .where(
                Transaction.account_id.in_(account_ids),
                Transaction.deleted_at.is_(None),
                Transaction.occurred_at >= start_dt,
                Transaction.occurred_at <= end_dt,
                or_(
                    Transaction.transfer_id.is_(None),
                    Transfer.voided_at.is_(None),
                ),
            )
            .group_by(Account.currency)
        )
        cf_rows = db.execute(cf_stmt).all()
        cash_flow_by_currency = [
            CurrencyCashFlowInfo(
                currency=row.currency.upper(),
                total_income=row.income,
                total_expense=row.expense,
                total_transfer_fee=row.transfer_fee,
                net_cash_flow=row.income - row.expense - row.transfer_fee,
            )
            for row in cf_rows
        ]

        # 3. Xu hướng 6 tháng gần nhất (Monthly Trend)
        # Tạo danh sách 6 tháng tính từ sel_year/sel_month lùi về trước
        month_keys: list[tuple[int, int]] = []
        cur_y, cur_m = sel_year, sel_month
        for _ in range(6):
            month_keys.append((cur_y, cur_m))
            cur_m -= 1
            if cur_m == 0:
                cur_m = 12
                cur_y -= 1
        month_keys.reverse()  # Thứ tự thời gian tăng dần

        first_y, first_m = month_keys[0]
        trend_start_dt = datetime.combine(date(first_y, first_m, 1), time.min, tzinfo=UTC)

        trend_stmt = (
            select(
                Account.currency,
                Transaction.occurred_at,
                Transaction.type,
                Transaction.amount,
            )
            .select_from(Transaction)
            .join(Account, Transaction.account_id == Account.id)
            .outerjoin(Transfer, Transaction.transfer_id == Transfer.id)
            .where(
                Transaction.account_id.in_(account_ids),
                Transaction.deleted_at.is_(None),
                Transaction.occurred_at >= trend_start_dt,
                Transaction.occurred_at <= end_dt,
                or_(
                    Transaction.transfer_id.is_(None),
                    Transfer.voided_at.is_(None),
                ),
                Transaction.type.in_(["income", "expense", "transfer_fee"]),
            )
        )
        trend_rows = db.execute(trend_stmt).all()

        # Tổng hợp dữ liệu 6 tháng theo (month_key, currency)
        trend_dict: dict[tuple[str, str], dict[str, Decimal]] = {}
        currencies_found = {b.currency for b in balances_by_currency} or {"VND"}

        for y, m in month_keys:
            m_key = f"{y:04d}-{m:02d}"
            for c in currencies_found:
                trend_dict[(m_key, c)] = {
                    "income": Decimal("0.00"),
                    "expense": Decimal("0.00"),
                    "transfer_fee": Decimal("0.00"),
                }

        for r in trend_rows:
            r_curr = r.currency.upper()
            r_key = f"{r.occurred_at.year:04d}-{r.occurred_at.month:02d}"
            if (r_key, r_curr) in trend_dict:
                if r.type == "income":
                    trend_dict[(r_key, r_curr)]["income"] += r.amount
                elif r.type == "expense":
                    trend_dict[(r_key, r_curr)]["expense"] += r.amount
                elif r.type == "transfer_fee":
                    trend_dict[(r_key, r_curr)]["transfer_fee"] += r.amount

        monthly_trend: list[MonthlyTrendPoint] = []
        for (m_key, c), vals in trend_dict.items():
            y_str, m_str = m_key.split("-")
            display_lbl = f"T{m_str}/{y_str}"
            monthly_trend.append(
                MonthlyTrendPoint(
                    month_key=m_key,
                    display_label=display_lbl,
                    currency=c,
                    income=vals["income"],
                    expense=vals["expense"],
                    transfer_fee=vals["transfer_fee"],
                    net=vals["income"] - vals["expense"] - vals["transfer_fee"],
                )
            )

        # 4. Cơ cấu chi tiêu theo danh mục trong kỳ
        cat_stmt = (
            select(
                Category.id,
                Category.name,
                Category.icon,
                Category.color,
                Account.currency,
                func.coalesce(func.sum(Transaction.amount), Decimal("0.00")).label("cat_total"),
            )
            .select_from(Transaction)
            .join(Account, Transaction.account_id == Account.id)
            .join(Category, Transaction.category_id == Category.id)
            .outerjoin(Transfer, Transaction.transfer_id == Transfer.id)
            .where(
                Transaction.account_id.in_(account_ids),
                Transaction.deleted_at.is_(None),
                Transaction.occurred_at >= start_dt,
                Transaction.occurred_at <= end_dt,
                Transaction.type == "expense",
                or_(
                    Transaction.transfer_id.is_(None),
                    Transfer.voided_at.is_(None),
                ),
            )
            .group_by(Category.id, Category.name, Category.icon, Category.color, Account.currency)
            .order_by(func.sum(Transaction.amount).desc())
        )
        cat_rows = db.execute(cat_stmt).all()

        # Tính tổng chi theo currency để tính tỷ trọng (%)
        total_expense_by_curr: dict[str, Decimal] = {}
        for cf in cash_flow_by_currency:
            total_expense_by_curr[cf.currency] = cf.total_expense

        expense_categories: list[ExpenseCategoryBreakdown] = []
        for cr in cat_rows:
            curr_str = cr.currency.upper()
            curr_total = total_expense_by_curr.get(curr_str, Decimal("0.00"))
            pct = (
                (cr.cat_total / curr_total * Decimal("100.00")).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                if curr_total > Decimal("0.00")
                else Decimal("0.00")
            )
            expense_categories.append(
                ExpenseCategoryBreakdown(
                    category_id=cr.id,
                    category_name=cr.name,
                    category_icon=cr.icon,
                    category_color=cr.color,
                    currency=curr_str,
                    total_amount=cr.cat_total,
                    percentage=pct,
                )
            )

        # 5. Hoạt động gần nhất: 5 Giao dịch thu/chi mới nhất
        recent_tx_stmt = (
            select(Transaction)
            .options(joinedload(Transaction.account), joinedload(Transaction.category))
            .outerjoin(Transfer, Transaction.transfer_id == Transfer.id)
            .where(
                Transaction.account_id.in_(account_ids),
                Transaction.deleted_at.is_(None),
                or_(
                    Transaction.transfer_id.is_(None),
                    Transfer.voided_at.is_(None),
                ),
                Transaction.type.in_(["income", "expense", "transfer_fee"]),
            )
            .order_by(Transaction.occurred_at.desc())
            .limit(5)
        )
        recent_tx_objs = list(db.scalars(recent_tx_stmt).all())
        recent_transactions = [
            RecentTransactionItem(
                id=tx.id,
                account_id=tx.account_id,
                account_name=tx.account.name if tx.account else "N/A",
                currency=tx.account.currency.upper() if tx.account else "VND",
                category_id=tx.category_id,
                category_name=tx.category.name if tx.category else None,
                category_icon=tx.category.icon if tx.category else None,
                category_color=tx.category.color if tx.category else None,
                type=tx.type,
                amount=tx.amount,
                note=tx.note,
                occurred_at=tx.occurred_at,
            )
            for tx in recent_tx_objs
        ]

        # 6. Chuyển tiền gần nhất: 5 lần chuyển tiền mới nhất
        recent_tr_stmt = (
            select(Transfer)
            .options(joinedload(Transfer.from_account), joinedload(Transfer.to_account))
            .where(
                or_(
                    Transfer.from_account_id.in_(account_ids),
                    Transfer.to_account_id.in_(account_ids),
                )
            )
            .order_by(Transfer.occurred_at.desc())
            .limit(5)
        )
        recent_tr_objs = list(db.scalars(recent_tr_stmt).all())
        recent_transfers = [
            RecentTransferItem(
                id=tr.id,
                from_account_id=tr.from_account_id,
                from_account_name=tr.from_account.name if tr.from_account else "N/A",
                to_account_id=tr.to_account_id,
                to_account_name=tr.to_account.name if tr.to_account else "N/A",
                currency=tr.from_account.currency.upper() if tr.from_account else "VND",
                amount=tr.amount,
                fee_amount=tr.fee_amount,
                note=tr.note,
                occurred_at=tr.occurred_at,
                is_voided=tr.voided_at is not None,
            )
            for tr in recent_tr_objs
        ]

        # 7. Ngân sách có cảnh báo trong kỳ (warning hoặc exceeded)
        # Dùng BudgetService để lấy danh sách ngân sách hiệu lực và tính trạng thái
        budget_scope_filter = None if scope == "all" else scope
        budgets_list = BudgetService.get_budgets(
            db=db,
            current_user=current_user,
            scope=budget_scope_filter,
            family_id=family_id if scope == "family" else None,
            include_archived=False,
            active_on=date(sel_year, sel_month, 15),  # Ngày giữa kỳ
            limit=50,
            offset=0,
        )
        budget_alerts = [
            DashboardBudgetAlert(
                id=b.id,
                name=b.name,
                scope=b.scope,
                category_name=b.category_name or "Chi tiêu",
                amount_limit=b.amount_limit,
                spent_amount=b.spent_amount,
                remaining_amount=b.remaining_amount,
                overspent_amount=b.overspent_amount,
                usage_percentage=b.usage_percentage,
                warning_threshold=b.warning_threshold,
                status=b.status,  # type: ignore[arg-type]
            )
            for b in budgets_list
            if b.status in ("warning", "exceeded")
        ]

        return DashboardSummaryResponse(
            period=period_info,
            filters=filter_info,
            balances_by_currency=balances_by_currency,
            cash_flow_by_currency=cash_flow_by_currency,
            monthly_trend=monthly_trend,
            expense_categories=expense_categories,
            recent_transactions=recent_transactions,
            recent_transfers=recent_transfers,
            budget_alerts=budget_alerts,
        )
