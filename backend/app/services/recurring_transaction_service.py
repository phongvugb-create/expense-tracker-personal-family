import calendar
import logging
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Literal

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.account import Account
from app.models.category import Category
from app.models.family import Family
from app.models.family_member import FamilyMember
from app.models.notification import Notification
from app.models.recurring_transaction import RecurringTransaction
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.recurring_transaction import (
    RecurringTransactionCreateRequest,
    RecurringTransactionGenerateResponse,
    RecurringTransactionResponse,
    RecurringTransactionUpdateRequest,
)

logger = logging.getLogger(__name__)


class RecurringTransactionService:
    """Service xử lý nghiệp vụ cho quy tắc thu/chi định kỳ."""

    @staticmethod
    def calculate_next_due_date(
        current_due: date,
        frequency: str,
        interval_value: int,
        start_date: date | None = None,
    ) -> date:
        """
        Tính ngày đến hạn tiếp theo, xử lý chính xác ngày cuối tháng (VD: 31/01 -> 28/02 -> 31/03).
        Nếu truyền start_date, lấy ngày gốc (anchor_day = start_date.day) để không bị trôi ngày.
        """
        anchor_day = start_date.day if start_date else current_due.day

        if frequency == "daily":
            return current_due + timedelta(days=interval_value)
        elif frequency == "weekly":
            return current_due + timedelta(weeks=interval_value)
        elif frequency == "monthly":
            # Chuyển tháng
            total_months = current_due.year * 12 + (current_due.month - 1) + interval_value
            new_year = total_months // 12
            new_month = (total_months % 12) + 1
            max_days = calendar.monthrange(new_year, new_month)[1]
            new_day = min(anchor_day, max_days)
            return date(new_year, new_month, new_day)
        elif frequency == "yearly":
            new_year = current_due.year + interval_value
            new_month = current_due.month
            max_days = calendar.monthrange(new_year, new_month)[1]
            new_day = min(anchor_day, max_days)
            return date(new_year, new_month, new_day)
        else:
            raise ValueError(f"Tần suất không hỗ trợ: {frequency}")

    @staticmethod
    def _check_family_role(
        db: Session, family_id: uuid.UUID, user: User, required_role: str = "viewer"
    ) -> bool:
        """Kiểm tra quyền của user trong nhóm gia đình."""
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
        db: Session, account_id: uuid.UUID, user: User, required_role: str = "editor"
    ) -> Account:
        """Xác minh quyền truy cập ví."""
        account = db.get(Account, account_id)
        if account is None or account.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ví tài khoản không tồn tại hoặc đã bị xóa.",
            )

        if account.scope == "personal":
            if account.user_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Ví tài khoản không tồn tại hoặc bạn không có quyền truy cập.",
                )
        elif account.scope == "family":
            if account.family_id is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Ví tài khoản không hợp lệ.",
                )
            has_role = RecurringTransactionService._check_family_role(
                db=db, family_id=account.family_id, user=user, required_role=required_role
            )
            if not has_role:
                # Nếu là viewer muốn thao tác editor -> 403 Forbidden
                if required_role == "editor" and RecurringTransactionService._check_family_role(
                    db=db, family_id=account.family_id, user=user, required_role="viewer"
                ):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Bạn chỉ có quyền xem (viewer), không thể thao tác trên ví gia đình này.",
                    )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Ví tài khoản không tồn tại hoặc bạn không có quyền truy cập.",
                )

        return account

    @staticmethod
    def _validate_category(
        db: Session, category_id: uuid.UUID, expected_type: str, scope: str, family_id: uuid.UUID | None, user: User
    ) -> Category:
        """Kiểm tra tính tương thích của danh mục với type và scope."""
        category = db.get(Category, category_id)
        if category is None or category.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Danh mục không tồn tại hoặc đã bị xóa.",
            )

        if category.type != expected_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Danh mục '{category.name}' không phù hợp với loại giao dịch '{expected_type}'.",
            )

        if category.scope == "personal":
            if category.user_id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Danh mục không tồn tại hoặc bạn không có quyền truy cập.",
                )
        elif category.scope == "family":
            if family_id is None or category.family_id != family_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Danh mục gia đình không khớp với nhóm gia đình của quy tắc này.",
                )
            if not RecurringTransactionService._check_family_role(db, family_id, user, "viewer"):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Danh mục không tồn tại hoặc bạn không có quyền truy cập.",
                )

        return category

    @classmethod
    def create(
        cls, db: Session, user: User, payload: RecurringTransactionCreateRequest
    ) -> RecurringTransactionResponse:
        """Tạo quy tắc thu chi định kỳ mới."""
        account = cls._validate_account_access(db, payload.account_id, user, required_role="editor")

        # Ràng buộc scope giữa ví và quy tắc
        if payload.scope != account.scope:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Phạm vi quy tắc ({payload.scope}) không khớp với phạm vi ví ({account.scope}).",
            )

        if payload.scope == "family" and (payload.family_id is None or payload.family_id != account.family_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nhóm gia đình không khớp với ví gia đình đã chọn.",
            )

        category = cls._validate_category(
            db, payload.category_id, payload.type, payload.scope, payload.family_id, user
        )

        # Ngày đến hạn ban đầu chính là start_date
        next_due = payload.start_date

        rule = RecurringTransaction(
            id=uuid.uuid4(),
            name=payload.name,
            type=payload.type,
            scope=payload.scope,
            user_id=user.id if payload.scope == "personal" else None,
            family_id=payload.family_id if payload.scope == "family" else None,
            created_by=user.id,
            account_id=account.id,
            category_id=category.id,
            amount=payload.amount,
            start_date=payload.start_date,
            next_due_date=next_due,
            frequency=payload.frequency,
            interval_value=payload.interval_value,
            end_date=payload.end_date,
            note=payload.note,
            is_active=True,
            is_archived=False,
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)

        return cls._to_response(rule)

    @classmethod
    def get_list(
        cls,
        db: Session,
        user: User,
        scope: Literal["all", "personal", "family"] = "all",
        family_id: uuid.UUID | None = None,
        type_: Literal["income", "expense"] | None = None,
        is_active: bool | None = None,
        include_archived: bool = False,
        due_before: date | None = None,
    ) -> list[RecurringTransactionResponse]:
        """Lấy danh sách các quy tắc định kỳ theo quyền truy cập."""
        stmt = (
            select(RecurringTransaction)
            .options(
                joinedload(RecurringTransaction.account),
                joinedload(RecurringTransaction.category),
            )
            .where(RecurringTransaction.deleted_at.is_(None))
        )

        if not include_archived:
            stmt = stmt.where(RecurringTransaction.is_archived.is_(False))

        # Phân quyền: Lấy danh sách family_id mà user có quyền xem
        fam_stmt = (
            select(Family.id)
            .where(Family.owner_user_id == user.id, Family.deleted_at.is_(None))
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
        accessible_fam_ids = set(db.scalars(fam_stmt).all())

        if scope == "personal":
            stmt = stmt.where(
                RecurringTransaction.scope == "personal",
                RecurringTransaction.user_id == user.id,
            )
        elif scope == "family":
            if family_id:
                if family_id not in accessible_fam_ids:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Bạn không có quyền truy cập nhóm gia đình này.",
                    )
                stmt = stmt.where(
                    RecurringTransaction.scope == "family",
                    RecurringTransaction.family_id == family_id,
                )
            else:
                if not accessible_fam_ids:
                    return []
                stmt = stmt.where(
                    RecurringTransaction.scope == "family",
                    RecurringTransaction.family_id.in_(accessible_fam_ids),
                )
        else:  # scope == "all"
            if family_id:
                if family_id not in accessible_fam_ids:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Bạn không có quyền truy cập nhóm gia đình này.",
                    )
                stmt = stmt.where(
                    or_(
                        (RecurringTransaction.scope == "personal") & (RecurringTransaction.user_id == user.id),
                        (RecurringTransaction.scope == "family") & (RecurringTransaction.family_id == family_id),
                    )
                )
            else:
                conditions = [
                    (RecurringTransaction.scope == "personal") & (RecurringTransaction.user_id == user.id)
                ]
                if accessible_fam_ids:
                    conditions.append(
                        (RecurringTransaction.scope == "family") & (RecurringTransaction.family_id.in_(accessible_fam_ids))
                    )
                stmt = stmt.where(or_(*conditions))

        if type_:
            stmt = stmt.where(RecurringTransaction.type == type_)
        if is_active is not None:
            stmt = stmt.where(RecurringTransaction.is_active.is_(is_active))
        if due_before:
            stmt = stmt.where(RecurringTransaction.next_due_date <= due_before)

        stmt = stmt.order_by(RecurringTransaction.next_due_date.asc(), RecurringTransaction.created_at.desc())
        rules = list(db.scalars(stmt).all())

        return [cls._to_response(r) for r in rules]

    @classmethod
    def get_by_id(cls, db: Session, user: User, rule_id: uuid.UUID) -> RecurringTransactionResponse:
        """Lấy thông tin chi tiết một quy tắc định kỳ."""
        rule = db.scalar(
            select(RecurringTransaction)
            .options(
                joinedload(RecurringTransaction.account),
                joinedload(RecurringTransaction.category),
            )
            .where(RecurringTransaction.id == rule_id, RecurringTransaction.deleted_at.is_(None))
        )
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quy tắc định kỳ không tồn tại hoặc đã bị xóa.",
            )

        # Kiểm tra quyền đọc
        cls._validate_account_access(db, rule.account_id, user, required_role="viewer")
        return cls._to_response(rule)

    @classmethod
    def update(
        cls, db: Session, user: User, rule_id: uuid.UUID, payload: RecurringTransactionUpdateRequest
    ) -> RecurringTransactionResponse:
        """Cập nhật cấu hình quy tắc định kỳ (yêu cầu quyền editor)."""
        rule = db.get(RecurringTransaction, rule_id)
        if not rule or rule.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quy tắc định kỳ không tồn tại hoặc đã bị xóa.",
            )

        cls._validate_account_access(db, rule.account_id, user, required_role="editor")

        if payload.name is not None:
            rule.name = payload.name
        if payload.amount is not None:
            rule.amount = payload.amount
        if payload.category_id is not None:
            category = cls._validate_category(
                db, payload.category_id, rule.type, rule.scope, rule.family_id, user
            )
            rule.category_id = category.id
        if payload.frequency is not None:
            rule.frequency = payload.frequency
        if payload.interval_value is not None:
            rule.interval_value = payload.interval_value
        if payload.end_date is not None:
            if payload.end_date < rule.start_date:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Ngày kết thúc không được trước ngày bắt đầu.",
                )
            rule.end_date = payload.end_date
        if payload.note is not None:
            rule.note = payload.note

        db.commit()
        db.refresh(rule)
        return cls._to_response(rule)

    @classmethod
    def pause(cls, db: Session, user: User, rule_id: uuid.UUID) -> RecurringTransactionResponse:
        """Tạm dừng quy tắc định kỳ."""
        rule = db.get(RecurringTransaction, rule_id)
        if not rule or rule.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quy tắc định kỳ không tồn tại.",
            )
        cls._validate_account_access(db, rule.account_id, user, required_role="editor")
        rule.is_active = False
        db.commit()
        db.refresh(rule)
        return cls._to_response(rule)

    @classmethod
    def resume(cls, db: Session, user: User, rule_id: uuid.UUID) -> RecurringTransactionResponse:
        """Kích hoạt lại quy tắc định kỳ."""
        rule = db.get(RecurringTransaction, rule_id)
        if not rule or rule.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quy tắc định kỳ không tồn tại.",
            )
        cls._validate_account_access(db, rule.account_id, user, required_role="editor")
        rule.is_active = True
        db.commit()
        db.refresh(rule)
        return cls._to_response(rule)

    @classmethod
    def archive(cls, db: Session, user: User, rule_id: uuid.UUID) -> RecurringTransactionResponse:
        """Lưu trữ quy tắc định kỳ."""
        rule = db.get(RecurringTransaction, rule_id)
        if not rule or rule.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quy tắc định kỳ không tồn tại.",
            )
        cls._validate_account_access(db, rule.account_id, user, required_role="editor")
        rule.is_archived = True
        rule.is_active = False
        db.commit()
        db.refresh(rule)
        return cls._to_response(rule)

    @classmethod
    def generate_transaction(
        cls, db: Session, user: User, rule_id: uuid.UUID
    ) -> RecurringTransactionGenerateResponse:
        """
        Tạo một giao dịch thực tế từ kỳ đến hạn hiện tại của quy tắc:
        1. Kiểm tra trạng thái hoạt động (is_active=True, is_archived=False).
        2. Kiểm tra ngày đến hạn: next_due_date <= ngày hôm nay (không cho phép tạo trước kỳ).
        3. Kiểm tra ngày kết thúc end_date: không cho phép tạo nếu next_due_date > end_date.
        4. Kiểm tra chống tạo trùng (idempotency): truy vấn Transaction đã có (recurring_rule_id, recurrence_date) chưa.
        5. Tạo Transaction thực tế, liên kết recurring_rule_id & recurrence_date.
        6. Cập nhật next_due_date sang kỳ tiếp theo trong cùng 1 DB transaction.
        """
        # Khóa dòng quy tắc bằng SELECT ... FOR UPDATE để chống race conditions
        stmt = (
            select(RecurringTransaction)
            .where(
                RecurringTransaction.id == rule_id,
                RecurringTransaction.deleted_at.is_(None),
            )
            .with_for_update()
        )
        rule = db.scalar(stmt)
        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quy tắc định kỳ không tồn tại hoặc đã bị xóa.",
            )

        # Quyền editor trên ví
        account = cls._validate_account_access(db, rule.account_id, user, required_role="editor")

        if rule.is_archived:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Không thể tạo giao dịch từ quy tắc đã được lưu trữ.",
            )

        if not rule.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quy tắc đang bị tạm dừng. Hãy kích hoạt lại trước khi tạo giao dịch.",
            )

        today = date.today()
        due_date = rule.next_due_date

        # Không tạo trước kỳ đến hạn
        if due_date > today:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Kỳ giao dịch tiếp theo là {due_date.isoformat()}, chưa đến hạn tạo.",
            )

        # Kiểm tra end_date
        if rule.end_date and due_date > rule.end_date:
            rule.is_active = False
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quy tắc đã đến ngày kết thúc và không còn kỳ phát sinh nào mới.",
            )

        # Chống tạo trùng kỳ (kể cả giao dịch đã bị xóa mềm)
        existing_tx = db.scalar(
            select(Transaction).where(
                Transaction.recurring_rule_id == rule.id,
                Transaction.recurrence_date == due_date,
            )
        )
        if existing_tx:
            # Nếu giao dịch đã tồn tại (dù active hay soft-deleted), bảo đảm next_due_date được cập nhật
            next_due = cls.calculate_next_due_date(
                due_date, rule.frequency, rule.interval_value, rule.start_date
            )
            rule.next_due_date = next_due
            if rule.end_date and next_due > rule.end_date:
                rule.is_active = False

            # Đảm bảo thông báo của kỳ này được lưu trữ
            now_utc = datetime.now(UTC)
            source_key = f"recurring:{rule.id}:{due_date.isoformat()}"
            notifs_to_archive = db.scalars(
                select(Notification).where(
                    Notification.source_key == source_key,
                    Notification.archived_at.is_(None),
                )
            ).all()
            for n in notifs_to_archive:
                n.archived_at = now_utc
                if n.read_at is None:
                    n.read_at = now_utc

            db.commit()

            status_msg = "đã được xóa mềm trước đó" if existing_tx.deleted_at else "đã được ghi nhận trước đó"
            return RecurringTransactionGenerateResponse(
                message=f"Kỳ giao dịch này {status_msg}. Không tạo trùng lặp.",
                transaction_id=existing_tx.id,
                recurrence_date=due_date,
                next_due_date=rule.next_due_date if rule.is_active else None,
                rule=cls._to_response(rule),
            )

        # Tạo Transaction thực tế
        tx_note = rule.note or f"Giao dịch định kỳ: {rule.name}"
        occurred_dt = datetime.combine(due_date, datetime.min.time(), tzinfo=UTC)

        new_tx = Transaction(
            id=uuid.uuid4(),
            account_id=account.id,
            category_id=rule.category_id,
            user_id=user.id,
            type=rule.type,
            amount=rule.amount,
            note=tx_note,
            occurred_at=occurred_dt,
            recurring_rule_id=rule.id,
            recurrence_date=due_date,
        )
        db.add(new_tx)

        # Tính kỳ tiếp theo
        next_due = cls.calculate_next_due_date(
            due_date, rule.frequency, rule.interval_value, rule.start_date
        )
        rule.next_due_date = next_due

        # Kiểm tra nếu kỳ tiếp theo vượt quá end_date -> tự động hoàn tất (deactivate)
        if rule.end_date and next_due > rule.end_date:
            rule.is_active = False

        # Tự động lưu trữ thông báo nhắc nhở tương ứng với kỳ đã phát sinh
        now_utc = datetime.now(UTC)
        source_key = f"recurring:{rule.id}:{due_date.isoformat()}"
        notifs_to_archive = db.scalars(
            select(Notification).where(
                Notification.source_key == source_key,
                Notification.archived_at.is_(None),
            )
        ).all()
        for n in notifs_to_archive:
            n.archived_at = now_utc
            if n.read_at is None:
                n.read_at = now_utc

        try:
            db.commit()
            db.refresh(rule)
            db.refresh(new_tx)
        except IntegrityError:
            db.rollback()
            # Bắt trường hợp race condition vi phạm unique constraint
            # Nạp lại bản ghi giao dịch đã được commit bởi request cạnh tranh
            race_tx = db.scalar(
                select(Transaction).where(
                    Transaction.recurring_rule_id == rule_id,
                    Transaction.recurrence_date == due_date,
                )
            )
            updated_rule = db.get(RecurringTransaction, rule_id)
            if race_tx and updated_rule:
                now_race = datetime.now(UTC)
                race_key = f"recurring:{rule_id}:{due_date.isoformat()}"
                race_notifs = db.scalars(
                    select(Notification).where(
                        Notification.source_key == race_key,
                        Notification.archived_at.is_(None),
                    )
                ).all()
                for rn in race_notifs:
                    rn.archived_at = now_race
                    if rn.read_at is None:
                        rn.read_at = now_race
                db.commit()

                return RecurringTransactionGenerateResponse(
                    message="Kỳ giao dịch này đã được ghi nhận bởi một thao tác song song.",
                    transaction_id=race_tx.id,
                    recurrence_date=due_date,
                    next_due_date=updated_rule.next_due_date if updated_rule.is_active else None,
                    rule=cls._to_response(updated_rule),
                )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Xung đột dữ liệu khi phát sinh giao dịch định kỳ. Vui lòng thử lại.",
            )

        return RecurringTransactionGenerateResponse(
            message=f"Đã tạo thành công giao dịch cho kỳ ngày {due_date.isoformat()}.",
            transaction_id=new_tx.id,
            recurrence_date=due_date,
            next_due_date=rule.next_due_date if rule.is_active else None,
            rule=cls._to_response(rule),
        )

    @classmethod
    def _to_response(cls, rule: RecurringTransaction) -> RecurringTransactionResponse:
        """Chuyển đổi ORM entity sang schema response."""
        today = date.today()
        is_completed = bool(rule.end_date and rule.next_due_date > rule.end_date)
        is_due = bool(rule.is_active and not rule.is_archived and rule.next_due_date <= today and not is_completed)

        return RecurringTransactionResponse(
            id=rule.id,
            name=rule.name,
            type=rule.type,  # type: ignore[arg-type]
            scope=rule.scope,  # type: ignore[arg-type]
            user_id=rule.user_id,
            family_id=rule.family_id,
            created_by=rule.created_by,
            account_id=rule.account_id,
            account_name=rule.account.name if rule.account else "N/A",
            currency=rule.account.currency.upper() if rule.account else "VND",
            category_id=rule.category_id,
            category_name=rule.category.name if rule.category else "N/A",
            category_icon=rule.category.icon if rule.category else None,
            category_color=rule.category.color if rule.category else None,
            amount=rule.amount,
            start_date=rule.start_date,
            next_due_date=rule.next_due_date,
            frequency=rule.frequency,  # type: ignore[arg-type]
            interval_value=rule.interval_value,
            end_date=rule.end_date,
            note=rule.note,
            is_active=rule.is_active,
            is_archived=rule.is_archived,
            is_completed=is_completed,
            is_due=is_due,
            created_at=rule.created_at,
            updated_at=rule.updated_at,
        )
