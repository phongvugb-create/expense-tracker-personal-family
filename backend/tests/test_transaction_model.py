import uuid
from datetime import UTC, datetime
from decimal import Decimal

from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction
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
    """Đảm bảo mapper configuration biên dịch hoàn hảo, không có lỗi quan hệ ORM hoặc ambiguous foreign keys."""
    configure_mappers()


def test_transaction_table_structure_and_columns():
    """Kiểm tra cấu trúc cột và kiểu dữ liệu của bảng transactions."""
    table = Transaction.__table__

    assert table.name == "transactions"

    # Primary key UUID
    assert table.c.id.primary_key is True
    assert isinstance(table.c.id.type, UUID)

    # account_id NOT NULL UUID
    assert table.c.account_id.nullable is False
    assert isinstance(table.c.account_id.type, UUID)

    # category_id & transfer_id nullable UUID
    assert table.c.category_id.nullable is True
    assert isinstance(table.c.category_id.type, UUID)

    assert table.c.transfer_id.nullable is True
    assert isinstance(table.c.transfer_id.type, UUID)

    # user_id NOT NULL UUID
    assert table.c.user_id.nullable is False
    assert isinstance(table.c.user_id.type, UUID)

    # type NOT NULL String(20)
    assert table.c.type.nullable is False
    assert table.c.type.type.length == 20

    # amount Numeric(15, 2) NOT NULL (tuyệt đối không dùng Float/Real)
    assert table.c.amount.nullable is False
    assert isinstance(table.c.amount.type, Numeric)
    assert table.c.amount.type.precision == 15
    assert table.c.amount.type.scale == 2

    # note Text nullable
    assert table.c.note.nullable is True
    assert isinstance(table.c.note.type, Text)

    # occurred_at TIMESTAMPTZ NOT NULL
    assert isinstance(table.c.occurred_at.type, DateTime)
    assert table.c.occurred_at.type.timezone is True
    assert table.c.occurred_at.nullable is False

    # created_at & updated_at TIMESTAMPTZ NOT NULL
    assert isinstance(table.c.created_at.type, DateTime)
    assert table.c.created_at.type.timezone is True
    assert table.c.created_at.nullable is False

    assert isinstance(table.c.updated_at.type, DateTime)
    assert table.c.updated_at.type.timezone is True
    assert table.c.updated_at.nullable is False

    # deleted_at TIMESTAMPTZ nullable
    assert isinstance(table.c.deleted_at.type, DateTime)
    assert table.c.deleted_at.type.timezone is True
    assert table.c.deleted_at.nullable is True


def test_transaction_foreign_keys_and_ondelete():
    """Kiểm tra foreign keys đến Account, Category, Transfer và User đều có ON DELETE RESTRICT an toàn."""
    table = Transaction.__table__
    fks = {fk.parent.name: fk for fk in table.foreign_keys}

    assert "account_id" in fks
    assert fks["account_id"].target_fullname == "accounts.id"
    assert fks["account_id"].ondelete == "RESTRICT"

    assert "category_id" in fks
    assert fks["category_id"].target_fullname == "categories.id"
    assert fks["category_id"].ondelete == "RESTRICT"

    assert "transfer_id" in fks
    assert fks["transfer_id"].target_fullname == "transfers.id"
    assert fks["transfer_id"].ondelete == "RESTRICT"

    assert "user_id" in fks
    assert fks["user_id"].target_fullname == "users.id"
    assert fks["user_id"].ondelete == "RESTRICT"


def test_transaction_constraints():
    """Kiểm tra các check constraints: amount_positive, type, type_reference_rules."""
    table = Transaction.__table__
    check_constraints = {c.name: str(c.sqltext) for c in table.constraints if isinstance(c, CheckConstraint)}

    # ck_transactions_amount_positive
    assert "ck_transactions_amount_positive" in check_constraints
    assert "amount > 0" in check_constraints["ck_transactions_amount_positive"]

    # ck_transactions_type
    assert "ck_transactions_type" in check_constraints
    assert "type IN ('income', 'expense', 'transfer_in', 'transfer_out', 'transfer_fee')" in check_constraints["ck_transactions_type"]

    # ck_transactions_type_reference_rules
    assert "ck_transactions_type_reference_rules" in check_constraints
    rules_sql = check_constraints["ck_transactions_type_reference_rules"]
    assert "type IN ('income', 'expense') AND category_id IS NOT NULL AND transfer_id IS NULL" in rules_sql
    assert "type IN ('transfer_in', 'transfer_out') AND transfer_id IS NOT NULL AND category_id IS NULL" in rules_sql
    assert "type = 'transfer_fee' AND transfer_id IS NOT NULL AND category_id IS NOT NULL" in rules_sql


def test_transaction_indexes_and_unique_constraint():
    """Kiểm tra các index và unique constraint trên cặp (transfer_id, type)."""
    table = Transaction.__table__
    indexed_columns = {tuple(col.name for col in idx.columns) for idx in table.indexes}

    assert ("account_id",) in indexed_columns
    assert ("category_id",) in indexed_columns
    assert ("transfer_id",) in indexed_columns
    assert ("user_id",) in indexed_columns
    assert ("type",) in indexed_columns
    assert ("occurred_at",) in indexed_columns
    assert ("deleted_at",) in indexed_columns

    # Partial unique index (transfer_id, type)
    transfer_type_uq = [
        idx for idx in table.indexes
        if tuple(col.name for col in idx.columns) == ("transfer_id", "type") and idx.unique
    ]
    assert len(transfer_type_uq) == 1
    assert "transfer_id IS NOT NULL" in str(transfer_type_uq[0].dialect_options["postgresql"]["where"])


def test_transaction_soft_delete_and_repr():
    """Kiểm tra thuộc tính is_deleted và hiển thị đối tượng an toàn qua __repr__."""
    tx = Transaction(
        id=uuid.uuid4(),
        account_id=uuid.uuid4(),
        category_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        type="expense",
        amount=Decimal("120000.00"),
        note="Tiền ăn trưa",
    )
    assert tx.is_deleted is False

    tx.deleted_at = datetime.now(UTC)
    assert tx.is_deleted is True

    rep = repr(tx)
    assert "120000.00" in rep
    assert "expense" in rep
    assert "deleted=True" in rep


def test_relationships_transaction():
    """Kiểm tra quan hệ 2 chiều giữa Transaction và Account, Category, Transfer, User."""
    tx_mapper = inspect(Transaction)
    account_mapper = inspect(Account)
    category_mapper = inspect(Category)
    transfer_mapper = inspect(Transfer)
    user_mapper = inspect(User)

    # Transaction -> account, category, transfer, creator
    assert "account" in tx_mapper.relationships
    assert tx_mapper.relationships["account"].target.name == "accounts"

    assert "category" in tx_mapper.relationships
    assert tx_mapper.relationships["category"].target.name == "categories"

    assert "transfer" in tx_mapper.relationships
    assert tx_mapper.relationships["transfer"].target.name == "transfers"

    assert "creator" in tx_mapper.relationships
    assert tx_mapper.relationships["creator"].target.name == "users"

    # Inverses
    assert "transactions" in account_mapper.relationships
    assert account_mapper.relationships["transactions"].target.name == "transactions"

    assert "transactions" in category_mapper.relationships
    assert category_mapper.relationships["transactions"].target.name == "transactions"

    assert "transactions" in transfer_mapper.relationships
    assert transfer_mapper.relationships["transactions"].target.name == "transactions"

    assert "transactions" in user_mapper.relationships
    assert user_mapper.relationships["transactions"].target.name == "transactions"
