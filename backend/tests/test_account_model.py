import uuid
from datetime import UTC, datetime
from decimal import Decimal

from app.models.account import Account
from app.models.family import Family
from app.models.user import User
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Numeric,
    String,
    inspect,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import configure_mappers


def test_mapper_configuration_clean():
    """Đảm bảo mapper configuration biên dịch hoàn hảo, không có lỗi ambiguous foreign keys."""
    configure_mappers()


def test_account_table_structure_and_columns():
    """Kiểm tra cấu trúc cột và kiểu dữ liệu của bảng accounts."""
    table = Account.__table__

    assert table.name == "accounts"

    # Primary key UUID
    assert table.c.id.primary_key is True
    assert isinstance(table.c.id.type, UUID)

    # name NOT NULL, String(100)
    assert table.c.name.nullable is False
    assert isinstance(table.c.name.type, String)
    assert table.c.name.type.length == 100

    # scope NOT NULL, String(10)
    assert table.c.scope.nullable is False
    assert isinstance(table.c.scope.type, String)
    assert table.c.scope.type.length == 10

    # user_id & family_id nullable, UUID
    assert table.c.user_id.nullable is True
    assert isinstance(table.c.user_id.type, UUID)

    assert table.c.family_id.nullable is True
    assert isinstance(table.c.family_id.type, UUID)

    # account_type NOT NULL, String(20)
    assert table.c.account_type.nullable is False
    assert isinstance(table.c.account_type.type, String)
    assert table.c.account_type.type.length == 20

    # currency NOT NULL, String(3)
    assert table.c.currency.nullable is False
    assert isinstance(table.c.currency.type, String)
    assert table.c.currency.type.length == 3

    # initial_balance Numeric(15, 2), NOT NULL (tuyệt đối không dùng Float/Real)
    assert table.c.initial_balance.nullable is False
    assert isinstance(table.c.initial_balance.type, Numeric)
    assert table.c.initial_balance.type.precision == 15
    assert table.c.initial_balance.type.scale == 2

    # is_archived Boolean, NOT NULL
    assert table.c.is_archived.nullable is False
    assert isinstance(table.c.is_archived.type, Boolean)

    # Timestamps with timezone
    assert isinstance(table.c.created_at.type, DateTime)
    assert table.c.created_at.type.timezone is True
    assert table.c.created_at.nullable is False

    assert isinstance(table.c.updated_at.type, DateTime)
    assert table.c.updated_at.type.timezone is True
    assert table.c.updated_at.nullable is False

    assert isinstance(table.c.deleted_at.type, DateTime)
    assert table.c.deleted_at.type.timezone is True
    assert table.c.deleted_at.nullable is True


def test_account_foreign_keys_and_ondelete():
    """Kiểm tra foreign keys đến users và families đều có ON DELETE RESTRICT an toàn."""
    table = Account.__table__
    fks = {fk.parent.name: fk for fk in table.foreign_keys}

    assert "user_id" in fks
    assert fks["user_id"].target_fullname == "users.id"
    assert fks["user_id"].ondelete == "RESTRICT"

    assert "family_id" in fks
    assert fks["family_id"].target_fullname == "families.id"
    assert fks["family_id"].ondelete == "RESTRICT"


def test_account_constraints():
    """Kiểm tra các check constraints: scope, scope_ownership, account_type, currency_length."""
    table = Account.__table__
    check_constraints = {c.name: str(c.sqltext) for c in table.constraints if isinstance(c, CheckConstraint)}

    # ck_accounts_scope
    assert "ck_accounts_scope" in check_constraints
    assert "scope IN ('personal', 'family')" in check_constraints["ck_accounts_scope"]

    # ck_accounts_scope_ownership (Scope exclusion rule)
    assert "ck_accounts_scope_ownership" in check_constraints
    ownership_sql = check_constraints["ck_accounts_scope_ownership"]
    assert "scope = 'personal' AND user_id IS NOT NULL AND family_id IS NULL" in ownership_sql
    assert "scope = 'family' AND family_id IS NOT NULL AND user_id IS NULL" in ownership_sql

    # ck_accounts_account_type
    assert "ck_accounts_account_type" in check_constraints
    assert "account_type IN ('cash', 'bank', 'e_wallet', 'credit_card', 'other')" in check_constraints["ck_accounts_account_type"]

    # ck_accounts_currency_length
    assert "ck_accounts_currency_length" in check_constraints
    assert "length(currency) = 3" in check_constraints["ck_accounts_currency_length"]


def test_account_indexes():
    """Kiểm tra các index trên user_id, family_id, deleted_at."""
    table = Account.__table__
    indexed_columns = {tuple(col.name for col in idx.columns) for idx in table.indexes}

    assert ("user_id",) in indexed_columns
    assert ("family_id",) in indexed_columns
    assert ("deleted_at",) in indexed_columns


def test_account_currency_normalization():
    """Kiểm tra validator chuẩn hóa tiền tệ uppercase và kiểm tra độ dài 3 ký tự."""
    acc = Account(
        name="Ví tiền mặt",
        scope="personal",
        account_type="cash",
        currency="  vnd  ",
        initial_balance=Decimal("500000.00"),
    )
    assert acc.currency == "VND"


def test_account_name_normalization():
    """Kiểm tra validator strip tên ví."""
    acc = Account(
        name="   Tài khoản MBBank   ",
        scope="personal",
        account_type="bank",
        currency="VND",
    )
    assert acc.name == "Tài khoản MBBank"


def test_account_negative_initial_balance_allowed():
    """Xác nhận không giới hạn initial_balance >= 0 (hỗ trợ ví thấu chi hoặc thẻ tín dụng)."""
    acc = Account(
        name="Thẻ tín dụng Visa",
        scope="personal",
        account_type="credit_card",
        currency="VND",
        initial_balance=Decimal("-5000000.00"),
    )
    assert acc.initial_balance == Decimal("-5000000.00")


def test_account_soft_delete_and_repr():
    """Kiểm tra thuộc tính is_deleted và __repr__."""
    acc = Account(
        id=uuid.uuid4(),
        name="Ví MoMo",
        scope="personal",
        account_type="e_wallet",
        currency="VND",
        is_archived=False,
    )
    assert acc.is_deleted is False

    acc.deleted_at = datetime.now(UTC)
    assert acc.is_deleted is True

    rep = repr(acc)
    assert "Ví MoMo" in rep
    assert "personal" in rep
    assert "e_wallet" in rep
    assert "VND" in rep


def test_relationships_account_user_and_family():
    """Kiểm tra các relationship hai chiều giữa Account, User và Family."""
    account_mapper = inspect(Account)
    user_mapper = inspect(User)
    family_mapper = inspect(Family)

    # Account -> owner & family
    assert "owner" in account_mapper.relationships
    assert account_mapper.relationships["owner"].target.name == "users"

    assert "family" in account_mapper.relationships
    assert account_mapper.relationships["family"].target.name == "families"

    # User -> accounts
    assert "accounts" in user_mapper.relationships
    assert user_mapper.relationships["accounts"].target.name == "accounts"

    # Family -> accounts
    assert "accounts" in family_mapper.relationships
    assert family_mapper.relationships["accounts"].target.name == "accounts"
