import logging
import uuid
from datetime import UTC, datetime
from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.account import Account
from app.models.category import Category
from app.models.family import Family
from app.models.family_member import FamilyMember
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.transaction import (
    TransactionCreateRequest,
    TransactionResponse,
    TransactionUpdateRequest,
)

logger = logging.getLogger(__name__)


class TransactionService:
    """Service xử lý nghiệp vụ giao dịch thu chi (income/expense), phân quyền và lọc dữ liệu."""

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
    def _validate_account_access(
        db: Session, account_id: uuid.UUID, user: User, required_role: str = "viewer"
    ) -> Account:
        """
        Kiểm tra quyền truy cập vào ví tài chính:
        - Ví cá nhân: chỉ chính chủ user_id == user.id mới có toàn quyền (viewer / editor / owner).
        - Ví gia đình: kiểm tra vai trò trong nhóm gia đình tương ứng.
        """
        account = db.get(Account, account_id)
        if account is None or account.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ví tài chính không tồn tại.",
            )

        if account.scope == "personal":
            if account.user_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Ví tài chính không tồn tại.",
                )
        elif account.scope == "family":
            if account.family_id is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Ví tài chính không tồn tại.",
                )
            has_role = TransactionService._check_family_role(
                db=db,
                family_id=account.family_id,
                user=user,
                required_role=required_role,
            )
            if not has_role:
                # Nếu là viewer muốn ghi dữ liệu -> 403 Forbidden
                if required_role == "editor" and TransactionService._check_family_role(
                    db=db,
                    family_id=account.family_id,
                    user=user,
                    required_role="viewer",
                ):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Bạn không có quyền thực hiện giao dịch trên ví gia đình này.",
                    )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Ví tài chính không tồn tại.",
                )

        return account

    @staticmethod
    def _validate_category(
        db: Session,
        category_id: uuid.UUID,
        transaction_type: str,
        account: Account,
        user: User,
    ) -> Category:
        """
        Kiểm tra tính hợp lệ của danh mục đối với giao dịch:
        1. Danh mục tồn tại và chưa bị xóa mềm.
        2. Không bị lưu trữ (`is_archived IS FALSE`).
        3. Cùng loại thu/chi (`category.type == transaction_type`).
        4. Tương thích phạm vi:
           - Category 'system': được dùng cho cả ví cá nhân và ví gia đình.
           - Category 'personal': chỉ được dùng khi user_id == user.id và account.scope == 'personal'.
           - Category 'family': chỉ được dùng khi category.family_id == account.family_id.
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
                detail="Không thể sử dụng danh mục đang bị lưu trữ.",
            )

        if category.type != transaction_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Loại danh mục ({category.type}) không khớp với loại giao dịch ({transaction_type}).",
            )

        # Kiểm tra tính tương thích phạm vi
        if category.scope == "system":
            pass  # Cho phép mọi ví
        elif category.scope == "personal":
            if account.scope != "personal" or category.user_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Danh mục cá nhân chỉ có thể sử dụng cho ví cá nhân của chính bạn.",
                )
        elif category.scope == "family" and (
            account.scope != "family" or category.family_id != account.family_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Danh mục gia đình chỉ có thể sử dụng cho ví thuộc cùng nhóm gia đình.",
            )

        return category

    @staticmethod
    def get_transactions(
        db: Session,
        current_user: User,
        account_id: uuid.UUID | None = None,
        category_id: uuid.UUID | None = None,
        type_: Literal["income", "expense"] | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TransactionResponse]:
        """
        Truy vấn danh sách giao dịch người dùng có quyền xem:
        - Chỉ trả giao dịch thuộc các ví mà user có quyền truy cập.
        - Tránh N+1 query bằng joinedload (account, category, creator).
        """
        if date_from and date_to and date_from > date_to:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Thời gian bắt đầu (date_from) không được lớn hơn thời gian kết thúc (date_to).",
            )

        # 1. Tập hợp các ví mà user có quyền xem
        accessible_family_ids = TransactionService._get_accessible_family_ids(db, current_user)
        accessible_account_filter = or_(
            (Account.scope == "personal") & (Account.user_id == current_user.id),
            (Account.scope == "family") & (Account.family_id.in_(accessible_family_ids))
            if accessible_family_ids
            else False,
        )

        conditions = [
            Transaction.deleted_at.is_(None),
            Account.deleted_at.is_(None),
            accessible_account_filter,
        ]

        # Bộ lọc cụ thể
        if account_id:
            # Xác minh quyền xem trên ví này
            TransactionService._validate_account_access(
                db=db, account_id=account_id, user=current_user, required_role="viewer"
            )
            conditions.append(Transaction.account_id == account_id)

        if category_id:
            conditions.append(Transaction.category_id == category_id)

        if type_:
            conditions.append(Transaction.type == type_)

        if date_from:
            conditions.append(Transaction.occurred_at >= date_from)

        if date_to:
            conditions.append(Transaction.occurred_at <= date_to)

        # Truy vấn với joinedload để nạp quan hệ cùng lúc
        stmt = (
            select(Transaction)
            .join(Account, Transaction.account_id == Account.id)
            .options(
                joinedload(Transaction.account),
                joinedload(Transaction.category),
                joinedload(Transaction.creator),
            )
            .where(*conditions)
            .order_by(Transaction.occurred_at.desc(), Transaction.id.desc())
            .limit(limit)
            .offset(offset)
        )

        transactions = db.scalars(stmt).all()

        return [
            TransactionResponse(
                id=tx.id,
                account_id=tx.account_id,
                account_name=tx.account.name if tx.account else None,
                account_currency=tx.account.currency if tx.account else None,
                category_id=tx.category_id,
                category_name=tx.category.name if tx.category else None,
                category_icon=tx.category.icon if tx.category else None,
                category_color=tx.category.color if tx.category else None,
                user_id=tx.user_id,
                creator_name=tx.creator.display_name if tx.creator else None,
                type=tx.type,  # type: ignore[arg-type]
                amount=tx.amount,
                note=tx.note,
                occurred_at=tx.occurred_at,
                created_at=tx.created_at,
                updated_at=tx.updated_at,
            )
            for tx in transactions
        ]

    @staticmethod
    def create_transaction(
        db: Session,
        current_user: User,
        request: TransactionCreateRequest,
    ) -> TransactionResponse:
        """Tạo giao dịch thu/chi mới."""
        if request.type not in ("income", "expense"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Loại giao dịch bắt buộc phải là 'income' hoặc 'expense'.",
            )

        if request.amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Số tiền giao dịch phải lớn hơn 0.",
            )

        # Kiểm tra ví: phải có quyền ghi (editor hoặc owner), ví không bị lưu trữ
        account = TransactionService._validate_account_access(
            db=db,
            account_id=request.account_id,
            user=current_user,
            required_role="editor",
        )
        if account.is_archived:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể tạo giao dịch trên ví đã bị lưu trữ.",
            )

        # Kiểm tra danh mục
        category = TransactionService._validate_category(
            db=db,
            category_id=request.category_id,
            transaction_type=request.type,
            account=account,
            user=current_user,
        )

        occurred_at = request.occurred_at or datetime.now(UTC)

        new_tx = Transaction(
            account_id=account.id,
            category_id=category.id,
            transfer_id=None,
            user_id=current_user.id,
            type=request.type,
            amount=request.amount,
            note=request.note.strip() if request.note and request.note.strip() else None,
            occurred_at=occurred_at,
        )

        db.add(new_tx)
        db.commit()
        db.refresh(new_tx)

        return TransactionResponse(
            id=new_tx.id,
            account_id=new_tx.account_id,
            account_name=account.name,
            account_currency=account.currency,
            category_id=new_tx.category_id,
            category_name=category.name,
            category_icon=category.icon,
            category_color=category.color,
            user_id=new_tx.user_id,
            creator_name=current_user.display_name,
            type=new_tx.type,  # type: ignore[arg-type]
            amount=new_tx.amount,
            note=new_tx.note,
            occurred_at=new_tx.occurred_at,
            created_at=new_tx.created_at,
            updated_at=new_tx.updated_at,
        )

    @staticmethod
    def get_transaction_detail(
        db: Session,
        transaction_id: uuid.UUID,
        current_user: User,
    ) -> TransactionResponse:
        """Xem chi tiết giao dịch."""
        stmt = (
            select(Transaction)
            .options(
                joinedload(Transaction.account),
                joinedload(Transaction.category),
                joinedload(Transaction.creator),
            )
            .where(
                Transaction.id == transaction_id,
                Transaction.deleted_at.is_(None),
            )
        )
        tx = db.scalar(stmt)
        if tx is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Giao dịch không tồn tại.",
            )

        # Kiểm tra quyền xem ví chứa giao dịch
        TransactionService._validate_account_access(
            db=db,
            account_id=tx.account_id,
            user=current_user,
            required_role="viewer",
        )

        return TransactionResponse(
            id=tx.id,
            account_id=tx.account_id,
            account_name=tx.account.name if tx.account else None,
            account_currency=tx.account.currency if tx.account else None,
            category_id=tx.category_id,
            category_name=tx.category.name if tx.category else None,
            category_icon=tx.category.icon if tx.category else None,
            category_color=tx.category.color if tx.category else None,
            user_id=tx.user_id,
            creator_name=tx.creator.display_name if tx.creator else None,
            type=tx.type,  # type: ignore[arg-type]
            amount=tx.amount,
            note=tx.note,
            occurred_at=tx.occurred_at,
            created_at=tx.created_at,
            updated_at=tx.updated_at,
        )

    @staticmethod
    def update_transaction(
        db: Session,
        transaction_id: uuid.UUID,
        current_user: User,
        request: TransactionUpdateRequest,
    ) -> TransactionResponse:
        """
        Chỉnh sửa giao dịch thu/chi (amount, category_id, type, note, occurred_at).
        Không cho đổi ví (account_id) để đảm bảo toàn vẹn phân quyền ví, không cho sửa transfer_id.
        """
        stmt = (
            select(Transaction)
            .options(
                joinedload(Transaction.account),
                joinedload(Transaction.category),
                joinedload(Transaction.creator),
            )
            .where(
                Transaction.id == transaction_id,
                Transaction.deleted_at.is_(None),
            )
        )
        tx = db.scalar(stmt)
        if tx is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Giao dịch không tồn tại hoặc đã bị xóa.",
            )

        # Không cho sửa giao dịch chuyển khoản qua API thu chi
        if tx.transfer_id is not None or tx.type not in ("income", "expense"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể chỉnh sửa giao dịch chuyển khoản qua API này.",
            )

        # Kiểm tra quyền ghi trên ví
        account = TransactionService._validate_account_access(
            db=db,
            account_id=tx.account_id,
            user=current_user,
            required_role="editor",
        )

        # Xác định type mới nếu có thay đổi
        new_type = request.type or tx.type
        if new_type not in ("income", "expense"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Loại giao dịch chỉ có thể là 'income' hoặc 'expense'.",
            )

        # Xác định category mới nếu có thay đổi
        new_category_id = request.category_id or tx.category_id
        if new_category_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Giao dịch thu/chi bắt buộc phải gắn với danh mục.",
            )

        category = TransactionService._validate_category(
            db=db,
            category_id=new_category_id,
            transaction_type=new_type,
            account=account,
            user=current_user,
        )

        if request.amount is not None:
            if request.amount <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Số tiền giao dịch phải lớn hơn 0.",
                )
            tx.amount = request.amount

        tx.type = new_type
        tx.category_id = category.id

        if request.note is not None:
            tx.note = request.note.strip() if request.note.strip() else None

        if request.occurred_at is not None:
            tx.occurred_at = request.occurred_at

        db.commit()
        db.refresh(tx)

        return TransactionResponse(
            id=tx.id,
            account_id=tx.account_id,
            account_name=account.name,
            account_currency=account.currency,
            category_id=category.id,
            category_name=category.name,
            category_icon=category.icon,
            category_color=category.color,
            user_id=tx.user_id,
            creator_name=tx.creator.display_name if tx.creator else None,
            type=tx.type,  # type: ignore[arg-type]
            amount=tx.amount,
            note=tx.note,
            occurred_at=tx.occurred_at,
            created_at=tx.created_at,
            updated_at=tx.updated_at,
        )

    @staticmethod
    def soft_delete_transaction(
        db: Session,
        transaction_id: uuid.UUID,
        current_user: User,
    ) -> dict[str, str]:
        """
        Xóa mềm giao dịch bằng deleted_at.
        Tự động loại bỏ ảnh hưởng khỏi số dư ví.
        """
        tx = db.get(Transaction, transaction_id)
        if tx is None or tx.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Giao dịch không tồn tại hoặc đã bị xóa.",
            )

        # Không cho xóa giao dịch chuyển tiền qua API này
        if tx.transfer_id is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể xóa giao dịch chuyển khoản qua API này.",
            )

        # Kiểm tra quyền ghi trên ví
        TransactionService._validate_account_access(
            db=db,
            account_id=tx.account_id,
            user=current_user,
            required_role="editor",
        )

        tx.deleted_at = datetime.now(UTC)
        db.commit()

        return {"message": "Đã xóa mềm giao dịch thành công."}
