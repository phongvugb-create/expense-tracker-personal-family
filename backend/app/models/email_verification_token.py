import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class EmailVerificationToken(Base):
    """Bảng lưu trữ token xác thực email gửi cho người dùng."""

    __tablename__ = "email_verification_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    token_hash: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(
        "User",
        back_populates="email_verification_tokens",
    )

    @property
    def is_used(self) -> bool:
        """Kiểm tra token đã được sử dụng hay chưa."""
        return self.used_at is not None

    @property
    def is_expired(self) -> bool:
        """Kiểm tra token đã hết hạn hay chưa."""
        return datetime.now(UTC) >= self.expires_at

    @property
    def is_valid(self) -> bool:
        """Kiểm tra token còn giá trị sử dụng hay không."""
        return not self.is_used and not self.is_expired

    def __repr__(self) -> str:
        """Hiển thị đối tượng an toàn, không chứa token_hash."""
        return f"<EmailVerificationToken id={self.id} user_id={self.user_id} expires_at={self.expires_at}>"
