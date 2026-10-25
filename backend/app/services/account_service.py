import logging
import uuid
from collections.abc import Sequence
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.family import Family
from app.models.family_member import FamilyMember
from app.models.transaction import Transaction
from app.models.transfer import Transfer
from app.models.user import User
from app.schemas.account import (
    AccountCreateRequest,
    AccountResponse,
    AccountUpdateRequest,
)

logger = logging.getLogger(__name__)


class AccountService:
    """Service xử lý nghiệp vụ quản lý ví tài chính, phân quyền cá nhân/gia đình và tính toán số dư."""

    @staticmethod
    def _compute_current_balances(
        db: Session, account_ids: Sequence[uuid.UUID]
    ) -> dict[uuid.UUID, Decimal]:
        """
        Tính toán tổng số dư phát sinh từ các giao dịch hợp lệ cho danh sách ví.
        Tránh N+1 query bằng một truy vấn tổng hợp duy nhất.
        
        Quy tắc lọc:
        - transactions.deleted_at IS NULL (loại bỏ soft-deleted).
        - Giao dịch liên quan đến transfer bị hủy (transfers.voided_at IS NOT NULL) bị loại trừ.
        
        Công thức:
        Delta = Income + Transfer_In - Expense - Transfer_Out - Transfer_Fee
        """
        if not account_ids:
            return {}

        # Subquery hoặc join với transfers để kiểm tra cờ voided
        delta_expr = func.coalesce(
            func.sum(
                case(
                    # Thu nhập: + amount
                    (Transaction.type == "income", Transaction.amount),
                    # Chuyển khoản đến ví đích: + amount
                    (Transaction.type == "transfer_in", Transaction.amount),
                    # Chi tiêu: - amount
                    (Transaction.type == "expense", -Transaction.amount),
                    # Chuyển khoản đi khỏi ví nguồn: - amount
                    (Transaction.type == "transfer_out", -Transaction.amount),
                    # Phí chuyển tiền trừ tại ví nguồn: - amount
                    (Transaction.type == "transfer_fee", -Transaction.amount),
                    else_=Decimal("0.00"),
                )
            ),
            Decimal("0.00"),
        )

        stmt = (
            select(Transaction.account_id, delta_expr.label("delta"))
            .outerjoin(Transfer, Transaction.transfer_id == Transfer.id)
            .where(
                Transaction.account_id.in_(account_ids),
                Transaction.deleted_at.is_(None),
                or_(
                    Transaction.transfer_id.is_(None),
                    Transfer.voided_at.is_(None),
                ),
            )
            .group_by(Transaction.account_id)
        )

        deltas = dict(db.execute(stmt).all())
        return {acc_id: deltas.get(acc_id, Decimal("0.00")) for acc_id in account_ids}

    @staticmethod
    def _check_family_permission(
        db: Session, family_id: uuid.UUID, user: User, required_role: str = "viewer"
    ) -> bool:
        """
        Kiểm tra quyền của người dùng đối với nhóm gia đình.
        - required_role = 'viewer': cho phép owner, editor, viewer (active).
        - required_role = 'editor': chỉ cho phép owner, editor (active).
        - required_role = 'owner': chỉ cho phép owner (active).
        """
        family = db.get(Family, family_id)
        if family is None or family.deleted_at is not None:
            return False

        # Nếu user là Family.owner_user_id -> toàn quyền
        if family.owner_user_id == user.id:
            return True

        # Kiểm tra bảng FamilyMember
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
    def get_accessible_accounts(
        db: Session,
        current_user: User,
        scope: str | None = None,
        family_id: uuid.UUID | None = None,
        include_archived: bool = False,
    ) -> list[AccountResponse]:
        """
        Truy vấn danh sách các ví mà người dùng có quyền xem (kèm số dư hiện tại).
        - Không trả các ví đã xóa mềm (deleted_at IS NOT NULL).
        - Lọc archived theo include_archived.
        """
        # 1. Tìm các gia đình mà user có quyền xem
        # - Gia đình do user làm owner
        # - Gia đình user là member (left_at IS NULL)
        accessible_family_ids_query = select(Family.id).where(
            Family.owner_user_id == current_user.id,
            Family.deleted_at.is_(None),
        ).union(
            select(FamilyMember.family_id).join(Family, FamilyMember.family_id == Family.id).where(
                FamilyMember.user_id == current_user.id,
                FamilyMember.left_at.is_(None),
                Family.deleted_at.is_(None),
            )
        )
        accessible_family_ids = set(db.scalars(accessible_family_ids_query).all())

        # Xây dựng điều kiện lọc accounts
        conditions = [Account.deleted_at.is_(None)]

        if not include_archived:
            conditions.append(Account.is_archived.is_(False))

        if scope == "personal":
            conditions.append(Account.scope == "personal")
            conditions.append(Account.user_id == current_user.id)
        elif scope == "family":
            conditions.append(Account.scope == "family")
            if family_id:
                if family_id not in accessible_family_ids:
                    return []
                conditions.append(Account.family_id == family_id)
            else:
                if not accessible_family_ids:
                    return []
                conditions.append(Account.family_id.in_(accessible_family_ids))
        else:
            # Cả hai: Ví cá nhân của mình HOẶC ví gia đình mình được phép
            conditions.append(
                or_(
                    (Account.scope == "personal") & (Account.user_id == current_user.id),
                    (Account.scope == "family") & (Account.family_id.in_(accessible_family_ids)),
                )
            )
            if family_id:
                if family_id not in accessible_family_ids:
                    return []
                conditions.append(Account.family_id == family_id)

        accounts = db.scalars(select(Account).where(*conditions).order_by(Account.created_at.desc())).all()

        if not accounts:
            return []

        # 2. Tính số dư cho toàn bộ ví cùng lúc
        acc_ids = [acc.id for acc in accounts]
        deltas = AccountService._compute_current_balances(db, acc_ids)

        result: list[AccountResponse] = []
        for acc in accounts:
            current_balance = acc.initial_balance + deltas.get(acc.id, Decimal("0.00"))
            result.append(
                AccountResponse(
                    id=acc.id,
                    name=acc.name,
                    scope=acc.scope,
                    account_type=acc.account_type,
                    currency=acc.currency,
                    initial_balance=acc.initial_balance,
                    current_balance=current_balance,
                    is_archived=acc.is_archived,
                    family_id=acc.family_id,
                    created_at=acc.created_at,
                    updated_at=acc.updated_at,
                )
            )

        return result

    @staticmethod
    def create_account(
        db: Session,
        current_user: User,
        request: AccountCreateRequest,
    ) -> AccountResponse:
        """Tạo ví mới cho cá nhân hoặc gia đình theo phân quyền."""
        if request.scope == "personal":
            if request.family_id is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Ví cá nhân không được gắn family_id.",
                )
            user_id = current_user.id
            family_id = None

        elif request.scope == "family":
            if request.family_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Ví gia đình bắt buộc phải cung cấp family_id.",
                )
            # Kiểm tra quyền tạo ví gia đình (cần quyền editor hoặc owner)
            has_permission = AccountService._check_family_permission(
                db=db,
                family_id=request.family_id,
                user=current_user,
                required_role="editor",
            )
            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Bạn không có quyền tạo ví cho nhóm gia đình này.",
                )
            user_id = None
            family_id = request.family_id
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phạm vi sở hữu không hợp lệ (chỉ 'personal' hoặc 'family').",
            )

        new_account = Account(
            name=request.name.strip(),
            scope=request.scope,
            user_id=user_id,
            family_id=family_id,
            account_type=request.account_type,
            currency=request.currency.strip().upper(),
            initial_balance=request.initial_balance,
            is_archived=False,
        )

        db.add(new_account)
        db.commit()
        db.refresh(new_account)

        return AccountResponse(
            id=new_account.id,
            name=new_account.name,
            scope=new_account.scope,
            account_type=new_account.account_type,
            currency=new_account.currency,
            initial_balance=new_account.initial_balance,
            current_balance=new_account.initial_balance,
            is_archived=new_account.is_archived,
            family_id=new_account.family_id,
            created_at=new_account.created_at,
            updated_at=new_account.updated_at,
        )

    @staticmethod
    def get_account_detail(
        db: Session,
        account_id: uuid.UUID,
        current_user: User,
    ) -> AccountResponse:
        """Xem chi tiết ví và số dư khả dụng."""
        account = db.get(Account, account_id)
        if account is None or account.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ví tài chính không tồn tại.",
            )

        # Kiểm tra quyền xem
        if account.scope == "personal" and account.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ví tài chính không tồn tại.",
            )
        if account.scope == "family" and (
            account.family_id is None
            or not AccountService._check_family_permission(
                db=db,
                family_id=account.family_id,
                user=current_user,
                required_role="viewer",
            )
        ):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ví tài chính không tồn tại.",
            )

        deltas = AccountService._compute_current_balances(db, [account.id])
        current_balance = account.initial_balance + deltas.get(account.id, Decimal("0.00"))

        return AccountResponse(
            id=account.id,
            name=account.name,
            scope=account.scope,
            account_type=account.account_type,
            currency=account.currency,
            initial_balance=account.initial_balance,
            current_balance=current_balance,
            is_archived=account.is_archived,
            family_id=account.family_id,
            created_at=account.created_at,
            updated_at=account.updated_at,
        )

    @staticmethod
    def update_account(
        db: Session,
        account_id: uuid.UUID,
        current_user: User,
        request: AccountUpdateRequest,
    ) -> AccountResponse:
        """Cập nhật thông tin ví (tên, phân loại)."""
        account = db.get(Account, account_id)
        if account is None or account.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ví tài chính không tồn tại.",
            )

        # Kiểm tra quyền chỉnh sửa
        if account.scope == "personal" and account.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ví tài chính không tồn tại.",
            )
        if account.scope == "family" and (
            account.family_id is None
            or not AccountService._check_family_permission(
                db=db,
                family_id=account.family_id,
                user=current_user,
                required_role="editor",
            )
        ):
            # Nếu là viewer -> 403 Forbidden
            if account.family_id and AccountService._check_family_permission(
                db=db,
                family_id=account.family_id,
                user=current_user,
                required_role="viewer",
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Bạn không có quyền chỉnh sửa ví gia đình này.",
                )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ví tài chính không tồn tại.",
            )

        if request.name is not None and request.name.strip():
            account.name = request.name.strip()
        if request.account_type is not None:
            account.account_type = request.account_type

        db.commit()
        db.refresh(account)

        deltas = AccountService._compute_current_balances(db, [account.id])
        current_balance = account.initial_balance + deltas.get(account.id, Decimal("0.00"))

        return AccountResponse(
            id=account.id,
            name=account.name,
            scope=account.scope,
            account_type=account.account_type,
            currency=account.currency,
            initial_balance=account.initial_balance,
            current_balance=current_balance,
            is_archived=account.is_archived,
            family_id=account.family_id,
            created_at=account.created_at,
            updated_at=account.updated_at,
        )

    @staticmethod
    def set_archive_status(
        db: Session,
        account_id: uuid.UUID,
        current_user: User,
        archive: bool,
    ) -> AccountResponse:
        """Lưu trữ (archive) hoặc khôi phục (restore) ví."""
        account = db.get(Account, account_id)
        if account is None or account.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ví tài chính không tồn tại.",
            )

        # Kiểm tra quyền sửa
        if account.scope == "personal" and account.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ví tài chính không tồn tại.",
            )
        if account.scope == "family" and (
            account.family_id is None
            or not AccountService._check_family_permission(
                db=db,
                family_id=account.family_id,
                user=current_user,
                required_role="editor",
            )
        ):
            if account.family_id and AccountService._check_family_permission(
                db=db,
                family_id=account.family_id,
                user=current_user,
                required_role="viewer",
            ):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Bạn không có quyền quản lý lưu trữ ví gia đình này.",
                )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ví tài chính không tồn tại.",
            )

        account.is_archived = archive
        db.commit()
        db.refresh(account)

        deltas = AccountService._compute_current_balances(db, [account.id])
        current_balance = account.initial_balance + deltas.get(account.id, Decimal("0.00"))

        return AccountResponse(
            id=account.id,
            name=account.name,
            scope=account.scope,
            account_type=account.account_type,
            currency=account.currency,
            initial_balance=account.initial_balance,
            current_balance=current_balance,
            is_archived=account.is_archived,
            family_id=account.family_id,
            created_at=account.created_at,
            updated_at=account.updated_at,
        )
