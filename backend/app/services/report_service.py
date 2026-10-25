import csv
import io
import logging
import uuid
from datetime import UTC, date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal

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
from app.schemas.report import (
    PeriodComparisonCurrency,
    ReportAccountBreakdown,
    ReportCashFlowByCurrency,
    ReportCategoryBreakdown,
    ReportComparison,
    ReportFilterInfo,
    ReportMonthlyTrendPoint,
    ReportPeriodInfo,
    ReportSummaryResponse,
    ReportTopExpenseItem,
)

logger = logging.getLogger(__name__)


class ReportService:
    """Service xử lý dữ liệu báo cáo chuyên sâu và xuất CSV."""

    @staticmethod
    def _get_accessible_family_ids(db: Session, user: User) -> set[uuid.UUID]:
        """Lấy danh sách ID gia đình mà user có quyền truy cập."""
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

    @classmethod
    def _resolve_and_validate_accounts(
        cls,
        db: Session,
        current_user: User,
        scope: str,
        family_id: uuid.UUID | None,
        account_id: uuid.UUID | None,
    ) -> tuple[list[Account], str | None, str | None]:
        """
        Xác minh quyền truy cập và lọc danh sách ví tài khoản.
        Trả về (list[Account], selected_family_name, selected_account_name).
        """
        if scope not in ["all", "personal", "family"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phạm vi (scope) không hợp lệ. Chỉ chấp nhận 'all', 'personal' hoặc 'family'.",
            )

        accessible_fam_ids = cls._get_accessible_family_ids(db, current_user)
        selected_family_name: str | None = None
        selected_account_name: str | None = None

        if family_id is not None:
            if family_id not in accessible_fam_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Bạn không có quyền truy cập nhóm gia đình này hoặc nhóm không tồn tại.",
                )
            fam = db.scalar(select(Family).where(Family.id == family_id, Family.deleted_at.is_(None)))
            if fam:
                selected_family_name = fam.name

        # Truy vấn các ví hợp lệ
        acc_stmt = select(Account).where(
            Account.deleted_at.is_(None),
            Account.is_archived.is_(False),
        )

        if scope == "personal":
            acc_stmt = acc_stmt.where(
                Account.scope == "personal",
                Account.user_id == current_user.id,
            )
        elif scope == "family":
            if family_id:
                acc_stmt = acc_stmt.where(
                    Account.scope == "family",
                    Account.family_id == family_id,
                )
            else:
                if not accessible_fam_ids:
                    acc_stmt = acc_stmt.where(Account.id == uuid.uuid4())  # Không có ví
                else:
                    acc_stmt = acc_stmt.where(
                        Account.scope == "family",
                        Account.family_id.in_(accessible_fam_ids),
                    )
        else:  # scope == "all"
            if family_id:
                acc_stmt = acc_stmt.where(
                    or_(
                        (Account.scope == "personal") & (Account.user_id == current_user.id),
                        (Account.scope == "family") & (Account.family_id == family_id),
                    )
                )
            else:
                conditions = [(Account.scope == "personal") & (Account.user_id == current_user.id)]
                if accessible_fam_ids:
                    conditions.append(
                        (Account.scope == "family") & (Account.family_id.in_(accessible_fam_ids))
                    )
                acc_stmt = acc_stmt.where(or_(*conditions))

        if account_id is not None:
            # Kiểm tra xem account_id có nằm trong phạm vi được phép không
            acc_stmt = acc_stmt.where(Account.id == account_id)

        accounts = list(db.scalars(acc_stmt).all())

        if account_id is not None:
            if not accounts:
                # Kiểm tra xem ví tồn tại không nhưng user không có quyền
                exist_acc = db.scalar(select(Account).where(Account.id == account_id, Account.deleted_at.is_(None)))
                if exist_acc:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Bạn không có quyền truy cập ví tài khoản này.",
                    )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Ví tài khoản không tồn tại hoặc đã bị xóa.",
                )
            selected_account_name = accounts[0].name

        return accounts, selected_family_name, selected_account_name

    @classmethod
    def get_summary(
        cls,
        db: Session,
        current_user: User,
        date_from: date,
        date_to: date,
        scope: str = "all",
        family_id: uuid.UUID | None = None,
        account_id: uuid.UUID | None = None,
    ) -> ReportSummaryResponse:
        """
        Tính toán toàn bộ số liệu thống kê cho báo cáo tài chính trong khoảng [date_from, date_to].
        """
        if date_from > date_to:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ngày bắt đầu (date_from) không được sau ngày kết thúc (date_to).",
            )

        accounts, selected_family_name, selected_account_name = cls._resolve_and_validate_accounts(
            db, current_user, scope, family_id, account_id
        )

        account_ids = [acc.id for acc in accounts]
        days_count = (date_to - date_from).days + 1

        period_info = ReportPeriodInfo(
            date_from=date_from,
            date_to=date_to,
            days_count=days_count,
        )
        filter_info = ReportFilterInfo(
            scope=scope,  # type: ignore[arg-type]
            family_id=family_id,
            family_name=selected_family_name,
            account_id=account_id,
            account_name=selected_account_name,
        )

        if not account_ids:
            return ReportSummaryResponse(
                period=period_info,
                filters=filter_info,
                cash_flow_by_currency=[],
                category_breakdown=[],
                account_breakdown=[],
                monthly_trend=[],
                top_expenses=[],
                comparison=None,
            )

        # Mốc thời gian UTC bao trọn ngày
        start_dt = datetime.combine(date_from, time.min, tzinfo=UTC)
        end_dt = datetime.combine(date_to, time.max, tzinfo=UTC)

        # 1. Dòng tiền theo Currency trong kỳ
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
            ReportCashFlowByCurrency(
                currency=row.currency.upper(),
                total_income=row.income,
                total_expense=row.expense,
                total_transfer_fee=row.transfer_fee,
                net_cash_flow=row.income - row.expense - row.transfer_fee,
            )
            for row in cf_rows
        ]

        # Map tổng chi theo currency để tính % mẫu số
        total_expense_by_curr: dict[str, Decimal] = {
            row.currency.upper(): row.expense for row in cf_rows
        }

        # 2. Chi tiêu theo danh mục (Category Breakdown)
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
            .group_by(
                Category.id,
                Category.name,
                Category.icon,
                Category.color,
                Account.currency,
            )
            .order_by(func.sum(Transaction.amount).desc())
        )
        cat_rows = db.execute(cat_stmt).all()
        category_breakdown: list[ReportCategoryBreakdown] = []
        for r in cat_rows:
            curr = r.currency.upper()
            total_exp = total_expense_by_curr.get(curr, Decimal("0.00"))
            if total_exp > Decimal("0.00"):
                pct = ((r.cat_total / total_exp) * Decimal("100.00")).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
            else:
                pct = Decimal("0.00")
            category_breakdown.append(
                ReportCategoryBreakdown(
                    category_id=r.id,
                    category_name=r.name,
                    category_icon=r.icon,
                    category_color=r.color,
                    currency=curr,
                    total_amount=r.cat_total,
                    percentage=pct,
                )
            )

        # 3. Phân tích theo ví tài khoản (Account Breakdown)
        acc_cf_stmt = (
            select(
                Account.id,
                Account.name,
                Account.account_type,
                Account.currency,
                Account.scope,
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
            .select_from(Account)
            .outerjoin(
                Transaction,
                (Transaction.account_id == Account.id)
                & (Transaction.deleted_at.is_(None))
                & (Transaction.occurred_at >= start_dt)
                & (Transaction.occurred_at <= end_dt),
            )
            .outerjoin(Transfer, Transaction.transfer_id == Transfer.id)
            .where(
                Account.id.in_(account_ids),
                or_(
                    Transaction.id.is_(None),
                    or_(
                        Transaction.transfer_id.is_(None),
                        Transfer.voided_at.is_(None),
                    ),
                ),
            )
            .group_by(
                Account.id,
                Account.name,
                Account.account_type,
                Account.currency,
                Account.scope,
            )
            .order_by(Account.name.asc())
        )
        acc_rows = db.execute(acc_cf_stmt).all()
        account_breakdown = [
            ReportAccountBreakdown(
                account_id=r.id,
                account_name=r.name,
                account_type=r.account_type,
                currency=r.currency.upper(),
                scope=r.scope,
                total_income=r.income,
                total_expense=r.expense,
                net_amount=r.income - r.expense - r.transfer_fee,
            )
            for r in acc_rows
        ]

        # 4. Xu hướng theo từng tháng trong khoảng date_from -> date_to
        # Lập danh sách các tháng trong khoảng
        month_keys: list[tuple[int, int]] = []
        curr_y, curr_m = date_from.year, date_from.month
        while (curr_y < date_to.year) or (curr_y == date_to.year and curr_m <= date_to.month):
            month_keys.append((curr_y, curr_m))
            curr_m += 1
            if curr_m > 12:
                curr_m = 1
                curr_y += 1

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
                Transaction.occurred_at >= start_dt,
                Transaction.occurred_at <= end_dt,
                or_(
                    Transaction.transfer_id.is_(None),
                    Transfer.voided_at.is_(None),
                ),
                Transaction.type.in_(["income", "expense", "transfer_fee"]),
            )
        )
        trend_rows = db.execute(trend_stmt).all()

        currencies_found = {b.currency for b in cash_flow_by_currency} or {acc.currency.upper() for acc in accounts}
        trend_dict: dict[tuple[str, str], dict[str, Decimal]] = {}
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

        monthly_trend: list[ReportMonthlyTrendPoint] = []
        for (m_key, c), vals in trend_dict.items():
            y_str, m_str = m_key.split("-")
            display_lbl = f"T{m_str}/{y_str}"
            monthly_trend.append(
                ReportMonthlyTrendPoint(
                    month_key=m_key,
                    display_label=display_lbl,
                    currency=c,
                    income=vals["income"],
                    expense=vals["expense"],
                    transfer_fee=vals["transfer_fee"],
                    net=vals["income"] - vals["expense"] - vals["transfer_fee"],
                )
            )

        # 5. Top 10 khoản chi lớn nhất trong kỳ
        top_stmt = (
            select(Transaction)
            .options(
                joinedload(Transaction.account),
                joinedload(Transaction.category),
            )
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
            .order_by(Transaction.amount.desc(), Transaction.occurred_at.desc())
            .limit(10)
        )
        top_txs = list(db.scalars(top_stmt).all())
        top_expenses: list[ReportTopExpenseItem] = [
            ReportTopExpenseItem(
                id=tx.id,
                account_id=tx.account_id,
                account_name=tx.account.name if tx.account else "N/A",
                currency=tx.account.currency.upper() if tx.account else "VND",
                category_id=tx.category_id,
                category_name=tx.category.name if tx.category else None,
                category_icon=tx.category.icon if tx.category else None,
                category_color=tx.category.color if tx.category else None,
                amount=tx.amount,
                occurred_at=tx.occurred_at.isoformat(),
                description=tx.note,
            )
            for tx in top_txs
        ]

        # 6. So sánh kỳ trước có độ dài tương đương
        prev_date_to = date_from - timedelta(days=1)
        prev_date_from = prev_date_to - timedelta(days=days_count - 1)
        prev_start_dt = datetime.combine(prev_date_from, time.min, tzinfo=UTC)
        prev_end_dt = datetime.combine(prev_date_to, time.max, tzinfo=UTC)

        prev_cf_stmt = (
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
                Transaction.occurred_at >= prev_start_dt,
                Transaction.occurred_at <= prev_end_dt,
                or_(
                    Transaction.transfer_id.is_(None),
                    Transfer.voided_at.is_(None),
                ),
            )
            .group_by(Account.currency)
        )
        prev_cf_rows = {row.currency.upper(): row for row in db.execute(prev_cf_stmt).all()}

        comparison_by_currency: list[PeriodComparisonCurrency] = []
        all_currencies = sorted(currencies_found | set(prev_cf_rows.keys()))

        curr_cf_map = {cf.currency: cf for cf in cash_flow_by_currency}

        for c in all_currencies:
            cur_cf = curr_cf_map.get(c)
            prv_cf = prev_cf_rows.get(c)

            c_inc = cur_cf.total_income if cur_cf else Decimal("0.00")
            c_exp = cur_cf.total_expense if cur_cf else Decimal("0.00")
            c_net = cur_cf.net_cash_flow if cur_cf else Decimal("0.00")

            p_inc = prv_cf.income if prv_cf else Decimal("0.00")
            p_exp = prv_cf.expense if prv_cf else Decimal("0.00")
            p_fee = prv_cf.transfer_fee if prv_cf else Decimal("0.00")
            p_net = p_inc - p_exp - p_fee

            inc_diff = c_inc - p_inc
            exp_diff = c_exp - p_exp
            net_diff = c_net - p_net

            inc_pct: Decimal | None = None
            if p_inc > Decimal("0.00"):
                inc_pct = ((inc_diff / p_inc) * Decimal("100.00")).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )

            exp_pct: Decimal | None = None
            if p_exp > Decimal("0.00"):
                exp_pct = ((exp_diff / p_exp) * Decimal("100.00")).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )

            net_pct: Decimal | None = None
            if p_net != Decimal("0.00"):
                net_pct = ((net_diff / abs(p_net)) * Decimal("100.00")).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )

            comparison_by_currency.append(
                PeriodComparisonCurrency(
                    currency=c,
                    current_income=c_inc,
                    previous_income=p_inc,
                    income_change_amount=inc_diff,
                    income_change_percentage=inc_pct,
                    current_expense=c_exp,
                    previous_expense=p_exp,
                    expense_change_amount=exp_diff,
                    expense_change_percentage=exp_pct,
                    current_net=c_net,
                    previous_net=p_net,
                    net_change_amount=net_diff,
                    net_change_percentage=net_pct,
                )
            )

        comparison_info = ReportComparison(
            previous_date_from=prev_date_from,
            previous_date_to=prev_date_to,
            by_currency=comparison_by_currency,
        )

        return ReportSummaryResponse(
            period=period_info,
            filters=filter_info,
            cash_flow_by_currency=cash_flow_by_currency,
            category_breakdown=category_breakdown,
            account_breakdown=account_breakdown,
            monthly_trend=monthly_trend,
            top_expenses=top_expenses,
            comparison=comparison_info,
        )

    @classmethod
    def export_csv(
        cls,
        db: Session,
        current_user: User,
        date_from: date,
        date_to: date,
        scope: str = "all",
        family_id: uuid.UUID | None = None,
        account_id: uuid.UUID | None = None,
    ) -> str:
        """
        Xuất danh sách giao dịch thu/chi/phí chuyển tiền hợp lệ trong kỳ ra định dạng CSV.
        """
        if date_from > date_to:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ngày bắt đầu (date_from) không được sau ngày kết thúc (date_to).",
            )

        accounts, _, _ = cls._resolve_and_validate_accounts(
            db, current_user, scope, family_id, account_id
        )
        account_ids = [acc.id for acc in accounts]

        output = io.StringIO()
        # Thêm UTF-8 BOM để Excel hiển thị tiếng Việt có dấu chuẩn xác
        output.write("\ufeff")
        writer = csv.writer(output)

        headers = [
            "Mã giao dịch",
            "Thời gian",
            "Loại giao dịch",
            "Danh mục",
            "Ví tài khoản",
            "Loại tiền",
            "Số tiền",
            "Ghi chú",
            "Phạm vi",
        ]
        writer.writerow(headers)

        if not account_ids:
            return output.getvalue()

        start_dt = datetime.combine(date_from, time.min, tzinfo=UTC)
        end_dt = datetime.combine(date_to, time.max, tzinfo=UTC)

        type_label_map = {
            "income": "Thu nhập",
            "expense": "Chi tiêu",
            "transfer_fee": "Phí chuyển tiền",
        }

        # Chỉ lấy income, expense, transfer_fee. Tuyệt đối không lấy transfer_in/transfer_out.
        tx_stmt = (
            select(Transaction)
            .options(
                joinedload(Transaction.account),
                joinedload(Transaction.category),
            )
            .outerjoin(Transfer, Transaction.transfer_id == Transfer.id)
            .where(
                Transaction.account_id.in_(account_ids),
                Transaction.deleted_at.is_(None),
                Transaction.occurred_at >= start_dt,
                Transaction.occurred_at <= end_dt,
                Transaction.type.in_(["income", "expense", "transfer_fee"]),
                or_(
                    Transaction.transfer_id.is_(None),
                    Transfer.voided_at.is_(None),
                ),
            )
            .order_by(Transaction.occurred_at.asc())
        )
        transactions = list(db.scalars(tx_stmt).all())

        for tx in transactions:
            row_type = type_label_map.get(tx.type, tx.type)
            cat_name = tx.category.name if tx.category else ("Phí giao dịch" if tx.type == "transfer_fee" else "Khác")
            acc_name = tx.account.name if tx.account else "N/A"
            currency = tx.account.currency.upper() if tx.account else "VND"
            scope_str = "Cá nhân" if (tx.account and tx.account.scope == "personal") else "Gia đình"

            writer.writerow([
                str(tx.id),
                tx.occurred_at.strftime("%Y-%m-%d %H:%M:%S"),
                row_type,
                cat_name,
                acc_name,
                currency,
                str(tx.amount),
                tx.note or "",
                scope_str,
            ])

        return output.getvalue()
