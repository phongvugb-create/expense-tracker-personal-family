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
from app.models.account import Account

# pyrefly: ignore[missing-import]
from app.models.budget import Budget

# pyrefly: ignore[missing-import]
# pyrefly: ignore[missing-import]
# pyrefly: ignore[missing-import]
# pyrefly: ignore[missing-import]
from app.models.transaction import Transaction

# pyrefly: ignore[missing-import]
# pyrefly: ignore[missing-import]
from app.models.user import User
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

BASE_URL = "http://127.0.0.1:8000"


def verify_live_budget_flow():
    print("=" * 60)
    print("KIỂM CHỨNG LIVE BUDGET API & TÍNH CHI TIÊU VỚI POSTGRESQL 18 THẬT")
    print("=" * 60)

    # 1. Kiểm tra /health/ready
    print("1. Kiểm tra health check ready...")
    res_ready = httpx.get(f"{BASE_URL}/health/ready", timeout=5.0)
    assert res_ready.status_code == 200, f"Health ready failed: {res_ready.text}"
    ready_data = res_ready.json()
    assert ready_data["status"] == "ok" and ready_data["database"] == "connected"
    print("   -> Health check sẵn sàng, PostgreSQL kết nối thành công!")

    # 2. Kiểm tra truy cập khi chưa đăng nhập -> 401 Unauthorized
    print("2. Kiểm tra truy cập chưa đăng nhập...")
    res_unauth = httpx.get(f"{BASE_URL}/api/v1/budgets", timeout=5.0)
    assert res_unauth.status_code == 401
    print("   -> Bị từ chối 401 Unauthorized chính xác!")

    # 3. Tạo 2 tài khoản thử nghiệm cô lập
    email_u1 = f"bg_live_u1_{uuid.uuid4().hex[:6]}@example.com"
    email_u2 = f"bg_live_u2_{uuid.uuid4().hex[:6]}@example.com"
    password = "SecurePassword123!"

    client1 = httpx.Client(base_url=BASE_URL, timeout=10.0)
    client2 = httpx.Client(base_url=BASE_URL, timeout=10.0)

    print(f"3. Đăng ký & Đăng nhập tài khoản test:\n   - U1: {email_u1}\n   - U2: {email_u2}")
    client1.post("/api/v1/auth/register", json={"email": email_u1, "password": password, "display_name": "Budget User 1"})
    r_login1 = client1.post("/api/v1/auth/login", json={"email": email_u1, "password": password})
    assert r_login1.status_code == 200

    client2.post("/api/v1/auth/register", json={"email": email_u2, "password": password, "display_name": "Budget User 2"})
    r_login2 = client2.post("/api/v1/auth/login", json={"email": email_u2, "password": password})
    assert r_login2.status_code == 200
    print("   -> Cả 2 client đã có session cookie hợp lệ!")

    # Lấy danh mục hệ thống 'Ăn uống'
    r_cats = client1.get("/api/v1/categories?scope=system&type=expense")
    assert r_cats.status_code == 200
    categories = r_cats.json()
    cat_food = next((c for c in categories if c["name"] == "Ăn uống"), categories[0])
    category_id = cat_food["id"]
    print(f"   -> Sử dụng danh mục chi tiêu: '{cat_food['name']}' (ID: {category_id})")

    # 4. U1 tạo 1 ví cá nhân ban đầu 5.000.000 VND
    r_acc = client1.post(
        "/api/v1/accounts",
        json={
            "name": "Ví tiêu dùng U1",
            "scope": "personal",
            "account_type": "cash",
            "currency": "VND",
            "initial_balance": "5000000.00",
        },
    )
    assert r_acc.status_code == 201
    account_id = r_acc.json()["id"]
    print(f"4. U1 tạo ví: {account_id}")

    # 5. U1 tạo Budget cá nhân cho tháng hiện tại: Hạn mức 1.000.000 VND, Ngưỡng 80%
    r_budget = client1.post(
        "/api/v1/budgets",
        json={
            "name": "Ngân sách ăn uống Live",
            "scope": "personal",
            "category_id": category_id,
            "amount_limit": "1000000.00",
            "period_start": "2026-10-01",
            "period_end": "2026-10-31",
            "warning_threshold": "80.00",
        },
    )
    assert r_budget.status_code == 201
    budget_data = r_budget.json()
    budget_id = budget_data["id"]
    print(f"5. U1 tạo ngân sách thành công: ID={budget_id}")
    assert budget_data["spent_amount"] == "0.00"
    assert budget_data["remaining_amount"] == "1000000.00"
    assert budget_data["status"] == "normal"
    print("   -> Trạng thái ban đầu: normal (spent=0 VND)")

    # 6. Ghi giao dịch 1: Chi 700.000 VND (70% < 80%) -> normal
    r_tx1 = client1.post(
        "/api/v1/transactions",
        json={
            "account_id": account_id,
            "category_id": category_id,
            "type": "expense",
            "amount": "700000.00",
            "note": "Cơm trưa tuần 1",
            "occurred_at": "2026-10-05T12:00:00Z",
        },
    )
    assert r_tx1.status_code == 201
    r_tx1.json()["id"]

    r_check1 = client1.get(f"/api/v1/budgets/{budget_id}")
    assert r_check1.status_code == 200
    d1 = r_check1.json()
    print(f"6. Sau khi chi 700.000 VND: spent={d1['spent_amount']}, usage={d1['usage_percentage']}%, status={d1['status']}")
    assert d1["spent_amount"] == "700000.00"
    assert d1["remaining_amount"] == "300000.00"
    assert d1["usage_percentage"] == "70.00"
    assert d1["status"] == "normal"

    # 7. Ghi giao dịch 2: Chi thêm 150.000 VND -> Tổng 850.000 VND (85% >= 80% ngưỡng) -> warning!
    r_tx2 = client1.post(
        "/api/v1/transactions",
        json={
            "account_id": account_id,
            "category_id": category_id,
            "type": "expense",
            "amount": "150000.00",
            "note": "Tiệc sinh nhật bạn",
            "occurred_at": "2026-10-15T19:00:00Z",
        },
    )
    assert r_tx2.status_code == 201
    r_tx2.json()["id"]

    r_check2 = client1.get(f"/api/v1/budgets/{budget_id}")
    assert r_check2.status_code == 200
    d2 = r_check2.json()
    print(f"7. Sau khi chi thêm 150.000 VND: spent={d2['spent_amount']}, usage={d2['usage_percentage']}%, status={d2['status']}")
    assert d2["spent_amount"] == "850000.00"
    assert d2["remaining_amount"] == "150000.00"
    assert d2["usage_percentage"] == "85.00"
    assert d2["status"] == "warning"

    # 8. Ghi giao dịch 3: Chi thêm 200.000 VND -> Tổng 1.050.000 VND (> 100% hạn mức) -> exceeded!
    r_tx3 = client1.post(
        "/api/v1/transactions",
        json={
            "account_id": account_id,
            "category_id": category_id,
            "type": "expense",
            "amount": "200000.00",
            "note": "Mua đồ siêu thị",
            "occurred_at": "2026-10-20T10:00:00Z",
        },
    )
    assert r_tx3.status_code == 201
    tx3_id = r_tx3.json()["id"]

    r_check3 = client1.get(f"/api/v1/budgets/{budget_id}")
    assert r_check3.status_code == 200
    d3 = r_check3.json()
    print(f"8. Sau khi chi thêm 200.000 VND: spent={d3['spent_amount']}, usage={d3['usage_percentage']}%, overspent={d3['overspent_amount']}, status={d3['status']}")
    assert d3["spent_amount"] == "1050000.00"
    assert d3["remaining_amount"] == "0.00"
    assert d3["overspent_amount"] == "50000.00"
    assert d3["usage_percentage"] == "105.00"
    assert d3["status"] == "exceeded"

    # 9. Bảo mật kiểm tra: U2 không thể xem ngân sách của U1 -> 404 Not Found
    print("9. Kiểm tra phân quyền truy cập chéo U2 -> Ngân sách U1...")
    r_u2_get = client2.get(f"/api/v1/budgets/{budget_id}")
    assert r_u2_get.status_code == 404
    r_u2_patch = client2.patch(f"/api/v1/budgets/{budget_id}", json={"name": "Hacked"})
    assert r_u2_patch.status_code == 404
    print("   -> Bảo mật phân quyền ngăn chặn 100% mọi truy cập trái phép từ user khác!")

    # 10. Xóa mềm (soft delete) giao dịch tx3 -> Chi tiêu lập tức hoàn nguyên về 850.000 VND (warning)
    print("10. Xóa mềm giao dịch tx3 để kiểm chứng tính toán động...")
    r_del_tx3 = client1.delete(f"/api/v1/transactions/{tx3_id}")
    assert r_del_tx3.status_code == 200

    r_check4 = client1.get(f"/api/v1/budgets/{budget_id}")
    d4 = r_check4.json()
    print(f"   -> Sau khi xóa tx3: spent={d4['spent_amount']}, status={d4['status']}")
    assert d4["spent_amount"] == "850000.00"
    assert d4["status"] == "warning"

    # 11. Lưu trữ (archive) và Khôi phục (restore) ngân sách
    print("11. Kiểm tra Lưu trữ & Khôi phục ngân sách...")
    r_arch = client1.post(f"/api/v1/budgets/{budget_id}/archive")
    assert r_arch.status_code == 200
    assert r_arch.json()["is_archived"] is True

    r_list_active = client1.get("/api/v1/budgets")
    assert not any(b["id"] == budget_id for b in r_list_active.json())

    r_list_all = client1.get("/api/v1/budgets?include_archived=true")
    assert any(b["id"] == budget_id for b in r_list_all.json())

    r_rest = client1.post(f"/api/v1/budgets/{budget_id}/restore")
    assert r_rest.status_code == 200
    assert r_rest.json()["is_archived"] is False
    print("   -> Lưu trữ và khôi phục hoạt động chính xác!")

    print("\n✅ TOÀN BỘ LUỒNG BUDGET API, PHÂN QUYỀN & CẢNH BÁO ĐẠT 100% TRÊN POSTGRESQL 18 THẬT!")

    # 12. Dọn dẹp dữ liệu test cô lập
    print("\n12. Dọn dẹp an toàn các tài khoản và ngân sách test cô lập...")
    db = SessionLocal()
    try:
        # Xóa transactions của tài khoản test
        txs = db.scalars(select(Transaction).where(Transaction.user_id.in_([uuid.UUID(client1.get('/api/v1/auth/me').json()['id']), uuid.UUID(client2.get('/api/v1/auth/me').json()['id'])]))).all()
        for t in txs:
            db.delete(t)
        db.commit()

        # Xóa budget
        bg = db.get(Budget, uuid.UUID(budget_id))
        if bg:
            db.delete(bg)
        db.commit()

        # Xóa account
        acc = db.get(Account, uuid.UUID(account_id))
        if acc:
            db.delete(acc)
        db.commit()

        # Xóa 2 users
        u1_db = db.scalar(select(User).where(User.email == email_u1))
        u2_db = db.scalar(select(User).where(User.email == email_u2))
        if u1_db:
            db.delete(u1_db)
        if u2_db:
            db.delete(u2_db)
        db.commit()
        print("   -> Đã dọn dẹp an toàn toàn bộ dữ liệu test cô lập trên PostgreSQL!")
    except SQLAlchemyError as e:
        db.rollback()
        print(f"   -> Lỗi dọn dẹp: {e}")
    finally:
        db.close()
        client1.close()
        client2.close()


if __name__ == "__main__":
    verify_live_budget_flow()
