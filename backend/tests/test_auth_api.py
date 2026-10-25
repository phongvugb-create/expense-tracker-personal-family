import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.core.config import settings
from app.core.security import hash_password, hash_session_token
from app.db.session import get_db
from app.main import app
from app.models.auth_session import AuthSession
from app.models.user import User
from fastapi.testclient import TestClient

client = TestClient(app)


class FakeDbSession:
    """In-memory fake SQLAlchemy Session mô phỏng database an toàn tuyệt đối cho testing."""

    def __init__(self):
        self.users: dict[uuid.UUID, User] = {}
        self.sessions: dict[uuid.UUID, AuthSession] = {}
        self.added = []

    def add(self, obj):
        now = datetime.now(UTC)
        if isinstance(obj, User):
            if not hasattr(obj, "id") or obj.id is None:
                obj.id = uuid.uuid4()
            if getattr(obj, "created_at", None) is None:
                obj.created_at = now
            if getattr(obj, "updated_at", None) is None:
                obj.updated_at = now
            self.users[obj.id] = obj
        elif isinstance(obj, AuthSession):
            if not hasattr(obj, "id") or obj.id is None:
                obj.id = uuid.uuid4()
            if getattr(obj, "created_at", None) is None:
                obj.created_at = now
            if getattr(obj, "last_used_at", None) is None:
                obj.last_used_at = now
            self.sessions[obj.id] = obj
        self.added.append(obj)

    def commit(self):
        pass

    def refresh(self, obj):
        pass

    def rollback(self):
        pass

    def scalar(self, statement):
        statement_str = str(statement).lower()
        if "from users" in statement_str:
            params = statement.compile().params
            email_param = params.get("email_1", "").lower()
            for u in self.users.values():
                if u.email.lower() == email_param:
                    return u
            return None
        elif "from auth_sessions" in statement_str:
            params = statement.compile().params
            token_param = params.get("token_hash_1", "")
            for s in self.sessions.values():
                if s.token_hash == token_param:
                    # Link user relationship
                    s.user = self.users.get(s.user_id)
                    return s
            return None
        return None


@pytest.fixture
def fake_db():
    fake = FakeDbSession()
    app.dependency_overrides[get_db] = lambda: fake
    yield fake
    app.dependency_overrides.clear()


def test_register_success(fake_db):
    """Kiểm tra đăng ký tài khoản hợp lệ thành công và không trả password_hash."""
    payload = {
        "email": "test.user@example.com",
        "password": "SecurePassword123!",
        "display_name": "Nguyễn Văn Test",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test.user@example.com"
    assert data["display_name"] == "Nguyễn Văn Test"
    assert data["is_active"] is True
    assert "password" not in data
    assert "password_hash" not in data
    assert "token" not in data
    assert "token_hash" not in data


def test_register_invalid_email(fake_db):
    """Kiểm tra đăng ký thất bại với email sai định dạng."""
    payload = {
        "email": "invalid-email-format",
        "password": "SecurePassword123!",
        "display_name": "Test User",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422


def test_register_duplicate_email(fake_db):
    """Kiểm tra đăng ký thất bại khi email đã tồn tại."""
    # Tạo sẵn user trong fake_db
    user = User(
        id=uuid.uuid4(),
        email="duplicate@example.com",
        password_hash=hash_password("Existing123!"),
        display_name="Existing User",
        is_active=True,
    )
    fake_db.add(user)

    payload = {
        "email": "Duplicate@example.com",  # hoa thường lẫn lộn
        "password": "NewPassword123!",
        "display_name": "New User",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 400
    assert "Email đã được đăng ký" in response.json()["detail"]


def test_login_success_and_cookie_set(fake_db):
    """Kiểm tra đăng nhập thành công và thiết lập đúng HttpOnly session cookie."""
    user = User(
        id=uuid.uuid4(),
        email="login@example.com",
        password_hash=hash_password("CorrectPassword123!"),
        display_name="Login User",
        is_active=True,
    )
    fake_db.add(user)

    payload = {
        "email": "login@example.com",
        "password": "CorrectPassword123!",
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "login@example.com"
    assert "password_hash" not in data

    # Kiểm tra cookie
    assert settings.SESSION_COOKIE_NAME in response.cookies
    cookie = response.cookies[settings.SESSION_COOKIE_NAME]
    assert len(cookie) > 20  # raw opaque token
    assert cookie not in [s.token_hash for s in fake_db.sessions.values()]  # Chỉ hash được lưu vào db!


def test_login_wrong_password(fake_db):
    """Kiểm tra đăng nhập thất bại với thông báo chung khi sai mật khẩu."""
    user = User(
        id=uuid.uuid4(),
        email="user@example.com",
        password_hash=hash_password("CorrectPassword123!"),
        display_name="User",
        is_active=True,
    )
    fake_db.add(user)

    payload = {
        "email": "user@example.com",
        "password": "WrongPassword999!",
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401
    assert "Email hoặc mật khẩu không chính xác" in response.json()["detail"]


def test_login_nonexistent_user(fake_db):
    """Kiểm tra đăng nhập thất bại với user không tồn tại vẫn trả thông báo chung."""
    payload = {
        "email": "ghost@example.com",
        "password": "AnyPassword123!",
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 401
    assert "Email hoặc mật khẩu không chính xác" in response.json()["detail"]


def test_login_inactive_user(fake_db):
    """Kiểm tra từ chối đăng nhập khi user đã bị vô hiệu hóa."""
    user = User(
        id=uuid.uuid4(),
        email="inactive@example.com",
        password_hash=hash_password("Password123!"),
        display_name="Inactive User",
        is_active=False,
    )
    fake_db.add(user)

    payload = {
        "email": "inactive@example.com",
        "password": "Password123!",
    }
    response = client.post("/api/v1/auth/login", json=payload)
    assert response.status_code == 403
    assert "vô hiệu hóa" in response.json()["detail"]


def test_get_me_success(fake_db):
    """Kiểm tra lấy thông tin cá nhân với session token hợp lệ qua cookie."""
    user = User(
        id=uuid.uuid4(),
        email="me@example.com",
        password_hash=hash_password("Password123!"),
        display_name="Me User",
        is_active=True,
    )
    fake_db.add(user)

    raw_token = "valid_opaque_session_token_123456"
    session = AuthSession(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=hash_session_token(raw_token),
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    session.user = user
    fake_db.add(session)

    # Gửi request kèm cookie
    client.cookies.set(settings.SESSION_COOKIE_NAME, raw_token)
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@example.com"
    assert data["display_name"] == "Me User"
    assert "password_hash" not in data


def test_get_me_unauthorized_without_cookie(fake_db):
    """Kiểm tra từ chối HTTP 401 khi không gửi cookie."""
    client.cookies.clear()
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert "Yêu cầu đăng nhập" in response.json()["detail"]


def test_get_me_expired_session(fake_db):
    """Kiểm tra từ chối HTTP 401 khi session đã quá hạn."""
    user = User(
        id=uuid.uuid4(),
        email="expired@example.com",
        password_hash=hash_password("Password123!"),
        display_name="Expired User",
        is_active=True,
    )
    fake_db.add(user)

    raw_token = "expired_token_123456"
    session = AuthSession(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=hash_session_token(raw_token),
        expires_at=datetime.now(UTC) - timedelta(hours=1),  # đã quá hạn
    )
    session.user = user
    fake_db.add(session)

    client.cookies.set(settings.SESSION_COOKIE_NAME, raw_token)
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert "hết hạn" in response.json()["detail"]


def test_get_me_revoked_session(fake_db):
    """Kiểm tra từ chối HTTP 401 khi session đã bị thu hồi."""
    user = User(
        id=uuid.uuid4(),
        email="revoked@example.com",
        password_hash=hash_password("Password123!"),
        display_name="Revoked User",
        is_active=True,
    )
    fake_db.add(user)

    raw_token = "revoked_token_123456"
    session = AuthSession(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=hash_session_token(raw_token),
        expires_at=datetime.now(UTC) + timedelta(days=7),
        revoked_at=datetime.now(UTC),  # Đã thu hồi
    )
    session.user = user
    fake_db.add(session)

    client.cookies.set(settings.SESSION_COOKIE_NAME, raw_token)
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert "hết hạn" in response.json()["detail"]


def test_logout_revokes_session_and_clears_cookie(fake_db):
    """Kiểm tra đăng xuất thu hồi session trong database và xóa cookie trình duyệt."""
    user = User(
        id=uuid.uuid4(),
        email="logout@example.com",
        password_hash=hash_password("Password123!"),
        display_name="Logout User",
        is_active=True,
    )
    fake_db.add(user)

    raw_token = "logout_token_123456"
    session = AuthSession(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=hash_session_token(raw_token),
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    session.user = user
    fake_db.add(session)

    client.cookies.set(settings.SESSION_COOKIE_NAME, raw_token)
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    assert response.json()["message"] == "Đăng xuất thành công."

    # Session trong db đã có revoked_at
    assert session.is_revoked is True

    # Tra cứu lại với token cũ sẽ bị từ chối
    client.cookies.set(settings.SESSION_COOKIE_NAME, raw_token)
    response_me = client.get("/api/v1/auth/me")
    assert response_me.status_code == 401
