import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.transaction import Transaction
    from app.models.user import User


class Transfer(Base):
    """Bảng quản lý nghiệp vụ chuyển tiền giữa hai ví (bút toán kép)."""

    __tablename__ = "transfers"
    __table_args__ = (
        CheckConstraint(
            "amount > 0",
            name="amount_positive",
        ),
        CheckConstraint(
            "fee_amount >= 0",
            name="fee_amount_non_negative",
        ),
        CheckConstraint(
            "from_account_id != to_account_id",
            name="distinct_accounts",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    from_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    to_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
    )

    fee_amount: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False,
        default=Decimal("0.00"),
        server_default=text("0.00"),
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

    voided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )

    # Relationships
    from_account: Mapped["Account"] = relationship(
        "Account",
        foreign_keys=[from_account_id],
        back_populates="transfers_sent",
    )

    to_account: Mapped["Account"] = relationship(
        "Account",
        foreign_keys=[to_account_id],
        back_populates="transfers_received",
    )

    creator: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by],
        back_populates="transfers",
    )

    # Transaction relationships (bút toán chuyển tiền)
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction",
        foreign_keys="Transaction.transfer_id",
        back_populates="transfer",
        passive_deletes="all",
    )

    @property
    def is_voided(self) -> bool:
        """Kiểm tra giao dịch chuyển khoản đã bị hủy/vô hiệu hóa hay chưa."""
        return self.voided_at is not None

    def __repr__(self) -> str:
        """Hiển thị đối tượng an toàn."""
        return (
            f"<Transfer id={self.id} from={self.from_account_id} to={self.to_account_id} "
            f"amount={self.amount} fee={self.fee_amount} voided={self.is_voided}>"
        )
