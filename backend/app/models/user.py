import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.auth_session import AuthSession
    from app.models.budget import Budget
    from app.models.category import Category
    from app.models.email_verification_token import EmailVerificationToken
    from app.models.family import Family
    from app.models.family_invitation import FamilyInvitation
    from app.models.family_member import FamilyMember
    from app.models.password_reset_token import PasswordResetToken
    from app.models.transaction import Transaction
    from app.models.transfer import Transfer


class User(Base):
    """Bảng lưu trữ thông tin tài khoản người dùng và hồ sơ."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    display_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    avatar_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("true"),
        nullable=False,
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

    # Auth relationships
    auth_sessions: Mapped[list["AuthSession"]] = relationship(
        "AuthSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    email_verification_tokens: Mapped[list["EmailVerificationToken"]] = relationship(
        "EmailVerificationToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    password_reset_tokens: Mapped[list["PasswordResetToken"]] = relationship(
        "PasswordResetToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # Family relationships
    owned_families: Mapped[list["Family"]] = relationship(
        "Family",
        foreign_keys="Family.owner_user_id",
        back_populates="owner",
    )

    family_memberships: Mapped[list["FamilyMember"]] = relationship(
        "FamilyMember",
        foreign_keys="FamilyMember.user_id",
        back_populates="user",
    )

    sent_invitations: Mapped[list["FamilyInvitation"]] = relationship(
        "FamilyInvitation",
        foreign_keys="FamilyInvitation.inviter_id",
        back_populates="inviter",
    )

    accepted_invitations: Mapped[list["FamilyInvitation"]] = relationship(
        "FamilyInvitation",
        foreign_keys="FamilyInvitation.accepted_by_user_id",
        back_populates="accepted_by",
    )

    # Account relationships
    accounts: Mapped[list["Account"]] = relationship(
        "Account",
        foreign_keys="Account.user_id",
        back_populates="owner",
        passive_deletes="all",
    )

    # Category relationships
    categories: Mapped[list["Category"]] = relationship(
        "Category",
        foreign_keys="Category.user_id",
        back_populates="owner",
        passive_deletes="all",
    )

    # Transfer relationships
    transfers: Mapped[list["Transfer"]] = relationship(
        "Transfer",
        foreign_keys="Transfer.created_by",
        back_populates="creator",
        passive_deletes="all",
    )

    # Transaction relationships
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction",
        foreign_keys="Transaction.user_id",
        back_populates="creator",
        passive_deletes="all",
    )

    # Budget relationships
    budgets: Mapped[list["Budget"]] = relationship(
        "Budget",
        foreign_keys="Budget.user_id",
        back_populates="owner",
        passive_deletes="all",
    )

    @validates("email")
    def validate_and_normalize_email(self, key: str, value: str) -> str:
        """Chuẩn hóa email tầng nghiệp vụ: loại bỏ khoảng trắng và đưa về chữ thường."""
        if not value or not isinstance(value, str):
            raise ValueError("Email không được để trống và phải là chuỗi hợp lệ.")
        normalized = value.strip().lower()
        if "@" not in normalized or len(normalized) < 3:
            raise ValueError("Email không đúng định dạng.")
        return normalized

    @property
    def is_verified(self) -> bool:
        """Thuộc tính kiểm tra tài khoản đã xác thực email hay chưa."""
        return self.email_verified_at is not None

    def __repr__(self) -> str:
        """Hiển thị đối tượng an toàn, tuyệt đối không in password_hash."""
        return f"<User id={self.id} email={self.email!r} is_active={self.is_active}>"
