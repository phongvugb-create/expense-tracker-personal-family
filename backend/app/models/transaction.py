import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.category import Category
    from app.models.recurring_transaction import RecurringTransaction
    from app.models.transfer import Transfer
    from app.models.user import User


class Transaction(Base):
    """Bảng lưu trữ giao dịch thu chi và các bút toán chuyển tiền."""

    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint(
            "amount > 0",
            name="amount_positive",
        ),
        CheckConstraint(
            "type IN ('income', 'expense', 'transfer_in', 'transfer_out', 'transfer_fee')",
            name="type",
        ),
        CheckConstraint(
            """(
                (type IN ('income', 'expense') AND category_id IS NOT NULL AND transfer_id IS NULL) OR
                (type IN ('transfer_in', 'transfer_out') AND transfer_id IS NOT NULL AND category_id IS NULL) OR
                (type = 'transfer_fee' AND transfer_id IS NOT NULL AND category_id IS NOT NULL)
            )""",
            name="type_reference_rules",
        ),
        # Partial unique index: Giới hạn mỗi Transfer chỉ có duy nhất 1 bút toán cho mỗi loại (transfer_out, transfer_in, transfer_fee)
        Index(
            "uq_transactions_transfer_type",
            "transfer_id",
            "type",
            unique=True,
            postgresql_where=text("transfer_id IS NOT NULL"),
        ),
        # Partial unique index: Chống phát sinh trùng kỳ định kỳ kể cả khi giao dịch đã bị xóa mềm
        Index(
            "uq_transactions_recurring_rule_date",
            "recurring_rule_id",
            "recurrence_date",
            unique=True,
            postgresql_where=text("recurring_rule_id IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    transfer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transfers.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    recurring_rule_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recurring_transactions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    recurrence_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
    )

    note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    # Relationships
    account: Mapped["Account"] = relationship(
        "Account",
        foreign_keys=[account_id],
        back_populates="transactions",
    )

    category: Mapped["Category | None"] = relationship(
        "Category",
        foreign_keys=[category_id],
        back_populates="transactions",
    )

    transfer: Mapped["Transfer | None"] = relationship(
        "Transfer",
        foreign_keys=[transfer_id],
        back_populates="transactions",
    )

    creator: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="transactions",
    )

    recurring_rule: Mapped["RecurringTransaction | None"] = relationship(
        "RecurringTransaction",
        foreign_keys=[recurring_rule_id],
        back_populates="transactions",
    )

    @property
    def is_deleted(self) -> bool:
        """Kiểm tra giao dịch đã bị xóa mềm hay chưa."""
        return self.deleted_at is not None

    def __repr__(self) -> str:
        """Hiển thị đối tượng an toàn."""
        return (
            f"<Transaction id={self.id} account_id={self.account_id} type={self.type!r} "
            f"amount={self.amount} deleted={self.is_deleted}>"
        )
