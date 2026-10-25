import sys
import uuid
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import httpx

# pyrefly: ignore[missing-import]
from app.db.session import SessionLocal

# pyrefly: ignore[missing-import]
from app.models.user import User
from sqlalchemy import select

BASE_URL = "http://127.0.0.1:8000"


def verify_live_categories_api():
    print("=" * 60)
    print("KIỂM CHỨNG LIVE CATEGORIES API VỚI POSTGRESQL 18 THẬT")
    print("=" * 60)

    # 1. Kiểm tra /health/ready
    print("1. Kiểm tra health check ready...")
    res_ready = httpx.get(f"{BASE_URL}/health/ready", timeout=5.0)
    assert res_ready.status_code == 200, f"Health ready failed: {res_ready.text}"
    ready_data = res_ready.json()
    assert ready_data["status"] == "ok", "Status not ok!"
    assert ready_data["database"] == "connected", "Database not connected!"
    print("   -> Health check sẵn sàng, PostgreSQL kết nối thành công!")

    # 2. Kiểm tra truy cập khi chưa đăng nhập -> 401 Unauthorized
    print("2. Kiểm tra truy cập chưa đăng nhập...")
    res_unauth = httpx.get(f"{BASE_URL}/api/v1/categories", timeout=5.0)
    assert res_unauth.status_code == 401, f"Expected 401, got {res_unauth.status_code}"
    print("   -> Bị từ chối 401 Unauthorized chính xác!")

    # 3. Tạo một tài khoản test duy nhất để đăng nhập
    test_email = f"test_cat_live_{uuid.uuid4().hex[:6]}@example.com"
    test_password = "SecurePassword123!"
    print(f"3. Đăng ký & Đăng nhập tài khoản test {test_email}...")

    client = httpx.Client(base_url=BASE_URL, timeout=10.0)
    res_reg = client.post(
        "/api/v1/auth/register",
        json={"email": test_email, "password": test_password, "display_name": "Category Tester"},
    )
    assert res_reg.status_code == 201, f"Register failed: {res_reg.text}"

    res_login = client.post(
        "/api/v1/auth/login",
        json={"email": test_email, "password": test_password},
    )
    assert res_login.status_code == 200, f"Login failed: {res_login.text}"
    print("   -> Đăng ký và đăng nhập thành công, nhận cookie session!")

    test_user_id = None
    try:
        # 4. Gọi GET /api/v1/categories -> Kiểm tra danh mục vừa seed
        print("4. Gọi GET /api/v1/categories (toàn bộ danh mục được phép)...")
        res_cats = client.get("/api/v1/categories")
        assert res_cats.status_code == 200, f"Get categories failed: {res_cats.text}"
        cats = res_cats.json()
        assert len(cats) == 30, f"Expected 30 categories, got {len(cats)}"
        print(f"   -> API trả về đầy đủ {len(cats)} danh mục hệ thống vừa seed!")

        # 5. Lọc type=income
        print("5. Kiểm tra lọc type=income...")
        res_income = client.get("/api/v1/categories?type=income")
        assert res_income.status_code == 200
        income_cats = res_income.json()
        assert len(income_cats) == 6, f"Expected 6 income categories, got {len(income_cats)}"
        assert all(c["type"] == "income" for c in income_cats)
        print(f"   -> Lọc type=income chính xác ({len(income_cats)} danh mục)!")

        # 6. Lọc type=expense
        print("6. Kiểm tra lọc type=expense...")
        res_expense = client.get("/api/v1/categories?type=expense")
        assert res_expense.status_code == 200
        expense_cats = res_expense.json()
        assert len(expense_cats) == 24, f"Expected 24 expense categories, got {len(expense_cats)}"
        assert all(c["type"] == "expense" for c in expense_cats)
        print(f"   -> Lọc type=expense chính xác ({len(expense_cats)} danh mục)!")

        # 7. Lọc scope=system
        print("7. Kiểm tra lọc scope=system...")
        res_sys = client.get("/api/v1/categories?scope=system")
        assert res_sys.status_code == 200
        sys_cats = res_sys.json()
        assert len(sys_cats) == 30
        assert all(c["scope"] == "system" for c in sys_cats)
        assert all(c["user_id"] is None for c in sys_cats)
        assert all(c["family_id"] is None for c in sys_cats)
        print("   -> Lọc scope=system chính xác, không để lộ thông tin riêng tư!")

        # 8. Tạo thử 1 danh mục cá nhân và lấy chi tiết
        print("8. Thử nghiệm tạo danh mục cá nhân mới...")
        res_create = client.post(
            "/api/v1/categories",
            json={"name": "Chi tiêu thử nghiệm", "type": "expense", "scope": "personal"},
        )
        assert res_create.status_code == 201
        created_cat = res_create.json()
        print(f"   -> Tạo danh mục cá nhân thành công: id={created_cat['id']}")

        # 9. Lưu trữ (archive) và Khôi phục (restore)
        print("9. Kiểm tra lưu trữ và khôi phục...")
        res_arc = client.post(f"/api/v1/categories/{created_cat['id']}/archive")
        assert res_arc.status_code == 200
        assert res_arc.json()["is_archived"] is True

        res_res = client.post(f"/api/v1/categories/{created_cat['id']}/restore")
        assert res_res.status_code == 200
        assert res_res.json()["is_archived"] is False
        print("   -> Lưu trữ và khôi phục hoạt động hoàn hảo!")

    finally:
        # 10. Dọn dẹp an toàn: Vô hiệu hóa tài khoản test
        print("10. Dọn dẹp an toàn cho tài khoản test trong PostgreSQL...")
        with SessionLocal() as db:
            user = db.scalar(select(User).where(User.email == test_email))
            if user:
                test_user_id = user.id
                user.is_active = False
                db.commit()
                print(f"   -> Đã vô hiệu hóa (deactivated) test user id={test_user_id} an toàn.")

    print("=" * 60)
    print("✅ TOÀN BỘ CÁC BƯỚC KIỂM TRA LIVE API VỚI POSTGRESQL 18 ĐỀU ĐẠT 100%!")


if __name__ == "__main__":
    verify_live_categories_api()
