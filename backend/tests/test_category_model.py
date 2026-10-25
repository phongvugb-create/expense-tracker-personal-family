import uuid
from datetime import UTC, datetime

import pytest
from app.models.category import Category
from app.models.family import Family
from app.models.user import User
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    String,
    inspect,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import configure_mappers


def test_mapper_configuration_clean():
    """Đảm bảo mapper configuration biên dịch hoàn hảo, không có lỗi quan hệ tự tham chiếu hoặc ambiguous foreign keys."""
    configure_mappers()


def test_category_table_structure_and_columns():
    """Kiểm tra cấu trúc cột và kiểu dữ liệu của bảng categories."""
    table = Category.__table__

    assert table.name == "categories"

    # Primary key UUID
    assert table.c.id.primary_key is True
    assert isinstance(table.c.id.type, UUID)

    # name NOT NULL, String(100)
    assert table.c.name.nullable is False
    assert isinstance(table.c.name.type, String)
    assert table.c.name.type.length == 100

    # type NOT NULL, String(10)
    assert table.c.type.nullable is False
    assert isinstance(table.c.type.type, String)
    assert table.c.type.type.length == 10

    # scope NOT NULL, String(10)
    assert table.c.scope.nullable is False
    assert isinstance(table.c.scope.type, String)
    assert table.c.scope.type.length == 10

    # user_id, family_id, parent_id nullable UUID
    assert table.c.user_id.nullable is True
    assert isinstance(table.c.user_id.type, UUID)

    assert table.c.family_id.nullable is True
    assert isinstance(table.c.family_id.type, UUID)

    assert table.c.parent_id.nullable is True
    assert isinstance(table.c.parent_id.type, UUID)

    # icon & color String nullable
    assert table.c.icon.nullable is True
    assert isinstance(table.c.icon.type, String)
    assert table.c.icon.type.length == 50

    assert table.c.color.nullable is True
    assert isinstance(table.c.color.type, String)
    assert table.c.color.type.length == 20

    # is_default & is_archived Boolean, NOT NULL
    assert table.c.is_default.nullable is False
    assert isinstance(table.c.is_default.type, Boolean)

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


def test_category_foreign_keys_and_ondelete():
    """Kiểm tra foreign keys đến users, families và categories đều có ON DELETE RESTRICT an toàn."""
    table = Category.__table__
    fks = {fk.parent.name: fk for fk in table.foreign_keys}

    assert "user_id" in fks
    assert fks["user_id"].target_fullname == "users.id"
    assert fks["user_id"].ondelete == "RESTRICT"

    assert "family_id" in fks
    assert fks["family_id"].target_fullname == "families.id"
    assert fks["family_id"].ondelete == "RESTRICT"

    assert "parent_id" in fks
    assert fks["parent_id"].target_fullname == "categories.id"
    assert fks["parent_id"].ondelete == "RESTRICT"


def test_category_constraints():
    """Kiểm tra các check constraints: type, scope, scope_ownership, default_system_only, no_self_parent."""
    table = Category.__table__
    check_constraints = {c.name: str(c.sqltext) for c in table.constraints if isinstance(c, CheckConstraint)}

    # ck_categories_type
    assert "ck_categories_type" in check_constraints
    assert "type IN ('income', 'expense')" in check_constraints["ck_categories_type"]

    # ck_categories_scope
    assert "ck_categories_scope" in check_constraints
    assert "scope IN ('system', 'personal', 'family')" in check_constraints["ck_categories_scope"]

    # ck_categories_scope_ownership
    assert "ck_categories_scope_ownership" in check_constraints
    ownership_sql = check_constraints["ck_categories_scope_ownership"]
    assert "scope = 'system' AND user_id IS NULL AND family_id IS NULL" in ownership_sql
    assert "scope = 'personal' AND user_id IS NOT NULL AND family_id IS NULL" in ownership_sql
    assert "scope = 'family' AND family_id IS NOT NULL AND user_id IS NULL" in ownership_sql

    # ck_categories_default_system_only
    assert "ck_categories_default_system_only" in check_constraints
    assert "(is_default IS FALSE) OR (is_default IS TRUE AND scope = 'system')" in check_constraints["ck_categories_default_system_only"]

    # ck_categories_no_self_parent
    assert "ck_categories_no_self_parent" in check_constraints
    assert "parent_id IS NULL OR parent_id != id" in check_constraints["ck_categories_no_self_parent"]


def test_category_indexes():
    """Kiểm tra các index trên type, scope, user_id, family_id, parent_id, is_archived, deleted_at."""
    table = Category.__table__
    indexed_columns = {tuple(col.name for col in idx.columns) for idx in table.indexes}

    assert ("type",) in indexed_columns
    assert ("scope",) in indexed_columns
    assert ("user_id",) in indexed_columns
    assert ("family_id",) in indexed_columns
    assert ("parent_id",) in indexed_columns
    assert ("is_archived",) in indexed_columns
    assert ("deleted_at",) in indexed_columns


def test_category_no_arbitrary_unique_on_name():
    """Đảm bảo không có unique constraint trên name để tránh xung đột giữa các scope."""
    table = Category.__table__
    assert table.c.name.unique is not True


def test_category_name_normalization():
    """Kiểm tra validator chuẩn hóa và strip tên danh mục."""
    cat = Category(
        name="   Ăn uống nhà hàng   ",
        type="expense",
        scope="personal",
        user_id=uuid.uuid4(),
    )
    assert cat.name == "Ăn uống nhà hàng"

    with pytest.raises(ValueError, match="Tên danh mục không được để trống"):
        Category(
            name="   ",
            type="expense",
            scope="personal",
            user_id=uuid.uuid4(),
        )


def test_category_soft_delete_and_repr():
    """Kiểm tra thuộc tính is_deleted và hàm __repr__."""
    cat = Category(
        id=uuid.uuid4(),
        name="Lương thưởng",
        type="income",
        scope="system",
        is_default=True,
    )
    assert cat.is_deleted is False

    cat.deleted_at = datetime.now(UTC)
    assert cat.is_deleted is True

    rep = repr(cat)
    assert "Lương thưởng" in rep
    assert "income" in rep
    assert "system" in rep
    assert "default=True" in rep


def test_relationships_category_user_family_and_self():
    """Kiểm tra các relationship hai chiều và tự tham chiếu cha–con."""
    category_mapper = inspect(Category)
    user_mapper = inspect(User)
    family_mapper = inspect(Family)

    # Category -> owner & family
    assert "owner" in category_mapper.relationships
    assert category_mapper.relationships["owner"].target.name == "users"

    assert "family" in category_mapper.relationships
    assert category_mapper.relationships["family"].target.name == "families"

    # Category self-referential: parent & children
    assert "parent" in category_mapper.relationships
    assert category_mapper.relationships["parent"].target.name == "categories"

    assert "children" in category_mapper.relationships
    assert category_mapper.relationships["children"].target.name == "categories"

    # User -> categories
    assert "categories" in user_mapper.relationships
    assert user_mapper.relationships["categories"].target.name == "categories"

    # Family -> categories
    assert "categories" in family_mapper.relationships
    assert family_mapper.relationships["categories"].target.name == "categories"
