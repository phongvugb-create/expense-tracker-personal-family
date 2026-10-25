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
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.family import Family
    from app.models.user import User


class Budget(Base):
    """Bảng quản lý hạn mức ngân sách chi tiêu cá nhân và gia đình theo kỳ."""

    __tablename__ = "budgets"
    __table_args__ = (
        CheckConstraint(
            "scope IN ('personal', 'family')",
            name="scope",
        ),
        CheckConstraint(
            "amount_limit > 0",
            name="amount_limit_positive",
        ),
        CheckConstraint(
            "period_end >= period_start",
            name="period_range",
        ),
        CheckConstraint(
            "warning_threshold > 0 AND warning_threshold <= 100",
            name="warning_threshold_range",
        ),
        CheckConstraint(
            """(
                (scope = 'personal' AND user_id IS NOT NULL AND family_id IS NULL) OR
                (scope = 'family' AND family_id IS NOT NULL AND user_id IS NULL)
            )""",
            name="scope_ownership",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    scope: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True,
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    family_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("families.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    amount_limit: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
    )

    period_start: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    period_end: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    warning_threshold: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        default=Decimal("80.00"),
        server_default=text("80.00"),
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
    owner: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="budgets",
    )

    family: Mapped["Family | None"] = relationship(
        "Family",
        foreign_keys=[family_id],
        back_populates="budgets",
    )

    category: Mapped["Category"] = relationship(
        "Category",
        foreign_keys=[category_id],
        back_populates="budgets",
    )

    @property
    def is_deleted(self) -> bool:
        """Kiểm tra ngân sách đã bị xóa mềm hay chưa."""
        return self.deleted_at is not None

    def __repr__(self) -> str:
        """Hiển thị đối tượng an toàn."""
        return (
            f"<Budget id={self.id} name={self.name!r} scope={self.scope!r} "
            f"amount_limit={self.amount_limit} threshold={self.warning_threshold}% "
            f"period=[{self.period_start} to {self.period_end}] archived={self.is_archived}>"
        )
