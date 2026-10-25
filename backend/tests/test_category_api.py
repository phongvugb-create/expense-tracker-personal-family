import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.core.config import settings
from app.core.security import hash_session_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.auth_session import AuthSession
from app.models.category import Category
from app.models.family import Family
from app.models.family_member import FamilyMember
from app.models.user import User
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from scripts.seed_system_categories import seed_system_categories

# Tạo isolated in-memory SQLite engine cho bộ test API Category
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
        password_hash="test_argon2_hash",
        display_name=display_name,
        is_active=True,
    )
    db.add(user)
    db.flush()

    raw_token = f"test_session_token_{uuid.uuid4().hex}"
    token_hash = hash_session_token(raw_token)
    session = AuthSession(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=token_hash,
        expires_at=now + timedelta(days=1),
    )
    db.add(session)
    db.commit()
    db.refresh(user)
    db.close()
    return user, raw_token


def create_family_helper(owner_id: uuid.UUID, name: str = "Gia đình mẫu") -> Family:
    """Helper tạo nhóm gia đình."""
    db = TestingSessionLocal()
    family = Family(
        id=uuid.uuid4(),
        name=name,
        owner_user_id=owner_id,
    )
    db.add(family)
    db.commit()
    db.refresh(family)
    db.close()
    return family


def add_family_member_helper(family_id: uuid.UUID, user_id: uuid.UUID, role: str) -> FamilyMember:
    """Helper thêm thành viên vào nhóm gia đình."""
    db = TestingSessionLocal()
    member = FamilyMember(
        id=uuid.uuid4(),
        family_id=family_id,
        user_id=user_id,
        role=role,
        joined_at=datetime.now(UTC),
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    db.close()
    return member


# ==============================================================================
# 1. Test chưa đăng nhập bị từ chối (HTTP 401)
# ==============================================================================
def test_categories_unauthenticated():
    res_get = client.get("/api/v1/categories")
    assert res_get.status_code == 401

    res_post = client.post(
        "/api/v1/categories",
        json={"name": "Chi tiêu cá nhân", "type": "expense", "scope": "personal"},
    )
    assert res_post.status_code == 401


# ==============================================================================
# 2. Test xem danh mục hệ thống và lọc theo type/scope
# ==============================================================================
def test_get_system_categories():
    _user, token = create_user_and_session("user1@example.com")
    db = TestingSessionLocal()
    # Tạo danh mục hệ thống
    cat1 = Category(
        name="Ăn uống",
        type="expense",
        scope="system",
        is_default=True,
    )
    cat2 = Category(
        name="Lương",
        type="income",
        scope="system",
        is_default=True,
    )
    db.add_all([cat1, cat2])
    db.commit()
    db.close()

    res = client.get(
        "/api/v1/categories",
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2
    names = [c["name"] for c in data]
    assert "Ăn uống" in names
    assert "Lương" in names

    # Lọc type=income
    res_income = client.get(
        "/api/v1/categories?type=income",
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert res_income.status_code == 200
    data_income = res_income.json()
    assert len(data_income) == 1
    assert data_income[0]["name"] == "Lương"


# ==============================================================================
# 3. Test người dùng chỉ thấy danh mục cá nhân của mình
# ==============================================================================
def test_personal_categories_isolation():
    user1, token1 = create_user_and_session("user1@example.com")
    user2, _token2 = create_user_and_session("user2@example.com")

    c1_id = uuid.uuid4()
    c2_id = uuid.uuid4()

    db = TestingSessionLocal()
    c1 = Category(
        id=c1_id,
        name="Quỹ đen của user 1",
        type="expense",
        scope="personal",
        user_id=user1.id,
    )
    c2 = Category(
        id=c2_id,
        name="Quỹ riêng của user 2",
        type="expense",
        scope="personal",
        user_id=user2.id,
    )
    db.add_all([c1, c2])
    db.commit()
    db.close()

    # User 1 kiểm tra
    res1 = client.get(
        "/api/v1/categories?scope=personal",
        cookies={settings.SESSION_COOKIE_NAME: token1},
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert len(data1) == 1
    assert data1[0]["name"] == "Quỹ đen của user 1"

    # User 1 không thể xem detail danh mục của User 2
    res_detail = client.get(
        f"/api/v1/categories/{c2_id}",
        cookies={settings.SESSION_COOKIE_NAME: token1},
    )
    assert res_detail.status_code == 404


# ==============================================================================
# 4 & 5. Tạo danh mục cá nhân thành công và không thể giả mạo user_id
# ==============================================================================
def test_create_personal_category():
    user, token = create_user_and_session("user@example.com")

    payload = {
        "name": "Tiền cafe sáng",
        "type": "expense",
        "scope": "personal",
        "icon": "coffee",
        "color": "#EF4444",
    }
    res = client.post(
        "/api/v1/categories",
        json=payload,
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert res.status_code == 201
    created = res.json()
    assert created["name"] == "Tiền cafe sáng"
    assert created["scope"] == "personal"
    assert created["user_id"] == str(user.id)
    assert created["family_id"] is None
    assert created["is_default"] is False

    # Thử gửi kèm family_id khi scope='personal' -> 400 Bad Request
    fake_fam_id = str(uuid.uuid4())
    res_bad = client.post(
        "/api/v1/categories",
        json={**payload, "family_id": fake_fam_id},
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert res_bad.status_code == 400


# ==============================================================================
# 6 & 7 & 8. Danh mục gia đình: Owner/Editor tạo được, Viewer bị cấm, Người ngoài 404
# ==============================================================================
def test_family_category_permissions():
    owner, owner_token = create_user_and_session("owner@example.com")
    editor, editor_token = create_user_and_session("editor@example.com")
    viewer, viewer_token = create_user_and_session("viewer@example.com")
    _outsider, outsider_token = create_user_and_session("outsider@example.com")

    family = create_family_helper(owner.id, "Gia đình Tuấn Tú")
    add_family_member_helper(family.id, editor.id, "editor")
    add_family_member_helper(family.id, viewer.id, "viewer")

    # 1. Owner tạo danh mục gia đình thành công
    res_owner = client.post(
        "/api/v1/categories",
        json={
            "name": "Tiền chợ gia đình",
            "type": "expense",
            "scope": "family",
            "family_id": str(family.id),
        },
        cookies={settings.SESSION_COOKIE_NAME: owner_token},
    )
    assert res_owner.status_code == 201
    fam_cat_id = res_owner.json()["id"]

    # 2. Editor tạo danh mục gia đình thành công
    res_editor = client.post(
        "/api/v1/categories",
        json={
            "name": "Tiền điện nước chung",
            "type": "expense",
            "scope": "family",
            "family_id": str(family.id),
        },
        cookies={settings.SESSION_COOKIE_NAME: editor_token},
    )
    assert res_editor.status_code == 201

    # 3. Viewer tạo danh mục gia đình -> 403 Forbidden
    res_viewer = client.post(
        "/api/v1/categories",
        json={
            "name": "Quỹ mua sắm",
            "type": "expense",
            "scope": "family",
            "family_id": str(family.id),
        },
        cookies={settings.SESSION_COOKIE_NAME: viewer_token},
    )
    assert res_viewer.status_code == 403

    # 4. Viewer xem danh mục gia đình -> Thành công
    res_viewer_get = client.get(
        f"/api/v1/categories?family_id={family.id}",
        cookies={settings.SESSION_COOKIE_NAME: viewer_token},
    )
    assert res_viewer_get.status_code == 200
    assert len(res_viewer_get.json()) == 2

    # 5. Người ngoài (outsider) xem hoặc sửa -> 404 Not Found
    res_out_get = client.get(
        f"/api/v1/categories/{fam_cat_id}",
        cookies={settings.SESSION_COOKIE_NAME: outsider_token},
    )
    assert res_out_get.status_code == 404

    res_out_patch = client.patch(
        f"/api/v1/categories/{fam_cat_id}",
        json={"name": "Đổi tên trộm"},
        cookies={settings.SESSION_COOKIE_NAME: outsider_token},
    )
    assert res_out_patch.status_code == 404


# ==============================================================================
# 9. Cấm tạo hoặc chỉnh sửa danh mục system
# ==============================================================================
def test_system_category_protection():
    _user, token = create_user_and_session("user@example.com")
    sys_cat_id = uuid.uuid4()
    db = TestingSessionLocal()
    sys_cat = Category(
        id=sys_cat_id,
        name="Giáo dục",
        type="expense",
        scope="system",
        is_default=True,
    )
    db.add(sys_cat)
    db.commit()
    db.close()

    # User không thể sửa danh mục hệ thống
    res_patch = client.patch(
        f"/api/v1/categories/{sys_cat_id}",
        json={"name": "Học thêm"},
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert res_patch.status_code == 403

    # User không thể lưu trữ danh mục hệ thống
    res_archive = client.post(
        f"/api/v1/categories/{sys_cat_id}/archive",
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert res_archive.status_code == 403


# ==============================================================================
# 11 & 12. Kiểm tra tính hợp lệ của danh mục cha và chống vòng lặp (parent hierarchy)
# ==============================================================================
def test_parent_category_validation_and_cycle_prevention():
    user, token = create_user_and_session("user@example.com")
    parent_sys_id = uuid.uuid4()
    parent_income_id = uuid.uuid4()

    db = TestingSessionLocal()
    # Danh mục cha hệ thống
    parent_sys = Category(
        id=parent_sys_id,
        name="Ăn uống",
        type="expense",
        scope="system",
        is_default=True,
    )
    # Danh mục thu nhập hệ thống
    parent_income = Category(
        id=parent_income_id,
        name="Lương",
        type="income",
        scope="system",
        is_default=True,
    )
    db.add_all([parent_sys, parent_income])
    db.commit()
    db.close()

    # 1. Tạo con cá nhân với cha hệ thống cùng loại -> Thành công
    res_ok = client.post(
        "/api/v1/categories",
        json={
            "name": "Ăn vặt văn phòng",
            "type": "expense",
            "scope": "personal",
            "parent_id": str(parent_sys_id),
        },
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert res_ok.status_code == 201
    child_id = res_ok.json()["id"]

    # 2. Khác type giữa con (expense) và cha (income) -> 400 Bad Request
    res_diff_type = client.post(
        "/api/v1/categories",
        json={
            "name": "Chi tiêu sai",
            "type": "expense",
            "scope": "personal",
            "parent_id": str(parent_income_id),
        },
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert res_diff_type.status_code == 400

    # 3. Tạo con cấp 2
    res_sub = client.post(
        "/api/v1/categories",
        json={
            "name": "Bánh tráng trộn",
            "type": "expense",
            "scope": "personal",
            "parent_id": child_id,
        },
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert res_sub.status_code == 201
    sub_child_id = res_sub.json()["id"]

    # 4. Ngăn vòng lặp: Đặt cha của `child_id` là `sub_child_id`
    # Trong hàm _validate_parent_category đã có kiểm tra cycle
    db = TestingSessionLocal()
    from app.services.category_service import CategoryService

    with pytest.raises(Exception) as exc_info:
        CategoryService._validate_parent_category(
            db=db,
            parent_id=uuid.UUID(sub_child_id),
            child_type="expense",
            child_scope="personal",
            child_user_id=user.id,
            child_family_id=None,
            current_user=user,
            current_category_id=uuid.UUID(child_id),
        )
    assert exc_info.value.status_code == 400
    db.close()


# ==============================================================================
# 13. Lưu trữ (archive) và Khôi phục (restore)
# ==============================================================================
def test_archive_and_restore_category():
    _user, token = create_user_and_session("user@example.com")

    # Tạo danh mục
    res = client.post(
        "/api/v1/categories",
        json={"name": "Dự án phụ", "type": "income", "scope": "personal"},
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert res.status_code == 201
    cat_id = res.json()["id"]

    # Lưu trữ
    res_archive = client.post(
        f"/api/v1/categories/{cat_id}/archive",
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert res_archive.status_code == 200
    assert res_archive.json()["is_archived"] is True

    # Mặc định GET không thấy danh mục đã lưu trữ
    res_get = client.get(
        "/api/v1/categories",
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert len(res_get.json()) == 0

    # Khi include_archived=true thì thấy
    res_get_archived = client.get(
        "/api/v1/categories?include_archived=true",
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert len(res_get_archived.json()) == 1

    # Khôi phục
    res_restore = client.post(
        f"/api/v1/categories/{cat_id}/restore",
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert res_restore.status_code == 200
    assert res_restore.json()["is_archived"] is False


# ==============================================================================
# 15. Kiểm tra script seed_system_categories (idempotent, không tạo trùng)
# ==============================================================================
def test_seed_system_categories_idempotent():
    db = TestingSessionLocal()
    # Chạy lần 1
    stats1 = seed_system_categories(db)
    assert stats1["created"] > 0
    assert stats1["existing"] == 0

    # Chạy lần 2
    stats2 = seed_system_categories(db)
    assert stats2["created"] == 0
    assert stats2["existing"] == stats1["created"]
    db.close()
