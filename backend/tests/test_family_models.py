import uuid
from datetime import UTC, datetime

from app.models.family import Family
from app.models.family_member import FamilyMember
from app.models.user import User
from sqlalchemy import CheckConstraint, DateTime, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import configure_mappers


def test_mapper_configuration_clean():
    """Đảm bảo toàn bộ mapper của SQLAlchemy được cấu hình nhất quán, không lỗi quan hệ mơ hồ."""
    configure_mappers()


def test_family_table_structure():
    """Kiểm tra cấu trúc metadata của bảng families."""
    table = Family.__table__
    assert table.name == "families"

    expected_columns = {
        "id",
        "name",
        "owner_user_id",
        "created_at",
        "updated_at",
        "deleted_at",
    }
    assert expected_columns.issubset(set(table.columns.keys()))

    # Primary key UUID
    assert table.c.id.primary_key is True
    assert isinstance(table.c.id.type, UUID)

    # name: NOT NULL
    assert table.c.name.nullable is False
    assert isinstance(table.c.name.type, String)

    # owner_user_id: FK users.id, ON DELETE RESTRICT
    assert table.c.owner_user_id.nullable is False
    foreign_keys = list(table.c.owner_user_id.foreign_keys)
    assert len(foreign_keys) == 1
    assert foreign_keys[0].target_fullname == "users.id"
    assert foreign_keys[0].ondelete == "RESTRICT"

    # Timezone check
    assert isinstance(table.c.created_at.type, DateTime)
    assert table.c.created_at.type.timezone is True
    assert isinstance(table.c.updated_at.type, DateTime)
    assert table.c.updated_at.type.timezone is True
    assert isinstance(table.c.deleted_at.type, DateTime)
    assert table.c.deleted_at.type.timezone is True
    assert table.c.deleted_at.nullable is True


def test_family_member_table_structure():
    """Kiểm tra cấu trúc metadata của bảng family_members với chính sách bảo toàn lịch sử."""
    table = FamilyMember.__table__
    assert table.name == "family_members"

    expected_columns = {
        "id",
        "family_id",
        "user_id",
        "role",
        "joined_at",
        "created_at",
        "updated_at",
        "left_at",
    }
    assert expected_columns.issubset(set(table.columns.keys()))

    # Primary key UUID
    assert table.c.id.primary_key is True
    assert isinstance(table.c.id.type, UUID)

    # family_id FK -> families.id, ON DELETE RESTRICT (ngăn xóa vật lý nhóm khi còn thành viên)
    assert table.c.family_id.nullable is False
    fks_family = list(table.c.family_id.foreign_keys)
    assert len(fks_family) == 1
    assert fks_family[0].target_fullname == "families.id"
    assert fks_family[0].ondelete == "RESTRICT"

    # user_id FK -> users.id, ON DELETE RESTRICT (ngăn xóa vật lý user khi còn liên kết thành viên)
    assert table.c.user_id.nullable is False
    fks_user = list(table.c.user_id.foreign_keys)
    assert len(fks_user) == 1
    assert fks_user[0].target_fullname == "users.id"
    assert fks_user[0].ondelete == "RESTRICT"

    # role String(20)
    assert table.c.role.nullable is False
    assert isinstance(table.c.role.type, String)

    # Timestamps with timezone
    assert table.c.joined_at.type.timezone is True
    assert table.c.created_at.type.timezone is True
    assert table.c.updated_at.type.timezone is True
    assert table.c.left_at.type.timezone is True
    assert table.c.left_at.nullable is True


def test_family_member_constraints():
    """Kiểm tra Unique Constraint và Check Constraint trên family_members."""
    table = FamilyMember.__table__

    # UniqueConstraint trên (family_id, user_id)
    unique_constraints = [c for c in table.constraints if isinstance(c, UniqueConstraint)]
    family_user_uq = any(
        {"family_id", "user_id"} == {col.name for col in uq.columns}
        for uq in unique_constraints
    )
    assert family_user_uq is True

    # CheckConstraint cho role in ('owner', 'editor', 'viewer')
    check_constraints = [c for c in table.constraints if isinstance(c, CheckConstraint)]
    assert len(check_constraints) >= 1
    role_ck_found = any(
        "role IN ('owner', 'editor', 'viewer')" in str(ck.sqltext)
        for ck in check_constraints
    )
    assert role_ck_found is True


def test_relationships_between_user_family_and_member():
    """Kiểm tra các relationship và xác nhận Family.members KHÔNG dùng delete-orphan."""
    user_mapper = User.__mapper__
    family_mapper = Family.__mapper__
    member_mapper = FamilyMember.__mapper__

    # User -> owned_families & family_memberships
    assert "owned_families" in user_mapper.relationships
    assert user_mapper.relationships["owned_families"].target.name == "families"

    assert "family_memberships" in user_mapper.relationships
    assert user_mapper.relationships["family_memberships"].target.name == "family_members"

    # Family -> owner & members
    assert "owner" in family_mapper.relationships
    assert family_mapper.relationships["owner"].target.name == "users"

    assert "members" in family_mapper.relationships
    members_rel = family_mapper.relationships["members"]
    assert members_rel.target.name == "family_members"

    # Ràng buộc cốt lõi: Không sử dụng delete-orphan để tránh xóa vật lý bản ghi lịch sử
    assert "delete-orphan" not in members_rel.cascade
    assert "delete" not in members_rel.cascade

    # FamilyMember -> family & user
    assert "family" in member_mapper.relationships
    assert member_mapper.relationships["family"].target.name == "families"

    assert "user" in member_mapper.relationships
    assert member_mapper.relationships["user"].target.name == "users"


def test_family_member_left_at_and_properties():
    """Kiểm tra thuộc tính left_at và is_active_member bảo toàn dữ liệu khi rời nhóm."""
    member = FamilyMember(
        id=uuid.uuid4(),
        family_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        role="editor",
    )
    assert member.is_active_member is True
    assert member.left_at is None

    # Mô phỏng rời nhóm: cập nhật left_at chứ không xóa bản ghi
    leave_time = datetime.now(UTC)
    member.left_at = leave_time
    assert member.is_active_member is False
    assert member.left_at == leave_time

    repr_str = repr(member)
    assert "editor" in repr_str
    assert str(member.id) in repr_str

    family = Family(
        id=uuid.uuid4(),
        name="Family Test",
        owner_user_id=uuid.uuid4(),
    )
    assert "Family Test" in repr(family)
