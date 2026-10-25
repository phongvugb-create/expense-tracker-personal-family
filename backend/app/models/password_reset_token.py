import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class PasswordResetToken(Base):
    """Bảng lưu trữ token khôi phục mật khẩu gửi cho người dùng."""

    __tablename__ = "password_reset_tokens"

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
        back_populates="password_reset_tokens",
    )

    @property
    def is_used(self) -> bool:
        """Kiểm tra token đã được dùng để đổi mật khẩu hay chưa."""
        return self.used_at is not None

    @property
    def is_expired(self) -> bool:
        """Kiểm tra token đặt lại mật khẩu đã hết hạn hay chưa."""
        return datetime.now(UTC) >= self.expires_at

    @property
    def is_valid(self) -> bool:
        """Kiểm tra token còn hạn và chưa được sử dụng hay không."""
        return not self.is_used and not self.is_expired

    def __repr__(self) -> str:
        """Hiển thị đối tượng an toàn, không chứa token_hash."""
        return f"<PasswordResetToken id={self.id} user_id={self.user_id} expires_at={self.expires_at}>"
