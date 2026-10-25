import uuid
from datetime import UTC, datetime

import pytest
from app.db.base import POSTGRES_NAMING_CONVENTION, Base
from app.models.user import User
from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID


def test_metadata_naming_convention():
    """Kiểm tra naming convention được gán chính xác vào Base metadata."""
    assert Base.metadata.naming_convention == POSTGRES_NAMING_CONVENTION
    assert Base.metadata.naming_convention["pk"] == "pk_%(table_name)s"
    assert Base.metadata.naming_convention["uq"] == "uq_%(table_name)s_%(column_0_name)s"


def test_user_table_structure_and_columns():
    """Kiểm tra cấu trúc metadata của bảng users mà không cần kết nối database."""
    table = User.__table__
    assert table.name == "users"

    # Danh sách các cột bắt buộc
    expected_columns = {
        "id",
        "email",
        "password_hash",
        "display_name",
        "avatar_url",
        "email_verified_at",
        "is_active",
        "created_at",
        "updated_at",
        "deleted_at",
    }
    actual_columns = set(table.columns.keys())
    assert expected_columns.issubset(actual_columns)

    # Kiểm tra Primary Key
    assert table.c.id.primary_key is True
    assert isinstance(table.c.id.type, UUID)

    # Kiểm tra email: NOT NULL và UNIQUE
    assert table.c.email.nullable is False
    assert isinstance(table.c.email.type, String)
    assert table.c.email.unique is True or any(
        table.c.email in idx.columns for idx in table.indexes if idx.unique
    )

    # Kiểm tra password_hash: NOT NULL
    assert table.c.password_hash.nullable is False

    # Kiểm tra display_name: NOT NULL
    assert table.c.display_name.nullable is False

    # Kiểm tra timezone của các trường thời gian
    assert isinstance(table.c.created_at.type, DateTime)
    assert table.c.created_at.type.timezone is True
    assert isinstance(table.c.updated_at.type, DateTime)
    assert table.c.updated_at.type.timezone is True
    assert isinstance(table.c.email_verified_at.type, DateTime)
    assert table.c.email_verified_at.type.timezone is True
    assert isinstance(table.c.deleted_at.type, DateTime)
    assert table.c.deleted_at.type.timezone is True


def test_user_email_normalization():
    """Kiểm tra email được chuẩn hóa (strip & lowercase) ở tầng nghiệp vụ."""
    user = User(
        email="   John.Doe@EXPENSETRACKER.Local  ",
        password_hash="hashed_secret",
        display_name="John Doe",
    )
    assert user.email == "john.doe@expensetracker.local"


def test_user_invalid_email_raises_error():
    """Kiểm tra email không hợp lệ sẽ kích hoạt lỗi validation."""
    with pytest.raises(ValueError, match="Email không đúng định dạng"):
        User(
            email="invalid-email-no-at-sign",
            password_hash="hashed_secret",
            display_name="John Doe",
        )

    with pytest.raises(ValueError, match="Email không được để trống"):
        User(
            email="",
            password_hash="hashed_secret",
            display_name="John Doe",
        )


def test_user_is_verified_property():
    """Kiểm tra thuộc tính is_verified phản ánh trạng thái email_verified_at."""
    user = User(
        email="user@test.local",
        password_hash="hashed_secret",
        display_name="Test User",
    )
    assert user.is_verified is False

    user.email_verified_at = datetime.now(UTC)
    assert user.is_verified is True


def test_user_repr_does_not_leak_password():
    """Đảm bảo password_hash không bao giờ bị rò rỉ qua __repr__."""
    user = User(
        id=uuid.uuid4(),
        email="secure@test.local",
        password_hash="super_secret_argon2_hash",
        display_name="Secure User",
    )
    repr_str = repr(user)
    assert "super_secret_argon2_hash" not in repr_str
    assert "secure@test.local" in repr_str
