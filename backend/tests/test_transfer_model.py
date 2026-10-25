import uuid
from datetime import UTC, datetime
from decimal import Decimal

from app.models.account import Account
from app.models.transfer import Transfer
from app.models.user import User
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Numeric,
    Text,
    inspect,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import configure_mappers


def test_mapper_configuration_clean():
    """Đảm bảo mapper configuration biên dịch hoàn hảo, không có lỗi ambiguous foreign keys."""
    configure_mappers()


def test_transfer_table_structure_and_columns():
    """Kiểm tra cấu trúc cột và kiểu dữ liệu của bảng transfers."""
    table = Transfer.__table__

    assert table.name == "transfers"

    # Primary key UUID
    assert table.c.id.primary_key is True
    assert isinstance(table.c.id.type, UUID)

    # from_account_id & to_account_id NOT NULL, UUID
    assert table.c.from_account_id.nullable is False
    assert isinstance(table.c.from_account_id.type, UUID)

    assert table.c.to_account_id.nullable is False
    assert isinstance(table.c.to_account_id.type, UUID)

    # created_by NOT NULL, UUID
    assert table.c.created_by.nullable is False
    assert isinstance(table.c.created_by.type, UUID)

    # amount & fee_amount Numeric(15, 2), NOT NULL
    assert table.c.amount.nullable is False
    assert isinstance(table.c.amount.type, Numeric)
    assert table.c.amount.type.precision == 15
    assert table.c.amount.type.scale == 2

    assert table.c.fee_amount.nullable is False
    assert isinstance(table.c.fee_amount.type, Numeric)
    assert table.c.fee_amount.type.precision == 15
    assert table.c.fee_amount.type.scale == 2

    # note Text, nullable
    assert table.c.note.nullable is True
    assert isinstance(table.c.note.type, Text)

    # occurred_at TIMESTAMPTZ, NOT NULL
    assert isinstance(table.c.occurred_at.type, DateTime)
    assert table.c.occurred_at.type.timezone is True
    assert table.c.occurred_at.nullable is False

    # created_at & updated_at TIMESTAMPTZ, NOT NULL
    assert isinstance(table.c.created_at.type, DateTime)
    assert table.c.created_at.type.timezone is True
    assert table.c.created_at.nullable is False

    assert isinstance(table.c.updated_at.type, DateTime)
    assert table.c.updated_at.type.timezone is True
    assert table.c.updated_at.nullable is False

    # voided_at TIMESTAMPTZ, nullable
    assert isinstance(table.c.voided_at.type, DateTime)
    assert table.c.voided_at.type.timezone is True
    assert table.c.voided_at.nullable is True


def test_transfer_foreign_keys_and_ondelete():
    """Kiểm tra foreign keys đến accounts (from/to) và users (created_by) đều có ON DELETE RESTRICT an toàn."""
    table = Transfer.__table__
    fks = {fk.parent.name: fk for fk in table.foreign_keys}

    assert "from_account_id" in fks
    assert fks["from_account_id"].target_fullname == "accounts.id"
    assert fks["from_account_id"].ondelete == "RESTRICT"

    assert "to_account_id" in fks
    assert fks["to_account_id"].target_fullname == "accounts.id"
    assert fks["to_account_id"].ondelete == "RESTRICT"

    assert "created_by" in fks
    assert fks["created_by"].target_fullname == "users.id"
    assert fks["created_by"].ondelete == "RESTRICT"


def test_transfer_constraints():
    """Kiểm tra các check constraints: amount_positive, fee_amount_non_negative, distinct_accounts."""
    table = Transfer.__table__
    check_constraints = {c.name: str(c.sqltext) for c in table.constraints if isinstance(c, CheckConstraint)}

    # ck_transfers_amount_positive
    assert "ck_transfers_amount_positive" in check_constraints
    assert "amount > 0" in check_constraints["ck_transfers_amount_positive"]

    # ck_transfers_fee_amount_non_negative
    assert "ck_transfers_fee_amount_non_negative" in check_constraints
    assert "fee_amount >= 0" in check_constraints["ck_transfers_fee_amount_non_negative"]

    # ck_transfers_distinct_accounts
    assert "ck_transfers_distinct_accounts" in check_constraints
    assert "from_account_id != to_account_id" in check_constraints["ck_transfers_distinct_accounts"]


def test_transfer_indexes():
    """Kiểm tra các index trên from_account_id, to_account_id, created_by, occurred_at, voided_at."""
    table = Transfer.__table__
    indexed_columns = {tuple(col.name for col in idx.columns) for idx in table.indexes}

    assert ("from_account_id",) in indexed_columns
    assert ("to_account_id",) in indexed_columns
    assert ("created_by",) in indexed_columns
    assert ("occurred_at",) in indexed_columns
    assert ("voided_at",) in indexed_columns


def test_transfer_properties_and_repr():
    """Kiểm tra property is_voided và hiển thị đối tượng an toàn qua __repr__."""
    transfer = Transfer(
        id=uuid.uuid4(),
        from_account_id=uuid.uuid4(),
        to_account_id=uuid.uuid4(),
        created_by=uuid.uuid4(),
        amount=Decimal("1500000.00"),
        fee_amount=Decimal("3300.00"),
        note="Chuyển khoản thanh toán",
    )
    assert transfer.is_voided is False

    transfer.voided_at = datetime.now(UTC)
    assert transfer.is_voided is True

    rep = repr(transfer)
    assert "1500000.00" in rep
    assert "3300.00" in rep
    assert "voided=True" in rep


def test_relationships_transfer_accounts_and_user():
    """Kiểm tra các relationship hai chiều giữa Transfer, Account (from/to) và User."""
    transfer_mapper = inspect(Transfer)
    account_mapper = inspect(Account)
    user_mapper = inspect(User)

    # Transfer -> from_account, to_account, creator
    assert "from_account" in transfer_mapper.relationships
    assert transfer_mapper.relationships["from_account"].target.name == "accounts"

    assert "to_account" in transfer_mapper.relationships
    assert transfer_mapper.relationships["to_account"].target.name == "accounts"

    assert "creator" in transfer_mapper.relationships
    assert transfer_mapper.relationships["creator"].target.name == "users"

    # Account -> transfers_sent, transfers_received
    assert "transfers_sent" in account_mapper.relationships
    assert account_mapper.relationships["transfers_sent"].target.name == "transfers"

    assert "transfers_received" in account_mapper.relationships
    assert account_mapper.relationships["transfers_received"].target.name == "transfers"

    # User -> transfers
    assert "transfers" in user_mapper.relationships
    assert user_mapper.relationships["transfers"].target.name == "transfers"
