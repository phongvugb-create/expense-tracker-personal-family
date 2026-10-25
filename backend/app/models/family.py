import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.budget import Budget
    from app.models.category import Category
    from app.models.family_invitation import FamilyInvitation
    from app.models.family_member import FamilyMember
    from app.models.user import User


class Family(Base):
    """Bảng lưu trữ thông tin nhóm gia đình chia sẻ tài chính."""

    __tablename__ = "families"

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

    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
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
    owner: Mapped["User"] = relationship(
        "User",
        foreign_keys=[owner_user_id],
        back_populates="owned_families",
    )

    members: Mapped[list["FamilyMember"]] = relationship(
        "FamilyMember",
        back_populates="family",
        passive_deletes="all",
    )

    invitations: Mapped[list["FamilyInvitation"]] = relationship(
        "FamilyInvitation",
        foreign_keys="FamilyInvitation.family_id",
        back_populates="family",
        passive_deletes="all",
    )

    accounts: Mapped[list["Account"]] = relationship(
        "Account",
        foreign_keys="Account.family_id",
        back_populates="family",
        passive_deletes="all",
    )

    categories: Mapped[list["Category"]] = relationship(
        "Category",
        foreign_keys="Category.family_id",
        back_populates="family",
        passive_deletes="all",
    )

    budgets: Mapped[list["Budget"]] = relationship(
        "Budget",
        foreign_keys="Budget.family_id",
        back_populates="family",
        passive_deletes="all",
    )

    def __repr__(self) -> str:
        """Hiển thị đối tượng an toàn."""
        return f"<Family id={self.id} name={self.name!r} owner_user_id={self.owner_user_id}>"
