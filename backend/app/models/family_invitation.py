import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
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
    from app.models.family import Family
    from app.models.user import User


class FamilyInvitation(Base):
    """Bảng quản lý lời mời tham gia nhóm gia đình gửi qua email."""

    __tablename__ = "family_invitations"
    __table_args__ = (
        CheckConstraint(
            "role IN ('editor', 'viewer')",
            name="role",
        ),
        CheckConstraint(
            """(
                (accepted_at IS NULL AND declined_at IS NULL AND revoked_at IS NULL) OR
                (accepted_at IS NOT NULL AND declined_at IS NULL AND revoked_at IS NULL) OR
                (accepted_at IS NULL AND declined_at IS NOT NULL AND revoked_at IS NULL) OR
                (accepted_at IS NULL AND declined_at IS NULL AND revoked_at IS NOT NULL)
            )""",
            name="status_conflict",
        ),
        CheckConstraint(
            """(
                (accepted_at IS NULL AND accepted_by_user_id IS NULL) OR
                (accepted_at IS NOT NULL AND accepted_by_user_id IS NOT NULL)
            )""",
            name="accepted_user",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )

    family_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("families.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    inviter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    invited_email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    token_hash: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    declined_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    accepted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    family: Mapped["Family"] = relationship(
        "Family",
        foreign_keys=[family_id],
        back_populates="invitations",
    )

    inviter: Mapped["User"] = relationship(
        "User",
        foreign_keys=[inviter_id],
        back_populates="sent_invitations",
    )

    accepted_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[accepted_by_user_id],
        back_populates="accepted_invitations",
    )

    @validates("invited_email")
    def validate_and_normalize_invited_email(self, key: str, value: str) -> str:
        """Chuẩn hóa email được mời: loại bỏ khoảng trắng và chuyển thành chữ thường."""
        if not value or not isinstance(value, str):
            raise ValueError("Email được mời không được để trống và phải là chuỗi hợp lệ.")
        normalized = value.strip().lower()
        if "@" not in normalized or len(normalized) < 3:
            raise ValueError("Email được mời không đúng định dạng.")
        return normalized

    @property
    def is_accepted(self) -> bool:
        """Kiểm tra lời mời đã được chấp nhận hay chưa."""
        return self.accepted_at is not None

    @property
    def is_declined(self) -> bool:
        """Kiểm tra lời mời đã bị từ chối hay chưa."""
        return self.declined_at is not None

    @property
    def is_revoked(self) -> bool:
        """Kiểm tra lời mời đã bị thu hồi bởi người gửi hay chưa."""
        return self.revoked_at is not None

    @property
    def is_expired(self) -> bool:
        """Kiểm tra lời mời đã quá thời hạn hiệu lực hay chưa."""
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        return datetime.now(UTC) >= expires

    @property
    def is_pending(self) -> bool:
        """Kiểm tra lời mời còn đang chờ xử lý hay không."""
        return (
            not self.is_accepted
            and not self.is_declined
            and not self.is_revoked
            and not self.is_expired
        )

    @property
    def status(self) -> str:
        """Xác định trạng thái tổng hợp của lời mời."""
        if self.is_accepted:
            return "accepted"
        if self.is_declined:
            return "declined"
        if self.is_revoked:
            return "revoked"
        if self.is_expired:
            return "expired"
        return "pending"

    def __repr__(self) -> str:
        """Hiển thị đối tượng an toàn, tuyệt đối không in token_hash."""
        return (
            f"<FamilyInvitation id={self.id} family_id={self.family_id} "
            f"invited_email={self.invited_email!r} role={self.role!r} status={self.status!r}>"
        )
