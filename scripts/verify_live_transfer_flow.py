import sys
import uuid
from decimal import Decimal
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
from app.models.transaction import Transaction

# pyrefly: ignore[missing-import]
from app.models.transfer import Transfer

# pyrefly: ignore[missing-import]
from app.models.user import User
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

BASE_URL = "http://127.0.0.1:8000"


def verify_live_transfer_flow():
    print("=" * 60)
    print("KIỂM CHỨNG LIVE TRANSFER & DOUBLE-ENTRY VỚI POSTGRESQL 18 THẬT")
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
    res_unauth = httpx.get(f"{BASE_URL}/api/v1/transfers", timeout=5.0)
    assert res_unauth.status_code == 401
    print("   -> Bị từ chối 401 Unauthorized chính xác!")

    # 3. Tạo 2 tài khoản thử nghiệm cô lập
    email_u1 = f"tr_live_u1_{uuid.uuid4().hex[:6]}@example.com"
    email_u2 = f"tr_live_u2_{uuid.uuid4().hex[:6]}@example.com"
    password = "SecurePassword123!"

    client1 = httpx.Client(base_url=BASE_URL, timeout=10.0)
    client2 = httpx.Client(base_url=BASE_URL, timeout=10.0)

    print(f"3. Đăng ký & Đăng nhập tài khoản test:\n   - U1: {email_u1}\n   - U2: {email_u2}")
    client1.post("/api/v1/auth/register", json={"email": email_u1, "password": password, "display_name": "Transfer User 1"})
    client1.post("/api/v1/auth/login", json={"email": email_u1, "password": password})

    client2.post("/api/v1/auth/register", json={"email": email_u2, "password": password, "display_name": "Transfer User 2"})
    client2.post("/api/v1/auth/login", json={"email": email_u2, "password": password})
    print("   -> Cả 2 client đã có session cookie hợp lệ!")

    acc_a_id = None
    acc_b_id = None
    acc_u2_id = None

    try:
        # Lấy danh mục hệ thống để làm phí chuyển tiền
        res_cats = client1.get("/api/v1/categories?scope=system&type=expense")
        assert res_cats.status_code == 200
        cats = res_cats.json()
        fee_cat = next((c for c in cats if c["name"] == "Phí ngân hàng & Chuyển tiền"), cats[0])
        print(f"   -> Sử dụng danh mục phí hệ thống: '{fee_cat['name']}' (ID: {fee_cat['id']})")

        # 4. U1 tạo 2 ví cá nhân: Ví A (1.000.000 VND), Ví B (300.000 VND)
        print("4. U1 tạo 2 ví cá nhân:\n   - Ví A ban đầu: 1.000.000 VND\n   - Ví B ban đầu: 300.000 VND...")
        res_acc_a = client1.post(
            "/api/v1/accounts",
            json={
                "name": "Ví Nguồn A",
                "scope": "personal",
                "account_type": "bank",
                "currency": "VND",
                "initial_balance": "1000000.00",
            },
        )
        assert res_acc_a.status_code == 201
        acc_a_id = res_acc_a.json()["id"]

        res_acc_b = client1.post(
            "/api/v1/accounts",
            json={
                "name": "Ví Đích B",
                "scope": "personal",
                "account_type": "bank",
                "currency": "VND",
                "initial_balance": "300000.00",
            },
        )
        assert res_acc_b.status_code == 201
        acc_b_id = res_acc_b.json()["id"]

        # U2 tạo 1 ví riêng
        res_acc_u2 = client2.post(
            "/api/v1/accounts",
            json={
                "name": "Ví U2 Riêng",
                "scope": "personal",
                "account_type": "cash",
                "currency": "VND",
                "initial_balance": "500000.00",
            },
        )
        acc_u2_id = res_acc_u2.json()["id"]

        # 5. U1 thực hiện chuyển tiền từ Ví A sang Ví B: 500.000 VND, phí: 2.000 VND
        print("5. U1 thực hiện chuyển tiền từ Ví A sang Ví B (500.000 VND, phí 2.000 VND)...")
        res_tr = client1.post(
            "/api/v1/transfers",
            json={
                "from_account_id": acc_a_id,
                "to_account_id": acc_b_id,
                "amount": "500000.00",
                "fee_amount": "2000.00",
                "fee_category_id": fee_cat["id"],
                "note": "Chuyển tiền tiết kiệm tháng 10",
            },
        )
        assert res_tr.status_code == 201, f"Tạo chuyển tiền thất bại: {res_tr.text}"
        tr_data = res_tr.json()
        transfer_id = tr_data["id"]
        print(f"   -> Chuyển tiền thành công! Transfer ID: {transfer_id}")

        # 6. Xác minh trực tiếp trên PostgreSQL bảng transfers và transactions
        print("6. Xác minh trực tiếp cấu trúc bút toán kép trong PostgreSQL...")
        db = SessionLocal()
        db_tr = db.get(Transfer, uuid.UUID(transfer_id))
        assert db_tr is not None
        assert db_tr.amount == Decimal("500000.00")
        assert db_tr.fee_amount == Decimal("2000.00")
        assert db_tr.voided_at is None

        db_txs = db.query(Transaction).filter(Transaction.transfer_id == db_tr.id).all()
        assert len(db_txs) == 3, f"Yêu cầu 3 bút toán, thực tế có: {len(db_txs)}"
        types = {t.type for t in db_txs}
        assert types == {"transfer_out", "transfer_in", "transfer_fee"}

        tx_out = next(t for t in db_txs if t.type == "transfer_out")
        tx_in = next(t for t in db_txs if t.type == "transfer_in")
        tx_fee = next(t for t in db_txs if t.type == "transfer_fee")

        assert str(tx_out.account_id) == acc_a_id and tx_out.amount == Decimal("500000.00")
        assert str(tx_in.account_id) == acc_b_id and tx_in.amount == Decimal("500000.00")
        assert str(tx_fee.account_id) == acc_a_id and tx_fee.amount == Decimal("2000.00")
        db.close()
        print("   -> Bút toán kép chính xác 100%: transfer_out (-500k ví A), transfer_in (+500k ví B), transfer_fee (-2k ví A)!")

        # 7. Kiểm tra số dư ví A và ví B từ API account
        print("7. Kiểm tra số dư động 2 ví qua GET /accounts/{id}...")
        res_chk_a = client1.get(f"/api/v1/accounts/{acc_a_id}")
        res_chk_b = client1.get(f"/api/v1/accounts/{acc_b_id}")
        # Ví A: 1.000.000 - 500.000 - 2.000 = 498.000 VND
        assert Decimal(res_chk_a.json()["current_balance"]) == Decimal("498000.00")
        # Ví B: 300.000 + 500.000 = 800.000 VND
        assert Decimal(res_chk_b.json()["current_balance"]) == Decimal("800000.00")
        print(f"   -> Số dư ví A: {res_chk_a.json()['current_balance']} VND (Chính xác 498.000 VND!)")
        print(f"   -> Số dư ví B: {res_chk_b.json()['current_balance']} VND (Chính xác 800.000 VND!)")

        # 8. Kiểm tra phân quyền truy cập chéo của U2 (U2 không xem và không void được)
        print("8. Kiểm tra bảo mật truy cập chéo giữa U2 và chuyển tiền của U1...")
        res_u2_view = client2.get(f"/api/v1/transfers/{transfer_id}")
        assert res_u2_view.status_code == 404, "U2 không được phép xem transfer của U1!"

        res_u2_void = client2.post(f"/api/v1/transfers/{transfer_id}/void")
        assert res_u2_void.status_code == 404, "U2 không được phép void transfer của U1!"

        res_u2_create = client2.post(
            "/api/v1/transfers",
            json={
                "from_account_id": acc_a_id,
                "to_account_id": acc_u2_id,
                "amount": "10000.00",
            },
        )
        assert res_u2_create.status_code == 404, "U2 không được phép chuyển từ ví của U1!"
        print("   -> Bảo mật phân quyền ngăn chặn 100% mọi truy cập trái phép từ user khác!")

        # 9. U1 thực hiện void chuyển tiền
        print("9. U1 thực hiện hủy hiệu lực (void) chuyển tiền...")
        res_void = client1.post(f"/api/v1/transfers/{transfer_id}/void")
        assert res_void.status_code == 200
        void_data = res_void.json()
        assert void_data["is_voided"] is True and void_data["voided_at"] is not None

        # Kiểm tra số dư ví A và ví B tự động hoàn nguyên về số dư ban đầu
        res_chk_a2 = client1.get(f"/api/v1/accounts/{acc_a_id}")
        res_chk_b2 = client1.get(f"/api/v1/accounts/{acc_b_id}")
        assert Decimal(res_chk_a2.json()["current_balance"]) == Decimal("1000000.00")
        assert Decimal(res_chk_b2.json()["current_balance"]) == Decimal("300000.00")
        print("   -> Số dư 2 ví tự động hoàn nguyên chính xác:\n"
              f"      - Ví A: {res_chk_a2.json()['current_balance']} VND (Phục hồi 1.000.000 VND)\n"
              f"      - Ví B: {res_chk_b2.json()['current_balance']} VND (Phục hồi 300.000 VND)")

        # Thử void lại lần 2 -> 400
        res_void_again = client1.post(f"/api/v1/transfers/{transfer_id}/void")
        assert res_void_again.status_code == 400
        print("   -> Từ chối void lại lần 2 chính xác (HTTP 400)!")

        print("\n✅ TOÀN BỘ LUỒNG CHUYỂN TIỀN BÚT TOÁN KÉP & SỐ DƯ ĐẠT 100% TRÊN POSTGRESQL 18 THẬT!")

    finally:
        # Dọn dẹp dữ liệu test cô lập
        print("\n10. Dọn dẹp an toàn các tài khoản và giao dịch test cô lập...")
        db = SessionLocal()
        try:
            db_u1 = db.scalar(select(User).where(User.email == email_u1))
            db_u2 = db.scalar(select(User).where(User.email == email_u2))

            # Xóa các giao dịch, chuyển tiền và ví của U1, U2
            acc_uuids = [uuid.UUID(aid) for aid in [acc_a_id, acc_b_id, acc_u2_id] if aid]
            if acc_uuids:
                # 1. Tìm các transfer_id liên quan
                tr_ids = db.scalars(
                    select(Transfer.id).where(
                        (Transfer.from_account_id.in_(acc_uuids)) | (Transfer.to_account_id.in_(acc_uuids))
                    )
                ).all()

                # 2. Xóa các transactions liên quan tới transfer_ids hoặc accounts
                if tr_ids:
                    db.query(Transaction).filter(Transaction.transfer_id.in_(tr_ids)).delete(synchronize_session=False)
                db.query(Transaction).filter(Transaction.account_id.in_(acc_uuids)).delete(synchronize_session=False)

                # 3. Xóa các transfers
                if tr_ids:
                    db.query(Transfer).filter(Transfer.id.in_(tr_ids)).delete(synchronize_session=False)

                # 4. Xóa accounts
                db.query(Account).filter(Account.id.in_(acc_uuids)).delete(synchronize_session=False)

            if db_u1:
                db.delete(db_u1)
            if db_u2:
                db.delete(db_u2)

            db.commit()
            print("   -> Đã dọn dẹp an toàn toàn bộ dữ liệu test cô lập trên PostgreSQL!")
        except (SQLAlchemyError, httpx.HTTPError) as e:
            db.rollback()
            print(f"   [Cảnh báo] Lỗi dọn dẹp test data: {e}")
        finally:
            db.close()


if __name__ == "__main__":
    verify_live_transfer_flow()
