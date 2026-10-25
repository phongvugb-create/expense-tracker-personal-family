import logging
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.account import Account
from app.models.category import Category
from app.models.family import Family
from app.models.family_member import FamilyMember
from app.models.transaction import Transaction
from app.models.transfer import Transfer
from app.models.user import User
from app.schemas.transfer import TransferCreateRequest, TransferResponse

logger = logging.getLogger(__name__)


class TransferService:
    """Service xử lý nghiệp vụ chuyển tiền giữa hai ví, hạch toán kép và bảo toàn số dư."""

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
    def _validate_transfer_accounts(
        db: Session,
        from_account_id: uuid.UUID,
        to_account_id: uuid.UUID,
        user: User,
    ) -> tuple[Account, Account]:
        """
        Xác minh quyền và tính tương thích giữa ví nguồn và ví đích:
        1. from_account_id != to_account_id.
        2. Cả 2 ví tồn tại, chưa bị xóa mềm (deleted_at IS NULL) và chưa lưu trữ (is_archived IS FALSE).
        3. Cùng loại tiền tệ (currency).
        4. Phân quyền và phạm vi tương thích:
           - Hai ví cá nhân: User phải là chủ sở hữu (user_id == user.id) của CẢ HAI ví.
           - Hai ví gia đình: Cùng thuộc 1 gia đình (family_id trùng nhau), user phải có vai trò owner hoặc editor.
           - Không cho phép chuyển chéo giữa ví cá nhân và ví gia đình, hoặc giữa hai gia đình khác nhau.
        """
        if from_account_id == to_account_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ví nguồn và ví đích phải khác nhau.",
            )

        from_acc = db.get(Account, from_account_id)
        to_acc = db.get(Account, to_account_id)

        # 404 nếu không tìm thấy hoặc đã bị xóa mềm
        if from_acc is None or from_acc.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ví nguồn không tồn tại hoặc đã bị xóa.",
            )
        if to_acc is None or to_acc.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ví đích không tồn tại hoặc đã bị xóa.",
            )

        # Kiểm tra trạng thái lưu trữ
        if from_acc.is_archived:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể thực hiện chuyển tiền từ ví đã được lưu trữ.",
            )
        if to_acc.is_archived:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể thực hiện chuyển tiền đến ví đã được lưu trữ.",
            )

        # Kiểm tra tính tương thích tiền tệ
        if from_acc.currency != to_acc.currency:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Hai ví phải sử dụng cùng loại tiền tệ ({from_acc.currency} != {to_acc.currency}).",
            )

        # Kiểm tra phân quyền và phạm vi sở hữu
        if from_acc.scope != to_acc.scope:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không hỗ trợ chuyển tiền trực tiếp giữa ví cá nhân và ví gia đình.",
            )

        if from_acc.scope == "personal":
            # Cả hai ví cá nhân phải thuộc chính user hiện tại
            if from_acc.user_id != user.id or to_acc.user_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Bạn chỉ có thể chuyển tiền giữa các ví cá nhân của chính mình.",
                )
        elif from_acc.scope == "family":
            # Cả hai ví gia đình phải thuộc cùng một nhóm gia đình
            if from_acc.family_id != to_acc.family_id or from_acc.family_id is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Không hỗ trợ chuyển tiền giữa hai nhóm gia đình khác nhau.",
                )

            # User phải là owner hoặc editor của nhóm gia đình đó
            has_write_perm = TransferService._check_family_role(
                db=db, family_id=from_acc.family_id, user=user, required_role="editor"
            )
            if not has_write_perm:
                # Kiểm tra nếu là viewer -> 403, nếu không thuộc nhóm -> 404
                has_view_perm = TransferService._check_family_role(
                    db=db, family_id=from_acc.family_id, user=user, required_role="viewer"
                )
                if has_view_perm:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Thành viên với vai trò Viewer không có quyền chuyển tiền trong ví gia đình.",
                    )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Không tìm thấy ví gia đình hoặc bạn không phải thành viên của nhóm.",
                )

        return from_acc, to_acc

    @staticmethod
    def _validate_fee_category(
        db: Session,
        fee_category_id: uuid.UUID,
        from_account: Account,
        user: User,
    ) -> Category:
        """
        Xác minh danh mục chi phí chuyển tiền:
        1. Tồn tại, chưa bị xóa mềm, chưa bị lưu trữ.
        2. category.type == 'expense'.
        3. Tương thích phạm vi với ví nguồn (from_account):
           - scope='system': hợp lệ cho mọi ví.
           - scope='personal': chỉ hợp lệ nếu from_account là cá nhân và category.user_id == user.id.
           - scope='family': chỉ hợp lệ nếu from_account là gia đình và category.family_id == from_account.family_id.
        """
        category = db.get(Category, fee_category_id)
        if category is None or category.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Danh mục phí chuyển tiền không tồn tại hoặc đã bị xóa.",
            )

        if category.is_archived:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể sử dụng danh mục phí đang bị lưu trữ.",
            )

        if category.type != "expense":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Danh mục phí chuyển tiền bắt buộc phải là loại chi tiêu ('expense').",
            )

        if category.scope == "system":
            pass
        elif category.scope == "personal":
            if from_account.scope != "personal" or category.user_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Danh mục phí cá nhân chỉ có thể sử dụng cho ví cá nhân của chính bạn.",
                )
        elif category.scope == "family" and (
            from_account.scope != "family" or category.family_id != from_account.family_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Danh mục phí gia đình chỉ có thể sử dụng cho ví thuộc cùng nhóm gia đình.",
            )

        return category

    @staticmethod
    def _build_transfer_response(
        transfer: Transfer,
        fee_category_id: uuid.UUID | None = None,
    ) -> TransferResponse:
        """Chuyển đổi ORM Transfer sang TransferResponse kèm thông tin nạp sẵn."""
        # Nếu chưa có fee_category_id, duyệt qua các transactions để tìm nếu có transfer_fee
        if fee_category_id is None and transfer.transactions:
            for tx in transfer.transactions:
                if tx.type == "transfer_fee":
                    fee_category_id = tx.category_id
                    break

        return TransferResponse(
            id=transfer.id,
            from_account_id=transfer.from_account_id,
            from_account_name=transfer.from_account.name if transfer.from_account else None,
            to_account_id=transfer.to_account_id,
            to_account_name=transfer.to_account.name if transfer.to_account else None,
            created_by=transfer.created_by,
            creator_name=transfer.creator.display_name if transfer.creator else None,
            amount=transfer.amount,
            fee_amount=transfer.fee_amount,
            fee_category_id=fee_category_id,
            currency=transfer.from_account.currency if transfer.from_account else None,
            note=transfer.note,
            occurred_at=transfer.occurred_at,
            created_at=transfer.created_at,
            updated_at=transfer.updated_at,
            voided_at=transfer.voided_at,
            is_voided=transfer.is_voided,
        )

    @staticmethod
    def get_transfers(
        db: Session,
        current_user: User,
        account_id: uuid.UUID | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        include_voided: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[TransferResponse]:
        """
        Lấy danh sách các giao dịch chuyển tiền mà người dùng có quyền xem:
        - Ví cá nhân của chính mình.
        - Ví gia đình thuộc nhóm mà người dùng có quyền (owner, editor, viewer).
        """
        if date_from and date_to and date_from > date_to:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Khoảng thời gian không hợp lệ: date_from không được lớn hơn date_to.",
            )

        accessible_family_ids = TransferService._get_accessible_family_ids(db, current_user)

        # Lấy danh sách ID các ví mà user có quyền xem
        acc_stmt = select(Account.id).where(
            Account.deleted_at.is_(None),
            or_(
                Account.user_id == current_user.id,
                Account.family_id.in_(accessible_family_ids),
            ),
        )
        accessible_acc_ids = set(db.scalars(acc_stmt).all())

        if not accessible_acc_ids:
            return []

        # Nếu có bộ lọc account_id
        if account_id:
            if account_id not in accessible_acc_ids:
                return []
            allowed_acc_ids = {account_id}
        else:
            allowed_acc_ids = accessible_acc_ids

        # Query Transfer với joinedload chống N+1
        stmt = (
            select(Transfer)
            .options(
                joinedload(Transfer.from_account),
                joinedload(Transfer.to_account),
                joinedload(Transfer.creator),
                joinedload(Transfer.transactions),
            )
            .where(
                or_(
                    Transfer.from_account_id.in_(allowed_acc_ids),
                    Transfer.to_account_id.in_(allowed_acc_ids),
                )
            )
        )

        if not include_voided:
            stmt = stmt.where(Transfer.voided_at.is_(None))

        if date_from:
            stmt = stmt.where(Transfer.occurred_at >= date_from)
        if date_to:
            stmt = stmt.where(Transfer.occurred_at <= date_to)

        # Sắp xếp occurred_at DESC, created_at DESC ổn định
        stmt = (
            stmt.order_by(
                Transfer.occurred_at.desc(),
                Transfer.created_at.desc(),
                Transfer.id.desc(),
            )
            .limit(limit)
            .offset(offset)
        )

        transfers = db.scalars(stmt).unique().all()
        return [TransferService._build_transfer_response(t) for t in transfers]

    @staticmethod
    def get_transfer_detail(
        db: Session,
        transfer_id: uuid.UUID,
        current_user: User,
    ) -> TransferResponse:
        """
        Xem chi tiết một chuyển tiền. Trả 404 nếu không tồn tại hoặc người dùng không có quyền truy cập.
        """
        transfer = db.scalar(
            select(Transfer)
            .options(
                joinedload(Transfer.from_account),
                joinedload(Transfer.to_account),
                joinedload(Transfer.creator),
                joinedload(Transfer.transactions),
            )
            .where(Transfer.id == transfer_id)
        )
        if transfer is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy giao dịch chuyển tiền.",
            )

        accessible_family_ids = TransferService._get_accessible_family_ids(db, current_user)

        # Kiểm tra user có quyền xem ít nhất 1 trong 2 ví (from hoặc to)
        has_perm_from = (
            transfer.from_account
            and transfer.from_account.deleted_at is None
            and (
                transfer.from_account.user_id == current_user.id
                or transfer.from_account.family_id in accessible_family_ids
            )
        )
        has_perm_to = (
            transfer.to_account
            and transfer.to_account.deleted_at is None
            and (
                transfer.to_account.user_id == current_user.id
                or transfer.to_account.family_id in accessible_family_ids
            )
        )

        if not (has_perm_from or has_perm_to):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy giao dịch chuyển tiền.",
            )

        return TransferService._build_transfer_response(transfer)

    @staticmethod
    def create_transfer(
        db: Session,
        current_user: User,
        request: TransferCreateRequest,
    ) -> TransferResponse:
        """
        Tạo giao dịch chuyển tiền và ghi nhận các bút toán kép nguyên tử (Atomic Unit):
        1. Xác minh quyền ghi trên cả hai ví (và sự tương thích ví).
        2. Nếu fee_amount > 0, xác minh danh mục chi phí.
        3. Tạo bản ghi Transfer.
        4. Tạo Transaction 'transfer_out' tại ví nguồn.
        5. Tạo Transaction 'transfer_in' tại ví đích.
        6. Tạo Transaction 'transfer_fee' tại ví nguồn (nếu fee_amount > 0).
        7. Flush và Commit duy nhất một lần. Nếu có lỗi, rollback toàn bộ.
        """
        from_acc, to_acc = TransferService._validate_transfer_accounts(
            db=db,
            from_account_id=request.from_account_id,
            to_account_id=request.to_account_id,
            user=current_user,
        )

        fee_category = None
        if request.fee_amount > Decimal(0):
            if not request.fee_category_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Vui lòng chọn danh mục chi phí khi có phát sinh phí chuyển tiền.",
                )
            fee_category = TransferService._validate_fee_category(
                db=db,
                fee_category_id=request.fee_category_id,
                from_account=from_acc,
                user=current_user,
            )

        occurred_at = request.occurred_at or datetime.now(UTC)

        try:
            # 1. Tạo bản ghi Transfer
            transfer = Transfer(
                id=uuid.uuid4(),
                from_account_id=from_acc.id,
                to_account_id=to_acc.id,
                created_by=current_user.id,
                amount=request.amount,
                fee_amount=request.fee_amount,
                note=request.note,
                occurred_at=occurred_at,
            )
            db.add(transfer)
            # Flush để có ID và thiết lập quan hệ foreign keys
            db.flush()

            # 2. Tạo Transaction transfer_out (tiền ra khỏi ví nguồn)
            tx_out = Transaction(
                id=uuid.uuid4(),
                account_id=from_acc.id,
                category_id=None,
                transfer_id=transfer.id,
                user_id=current_user.id,
                type="transfer_out",
                amount=request.amount,
                note=request.note,
                occurred_at=occurred_at,
            )
            db.add(tx_out)

            # 3. Tạo Transaction transfer_in (tiền vào ví đích)
            tx_in = Transaction(
                id=uuid.uuid4(),
                account_id=to_acc.id,
                category_id=None,
                transfer_id=transfer.id,
                user_id=current_user.id,
                type="transfer_in",
                amount=request.amount,
                note=request.note,
                occurred_at=occurred_at,
            )
            db.add(tx_in)

            # 4. Tạo Transaction transfer_fee (phí chuyển tiền tại ví nguồn) nếu có phí
            if request.fee_amount > Decimal(0) and fee_category:
                tx_fee = Transaction(
                    id=uuid.uuid4(),
                    account_id=from_acc.id,
                    category_id=fee_category.id,
                    transfer_id=transfer.id,
                    user_id=current_user.id,
                    type="transfer_fee",
                    amount=request.fee_amount,
                    note=f"Phí chuyển tiền: {request.note or ''}".strip(),
                    occurred_at=occurred_at,
                )
                db.add(tx_fee)

            # Commit nguyên tử toàn bộ giao dịch
            db.commit()
            db.refresh(transfer)

            return TransferService._build_transfer_response(
                transfer=transfer,
                fee_category_id=request.fee_category_id if request.fee_amount > Decimal(0) else None,
            )

        except Exception as e:
            db.rollback()
            logger.error("Lỗi nguyên tử khi tạo chuyển tiền: %s", e)
            if isinstance(e, HTTPException):
                raise
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể thực hiện chuyển tiền. Toàn bộ thao tác đã được hủy an toàn.",
            ) from e

    @staticmethod
    def void_transfer(
        db: Session,
        transfer_id: uuid.UUID,
        current_user: User,
    ) -> TransferResponse:
        """
        Hủy hiệu lực (void) một giao dịch chuyển tiền:
        - Đặt voided_at = now(UTC).
        - Giữ nguyên các bản ghi Transfer và Transaction (không xóa cứng).
        - Khi tính số dư, AccountService tự động loại trừ các transaction thuộc transfer có voided_at IS NOT NULL.
        - Chỉ chủ sở hữu (ví cá nhân) hoặc owner/editor (ví gia đình) mới có quyền void.
        - Không cho void lại nếu đã void trước đó.
        """
        transfer = db.scalar(
            select(Transfer)
            .options(
                joinedload(Transfer.from_account),
                joinedload(Transfer.to_account),
                joinedload(Transfer.creator),
                joinedload(Transfer.transactions),
            )
            .where(Transfer.id == transfer_id)
        )
        if transfer is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Không tìm thấy giao dịch chuyển tiền.",
            )

        if transfer.is_voided:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Giao dịch chuyển tiền này đã bị hủy trước đó.",
            )

        from_acc = transfer.from_account
        if from_acc is None or from_acc.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ví liên quan không tồn tại hoặc đã bị xóa.",
            )

        # Kiểm tra quyền ghi để void
        if from_acc.scope == "personal":
            if from_acc.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Không tìm thấy giao dịch chuyển tiền.",
                )
        elif from_acc.scope == "family":
            has_write_perm = TransferService._check_family_role(
                db=db, family_id=from_acc.family_id, user=current_user, required_role="editor"
            )
            if not has_write_perm:
                has_view_perm = TransferService._check_family_role(
                    db=db, family_id=from_acc.family_id, user=current_user, required_role="viewer"
                )
                if has_view_perm:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Thành viên với vai trò Viewer không có quyền hủy chuyển tiền.",
                    )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Không tìm thấy giao dịch chuyển tiền.",
                )

        try:
            transfer.voided_at = datetime.now(UTC)
            db.commit()
            db.refresh(transfer)
            return TransferService._build_transfer_response(transfer)
        except Exception as e:
            db.rollback()
            logger.error("Lỗi khi hủy chuyển tiền: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Lỗi hệ thống khi hủy giao dịch chuyển tiền.",
            ) from e
