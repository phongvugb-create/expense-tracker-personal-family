import sys
import uuid
from pathlib import Path

import httpx

# Thêm backend vào sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from datetime import UTC, datetime

# pyrefly: ignore[missing-import]
from app.db.session import engine

# pyrefly: ignore[missing-import]
from app.models.auth_session import AuthSession

# pyrefly: ignore[missing-import]
from app.models.user import User
from sqlalchemy import select

API_BASE = "http://127.0.0.1:8000/api/v1"
TEST_EMAIL = f"test.integration.{uuid.uuid4().hex[:8]}@example.com"
TEST_PASSWORD = "StrongAuthPassword123!"
TEST_NAME = "Tester Integration"


def run_e2e_api_verification():
    print("=" * 60)
    print("BẮT ĐẦU KIỂM CHỨNG TOÀN DIỆN HTTP CLIENT + REAL DB SESSION")
    print(f"Target test email: {TEST_EMAIL}")
    print("=" * 60)

    # 1. Health checks
    with httpx.Client(base_url="http://127.0.0.1:8000") as client:
        r_live = client.get("/health/live")
        r_ready = client.get("/health/ready")
        print(f"1. Health Check Live: {r_live.status_code} -> {r_live.json()}")
        print(f"   Health Check Ready: {r_ready.status_code} -> {r_ready.json()}")
        assert r_live.status_code == 200
        assert r_ready.status_code == 200

    # Dùng client có cookie jar thực tế
    client = httpx.Client(base_url=API_BASE)

    try:
        # 2. Đăng ký tài khoản mới (POST /auth/register)
        r_reg = client.post(
            "/auth/register",
            json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
                "display_name": TEST_NAME,
            },
        )
        print(f"\n2. Register HTTP {r_reg.status_code}: {r_reg.json()}")
        assert r_reg.status_code == 201
        reg_data = r_reg.json()
        assert reg_data["email"] == TEST_EMAIL.lower()
        assert "password" not in reg_data
        assert "password_hash" not in reg_data
        assert "token" not in reg_data
        assert "token_hash" not in reg_data
        user_id = uuid.UUID(reg_data["id"])

        # 3. Đăng ký trùng email bị từ chối
        r_dup = client.post(
            "/auth/register",
            json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
                "display_name": "Another Name",
            },
        )
        print(f"\n3. Duplicate Register HTTP {r_dup.status_code}: {r_dup.json()}")
        assert r_dup.status_code == 400
        assert "đã được đăng ký" in r_dup.json()["detail"]

        # 4. Đăng nhập sai mật khẩu bị từ chối HTTP 401
        r_wrong = client.post(
            "/auth/login",
            json={
                "email": TEST_EMAIL,
                "password": "WrongPassword999!",
            },
        )
        print(f"\n4. Wrong password login HTTP {r_wrong.status_code}: {r_wrong.json()}")
        assert r_wrong.status_code == 401
        assert "Email hoặc mật khẩu không chính xác" in r_wrong.json()["detail"]

        # 5. Đăng nhập đúng mật khẩu thành công (POST /auth/login)
        r_login = client.post(
            "/auth/login",
            json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD,
            },
        )
        print(f"\n5. Correct login HTTP {r_login.status_code}: {r_login.json()}")
        assert r_login.status_code == 200
        login_data = r_login.json()
        assert login_data["email"] == TEST_EMAIL.lower()
        assert "password_hash" not in login_data

        # Kiểm tra cookie session được thiết lập
        assert "session_token" in client.cookies
        session_token_value = client.cookies["session_token"]
        print(f"   Cookie session_token nhận được: độ dài {len(session_token_value)} chars")

        # 6. Gọi GET /auth/me với cookie session
        r_me = client.get("/auth/me")
        print(f"\n6. GET /auth/me HTTP {r_me.status_code}: {r_me.json()}")
        assert r_me.status_code == 200
        me_data = r_me.json()
        assert me_data["id"] == str(user_id)
        assert me_data["email"] == TEST_EMAIL.lower()
        assert "password_hash" not in me_data
        assert "token_hash" not in me_data

        # 7. Kiểm tra dữ liệu thực tế trong PostgreSQL
        from sqlalchemy.orm import Session as DbSession
        with DbSession(engine) as session:
            db_user = session.get(User, user_id)
            print("\n7. Xác minh PostgreSQL - Bảng users:")
            print(f"   - User ID: {db_user.id}")
            print(f"   - Email: {db_user.email}")
            print(f"   - Password hash format: {db_user.password_hash[:15]}... (Argon2id)")

            # Kiểm tra session trong auth_sessions
            db_sessions = session.scalars(
                select(AuthSession).where(AuthSession.user_id == user_id)
            ).all()
            print("   Xác minh PostgreSQL - Bảng auth_sessions:")
            print(f"   - Số lượng sessions: {len(db_sessions)}")
            for s in db_sessions:
                print(f"     Session ID: {s.id}")
                print(f"     Token hash: {s.token_hash[:15]}... (SHA-256)")
                print(f"     Is revoked: {s.is_revoked}")
                print(f"     Is expired: {s.is_expired}")
                assert s.token_hash != session_token_value  # Chỉ hash được lưu!
                assert s.is_revoked is False

        # 8. Đăng xuất (POST /auth/logout)
        r_logout = client.post("/auth/logout")
        print(f"\n8. POST /auth/logout HTTP {r_logout.status_code}: {r_logout.json()}")
        assert r_logout.status_code == 200
        assert r_logout.json()["message"] == "Đăng xuất thành công."

        # 9. Gọi lại /auth/me bằng cookie cũ phải bị từ chối HTTP 401
        # Set lại cookie cũ bằng tay để thử tấn công replay
        client.cookies.set("session_token", session_token_value)
        r_me_after = client.get("/auth/me")
        print(f"\n9. GET /auth/me sau logout HTTP {r_me_after.status_code}: {r_me_after.json()}")
        assert r_me_after.status_code == 401
        assert "hết hạn" in r_me_after.json()["detail"] or "không hợp lệ" in r_me_after.json()["detail"]

        # 10. Xác minh session trong PostgreSQL đã bị thu hồi (revoked_at IS NOT NULL)
        with DbSession(engine) as session:
            revoked_sessions = session.scalars(
                select(AuthSession).where(AuthSession.user_id == user_id)
            ).all()
            print("\n10. Xác minh PostgreSQL sau logout:")
            for s in revoked_sessions:
                print(f"    - Session ID: {s.id}, revoked_at: {s.revoked_at}, is_revoked: {s.is_revoked}")
                assert s.is_revoked is True

            # Xử lý dọn dẹp an toàn: Đánh dấu xóa mềm test user (deleted_at) để không làm bẩn dữ liệu
            u = session.get(User, user_id)
            if u:
                u.deleted_at = datetime.now(UTC)
                u.is_active = False
                session.commit()
            print(f"    - Đã soft-delete an toàn test user {user_id} (deleted_at gắn mốc UTC, is_active=false).")

        print("\n" + "=" * 60)
        print("TẤT CẢ 10 BƯỚC KIỂM CHỨNG HTTP CLIENT & POSTGRESQL ĐÃ HOÀN TẤT THÀNH CÔNG!")
        print("=" * 60)

    finally:
        client.close()


if __name__ == "__main__":
    run_e2e_api_verification()
