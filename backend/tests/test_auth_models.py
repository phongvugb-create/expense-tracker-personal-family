import uuid
from datetime import UTC, datetime, timedelta

from app.models.auth_session import AuthSession
from app.models.email_verification_token import EmailVerificationToken
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID


def test_auth_session_table_structure():
    """Kiểm tra cấu trúc metadata của bảng auth_sessions mà không cần kết nối database."""
    table = AuthSession.__table__
    assert table.name == "auth_sessions"

    expected_columns = {
        "id",
        "user_id",
        "token_hash",
        "ip_address",
        "user_agent",
        "expires_at",
        "revoked_at",
        "last_used_at",
        "created_at",
    }
    assert expected_columns.issubset(set(table.columns.keys()))

    # Khóa chính UUID
    assert table.c.id.primary_key is True
    assert isinstance(table.c.id.type, UUID)

    # Khóa ngoại user_id -> users.id
    assert table.c.user_id.nullable is False
    foreign_keys = list(table.c.user_id.foreign_keys)
    assert len(foreign_keys) == 1
    assert foreign_keys[0].target_fullname == "users.id"
    assert foreign_keys[0].ondelete == "CASCADE"

    # token_hash NOT NULL, UNIQUE, String(255)
    assert table.c.token_hash.nullable is False
    assert isinstance(table.c.token_hash.type, String)
    assert table.c.token_hash.unique is True or any(
        table.c.token_hash in idx.columns for idx in table.indexes if idx.unique
    )

    # Thời gian hỗ trợ timezone
    assert isinstance(table.c.expires_at.type, DateTime)
    assert table.c.expires_at.type.timezone is True
    assert table.c.expires_at.nullable is False

    assert isinstance(table.c.revoked_at.type, DateTime)
    assert table.c.revoked_at.type.timezone is True
    assert table.c.revoked_at.nullable is True

    assert isinstance(table.c.last_used_at.type, DateTime)
    assert table.c.last_used_at.type.timezone is True
    assert table.c.last_used_at.nullable is False


def test_auth_session_properties_and_repr():
    """Kiểm tra logic thuộc tính phiên đăng nhập và tính an toàn của __repr__."""
    now = datetime.now(UTC)
    future = now + timedelta(days=7)
    past = now - timedelta(days=1)

    # Phiên hợp lệ
    session = AuthSession(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        token_hash="sha256_hashed_session_token_123",
        expires_at=future,
    )
    assert session.is_revoked is False
    assert session.is_expired is False
    assert session.is_valid is True

    # Phiên bị thu hồi
    session.revoked_at = now
    assert session.is_revoked is True
    assert session.is_valid is False

    # Phiên quá hạn
    expired_session = AuthSession(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        token_hash="sha256_hashed_session_token_456",
        expires_at=past,
    )
    assert expired_session.is_expired is True
    assert expired_session.is_valid is False

    # Không lộ token_hash trong __repr__
    repr_str = repr(session)
    assert "sha256_hashed_session_token" not in repr_str


def test_email_verification_token_table_structure():
    """Kiểm tra cấu trúc metadata của bảng email_verification_tokens."""
    table = EmailVerificationToken.__table__
    assert table.name == "email_verification_tokens"

    expected_columns = {
        "id",
        "user_id",
        "token_hash",
        "expires_at",
        "used_at",
        "created_at",
    }
    assert expected_columns.issubset(set(table.columns.keys()))

    assert table.c.id.primary_key is True
    assert isinstance(table.c.id.type, UUID)

    assert table.c.user_id.nullable is False
    foreign_keys = list(table.c.user_id.foreign_keys)
    assert len(foreign_keys) == 1
    assert foreign_keys[0].target_fullname == "users.id"
    assert foreign_keys[0].ondelete == "CASCADE"

    assert table.c.token_hash.nullable is False
    assert table.c.token_hash.unique is True or any(
        table.c.token_hash in idx.columns for idx in table.indexes if idx.unique
    )

    assert table.c.expires_at.nullable is False
    assert table.c.expires_at.type.timezone is True
    assert table.c.used_at.nullable is True
    assert table.c.used_at.type.timezone is True


def test_email_verification_token_properties_and_repr():
    """Kiểm tra trạng thái sử dụng của email verification token và repr."""
    now = datetime.now(UTC)
    future = now + timedelta(hours=24)

    token = EmailVerificationToken(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        token_hash="sha256_verify_token_abc",
        expires_at=future,
    )
    assert token.is_used is False
    assert token.is_expired is False
    assert token.is_valid is True

    token.used_at = now
    assert token.is_used is True
    assert token.is_valid is False

    # Repr an toàn
    assert "sha256_verify_token_abc" not in repr(token)


def test_password_reset_token_table_structure():
    """Kiểm tra cấu trúc metadata của bảng password_reset_tokens."""
    table = PasswordResetToken.__table__
    assert table.name == "password_reset_tokens"

    expected_columns = {
        "id",
        "user_id",
        "token_hash",
        "expires_at",
        "used_at",
        "created_at",
    }
    assert expected_columns.issubset(set(table.columns.keys()))

    assert table.c.id.primary_key is True
    assert isinstance(table.c.id.type, UUID)

    assert table.c.user_id.nullable is False
    foreign_keys = list(table.c.user_id.foreign_keys)
    assert len(foreign_keys) == 1
    assert foreign_keys[0].target_fullname == "users.id"
    assert foreign_keys[0].ondelete == "CASCADE"

    assert table.c.token_hash.nullable is False
    assert table.c.token_hash.unique is True or any(
        table.c.token_hash in idx.columns for idx in table.indexes if idx.unique
    )

    assert table.c.expires_at.nullable is False
    assert table.c.expires_at.type.timezone is True
    assert table.c.used_at.nullable is True
    assert table.c.used_at.type.timezone is True


def test_password_reset_token_properties_and_repr():
    """Kiểm tra trạng thái sử dụng của password reset token và repr."""
    now = datetime.now(UTC)
    future = now + timedelta(minutes=30)

    token = PasswordResetToken(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        token_hash="sha256_reset_token_xyz",
        expires_at=future,
    )
    assert token.is_used is False
    assert token.is_expired is False
    assert token.is_valid is True

    token.used_at = now
    assert token.is_used is True
    assert token.is_valid is False

    # Repr an toàn
    assert "sha256_reset_token_xyz" not in repr(token)


def test_user_relationships_to_auth_models():
    """Kiểm tra các relationship giữa User và các model xác thực."""
    mapper = User.__mapper__
    relationships = mapper.relationships

    assert "auth_sessions" in relationships
    assert relationships["auth_sessions"].target.name == "auth_sessions"

    assert "email_verification_tokens" in relationships
    assert relationships["email_verification_tokens"].target.name == "email_verification_tokens"

    assert "password_reset_tokens" in relationships
    assert relationships["password_reset_tokens"].target.name == "password_reset_tokens"
