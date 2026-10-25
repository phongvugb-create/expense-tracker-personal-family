import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.core.config import settings
from app.core.security import hash_session_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.auth_session import AuthSession
from app.models.family import Family
from app.models.family_member import FamilyMember
from app.models.user import User
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Tạo isolated in-memory SQLite engine cho bộ test API Family
sqlite_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sqlite_engine)

# Tạo bảng từ Base metadata trên SQLite in-memory
Base.metadata.create_all(bind=sqlite_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    """Làm sạch dữ liệu in-memory trước mỗi test case mà không chạm tới PostgreSQL."""
    app.dependency_overrides[get_db] = override_get_db
    db = TestingSessionLocal()
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()
    db.close()


def create_user_and_session(email: str, display_name: str = "Test User") -> tuple[User, str]:
    """Helper tạo User và AuthSession, trả về (User, raw_token)."""
    db = TestingSessionLocal()
    now = datetime.now(UTC)
    user = User(
        id=uuid.uuid4(),
        email=email.strip().lower(),
        password_hash="argon2id_mock_hash",
        display_name=display_name,
        is_active=True,
        email_verified_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(user)

    raw_token = f"session_token_{uuid.uuid4().hex}"
    session = AuthSession(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=hash_session_token(raw_token),
        ip_address="127.0.0.1",
        user_agent="pytest-agent",
        revoked_at=None,
        expires_at=now + timedelta(days=7),
        created_at=now,
        last_used_at=now,
    )
    db.add(session)
    db.commit()
    user_id = user.id
    db.close()

    # Re-fetch user
    db2 = TestingSessionLocal()
    user_obj = db2.get(User, user_id)
    assert user_obj is not None
    db2.close()
    return user_obj, raw_token


# ==============================================================================
# 1. Chưa đăng nhập bị từ chối (401)
# ==============================================================================
def test_unauthenticated_request_rejected():
    res = client.get("/api/v1/families")
    assert res.status_code == 401
    assert "Yêu cầu đăng nhập" in res.json()["detail"]


# ==============================================================================
# 2. Tạo nhóm gia đình hợp lệ (201)
# ==============================================================================
def test_create_family_success():
    owner, token = create_user_and_session("owner1@family.com", "Chủ Hộ")
    client.cookies.set(settings.SESSION_COOKIE_NAME, token)

    payload = {"name": "Gia Đình Hạnh Phúc"}
    res = client.post("/api/v1/families", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Gia Đình Hạnh Phúc"
    assert data["owner_user_id"] == str(owner.id)
    assert data["my_role"] == "owner"
    assert data["member_count"] == 1


# ==============================================================================
# 3. Owner và thành viên xem được danh sách nhóm; người ngoài bị phân lập
# ==============================================================================
def test_get_families_isolation_between_users():
    owner, token_owner = create_user_and_session("owner2@family.com", "Owner")
    member_user, token_member = create_user_and_session("member2@family.com", "Member")
    _stranger, token_stranger = create_user_and_session("stranger2@family.com", "Stranger")

    db = TestingSessionLocal()
    family = Family(
        id=uuid.uuid4(),
        name="Nhóm Của Owner",
        owner_user_id=owner.id,
    )
    db.add(family)
    db.flush()

    fm = FamilyMember(
        id=uuid.uuid4(),
        family_id=family.id,
        user_id=member_user.id,
        role="editor",
    )
    db.add(fm)
    db.commit()
    family_id = family.id
    db.close()

    # 1. Owner thấy nhóm với my_role = owner
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_owner)
    res_owner = client.get("/api/v1/families")
    assert res_owner.status_code == 200
    list_owner = res_owner.json()
    assert len(list_owner) == 1
    assert list_owner[0]["id"] == str(family_id)
    assert list_owner[0]["my_role"] == "owner"
    assert list_owner[0]["member_count"] == 2

    # 2. Member thấy nhóm với my_role = editor
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_member)
    res_member = client.get("/api/v1/families")
    assert res_member.status_code == 200
    list_member = res_member.json()
    assert len(list_member) == 1
    assert list_member[0]["id"] == str(family_id)
    assert list_member[0]["my_role"] == "editor"

    # 3. Stranger không thấy nhóm nào
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_stranger)
    res_stranger = client.get("/api/v1/families")
    assert res_stranger.status_code == 200
    assert len(res_stranger.json()) == 0


# ==============================================================================
# 4. Người ngoài không xem hoặc sửa được nhóm (404)
# ==============================================================================
def test_stranger_cannot_view_or_patch_family():
    owner, _ = create_user_and_session("owner3@family.com")
    _, token_stranger = create_user_and_session("stranger3@family.com")

    db = TestingSessionLocal()
    family = Family(id=uuid.uuid4(), name="Nhóm Riêng Tư", owner_user_id=owner.id)
    db.add(family)
    db.commit()
    family_id = family.id
    db.close()

    client.cookies.set(settings.SESSION_COOKIE_NAME, token_stranger)

    # Xem chi tiết -> 404
    get_res = client.get(f"/api/v1/families/{family_id}")
    assert get_res.status_code == 404

    # Sửa tên -> 404
    patch_res = client.patch(f"/api/v1/families/{family_id}", json={"name": "Tên hack"})
    assert patch_res.status_code == 404


# ==============================================================================
# 5. Chỉ owner được đổi tên nhóm (Editor / Viewer bị 403)
# ==============================================================================
def test_only_owner_can_update_family_name():
    owner, token_owner = create_user_and_session("owner4@family.com")
    editor, token_editor = create_user_and_session("editor4@family.com")

    db = TestingSessionLocal()
    family = Family(id=uuid.uuid4(), name="Tên Cũ", owner_user_id=owner.id)
    db.add(family)
    db.flush()
    member = FamilyMember(id=uuid.uuid4(), family_id=family.id, user_id=editor.id, role="editor")
    db.add(member)
    db.commit()
    family_id = family.id
    db.close()

    # Editor cố đổi tên -> 403 Forbidden
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_editor)
    res_ed = client.patch(f"/api/v1/families/{family_id}", json={"name": "Editor đổi tên"})
    assert res_ed.status_code == 403

    # Owner đổi tên -> 200 OK
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_owner)
    res_ow = client.patch(f"/api/v1/families/{family_id}", json={"name": "Tên Mới Của Owner"})
    assert res_ow.status_code == 200
    assert res_ow.json()["name"] == "Tên Mới Của Owner"


# ==============================================================================
# 6. Thành viên: Owner được hiển thị chính xác kể cả khi không có row FamilyMember riêng
# ==============================================================================
def test_family_members_list_includes_owner():
    owner, token_owner = create_user_and_session("owner5@family.com", "Chủ Nhóm Vĩ Đại")
    db = TestingSessionLocal()
    family = Family(id=uuid.uuid4(), name="Nhóm Solo", owner_user_id=owner.id)
    db.add(family)
    db.commit()
    family_id = family.id
    db.close()

    client.cookies.set(settings.SESSION_COOKIE_NAME, token_owner)
    res = client.get(f"/api/v1/families/{family_id}/members")
    assert res.status_code == 200
    members = res.json()
    assert len(members) == 1
    assert members[0]["user_id"] == str(owner.id)
    assert members[0]["role"] == "owner"
    assert members[0]["is_owner"] is True
    assert members[0]["display_name"] == "Chủ Nhóm Vĩ Đại"


# ==============================================================================
# 7. Phân quyền vai trò: Owner thay đổi role thành viên (chỉ editor/viewer)
# ==============================================================================
def test_owner_updates_member_role_success_and_restrictions():
    owner, token_owner = create_user_and_session("owner6@family.com")
    member_user, token_member = create_user_and_session("member6@family.com")

    db = TestingSessionLocal()
    family = Family(id=uuid.uuid4(), name="Nhóm Role Test", owner_user_id=owner.id)
    db.add(family)
    db.flush()
    fm = FamilyMember(id=uuid.uuid4(), family_id=family.id, user_id=member_user.id, role="viewer")
    db.add(fm)
    db.commit()
    family_id = family.id
    member_id = fm.id
    db.close()

    # Member cố tự nâng quyền lên editor -> 403 Forbidden
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_member)
    res_self = client.patch(
        f"/api/v1/families/{family_id}/members/{member_id}/role",
        json={"role": "editor"},
    )
    assert res_self.status_code == 403

    # Owner đổi role thành viên lên editor -> 200 OK
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_owner)
    res_up = client.patch(
        f"/api/v1/families/{family_id}/members/{member_id}/role",
        json={"role": "editor"},
    )
    assert res_up.status_code == 200
    assert res_up.json()["role"] == "editor"

    # Cố gán role owner cho thành viên thường -> 422 Unprocessable (Validation)
    res_invalid_role = client.patch(
        f"/api/v1/families/{family_id}/members/{member_id}/role",
        json={"role": "owner"},
    )
    assert res_invalid_role.status_code == 422


# ==============================================================================
# 8. Thành viên rời nhóm (leave) và Owner kick thành viên
# ==============================================================================
def test_member_leave_and_owner_kick():
    owner, _token_owner = create_user_and_session("owner7@family.com")
    member_user, token_member = create_user_and_session("member7@family.com")

    db = TestingSessionLocal()
    family = Family(id=uuid.uuid4(), name="Nhóm Rời Đi", owner_user_id=owner.id)
    db.add(family)
    db.flush()
    fm = FamilyMember(id=uuid.uuid4(), family_id=family.id, user_id=member_user.id, role="viewer")
    db.add(fm)
    db.commit()
    family_id = family.id
    member_id = fm.id
    db.close()

    # Member tự rời nhóm
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_member)
    res_leave = client.post(f"/api/v1/families/{family_id}/members/{member_id}/leave")
    assert res_leave.status_code == 200

    # Sau khi rời nhóm, xem danh sách gia đình -> không còn nhóm này
    res_list = client.get("/api/v1/families")
    assert len(res_list.json()) == 0

    # Cố xem chi tiết -> 404
    res_detail = client.get(f"/api/v1/families/{family_id}")
    assert res_detail.status_code == 404


# ==============================================================================
# 9. Lời mời: Owner/Editor được mời, Viewer bị cấm (403)
# ==============================================================================
def test_invitation_permissions_by_role():
    owner, _token_owner = create_user_and_session("owner8@family.com")
    editor, token_editor = create_user_and_session("editor8@family.com")
    viewer, token_viewer = create_user_and_session("viewer8@family.com")

    db = TestingSessionLocal()
    family = Family(id=uuid.uuid4(), name="Nhóm Lời Mời", owner_user_id=owner.id)
    db.add(family)
    db.flush()
    m_editor = FamilyMember(id=uuid.uuid4(), family_id=family.id, user_id=editor.id, role="editor")
    m_viewer = FamilyMember(id=uuid.uuid4(), family_id=family.id, user_id=viewer.id, role="viewer")
    db.add_all([m_editor, m_viewer])
    db.commit()
    family_id = family.id
    db.close()

    # Viewer cố tạo lời mời -> 403 Forbidden
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_viewer)
    res_v = client.post(
        f"/api/v1/families/{family_id}/invitations",
        json={"invited_email": "guest1@example.com", "role": "viewer"},
    )
    assert res_v.status_code == 403

    # Editor tạo lời mời -> 201 Created (kèm token trả về cho dev/demo)
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_editor)
    res_e = client.post(
        f"/api/v1/families/{family_id}/invitations",
        json={"invited_email": "guest2@example.com", "role": "editor"},
    )
    assert res_e.status_code == 201
    assert res_e.json()["invited_email"] == "guest2@example.com"
    assert res_e.json()["invitation_token"] is not None


# ==============================================================================
# 10. Chấp nhận lời mời (Accept Invitation): Thành công và xác thực email
# ==============================================================================
def test_accept_invitation_flow_and_validation():
    _owner, token_owner = create_user_and_session("owner9@family.com")
    guest, token_guest = create_user_and_session("guest9@example.com", "Khách Mời")
    _wrong_user, token_wrong = create_user_and_session("wrong9@example.com", "Người Lạ")

    client.cookies.set(settings.SESSION_COOKIE_NAME, token_owner)
    res_fam = client.post("/api/v1/families", json={"name": "Gia Đình Đón Khách"})
    family_id = res_fam.json()["id"]

    # Owner mời guest9@example.com
    res_inv = client.post(
        f"/api/v1/families/{family_id}/invitations",
        json={"invited_email": "guest9@example.com", "role": "editor"},
    )
    assert res_inv.status_code == 201
    token = res_inv.json()["invitation_token"]
    assert token is not None

    # 1. Người lạ (wrong9) cố dùng token -> 403 Forbidden vì email không khớp
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_wrong)
    res_wrong = client.post("/api/v1/families/invitations/accept", json={"token": token})
    assert res_wrong.status_code == 403
    assert "không trùng khớp" in res_wrong.json()["detail"]

    # 2. Đúng người (guest9) chấp nhận lời mời -> 200 OK
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_guest)
    res_accept = client.post("/api/v1/families/invitations/accept", json={"token": token})
    assert res_accept.status_code == 200
    member_data = res_accept.json()
    assert member_data["user_id"] == str(guest.id)
    assert member_data["role"] == "editor"

    # 3. Sau khi chấp nhận, guest9 thấy nhóm gia đình
    res_list = client.get("/api/v1/families")
    assert len(res_list.json()) == 1
    assert res_list.json()[0]["id"] == family_id
    assert res_list.json()[0]["my_role"] == "editor"

    # 4. Token đã dùng không thể chấp nhận lần 2 -> 400 Bad Request
    res_reuse = client.post("/api/v1/families/invitations/accept", json={"token": token})
    assert res_reuse.status_code == 400


# ==============================================================================
# 11. Thu hồi lời mời (Revoke Invitation)
# ==============================================================================
def test_revoke_invitation_flow():
    _owner, token_owner = create_user_and_session("owner10@family.com")
    _guest, token_guest = create_user_and_session("guest10@example.com")

    client.cookies.set(settings.SESSION_COOKIE_NAME, token_owner)
    res_fam = client.post("/api/v1/families", json={"name": "Gia Đình Thu Hồi"})
    family_id = res_fam.json()["id"]

    res_inv = client.post(
        f"/api/v1/families/{family_id}/invitations",
        json={"invited_email": "guest10@example.com", "role": "viewer"},
    )
    invitation_id = res_inv.json()["id"]
    token = res_inv.json()["invitation_token"]

    # Owner thu hồi lời mời
    res_rev = client.post(f"/api/v1/families/{family_id}/invitations/{invitation_id}/revoke")
    assert res_rev.status_code == 200

    # Guest cố chấp nhận lời mời bị thu hồi -> 400 Bad Request
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_guest)
    res_accept = client.post("/api/v1/families/invitations/accept", json={"token": token})
    assert res_accept.status_code == 400
    assert "không còn hiệu lực" in res_accept.json()["detail"]


# ==============================================================================
# 12. Danh sách lời mời không làm lộ token_hash hoặc secret
# ==============================================================================
def test_invitations_list_does_not_leak_secret():
    _owner, token_owner = create_user_and_session("owner11@family.com")
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_owner)

    res_fam = client.post("/api/v1/families", json={"name": "Gia Đình Bảo Mật"})
    family_id = res_fam.json()["id"]

    client.post(
        f"/api/v1/families/{family_id}/invitations",
        json={"invited_email": "guest11@example.com", "role": "viewer"},
    )

    # Lấy danh sách lời mời
    res_list = client.get(f"/api/v1/families/{family_id}/invitations")
    assert res_list.status_code == 200
    items = res_list.json()
    assert len(items) == 1
    assert "token_hash" not in items[0]
    assert items[0]["invitation_token"] is None
