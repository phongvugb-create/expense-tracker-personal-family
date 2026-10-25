import uuid
from datetime import UTC, datetime

from app.models.family import Family
from app.models.family_invitation import FamilyInvitation
from app.models.user import User
from sqlalchemy import (
    CheckConstraint,
    Index,
    String,
    UniqueConstraint,
    inspect,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import configure_mappers


def test_mapper_configuration_clean():
    """Đảm bảo mapper configuration biên dịch hoàn hảo, không có lỗi ambiguous foreign keys."""
    configure_mappers()


def test_family_invitation_table_structure():
    """Kiểm tra cấu trúc cột và kiểu dữ liệu của bảng family_invitations."""
    table = FamilyInvitation.__table__

    assert table.name == "family_invitations"

    # Kiểm tra Primary Key
    assert table.c.id.primary_key is True
    assert isinstance(table.c.id.type, UUID)

    # Kiểm tra các cột bắt buộc (NOT NULL)
    assert table.c.family_id.nullable is False
    assert isinstance(table.c.family_id.type, UUID)

    assert table.c.inviter_id.nullable is False
    assert isinstance(table.c.inviter_id.type, UUID)

    assert table.c.invited_email.nullable is False
    assert isinstance(table.c.invited_email.type, String)
    assert table.c.invited_email.type.length == 255

    assert table.c.token_hash.nullable is False
    assert isinstance(table.c.token_hash.type, String)
    assert table.c.token_hash.type.length == 255

    assert table.c.role.nullable is False
    assert isinstance(table.c.role.type, String)
    assert table.c.role.type.length == 20

    assert table.c.expires_at.nullable is False
    assert table.c.expires_at.type.timezone is True

    assert table.c.created_at.nullable is False
    assert table.c.created_at.type.timezone is True

    # Kiểm tra các cột có thể NULL
    assert table.c.accepted_at.nullable is True
    assert table.c.accepted_at.type.timezone is True

    assert table.c.declined_at.nullable is True
    assert table.c.declined_at.type.timezone is True

    assert table.c.revoked_at.nullable is True
    assert table.c.revoked_at.type.timezone is True

    assert table.c.accepted_by_user_id.nullable is True
    assert isinstance(table.c.accepted_by_user_id.type, UUID)


def test_family_invitation_foreign_keys_and_ondelete():
    """Kiểm tra Foreign Keys và chính sách ON DELETE RESTRICT an toàn cho dữ liệu kiểm toán."""
    table = FamilyInvitation.__table__
    fks = {fk.parent.name: fk for fk in table.foreign_keys}

    assert "family_id" in fks
    assert fks["family_id"].target_fullname == "families.id"
    assert fks["family_id"].ondelete == "RESTRICT"

    assert "inviter_id" in fks
    assert fks["inviter_id"].target_fullname == "users.id"
    assert fks["inviter_id"].ondelete == "RESTRICT"

    assert "accepted_by_user_id" in fks
    assert fks["accepted_by_user_id"].target_fullname == "users.id"
    assert fks["accepted_by_user_id"].ondelete == "RESTRICT"


def test_family_invitation_constraints():
    """Kiểm tra các Unique và Check Constraints trên bảng family_invitations."""
    table = FamilyInvitation.__table__

    # Unique constraint token_hash
    unique_constraints = [c for c in table.constraints if isinstance(c, UniqueConstraint)]
    unique_cols = {tuple(col.name for col in c.columns) for c in unique_constraints}
    assert (
        table.c.token_hash.unique is True
        or ("token_hash",) in unique_cols
        or any(table.c.token_hash in idx.columns for idx in table.indexes if idx.unique)
    )

    # Check constraints
    check_constraints = {c.name: str(c.sqltext) for c in table.constraints if isinstance(c, CheckConstraint)}

    assert "ck_family_invitations_role" in check_constraints
    assert "role IN ('editor', 'viewer')" in check_constraints["ck_family_invitations_role"]

    assert "ck_family_invitations_status_conflict" in check_constraints
    assert "ck_family_invitations_accepted_user" in check_constraints


def test_family_invitation_indexes():
    """Kiểm tra các index phục vụ tìm kiếm và kiểm tra hiệu năng."""
    table = FamilyInvitation.__table__
    indexes = [c for c in table.indexes if isinstance(c, Index)]
    index_cols = {tuple(col.name for col in idx.columns) for idx in indexes}

    assert ("family_id",) in index_cols
    assert ("invited_email",) in index_cols
    assert ("expires_at",) in index_cols


def test_family_invitation_email_normalization():
    """Kiểm tra chuẩn hóa email: strip khoảng trắng và chuyển sang lowercase."""
    invitation = FamilyInvitation(
        invited_email="  Partner.Work@Example.COM  ",
        role="editor",
        token_hash="hash_123456",
        expires_at=datetime.now(UTC),
    )
    assert invitation.invited_email == "partner.work@example.com"


def test_family_invitation_status_properties():
    """Kiểm tra các property logic trạng thái của FamilyInvitation."""
    now = datetime.now(UTC)
    future = datetime(2099, 1, 1, tzinfo=UTC)
    past = datetime(2020, 1, 1, tzinfo=UTC)

    # Pending
    inv1 = FamilyInvitation(
        role="editor",
        invited_email="user1@example.com",
        token_hash="hash_1",
        expires_at=future,
    )
    assert inv1.is_pending is True
    assert inv1.is_accepted is False
    assert inv1.is_expired is False
    assert inv1.status == "pending"

    # Accepted
    inv2 = FamilyInvitation(
        role="viewer",
        invited_email="user2@example.com",
        token_hash="hash_2",
        expires_at=future,
        accepted_at=now,
    )
    assert inv2.is_accepted is True
    assert inv2.is_pending is False
    assert inv2.status == "accepted"

    # Declined
    inv3 = FamilyInvitation(
        role="viewer",
        invited_email="user3@example.com",
        token_hash="hash_3",
        expires_at=future,
        declined_at=now,
    )
    assert inv3.is_declined is True
    assert inv3.status == "declined"

    # Revoked
    inv4 = FamilyInvitation(
        role="editor",
        invited_email="user4@example.com",
        token_hash="hash_4",
        expires_at=future,
        revoked_at=now,
    )
    assert inv4.is_revoked is True
    assert inv4.status == "revoked"

    # Expired
    inv5 = FamilyInvitation(
        role="viewer",
        invited_email="user5@example.com",
        token_hash="hash_5",
        expires_at=past,
    )
    assert inv5.is_expired is True
    assert inv5.is_pending is False
    assert inv5.status == "expired"


def test_family_invitation_repr_security():
    """Đảm bảo __repr__ không để lộ token_hash."""
    invitation = FamilyInvitation(
        id=uuid.uuid4(),
        role="editor",
        invited_email="secure@example.com",
        token_hash="super_secret_hash_value_999",
        expires_at=datetime.now(UTC),
    )
    rep = repr(invitation)
    assert "super_secret_hash_value_999" not in rep
    assert "secure@example.com" in rep
    assert "editor" in rep


def test_relationships_family_invitation():
    """Kiểm tra relationships giữa FamilyInvitation, Family và User."""
    invitation_mapper = inspect(FamilyInvitation)
    family_mapper = inspect(Family)
    user_mapper = inspect(User)

    # Relationships on FamilyInvitation
    assert "family" in invitation_mapper.relationships
    assert invitation_mapper.relationships["family"].target.name == "families"

    assert "inviter" in invitation_mapper.relationships
    assert invitation_mapper.relationships["inviter"].target.name == "users"

    assert "accepted_by" in invitation_mapper.relationships
    assert invitation_mapper.relationships["accepted_by"].target.name == "users"

    # Relationships on Family
    assert "invitations" in family_mapper.relationships
    assert family_mapper.relationships["invitations"].target.name == "family_invitations"

    # Relationships on User
    assert "sent_invitations" in user_mapper.relationships
    assert user_mapper.relationships["sent_invitations"].target.name == "family_invitations"

    assert "accepted_invitations" in user_mapper.relationships
    assert user_mapper.relationships["accepted_invitations"].target.name == "family_invitations"
