import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.family import Family
    from app.models.transaction import Transaction
    from app.models.transfer import Transfer
    from app.models.user import User


class Account(Base):
    """Bảng quản lý ví tiền cá nhân và ví chung gia đình."""

    __tablename__ = "accounts"
    __table_args__ = (
        CheckConstraint(
            "scope IN ('personal', 'family')",
            name="scope",
        ),
        CheckConstraint(
            """(
                (scope = 'personal' AND user_id IS NOT NULL AND family_id IS NULL) OR
                (scope = 'family' AND family_id IS NOT NULL AND user_id IS NULL)
            )""",
            name="scope_ownership",
        ),
        CheckConstraint(
            "account_type IN ('cash', 'bank', 'e_wallet', 'credit_card', 'other')",
            name="account_type",
        ),
        CheckConstraint(
            "length(currency) = 3",
            name="currency_length",
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

    scope: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
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

    account_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="cash",
    )

    currency: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        default="VND",
        server_default=text("'VND'"),
    )

    initial_balance: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0.00"),
    )

    is_archived: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
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
        back_populates="accounts",
    )

    family: Mapped["Family | None"] = relationship(
        "Family",
        foreign_keys=[family_id],
        back_populates="accounts",
    )

    # Transfer relationships
    transfers_sent: Mapped[list["Transfer"]] = relationship(
        "Transfer",
        foreign_keys="Transfer.from_account_id",
        back_populates="from_account",
        passive_deletes="all",
    )

    transfers_received: Mapped[list["Transfer"]] = relationship(
        "Transfer",
        foreign_keys="Transfer.to_account_id",
        back_populates="to_account",
        passive_deletes="all",
    )

    # Transaction relationships
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction",
        foreign_keys="Transaction.account_id",
        back_populates="account",
        passive_deletes="all",
    )

    @validates("currency")
    def validate_and_normalize_currency(self, key: str, value: str) -> str:
        """Chuẩn hóa mã tiền tệ: loại bỏ khoảng trắng và chuyển thành 3 ký tự in hoa."""
        if not value or not isinstance(value, str):
            raise ValueError("Mã tiền tệ không được để trống và phải là chuỗi hợp lệ.")
        normalized = value.strip().upper()
        if len(normalized) != 3:
            raise ValueError("Mã tiền tệ phải gồm đúng 3 ký tự chuẩn ISO 4217 (ví dụ: VND, USD).")
        return normalized

    @validates("name")
    def validate_name(self, key: str, value: str) -> str:
        """Kiểm tra và chuẩn hóa tên ví."""
        if not value or not isinstance(value, str) or not value.strip():
            raise ValueError("Tên ví không được để trống.")
        return value.strip()

    @property
    def is_deleted(self) -> bool:
        """Kiểm tra ví đã bị xóa mềm hay chưa."""
        return self.deleted_at is not None

    def __repr__(self) -> str:
        """Hiển thị đối tượng an toàn."""
        return (
            f"<Account id={self.id} name={self.name!r} scope={self.scope!r} "
            f"type={self.account_type!r} currency={self.currency!r} "
            f"archived={self.is_archived}>"
        )
