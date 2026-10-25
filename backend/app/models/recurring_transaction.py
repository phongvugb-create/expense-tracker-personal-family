import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
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
    from app.models.family import Family
    from app.models.transaction import Transaction
    from app.models.user import User


class RecurringTransaction(Base):
    """Bảng lưu trữ quy tắc giao dịch định kỳ (thu / chi tự động lên lịch)."""

    __tablename__ = "recurring_transactions"
    __table_args__ = (
        CheckConstraint(
            "type IN ('income', 'expense')",
            name="recurring_type",
        ),
        CheckConstraint(
            "amount > 0",
            name="recurring_amount_positive",
        ),
        CheckConstraint(
            "frequency IN ('daily', 'weekly', 'monthly', 'yearly')",
            name="recurring_frequency",
        ),
        CheckConstraint(
            "interval_value >= 1",
            name="recurring_interval_value_min",
        ),
        CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="recurring_date_range",
        ),
        CheckConstraint(
            "scope IN ('personal', 'family')",
            name="recurring_scope",
        ),
        CheckConstraint(
            """(
                (scope = 'personal' AND user_id IS NOT NULL AND family_id IS NULL) OR
                (scope = 'family' AND family_id IS NOT NULL AND user_id IS NULL)
            )""",
            name="recurring_scope_ownership",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    scope: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="personal",
        index=True,
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    family_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("families.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
    )

    start_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    next_due_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    frequency: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    interval_value: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    end_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
        index=True,
    )

    is_archived: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
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
    )

    category: Mapped["Category"] = relationship(
        "Category",
        foreign_keys=[category_id],
    )

    user: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[user_id],
    )

    family: Mapped["Family | None"] = relationship(
        "Family",
        foreign_keys=[family_id],
    )

    creator: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by],
    )

    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction",
        back_populates="recurring_rule",
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def __repr__(self) -> str:
        return (
            f"<RecurringTransaction id={self.id} name={self.name!r} type={self.type!r} "
            f"amount={self.amount} next_due_date={self.next_due_date} is_active={self.is_active}>"
        )
