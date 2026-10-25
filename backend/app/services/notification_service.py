import logging
import uuid
from datetime import UTC, date, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.family import Family
from app.models.family_member import FamilyMember
from app.models.notification import Notification
from app.models.recurring_transaction import RecurringTransaction
from app.models.transaction import Transaction
from app.models.user import User
from app.schemas.notification import (
    NotificationResponse,
    NotificationSyncResponse,
)
from app.services.budget_service import BudgetService

logger = logging.getLogger(__name__)


class NotificationService:
    """Service xử lý nghiệp vụ thông báo, nhắc nhở tài chính và đồng bộ idempotent."""

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

    @classmethod
    def sync_notifications(cls, db: Session, user: User) -> NotificationSyncResponse:
        """
        Đồng bộ thông báo tài chính cho người dùng hiện tại theo cơ chế Idempotent:
        1. Quét các quy tắc định kỳ (Recurring Transactions) còn hiệu lực trong phạm vi truy cập:
           - recurring_overdue: next_due_date < today
           - recurring_due_today: next_due_date == today
           - recurring_due_soon: today < next_due_date <= today + 7 days
        2. Quét các ngân sách (Budgets) còn hiệu lực trong phạm vi truy cập:
           - budget_exceeded: chi tiêu vượt 100% hạn mức
           - budget_warning: chi tiêu đạt hoặc vượt ngưỡng cảnh báo (thường là 80%) nhưng chưa quá 100%
        3. Tạo mới hoặc cập nhật thông báo dựa trên unique constraint (user_id, source_key).
        """
        today = date.today()
        created_count = 0
        updated_count = 0

        accessible_family_ids = cls._get_accessible_family_ids(db, user)
        now_sync = datetime.now(UTC)

        # ---------------------------------------------------------
        # 0. Quét dọn dẹp các thông báo định kỳ cũ đã hoàn thành kỳ
        # hoặc quy tắc đã bị lưu trữ/xóa mềm
        # ---------------------------------------------------------
        active_user_recur_notifs = db.scalars(
            select(Notification).where(
                Notification.user_id == user.id,
                Notification.entity_type == "recurring_transaction",
                Notification.archived_at.is_(None),
            )
        ).all()
        for notif in active_user_recur_notifs:
            r_id = notif.entity_id
            d_str = None
            if notif.notification_metadata and "due_date" in notif.notification_metadata:
                d_str = notif.notification_metadata["due_date"]
            elif notif.source_key and notif.source_key.startswith("recurring:"):
                parts = notif.source_key.split(":")
                if len(parts) >= 3:
                    d_str = parts[2]

            should_archive = False
            if r_id and d_str:
                try:
                    d_parsed = date.fromisoformat(d_str)
                    has_generated_tx = db.scalar(
                        select(func.count(Transaction.id)).where(
                            Transaction.recurring_rule_id == r_id,
                            Transaction.recurrence_date == d_parsed,
                        )
                    )
                    if has_generated_tx and has_generated_tx > 0:
                        should_archive = True
                except (ValueError, TypeError):
                    pass

            if not should_archive and r_id:
                rule_ent = db.get(RecurringTransaction, r_id)
                if rule_ent is None or rule_ent.deleted_at is not None or rule_ent.is_archived:
                    should_archive = True

            if should_archive:
                notif.archived_at = now_sync
                if notif.read_at is None:
                    notif.read_at = now_sync

        # ---------------------------------------------------------
        # 1. Quét các khoản giao dịch định kỳ (Recurring Transactions)
        # ---------------------------------------------------------
        recur_stmt = select(RecurringTransaction).where(
            RecurringTransaction.deleted_at.is_(None),
            RecurringTransaction.is_active.is_(True),
            RecurringTransaction.is_archived.is_(False),
        )
        # Lọc phạm vi người dùng có quyền xem
        if accessible_family_ids:
            recur_stmt = recur_stmt.where(
                (RecurringTransaction.scope == "personal") & (RecurringTransaction.user_id == user.id)
                | (RecurringTransaction.scope == "family") & (RecurringTransaction.family_id.in_(accessible_family_ids))
            )
        else:
            recur_stmt = recur_stmt.where(
                (RecurringTransaction.scope == "personal") & (RecurringTransaction.user_id == user.id)
            )

        active_rules = db.scalars(recur_stmt).all()

        for rule in active_rules:
            # Kiểm tra xem quy tắc đã hoàn tất do vượt end_date chưa
            if rule.end_date and rule.next_due_date > rule.end_date:
                continue

            due_date = rule.next_due_date

            # Kiểm tra xem kỳ này đã được phát sinh giao dịch thật chưa (kể cả đã xóa mềm theo chính sách chống trùng)
            has_tx = db.scalar(
                select(func.count(Transaction.id)).where(
                    Transaction.recurring_rule_id == rule.id,
                    Transaction.recurrence_date == due_date,
                )
            )
            if has_tx and has_tx > 0:
                # Kỳ này đã được phát sinh thành giao dịch -> không nhắc nữa, tự động lưu trữ thông báo nếu còn active
                source_key = f"recurring:{rule.id}:{due_date.isoformat()}"
                active_curr_notif = db.scalar(
                    select(Notification).where(
                        Notification.user_id == user.id,
                        Notification.source_key == source_key,
                        Notification.archived_at.is_(None),
                    )
                )
                if active_curr_notif:
                    active_curr_notif.archived_at = now_sync
                    if active_curr_notif.read_at is None:
                        active_curr_notif.read_at = now_sync
                continue

            # Phân loại thời hạn
            diff_days = (due_date - today).days

            notif_type = None
            title = ""
            message = ""

            account_name = rule.account.name if rule.account else "Ví"
            currency = rule.account.currency if rule.account else "VND"
            amount_str = f"{rule.amount:,.0f} {currency}"

            if diff_days < 0:
                notif_type = "recurring_overdue"
                days_over = abs(diff_days)
                title = f"Khoản định kỳ quá hạn: {rule.name}"
                message = (
                    f"Khoản {rule.type} '{rule.name}' ({amount_str}) trên {account_name} "
                    f"đã quá hạn {days_over} ngày (hạn: {due_date.strftime('%d/%m/%Y')}). "
                    f"Vui lòng kiểm tra và tạo giao dịch khi phù hợp."
                )
            elif diff_days == 0:
                notif_type = "recurring_due_today"
                title = f"Khoản định kỳ đến hạn hôm nay: {rule.name}"
                message = (
                    f"Khoản {rule.type} '{rule.name}' ({amount_str}) trên {account_name} "
                    f"đến hạn hôm nay ({due_date.strftime('%d/%m/%Y')}). Hãy tạo giao dịch vào sổ."
                )
            elif 0 < diff_days <= 7:
                notif_type = "recurring_due_soon"
                title = f"Khoản định kỳ sắp đến hạn: {rule.name}"
                message = (
                    f"Khoản {rule.type} '{rule.name}' ({amount_str}) trên {account_name} "
                    f"sẽ đến hạn vào ngày {due_date.strftime('%d/%m/%Y')} (còn {diff_days} ngày)."
                )

            if notif_type:
                # Khóa nhận diện nghiệp vụ: định danh rule + ngày đến hạn của kỳ
                source_key = f"recurring:{rule.id}:{due_date.isoformat()}"
                metadata = {
                    "rule_id": str(rule.id),
                    "due_date": due_date.isoformat(),
                    "amount": str(rule.amount),
                    "currency": currency,
                    "scope": rule.scope,
                    "family_id": str(rule.family_id) if rule.family_id else None,
                }

                created, updated = cls._upsert_notification(
                    db=db,
                    user_id=user.id,
                    source_key=source_key,
                    notif_type=notif_type,
                    title=title,
                    message=message,
                    entity_type="recurring_transaction",
                    entity_id=rule.id,
                    action_url="/recurring-transactions",
                    metadata=metadata,
                )
                if created:
                    created_count += 1
                elif updated:
                    updated_count += 1

        # ---------------------------------------------------------
        # 2. Quét các ngân sách (Budgets)
        # ---------------------------------------------------------
        budgets_resp = BudgetService.get_budgets(
            db=db,
            current_user=user,
            include_archived=False,
            active_on=today,
            limit=200,
            offset=0,
        )

        for b in budgets_resp:
            if b.status in ("warning", "exceeded"):
                notif_type = "budget_exceeded" if b.status == "exceeded" else "budget_warning"
                # Khóa nhận diện ngân sách: id + kỳ bắt đầu + kỳ kết thúc
                source_key = f"budget:{b.id}:{b.period_start.isoformat()}:{b.period_end.isoformat()}"

                pct = f"{b.usage_percentage:.1f}%"
                limit_str = f"{b.amount_limit:,.0f}"
                spent_str = f"{b.spent_amount:,.0f}"

                if b.status == "exceeded":
                    title = f"Ngân sách vượt hạn mức: {b.name}"
                    message = (
                        f"Ngân sách '{b.name}' đã chi {spent_str} / {limit_str} ({pct}), "
                        f"vượt hạn mức {b.overspent_amount:,.0f}. Vui lòng kiểm soát chi tiêu!"
                    )
                else:
                    title = f"Cảnh báo ngân sách sắp chạm ngưỡng: {b.name}"
                    message = (
                        f"Ngân sách '{b.name}' đã chi {spent_str} / {limit_str} ({pct}), "
                        f"đạt ngưỡng cảnh báo {b.warning_threshold}%. Còn lại: {b.remaining_amount:,.0f}."
                    )

                metadata = {
                    "budget_id": str(b.id),
                    "status": b.status,
                    "usage_percentage": str(b.usage_percentage),
                    "amount_limit": str(b.amount_limit),
                    "spent_amount": str(b.spent_amount),
                    "period_start": b.period_start.isoformat(),
                    "period_end": b.period_end.isoformat(),
                }

                created, updated = cls._upsert_notification(
                    db=db,
                    user_id=user.id,
                    source_key=source_key,
                    notif_type=notif_type,
                    title=title,
                    message=message,
                    entity_type="budget",
                    entity_id=b.id,
                    action_url="/budgets",
                    metadata=metadata,
                    reset_read_on_upgrade=(b.status == "exceeded"),
                )
                if created:
                    created_count += 1
                elif updated:
                    updated_count += 1

        db.commit()

        unread = cls.get_unread_count(db, user)

        return NotificationSyncResponse(
            created_count=created_count,
            updated_count=updated_count,
            unread_count=unread,
            message="Đồng bộ thông báo hoàn tất.",
        )

    @classmethod
    def _upsert_notification(
        cls,
        db: Session,
        user_id: uuid.UUID,
        source_key: str,
        notif_type: str,
        title: str,
        message: str,
        entity_type: str | None,
        entity_id: uuid.UUID | None,
        action_url: str | None,
        metadata: dict[str, Any] | None,
        reset_read_on_upgrade: bool = False,
    ) -> tuple[bool, bool]:
        """Tạo mới hoặc cập nhật thông báo an toàn, trả về (is_created, is_updated)."""
        existing = db.scalar(
            select(Notification).where(
                Notification.user_id == user_id,
                Notification.source_key == source_key,
            )
        )
        if not existing:
            new_notif = Notification(
                id=uuid.uuid4(),
                user_id=user_id,
                source_key=source_key,
                type=notif_type,
                title=title,
                message=message,
                entity_type=entity_type,
                entity_id=entity_id,
                action_url=action_url,
                notification_metadata=metadata,
                read_at=None,
                archived_at=None,
            )
            db.add(new_notif)
            return True, False

        # Đã tồn tại nhưng đã bị lưu trữ -> giữ nguyên trạng thái lưu trữ, không tái kích hoạt
        if existing.archived_at is not None:
            return False, False

        # Đã tồn tại: kiểm tra có thay đổi type hoặc nội dung không
        is_changed = False
        if existing.type != notif_type:
            # Ví dụ: từ warning sang exceeded, hoặc từ due_soon sang overdue
            existing.type = notif_type
            is_changed = True
            if reset_read_on_upgrade:
                existing.read_at = None

        if existing.title != title:
            existing.title = title
            is_changed = True

        if existing.message != message:
            existing.message = message
            is_changed = True

        if metadata and existing.notification_metadata != metadata:
            existing.notification_metadata = metadata
            is_changed = True

        if is_changed:
            existing.updated_at = datetime.now(UTC)

        return False, is_changed

    @classmethod
    def get_notifications(
        cls,
        db: Session,
        user: User,
        unread_only: bool = False,
        include_archived: bool = False,
        type_: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[NotificationResponse]:
        """Lấy danh sách thông báo của người dùng với các bộ lọc và phân trang."""
        stmt = select(Notification).where(Notification.user_id == user.id)

        if not include_archived:
            stmt = stmt.where(Notification.archived_at.is_(None))

        if unread_only:
            stmt = stmt.where(Notification.read_at.is_(None))

        if type_:
            stmt = stmt.where(Notification.type == type_)

        # Sắp xếp: Ưu tiên thông báo chưa đọc lên đầu, sau đó theo created_at giảm dần
        stmt = stmt.order_by(
            Notification.read_at.is_(None).desc(),
            Notification.created_at.desc(),
        ).limit(limit).offset(offset)

        notifications = db.scalars(stmt).all()
        return [cls._to_response(n) for n in notifications]

    @classmethod
    def get_unread_count(cls, db: Session, user: User) -> int:
        """Đếm số lượng thông báo chưa đọc và chưa lưu trữ của người dùng."""
        stmt = select(func.count(Notification.id)).where(
            Notification.user_id == user.id,
            Notification.read_at.is_(None),
            Notification.archived_at.is_(None),
        )
        return int(db.scalar(stmt) or 0)

    @classmethod
    def mark_as_read(cls, db: Session, user: User, notification_id: uuid.UUID) -> NotificationResponse:
        """Đánh dấu một thông báo là đã đọc (idempotent)."""
        notif = db.get(Notification, notification_id)
        if not notif or notif.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thông báo không tồn tại hoặc bạn không có quyền truy cập.",
            )

        if notif.read_at is None:
            notif.read_at = datetime.now(UTC)
            db.commit()
            db.refresh(notif)

        return cls._to_response(notif)

    @classmethod
    def mark_all_as_read(cls, db: Session, user: User) -> int:
        """Đánh dấu tất cả thông báo chưa đọc của user là đã đọc."""
        now = datetime.now(UTC)
        unread_notifs = db.scalars(
            select(Notification).where(
                Notification.user_id == user.id,
                Notification.read_at.is_(None),
                Notification.archived_at.is_(None),
            )
        ).all()

        count = len(unread_notifs)
        for n in unread_notifs:
            n.read_at = now

        db.commit()
        return count

    @classmethod
    def archive_notification(cls, db: Session, user: User, notification_id: uuid.UUID) -> NotificationResponse:
        """Lưu trữ thông báo (idempotent)."""
        notif = db.get(Notification, notification_id)
        if not notif or notif.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thông báo không tồn tại hoặc bạn không có quyền truy cập.",
            )

        if notif.archived_at is None:
            notif.archived_at = datetime.now(UTC)
            db.commit()
            db.refresh(notif)

        return cls._to_response(notif)

    @classmethod
    def _to_response(cls, notif: Notification) -> NotificationResponse:
        """Chuyển entity ORM sang schema response an toàn."""
        # Whitelist action_url nội bộ
        safe_action_url = notif.action_url
        if safe_action_url and not safe_action_url.startswith(("/", "#")):
            safe_action_url = None

        return NotificationResponse(
            id=notif.id,
            user_id=notif.user_id,
            type=notif.type,  # type: ignore[arg-type]
            title=notif.title,
            message=notif.message,
            source_key=notif.source_key,
            entity_type=notif.entity_type,
            entity_id=notif.entity_id,
            action_url=safe_action_url,
            metadata=notif.notification_metadata,
            read_at=notif.read_at,
            archived_at=notif.archived_at,
            created_at=notif.created_at,
            updated_at=notif.updated_at,
        )
