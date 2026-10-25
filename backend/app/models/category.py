import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.budget import Budget
    from app.models.family import Family
    from app.models.transaction import Transaction
    from app.models.user import User


class Category(Base):
    """Bảng quản lý danh mục thu nhập và chi tiêu (hệ thống, cá nhân, gia đình)."""

    __tablename__ = "categories"
    __table_args__ = (
        CheckConstraint(
            "type IN ('income', 'expense')",
            name="type",
        ),
        CheckConstraint(
            "scope IN ('system', 'personal', 'family')",
            name="scope",
        ),
        CheckConstraint(
            """(
                (scope = 'system' AND user_id IS NULL AND family_id IS NULL) OR
                (scope = 'personal' AND user_id IS NOT NULL AND family_id IS NULL) OR
                (scope = 'family' AND family_id IS NOT NULL AND user_id IS NULL)
            )""",
            name="scope_ownership",
        ),
        CheckConstraint(
            "(is_default IS FALSE) OR (is_default IS TRUE AND scope = 'system')",
            name="default_system_only",
        ),
        CheckConstraint(
            "parent_id IS NULL OR parent_id != id",
            name="no_self_parent",
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
        String(10),
        nullable=False,
        index=True,
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

    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    icon: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    color: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )

    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
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
        back_populates="categories",
    )

    family: Mapped["Family | None"] = relationship(
        "Family",
        foreign_keys=[family_id],
        back_populates="categories",
    )

    # Self-referencing parent-child relationship
    parent: Mapped["Category | None"] = relationship(
        "Category",
        remote_side=[id],
        foreign_keys=[parent_id],
        back_populates="children",
    )

    children: Mapped[list["Category"]] = relationship(
        "Category",
        foreign_keys=[parent_id],
        back_populates="parent",
        passive_deletes="all",
    )

    # Transaction relationships
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction",
        foreign_keys="Transaction.category_id",
        back_populates="category",
        passive_deletes="all",
    )

    # Budget relationships
    budgets: Mapped[list["Budget"]] = relationship(
        "Budget",
        foreign_keys="Budget.category_id",
        back_populates="category",
        passive_deletes="all",
    )

    @validates("name")
    def validate_name(self, key: str, value: str) -> str:
        """Chuẩn hóa tên danh mục: loại bỏ khoảng trắng thừa và không cho phép rỗng."""
        if not value or not isinstance(value, str) or not value.strip():
            raise ValueError("Tên danh mục không được để trống.")
        return value.strip()

    @property
    def is_deleted(self) -> bool:
        """Kiểm tra danh mục đã bị xóa mềm hay chưa."""
        return self.deleted_at is not None

    def __repr__(self) -> str:
        """Hiển thị đối tượng an toàn."""
        return (
            f"<Category id={self.id} name={self.name!r} type={self.type!r} "
            f"scope={self.scope!r} default={self.is_default} archived={self.is_archived}>"
        )
