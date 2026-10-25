import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from app.models.budget import Budget
from app.models.category import Category
from app.models.family import Family
from app.models.user import User
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
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


def test_budget_table_structure_and_columns():
    """Kiểm tra cấu trúc cột và kiểu dữ liệu của bảng budgets."""
    table = Budget.__table__

    assert table.name == "budgets"

    # Primary key UUID
    assert table.c.id.primary_key is True
    assert isinstance(table.c.id.type, UUID)

    # name nullable String(100)
    assert table.c.name.nullable is True
    assert isinstance(table.c.name.type, String)
    assert table.c.name.type.length == 100

    # scope NOT NULL String(10)
    assert table.c.scope.nullable is False
    assert isinstance(table.c.scope.type, String)
    assert table.c.scope.type.length == 10

    # user_id & family_id nullable UUID
    assert table.c.user_id.nullable is True
    assert isinstance(table.c.user_id.type, UUID)

    assert table.c.family_id.nullable is True
    assert isinstance(table.c.family_id.type, UUID)

    # category_id NOT NULL UUID
    assert table.c.category_id.nullable is False
    assert isinstance(table.c.category_id.type, UUID)

    # amount_limit Numeric(15, 2) NOT NULL (tuyệt đối không dùng Float/Real)
    assert table.c.amount_limit.nullable is False
    assert isinstance(table.c.amount_limit.type, Numeric)
    assert table.c.amount_limit.type.precision == 15
    assert table.c.amount_limit.type.scale == 2

    # warning_threshold Numeric(5, 2) NOT NULL
    assert table.c.warning_threshold.nullable is False
    assert isinstance(table.c.warning_threshold.type, Numeric)
    assert table.c.warning_threshold.type.precision == 5
    assert table.c.warning_threshold.type.scale == 2

    # period_start & period_end Date NOT NULL
    assert table.c.period_start.nullable is False
    assert isinstance(table.c.period_start.type, Date)

    assert table.c.period_end.nullable is False
    assert isinstance(table.c.period_end.type, Date)

    # is_archived Boolean NOT NULL
    assert table.c.is_archived.nullable is False
    assert isinstance(table.c.is_archived.type, Boolean)

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

    # Xác nhận KHÔNG có cột spent_amount lưu cứng (số đã chi được tính toán động)
    assert "spent_amount" not in table.c


def test_budget_foreign_keys_and_ondelete():
    """Kiểm tra foreign keys đến User, Family và Category đều có ON DELETE RESTRICT an toàn."""
    table = Budget.__table__
    fks = {fk.parent.name: fk for fk in table.foreign_keys}

    assert "user_id" in fks
    assert fks["user_id"].target_fullname == "users.id"
    assert fks["user_id"].ondelete == "RESTRICT"

    assert "family_id" in fks
    assert fks["family_id"].target_fullname == "families.id"
    assert fks["family_id"].ondelete == "RESTRICT"

    assert "category_id" in fks
    assert fks["category_id"].target_fullname == "categories.id"
    assert fks["category_id"].ondelete == "RESTRICT"


def test_budget_constraints():
    """Kiểm tra các check constraints: scope, amount_limit, period_range, warning_threshold, scope_ownership."""
    table = Budget.__table__
    check_constraints = {c.name: str(c.sqltext) for c in table.constraints if isinstance(c, CheckConstraint)}

    # ck_budgets_scope
    assert "ck_budgets_scope" in check_constraints
    assert "scope IN ('personal', 'family')" in check_constraints["ck_budgets_scope"]

    # ck_budgets_amount_limit_positive
    assert "ck_budgets_amount_limit_positive" in check_constraints
    assert "amount_limit > 0" in check_constraints["ck_budgets_amount_limit_positive"]

    # ck_budgets_period_range
    assert "ck_budgets_period_range" in check_constraints
    assert "period_end >= period_start" in check_constraints["ck_budgets_period_range"]

    # ck_budgets_warning_threshold_range
    assert "ck_budgets_warning_threshold_range" in check_constraints
    assert "warning_threshold > 0 AND warning_threshold <= 100" in check_constraints["ck_budgets_warning_threshold_range"]

    # ck_budgets_scope_ownership
    assert "ck_budgets_scope_ownership" in check_constraints
    ownership_sql = check_constraints["ck_budgets_scope_ownership"]
    assert "scope = 'personal' AND user_id IS NOT NULL AND family_id IS NULL" in ownership_sql
    assert "scope = 'family' AND family_id IS NOT NULL AND user_id IS NULL" in ownership_sql


def test_budget_indexes():
    """Kiểm tra các index trên scope, user_id, family_id, category_id, period_start, period_end, is_archived, deleted_at."""
    table = Budget.__table__
    indexed_columns = {tuple(col.name for col in idx.columns) for idx in table.indexes}

    assert ("scope",) in indexed_columns
    assert ("user_id",) in indexed_columns
    assert ("family_id",) in indexed_columns
    assert ("category_id",) in indexed_columns
    assert ("period_start",) in indexed_columns
    assert ("period_end",) in indexed_columns
    assert ("is_archived",) in indexed_columns
    assert ("deleted_at",) in indexed_columns


def test_budget_soft_delete_and_repr():
    """Kiểm tra thuộc tính is_deleted và hiển thị đối tượng qua __repr__."""
    budget = Budget(
        id=uuid.uuid4(),
        name="Ngân sách ăn uống tháng 10",
        scope="personal",
        category_id=uuid.uuid4(),
        amount_limit=Decimal("5000000.00"),
        warning_threshold=Decimal("80.00"),
        period_start=date(2026, 10, 1),
        period_end=date(2026, 10, 31),
    )
    assert budget.is_deleted is False

    budget.deleted_at = datetime.now(UTC)
    assert budget.is_deleted is True

    rep = repr(budget)
    assert "Ngân sách ăn uống tháng 10" in rep
    assert "5000000.00" in rep
    assert "80.00%" in rep
    assert "2026-10-01" in rep
    assert "2026-10-31" in rep


def test_relationships_budget():
    """Kiểm tra quan hệ 2 chiều giữa Budget và User, Family, Category."""
    budget_mapper = inspect(Budget)
    user_mapper = inspect(User)
    family_mapper = inspect(Family)
    category_mapper = inspect(Category)

    # Budget -> owner, family, category
    assert "owner" in budget_mapper.relationships
    assert budget_mapper.relationships["owner"].target.name == "users"

    assert "family" in budget_mapper.relationships
    assert budget_mapper.relationships["family"].target.name == "families"

    assert "category" in budget_mapper.relationships
    assert budget_mapper.relationships["category"].target.name == "categories"

    # Inverses
    assert "budgets" in user_mapper.relationships
    assert user_mapper.relationships["budgets"].target.name == "budgets"

    assert "budgets" in family_mapper.relationships
    assert family_mapper.relationships["budgets"].target.name == "budgets"

    assert "budgets" in category_mapper.relationships
    assert category_mapper.relationships["budgets"].target.name == "budgets"
