import sys
import uuid
from decimal import Decimal
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import httpx
from app.db.session import SessionLocal
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.user import User
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

BASE_URL = "http://127.0.0.1:8000"


def verify_live_transaction_flow():
    print("=" * 60)
    print("KIỂM CHỨNG LIVE TRANSACTION FLOW VỚI POSTGRESQL 18 THẬT")
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
    res_unauth = httpx.get(f"{BASE_URL}/api/v1/transactions", timeout=5.0)
    assert res_unauth.status_code == 401
    print("   -> Bị từ chối 401 Unauthorized chính xác!")

    # 3. Tạo tài khoản test 1 và test 2 (để kiểm tra phân quyền truy cập chéo)
    email_u1 = f"tx_live_u1_{uuid.uuid4().hex[:6]}@example.com"
    email_u2 = f"tx_live_u2_{uuid.uuid4().hex[:6]}@example.com"
    password = "SecurePassword123!"

    client1 = httpx.Client(base_url=BASE_URL, timeout=10.0)
    client2 = httpx.Client(base_url=BASE_URL, timeout=10.0)

    print(f"3. Đăng ký & Đăng nhập tài khoản test:\n   - U1: {email_u1}\n   - U2: {email_u2}")
    client1.post("/api/v1/auth/register", json={"email": email_u1, "password": password, "display_name": "User One"})
    client1.post("/api/v1/auth/login", json={"email": email_u1, "password": password})

    client2.post("/api/v1/auth/register", json={"email": email_u2, "password": password, "display_name": "User Two"})
    client2.post("/api/v1/auth/login", json={"email": email_u2, "password": password})
    print("   -> Cả 2 client đã có session cookie hợp lệ!")

    account_id = None
    account2_id = None

    try:
        # Lấy danh mục hệ thống
        res_cats = client1.get("/api/v1/categories?scope=system")
        assert res_cats.status_code == 200
        cats = res_cats.json()
        salary_cat = next((c for c in cats if c["type"] == "income"), None)
        food_cat = next((c for c in cats if c["type"] == "expense"), None)
        assert salary_cat is not None, "Không tìm thấy danh mục thu nhập hệ thống!"
        assert food_cat is not None, "Không tìm thấy danh mục chi tiêu hệ thống!"
        print(f"   -> Sử dụng danh mục hệ thống: Thu nhập='{salary_cat['name']}', Chi tiêu='{food_cat['name']}'")

        # 4. U1 tạo một ví cá nhân với số dư ban đầu 1,000,000 VND
        print("4. U1 tạo ví cá nhân ban đầu 1,000,000 VND...")
        res_acc = client1.post(
            "/api/v1/accounts",
            json={
                "name": "Ví chính U1",
                "scope": "personal",
                "account_type": "bank",
                "currency": "VND",
                "initial_balance": "1000000.00",
            },
        )
        assert res_acc.status_code == 201, f"Tạo ví thất bại: {res_acc.text}"
        acc_data = res_acc.json()
        account_id = acc_data["id"]
        assert Decimal(acc_data["current_balance"]) == Decimal("1000000.00")
        print(f"   -> Ví tạo thành công, số dư ban đầu: {acc_data['current_balance']} VND")

        # U2 tạo một ví riêng
        res_acc2 = client2.post(
            "/api/v1/accounts",
            json={
                "name": "Ví riêng U2",
                "scope": "personal",
                "account_type": "cash",
                "currency": "VND",
                "initial_balance": "500000.00",
            },
        )
        account2_id = res_acc2.json()["id"]

        # 5. U1 tạo giao dịch income +500,000 VND
        print("5. U1 tạo giao dịch thu nhập (+500,000 VND)...")
        res_tx_inc = client1.post(
            "/api/v1/transactions",
            json={
                "account_id": account_id,
                "category_id": salary_cat["id"],
                "type": "income",
                "amount": "500000.00",
                "note": "Lương tháng",
            },
        )
        assert res_tx_inc.status_code == 201, f"Tạo thu nhập thất bại: {res_tx_inc.text}"
        tx_inc = res_tx_inc.json()
        print(f"   -> Tạo thu nhập thành công, tx_id={tx_inc['id']}")

        # Kiểm tra số dư ví U1 -> Phải là 1,500,000 VND
        res_acc_chk1 = client1.get(f"/api/v1/accounts/{account_id}")
        assert Decimal(res_acc_chk1.json()["current_balance"]) == Decimal("1500000.00")
        print(f"   -> Số dư ví sau thu nhập: {res_acc_chk1.json()['current_balance']} VND (Chính xác +500,000!)")

        # 6. U1 tạo giao dịch expense -200,000 VND
        print("6. U1 tạo giao dịch chi tiêu (-200,000 VND)...")
        res_tx_exp = client1.post(
            "/api/v1/transactions",
            json={
                "account_id": account_id,
                "category_id": food_cat["id"],
                "type": "expense",
                "amount": "200000.00",
                "note": "Đi siêu thị",
            },
        )
        assert res_tx_exp.status_code == 201, f"Tạo chi tiêu thất bại: {res_tx_exp.text}"
        tx_exp = res_tx_exp.json()
        print(f"   -> Tạo chi tiêu thành công, tx_id={tx_exp['id']}")

        # Kiểm tra số dư ví U1 -> Phải là 1,300,000 VND
        res_acc_chk2 = client1.get(f"/api/v1/accounts/{account_id}")
        assert Decimal(res_acc_chk2.json()["current_balance"]) == Decimal("1300000.00")
        print(f"   -> Số dư ví sau chi tiêu: {res_acc_chk2.json()['current_balance']} VND (Chính xác -200,000!)")

        # 7. U2 không thể xem hoặc tạo giao dịch trên ví của U1 (Kiểm tra bảo mật phân quyền)
        print("7. Kiểm tra U2 truy cập ví U1...")
        res_u2_create = client2.post(
            "/api/v1/transactions",
            json={
                "account_id": account_id,
                "category_id": food_cat["id"],
                "type": "expense",
                "amount": "10000.00",
            },
        )
        assert res_u2_create.status_code == 404, f"U2 không được phép ghi: {res_u2_create.status_code}"

        res_u2_view = client2.get(f"/api/v1/transactions/{tx_inc['id']}")
        assert res_u2_view.status_code == 404, f"U2 không được phép xem: {res_u2_view.status_code}"

        res_u2_list = client2.get("/api/v1/transactions")
        assert len(res_u2_list.json()) == 0, "U2 không được thấy giao dịch của U1!"
        print("   -> Phân quyền cá nhân bảo vệ tuyệt đối: U2 bị chặn 404 hoàn toàn!")

        # 8. Cập nhật giao dịch chi tiêu (sửa amount từ 200,000 -> 300,000)
        print("8. U1 cập nhật giao dịch chi tiêu từ 200,000 thành 300,000 VND...")
        res_patch = client1.patch(
            f"/api/v1/transactions/{tx_exp['id']}",
            json={"amount": "300000.00", "note": "Siêu thị + hoa quả"},
        )
        assert res_patch.status_code == 200
        assert Decimal(res_patch.json()["amount"]) == Decimal("300000.00")

        # Số dư phải là 1,000,000 + 500,000 - 300,000 = 1,200,000 VND
        res_acc_chk3 = client1.get(f"/api/v1/accounts/{account_id}")
        assert Decimal(res_acc_chk3.json()["current_balance"]) == Decimal("1200000.00")
        print(f"   -> Cập nhật thành công, số dư tự động cập nhật: {res_acc_chk3.json()['current_balance']} VND!")

        # 9. Xóa mềm giao dịch chi tiêu
        print("9. Xóa mềm giao dịch chi tiêu...")
        res_del = client1.delete(f"/api/v1/transactions/{tx_exp['id']}")
        assert res_del.status_code == 200, f"Expected 200, got {res_del.status_code}"
        del_data = res_del.json()
        assert "message" in del_data
        print(f"   -> Xóa mềm thành công: {del_data['message']}!")

        # Kiểm tra danh sách mặc định không còn tx_exp
        res_list_after = client1.get("/api/v1/transactions")
        ids = [t["id"] for t in res_list_after.json()]
        assert tx_exp["id"] not in ids, "Giao dịch đã xóa mềm không được xuất hiện trong list!"
        assert tx_inc["id"] in ids
        print("   -> Giao dịch đã tự động bị loại khỏi danh sách giao dịch hoạt động!")

        # Số dư phải tự động phục hồi về 1,500,000 VND (loại bỏ chi tiêu đã xóa)
        res_acc_chk4 = client1.get(f"/api/v1/accounts/{account_id}")
        assert Decimal(res_acc_chk4.json()["current_balance"]) == Decimal("1500000.00")
        print(f"   -> Số dư ví sau khi xóa mềm: {res_acc_chk4.json()['current_balance']} VND (Phục hồi chính xác!)")

        # Không thể sửa giao dịch đã xóa mềm
        res_patch_del = client1.patch(
            f"/api/v1/transactions/{tx_exp['id']}",
            json={"amount": "50000.00"},
        )
        assert res_patch_del.status_code == 404
        print("   -> Không thể sửa giao dịch đã xóa mềm (HTTP 404)!")

        print("\n✅ TOÀN BỘ LUỒNG NGHIỆP VỤ TRANSACTION ĐẠT 100% TRÊN POSTGRESQL 18 THẬT!")

    finally:
        # Dọn dẹp dữ liệu test cô lập
        print("\n10. Dọn dẹp dữ liệu test cô lập trên PostgreSQL...")
        db = SessionLocal()
        try:
            db_u1 = db.scalar(select(User).where(User.email == email_u1))
            db_u2 = db.scalar(select(User).where(User.email == email_u2))

            # Xóa các giao dịch của test accounts
            if account_id:
                acc_uuid = uuid.UUID(account_id)
                db.query(Transaction).filter(Transaction.account_id == acc_uuid).delete()
                db.query(Account).filter(Account.id == acc_uuid).delete()

            if account2_id:
                acc2_uuid = uuid.UUID(account2_id)
                db.query(Transaction).filter(Transaction.account_id == acc2_uuid).delete()
                db.query(Account).filter(Account.id == acc2_uuid).delete()

            if db_u1:
                db.delete(db_u1)
            if db_u2:
                db.delete(db_u2)

            db.commit()
            print("   -> Đã dọn dẹp an toàn các tài khoản và giao dịch test cô lập!")
        except (SQLAlchemyError, httpx.HTTPError) as e:
            db.rollback()
            print(f"   [Cảnh báo] Lỗi dọn dẹp test data: {e}")
        finally:
            db.close()


if __name__ == "__main__":
    verify_live_transaction_flow()
