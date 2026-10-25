import logging
import uuid
from collections.abc import Sequence
from datetime import UTC, date, datetime, time
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.account import Account
from app.models.budget import Budget
from app.models.category import Category
from app.models.family import Family
from app.models.family_member import FamilyMember
from app.models.transaction import Transaction
from app.models.transfer import Transfer
from app.models.user import User
from app.schemas.budget import (
    BudgetCreateRequest,
    BudgetResponse,
    BudgetUpdateRequest,
)

logger = logging.getLogger(__name__)


class BudgetService:
    """Service xử lý nghiệp vụ quản lý ngân sách chi tiêu, phân quyền và tính toán hạn mức động."""

    @staticmethod
    def _get_accessible_family_ids(db: Session, user: User) -> set[uuid.UUID]:
        """Lấy danh sách các family_id mà user có quyền xem (owner hoặc active member)."""
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
    def _check_family_role(
        db: Session, family_id: uuid.UUID, user: User, required_role: str = "viewer"
    ) -> bool:
        """
        Kiểm tra vai trò của user trong nhóm gia đình:
        - required_role='viewer': owner, editor, viewer (active).
        - required_role='editor': owner, editor (active).
        - required_role='owner': owner.
        """
        family = db.get(Family, family_id)
        if family is None or family.deleted_at is not None:
            return False

        if family.owner_user_id == user.id:
            return True

        member = db.scalar(
            select(FamilyMember).where(
                FamilyMember.family_id == family_id,
                FamilyMember.user_id == user.id,
                FamilyMember.left_at.is_(None),
            )
        )
        if member is None:
            return False

        if required_role == "viewer":
            return member.role in ("owner", "editor", "viewer")
        elif required_role == "editor":
            return member.role in ("owner", "editor")
        elif required_role == "owner":
            return member.role == "owner"

        return False

    @staticmethod
    def _validate_category_for_budget(
        db: Session,
        category_id: uuid.UUID,
        scope: str,
        family_id: uuid.UUID | None,
        user: User,
    ) -> Category:
        """
        Xác thực tính hợp lệ của danh mục khi tạo hoặc cập nhật ngân sách:
        1. Tồn tại và chưa bị soft-delete (`deleted_at IS NULL`).
        2. Không bị lưu trữ (`is_archived IS FALSE`).
        3. Phải là danh mục chi tiêu (`type == 'expense'`).
        4. Tương thích phạm vi (scope):
           - 'system': dùng được cho cả personal và family budget.
           - 'personal': chỉ dùng khi scope == 'personal' và category.user_id == user.id.
           - 'family': chỉ dùng khi scope == 'family' và category.family_id == budget.family_id.
        """
        category = db.get(Category, category_id)
        if category is None or category.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Danh mục không tồn tại hoặc đã bị xóa.",
            )

        if category.is_archived:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể tạo hoặc cập nhật ngân sách cho danh mục đang bị lưu trữ.",
            )

        if category.type != "expense":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ngân sách chi tiêu chỉ áp dụng cho danh mục loại 'expense', danh mục hiện tại là '{category.type}'.",
            )

        if category.scope == "system":
            pass
        elif category.scope == "personal":
            if scope != "personal" or category.user_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Danh mục cá nhân chỉ có thể sử dụng cho ngân sách cá nhân của chính bạn.",
                )
        elif category.scope == "family" and (
            scope != "family" or category.family_id != family_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Danh mục gia đình chỉ có thể sử dụng cho ngân sách thuộc cùng nhóm gia đình.",
            )

        return category

    @staticmethod
    def _compute_spent_amounts(
        db: Session,
        budgets: Sequence[Budget],
    ) -> dict[uuid.UUID, Decimal]:
        """
        Tính toán tổng số tiền đã chi tiêu thực tế cho một danh sách ngân sách.
        Tránh N+1 query bằng cách nhóm và thực hiện batch aggregated queries theo phạm vi.

        Quy tắc tính toán spent_amount:
        - Giao dịch phải thuộc các ví (Account) có cùng phạm vi với ngân sách:
          + scope == 'personal': các ví có account.scope == 'personal' AND account.user_id == budget.user_id AND account.deleted_at IS NULL.
          + scope == 'family': các ví có account.scope == 'family' AND account.family_id == budget.family_id AND account.deleted_at IS NULL.
        - Giao dịch có transaction.category_id == budget.category_id.
        - Giao dịch chưa bị xóa mềm: transaction.deleted_at IS NULL.
        - Loại giao dịch hợp lệ:
          + 'expense' (giao dịch chi tiêu thông thường).
          + 'transfer_fee' (phí chuyển tiền phát sinh gán vào danh mục chi tiêu này).
          (Các loại 'income', 'transfer_in', 'transfer_out' không bao giờ được tính vào chi tiêu ngân sách).
        - Nếu giao dịch gắn với Transfer (đối với transfer_fee): transfer đó chưa bị void (`transfers.voided_at IS NULL`).
        - Thời điểm phát sinh `occurred_at` nằm trọn vẹn trong khoảng ngân sách:
          start_dt <= occurred_at <= end_dt
          (Với start_dt = period_start lúc 00:00:00 UTC, end_dt = period_end lúc 23:59:59.999999 UTC).
        """
        if not budgets:
            return {}

        results: dict[uuid.UUID, Decimal] = {b.id: Decimal("0.00") for b in budgets}

        # Duyệt từng ngân sách để thực hiện câu lệnh tổng hợp chính xác theo điều kiện cụ thể của kỳ
        for b in budgets:
            start_dt = datetime.combine(b.period_start, time.min, tzinfo=UTC)
            end_dt = datetime.combine(b.period_end, time.max, tzinfo=UTC)

            # Xác định điều kiện lọc ví theo scope của budget
            if b.scope == "personal":
                wallet_filter = (Account.scope == "personal") & (Account.user_id == b.user_id)
            else:
                wallet_filter = (Account.scope == "family") & (Account.family_id == b.family_id)

            stmt = (
                select(
                    func.coalesce(
                        func.sum(Transaction.amount),
                        Decimal("0.00"),
                    )
                )
                .select_from(Transaction)
                .join(Account, Transaction.account_id == Account.id)
                .outerjoin(Transfer, Transaction.transfer_id == Transfer.id)
                .where(
                    wallet_filter,
                    Account.deleted_at.is_(None),
                    Transaction.category_id == b.category_id,
                    Transaction.deleted_at.is_(None),
                    Transaction.type.in_(["expense", "transfer_fee"]),
                    or_(
                        Transaction.transfer_id.is_(None),
                        Transfer.voided_at.is_(None),
                    ),
                    Transaction.occurred_at >= start_dt,
                    Transaction.occurred_at <= end_dt,
                )
            )

            spent = db.scalar(stmt)
            results[b.id] = spent if spent is not None else Decimal("0.00")

        return results

    @staticmethod
    def _build_budget_response(
        budget: Budget,
        spent_amount: Decimal,
    ) -> BudgetResponse:
        """
        Xây dựng response DTO cho ngân sách kèm các chỉ số tài chính và trạng thái cảnh báo.
        Tất cả phép toán đều được thực hiện trên Decimal.
        """
        amount_limit = budget.amount_limit
        warning_threshold = budget.warning_threshold

        # 1. Số tiền còn lại: max(amount_limit - spent_amount, 0)
        remaining = amount_limit - spent_amount
        remaining_amount = max(Decimal("0.00"), remaining)

        # 2. Số tiền vượt hạn mức: max(spent_amount - amount_limit, 0)
        overspent = spent_amount - amount_limit
        overspent_amount = max(Decimal("0.00"), overspent)

        # 3. Tỷ lệ sử dụng phần trăm: (spent_amount / amount_limit) * 100, làm tròn 2 chữ số thập phân
        usage_percentage = (
            (spent_amount / amount_limit * Decimal("100.00")).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if amount_limit > Decimal("0.00")
            else Decimal("0.00")
        )

        # 4. Trạng thái cảnh báo:
        # - exceeded: spent_amount >= amount_limit
        # - warning: spent_amount >= amount_limit * (warning_threshold / 100) và < amount_limit
        # - normal: ngược lại
        warning_amount = amount_limit * (warning_threshold / Decimal("100.00"))
        if spent_amount >= amount_limit:
            budget_status = "exceeded"
        elif spent_amount >= warning_amount:
            budget_status = "warning"
        else:
            budget_status = "normal"

        category = budget.category

        return BudgetResponse(
            id=budget.id,
            name=budget.name,
            scope=budget.scope,
            user_id=budget.user_id,
            family_id=budget.family_id,
            category_id=budget.category_id,
            category_name=category.name if category else None,
            category_icon=category.icon if category else None,
            category_color=category.color if category else None,
            amount_limit=amount_limit,
            period_start=budget.period_start,
            period_end=budget.period_end,
            warning_threshold=warning_threshold,
            is_archived=budget.is_archived,
            created_at=budget.created_at,
            updated_at=budget.updated_at,
            spent_amount=spent_amount,
            remaining_amount=remaining_amount,
            overspent_amount=overspent_amount,
            usage_percentage=usage_percentage,
            status=budget_status,
        )

    @staticmethod
    def get_budgets(
        db: Session,
        current_user: User,
        scope: str | None = None,
        family_id: uuid.UUID | None = None,
        category_id: uuid.UUID | None = None,
        include_archived: bool = False,
        active_on: date | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[BudgetResponse]:
        """Liệt kê danh sách các ngân sách mà người dùng có quyền truy cập."""
        accessible_family_ids = BudgetService._get_accessible_family_ids(db, current_user)

        # Điều kiện truy cập cơ sở:
        # Ngân sách cá nhân của user HOẶC ngân sách gia đình thuộc các gia đình user được truy cập
        access_condition = or_(
            (Budget.scope == "personal") & (Budget.user_id == current_user.id),
            (Budget.scope == "family") & (Budget.family_id.in_(accessible_family_ids)),
        )

        stmt = (
            select(Budget)
            .options(joinedload(Budget.category))
            .where(
                Budget.deleted_at.is_(None),
                access_condition,
            )
        )

        # Bộ lọc scope
        if scope:
            stmt = stmt.where(Budget.scope == scope)

        # Bộ lọc family_id (chỉ khi user có quyền)
        if family_id:
            if family_id not in accessible_family_ids:
                return []
            stmt = stmt.where(Budget.family_id == family_id)

        # Bộ lọc category_id
        if category_id:
            stmt = stmt.where(Budget.category_id == category_id)

        # Bộ lọc archived
        if not include_archived:
            stmt = stmt.where(Budget.is_archived.is_(False))

        # Bộ lọc active_on (ngày ngân sách đang có hiệu lực)
        if active_on:
            stmt = stmt.where(
                Budget.period_start <= active_on,
                Budget.period_end >= active_on,
            )

        stmt = stmt.order_by(Budget.created_at.desc()).limit(limit).offset(offset)
        budgets = list(db.scalars(stmt).all())

        # Tính toán spent_amount cho toàn bộ ngân sách
        spent_map = BudgetService._compute_spent_amounts(db, budgets)

        return [
            BudgetService._build_budget_response(b, spent_map.get(b.id, Decimal("0.00")))
            for b in budgets
        ]

    @staticmethod
    def get_budget_by_id(
        db: Session,
        budget_id: uuid.UUID,
        current_user: User,
    ) -> BudgetResponse:
        """Lấy chi tiết một ngân sách theo ID kèm tính toán chi tiêu."""
        budget = db.scalar(
            select(Budget)
            .options(joinedload(Budget.category))
            .where(
                Budget.id == budget_id,
                Budget.deleted_at.is_(None),
            )
        )
        if budget is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ngân sách không tồn tại.",
            )

        # Kiểm tra quyền truy cập
        if budget.scope == "personal":
            if budget.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Ngân sách không tồn tại.",
                )
        elif budget.scope == "family":
            if budget.family_id is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Ngân sách không tồn tại.",
                )
            has_role = BudgetService._check_family_role(
                db=db,
                family_id=budget.family_id,
                user=current_user,
                required_role="viewer",
            )
            if not has_role:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Ngân sách không tồn tại.",
                )

        spent_map = BudgetService._compute_spent_amounts(db, [budget])
        spent_amount = spent_map.get(budget.id, Decimal("0.00"))

        return BudgetService._build_budget_response(budget, spent_amount)

    @staticmethod
    def create_budget(
        db: Session,
        req: BudgetCreateRequest,
        current_user: User,
    ) -> BudgetResponse:
        """Tạo ngân sách chi tiêu mới với phân quyền và validation chặt chẽ."""
        # 1. Kiểm tra quyền sở hữu theo scope
        if req.scope == "personal":
            target_user_id = current_user.id
            target_family_id = None
        else:
            assert req.family_id is not None
            # Kiểm tra quyền editor/owner trong gia đình
            family = db.get(Family, req.family_id)
            if family is None or family.deleted_at is not None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Nhóm gia đình không tồn tại.",
                )

            has_role = BudgetService._check_family_role(
                db=db,
                family_id=req.family_id,
                user=current_user,
                required_role="editor",
            )
            if not has_role:
                # Nếu là viewer -> 403 Forbidden
                if BudgetService._check_family_role(
                    db=db, family_id=req.family_id, user=current_user, required_role="viewer"
                ):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Bạn không có quyền tạo ngân sách cho nhóm gia đình này.",
                    )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Nhóm gia đình không tồn tại.",
                )
            target_user_id = None
            target_family_id = req.family_id

        # 2. Kiểm tra danh mục
        BudgetService._validate_category_for_budget(
            db=db,
            category_id=req.category_id,
            scope=req.scope,
            family_id=target_family_id,
            user=current_user,
        )

        # 3. Tạo Budget entity
        budget = Budget(
            id=uuid.uuid4(),
            name=req.name,
            scope=req.scope,
            user_id=target_user_id,
            family_id=target_family_id,
            category_id=req.category_id,
            amount_limit=req.amount_limit,
            period_start=req.period_start,
            period_end=req.period_end,
            warning_threshold=req.warning_threshold,
            is_archived=False,
        )

        db.add(budget)
        db.commit()
        db.refresh(budget)

        # Load category relation
        db.refresh(budget, attribute_names=["category"])

        # Tính toán spent_amount ngay sau khi tạo
        spent_map = BudgetService._compute_spent_amounts(db, [budget])
        spent_amount = spent_map.get(budget.id, Decimal("0.00"))

        logger.info(
            f"Budget created successfully: id={budget.id}, scope={budget.scope}, "
            f"category_id={budget.category_id}, limit={budget.amount_limit}"
        )

        return BudgetService._build_budget_response(budget, spent_amount)

    @staticmethod
    def update_budget(
        db: Session,
        budget_id: uuid.UUID,
        req: BudgetUpdateRequest,
        current_user: User,
    ) -> BudgetResponse:
        """Cập nhật thông tin ngân sách hiện có."""
        budget = db.scalar(
            select(Budget)
            .options(joinedload(Budget.category))
            .where(
                Budget.id == budget_id,
                Budget.deleted_at.is_(None),
            )
        )
        if budget is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ngân sách không tồn tại.",
            )

        # Phân quyền chỉnh sửa
        if budget.scope == "personal":
            if budget.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Ngân sách không tồn tại.",
                )
        elif budget.scope == "family":
            if budget.family_id is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Ngân sách không tồn tại.",
                )
            has_role = BudgetService._check_family_role(
                db=db,
                family_id=budget.family_id,
                user=current_user,
                required_role="editor",
            )
            if not has_role:
                if BudgetService._check_family_role(
                    db=db, family_id=budget.family_id, user=current_user, required_role="viewer"
                ):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Bạn không có quyền chỉnh sửa ngân sách nhóm gia đình.",
                    )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Ngân sách không tồn tại.",
                )

        # Xác thực khoảng thời gian mới nếu có cập nhật
        new_start = req.period_start if req.period_start is not None else budget.period_start
        new_end = req.period_end if req.period_end is not None else budget.period_end
        if new_end < new_start:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ngày kết thúc ngân sách không được trước ngày bắt đầu.",
            )

        # Xác thực danh mục mới nếu có cập nhật
        if req.category_id is not None and req.category_id != budget.category_id:
            BudgetService._validate_category_for_budget(
                db=db,
                category_id=req.category_id,
                scope=budget.scope,
                family_id=budget.family_id,
                user=current_user,
            )
            budget.category_id = req.category_id

        if req.name is not None:
            budget.name = req.name
        if req.amount_limit is not None:
            budget.amount_limit = req.amount_limit
        if req.period_start is not None:
            budget.period_start = req.period_start
        if req.period_end is not None:
            budget.period_end = req.period_end
        if req.warning_threshold is not None:
            budget.warning_threshold = req.warning_threshold

        db.commit()
        db.refresh(budget)
        db.refresh(budget, attribute_names=["category"])

        spent_map = BudgetService._compute_spent_amounts(db, [budget])
        spent_amount = spent_map.get(budget.id, Decimal("0.00"))

        return BudgetService._build_budget_response(budget, spent_amount)

    @staticmethod
    def archive_budget(
        db: Session,
        budget_id: uuid.UUID,
        current_user: User,
    ) -> BudgetResponse:
        """Lưu trữ ngân sách (is_archived = True)."""
        budget = db.scalar(
            select(Budget)
            .options(joinedload(Budget.category))
            .where(
                Budget.id == budget_id,
                Budget.deleted_at.is_(None),
            )
        )
        if budget is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ngân sách không tồn tại.",
            )

        # Phân quyền
        if budget.scope == "personal":
            if budget.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Ngân sách không tồn tại.",
                )
        elif budget.scope == "family":
            if budget.family_id is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Ngân sách không tồn tại.",
                )
            has_role = BudgetService._check_family_role(
                db=db,
                family_id=budget.family_id,
                user=current_user,
                required_role="editor",
            )
            if not has_role:
                if BudgetService._check_family_role(
                    db=db, family_id=budget.family_id, user=current_user, required_role="viewer"
                ):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Bạn không có quyền lưu trữ ngân sách gia đình.",
                    )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Ngân sách không tồn tại.",
                )

        budget.is_archived = True
        db.commit()
        db.refresh(budget)
        db.refresh(budget, attribute_names=["category"])

        spent_map = BudgetService._compute_spent_amounts(db, [budget])
        spent_amount = spent_map.get(budget.id, Decimal("0.00"))

        return BudgetService._build_budget_response(budget, spent_amount)

    @staticmethod
    def restore_budget(
        db: Session,
        budget_id: uuid.UUID,
        current_user: User,
    ) -> BudgetResponse:
        """Khôi phục ngân sách từ trạng thái lưu trữ (is_archived = False)."""
        budget = db.scalar(
            select(Budget)
            .options(joinedload(Budget.category))
            .where(
                Budget.id == budget_id,
                Budget.deleted_at.is_(None),
            )
        )
        if budget is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ngân sách không tồn tại.",
            )

        # Phân quyền
        if budget.scope == "personal":
            if budget.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Ngân sách không tồn tại.",
                )
        elif budget.scope == "family":
            if budget.family_id is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Ngân sách không tồn tại.",
                )
            has_role = BudgetService._check_family_role(
                db=db,
                family_id=budget.family_id,
                user=current_user,
                required_role="editor",
            )
            if not has_role:
                if BudgetService._check_family_role(
                    db=db, family_id=budget.family_id, user=current_user, required_role="viewer"
                ):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Bạn không có quyền khôi phục ngân sách gia đình.",
                    )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Ngân sách không tồn tại.",
                )

        budget.is_archived = False
        db.commit()
        db.refresh(budget)
        db.refresh(budget, attribute_names=["category"])

        spent_map = BudgetService._compute_spent_amounts(db, [budget])
        spent_amount = spent_map.get(budget.id, Decimal("0.00"))

        return BudgetService._build_budget_response(budget, spent_amount)
