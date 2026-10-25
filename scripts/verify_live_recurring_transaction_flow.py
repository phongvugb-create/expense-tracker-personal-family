"""Verify live recurring transaction flow on PostgreSQL 18.

This script tests the Recurring Transactions API against a running FastAPI backend
and PostgreSQL 18 database with an isolated test user.
"""

import sys
import uuid
from datetime import date
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
from app.models.recurring_transaction import RecurringTransaction

# pyrefly: ignore[missing-import]
from app.models.transaction import Transaction

# pyrefly: ignore[missing-import]
from app.models.user import User

BASE_URL = "http://127.0.0.1:8000/api/v1"
HEALTH_URL = "http://127.0.0.1:8000/health/ready"


def run_verification() -> bool:
    client = httpx.Client(timeout=10.0)

    print("[1] Checking backend health...")
    try:
        resp = client.get(HEALTH_URL)
        if resp.status_code != 200:
            print(f"FAILED: Backend health check returned {resp.status_code}")
            return False
        print("Backend health check PASSED")
    except Exception as exc:  # noqa: BLE001
        print(f"FAILED to connect to backend: {exc}")
        return False

    print("\n[2] Testing unauthenticated access to /recurring-transactions...")
    resp = client.get(f"{BASE_URL}/recurring-transactions")
    if resp.status_code != 401:
        print(f"FAILED: Expected 401 Unauthenticated, got {resp.status_code}")
        return False
    print("401 Unauthenticated check PASSED")

    # 3. Register and login isolated user
    suffix = uuid.uuid4().hex[:8]
    email = f"recur_live_{suffix}@example.com"
    password = "LivePassword123!"
    display_name = f"Recurring Test User {suffix}"

    print(f"\n[3] Registering and logging in isolated user: {email}...")
    reg_resp = client.post(
        f"{BASE_URL}/auth/register",
        json={"email": email, "password": password, "display_name": display_name},
    )
    if reg_resp.status_code != 201:
        print(f"FAILED: Registration returned {reg_resp.status_code}: {reg_resp.text}")
        return False

    login_resp = client.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": password},
    )
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    user_data = login_resp.json()
    user_id = user_data["id"]
    print(f"User logged in successfully (ID: {user_id})")

    today = date.today()

    try:
        # 4. Check initial empty rules
        print("\n[4] Querying initial empty recurring transactions list...")
        resp = client.get(f"{BASE_URL}/recurring-transactions")
        assert resp.status_code == 200, resp.text
        rules = resp.json()
        assert len(rules) == 0
        print("Initial empty list PASSED")

        # 5. Create wallet
        print("\n[5] Creating wallet...")
        acc_resp = client.post(
            f"{BASE_URL}/accounts",
            json={
                "name": "Live Recur Wallet",
                "scope": "personal",
                "account_type": "bank",
                "currency": "VND",
                "initial_balance": "10000000.00",
                "color": "#10B981",
            },
        )
        assert acc_resp.status_code == 201, acc_resp.text
        acc_id = acc_resp.json()["id"]

        # 6. Fetch category
        cat_resp = client.get(f"{BASE_URL}/categories?scope=system")
        assert cat_resp.status_code == 200, cat_resp.text
        expense_cats = [c for c in cat_resp.json() if c["type"] == "expense"]
        cat_id = expense_cats[0]["id"]

        # 7. Create Recurring Rule
        print(f"\n[7] Creating recurring rule (monthly rent VND 4,500,000 due {today.isoformat()})...")
        rule_payload = {
            "name": "Tiền nhà định kỳ Live",
            "type": "expense",
            "scope": "personal",
            "account_id": acc_id,
            "category_id": cat_id,
            "amount": "4500000.00",
            "start_date": today.isoformat(),
            "frequency": "monthly",
            "interval_value": 1,
            "note": "Tiền nhà thanh toán qua ngân hàng",
        }
        create_rule_resp = client.post(f"{BASE_URL}/recurring-transactions", json=rule_payload)
        assert create_rule_resp.status_code == 201, create_rule_resp.text
        rule = create_rule_resp.json()
        rule_id = rule["id"]
        assert rule["next_due_date"] == today.isoformat()
        assert rule["is_due"] is True
        print(f"Recurring Rule created successfully (ID: {rule_id})")

        # 8. Generate actual Transaction for today's due period
        print(f"\n[8] Generating transaction for due date {today.isoformat()}...")
        gen_resp = client.post(f"{BASE_URL}/recurring-transactions/{rule_id}/generate")
        assert gen_resp.status_code == 200, gen_resp.text
        gen_data = gen_resp.json()
        tx_id = gen_data["transaction_id"]
        print(f"Generated Transaction ID: {tx_id}")
        assert "Đã tạo thành công" in gen_data["message"]
        assert gen_data["rule"]["next_due_date"] > today.isoformat()

        # 9. Test Idempotency (prevent generating duplicate for same period)
        print("\n[9] Testing idempotency / duplicate generate prevention...")
        # Lặp lại generate khi kỳ tiếp theo chưa đến hạn -> 400 Bad Request
        dup_resp = client.post(f"{BASE_URL}/recurring-transactions/{rule_id}/generate")
        assert dup_resp.status_code == 400
        assert "chưa đến hạn tạo" in dup_resp.json()["detail"]
        print("Idempotency prevention PASSED (cannot generate before due date)")

        # 10. Verify generated transaction in /transactions endpoint and balance impact
        print("\n[10] Verifying generated transaction impact on /transactions and /accounts...")
        tx_get = client.get(f"{BASE_URL}/transactions/{tx_id}")
        assert tx_get.status_code == 200, tx_get.text
        tx_data = tx_get.json()
        assert Decimal(tx_data["amount"]) == Decimal("4500000.00")

        acc_get = client.get(f"{BASE_URL}/accounts/{acc_id}")
        assert acc_get.status_code == 200, acc_get.text
        # Initial 10,000,000 - 4,500,000 = 5,500,000
        assert Decimal(acc_get.json()["current_balance"]) == Decimal("5500000.00")
        print("Balance updated accurately on PostgreSQL: 10,000,000 - 4,500,000 = 5,500,000 VND")

        # 11. Test Pause & Resume
        print("\n[11] Testing Pause and Resume lifecycle...")
        pause_resp = client.post(f"{BASE_URL}/recurring-transactions/{rule_id}/pause")
        assert pause_resp.status_code == 200
        assert pause_resp.json()["is_active"] is False

        resume_resp = client.post(f"{BASE_URL}/recurring-transactions/{rule_id}/resume")
        assert resume_resp.status_code == 200
        assert resume_resp.json()["is_active"] is True
        print("Pause and Resume PASSED")

        # 12. Test soft-delete idempotency on PostgreSQL 18
        print("\n[12] Testing idempotency after transaction is soft-deleted on PostgreSQL 18...")
        # Xóa mềm transaction tx_id
        del_tx_resp = client.delete(f"{BASE_URL}/transactions/{tx_id}")
        assert del_tx_resp.status_code == 200, del_tx_resp.text

        # Số dư ví phải được hoàn lại (10,000,000 VND)
        acc_after_del = client.get(f"{BASE_URL}/accounts/{acc_id}")
        assert Decimal(acc_after_del.json()["current_balance"]) == Decimal("10000000.00")

        # Đặt lại next_due_date của rule trong PostgreSQL về today để mô phỏng người dùng thử tạo lại kỳ đó
        with SessionLocal() as db:
            rule_db = db.get(RecurringTransaction, uuid.UUID(rule_id))
            assert rule_db is not None
            rule_db.next_due_date = today
            db.commit()

        # Thử generate lại cùng kỳ -> Phải phát hiện kỳ này đã được ghi nhận trước đó (dù đã xóa mềm) và không tạo bản ghi mới
        regen_resp = client.post(f"{BASE_URL}/recurring-transactions/{rule_id}/generate")
        assert regen_resp.status_code == 200
        assert "xóa mềm" in regen_resp.json()["message"]
        assert regen_resp.json()["transaction_id"] == tx_id
        print("Soft-delete idempotency protection on PostgreSQL 18 PASSED")

        # 13. Test concurrent generation with 2 parallel threads
        print("\n[13] Testing concurrent generation handling (FOR UPDATE / Unique Constraint)...")
        import concurrent.futures

        # Tạo rule thứ 2 cho kịch bản concurrent
        rule2_payload = {
            "name": "Live Concurrent Test",
            "type": "expense",
            "scope": "personal",
            "account_id": acc_id,
            "category_id": cat_id,
            "amount": "100000.00",
            "start_date": today.isoformat(),
            "frequency": "daily",
            "interval_value": 1,
        }
        r2_resp = client.post(f"{BASE_URL}/recurring-transactions", json=rule2_payload)
        assert r2_resp.status_code == 201
        r2_id = r2_resp.json()["id"]

        def generate_call():
            c = httpx.Client(timeout=10.0, cookies=client.cookies)
            return c.post(f"{BASE_URL}/recurring-transactions/{r2_id}/generate")

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            future1 = executor.submit(generate_call)
            future2 = executor.submit(generate_call)
            res1 = future1.result()
            res2 = future2.result()

        # Cả 2 request phải kết thúc với mã HTTP hợp lệ (200 hoặc 409/400), không để xảy ra 500
        assert res1.status_code in (200, 400, 409)
        assert res2.status_code in (200, 400, 409)
        # Kiểm tra trong DB chỉ có đúng 1 transaction được sinh ra cho rule 2
        with SessionLocal() as db:
            r2_tx_count = db.query(Transaction).filter(
                Transaction.recurring_rule_id == uuid.UUID(r2_id),
                Transaction.recurrence_date == today,
            ).count()
            assert r2_tx_count == 1
        print("Concurrent race test PASSED: Exactly 1 transaction recorded in PostgreSQL 18")

        print("\nAll financial assertions in Live Recurring Transaction verification PASSED!")
        return True

    finally:
        # Cleanup
        print("\n[Cleanup] Cleaning up isolated test user data from PostgreSQL...")
        try:
            with SessionLocal() as db:
                db.query(Transaction).filter(Transaction.user_id == uuid.UUID(user_id)).delete()
                db.query(RecurringTransaction).filter(RecurringTransaction.user_id == uuid.UUID(user_id)).delete()
                db.query(Account).filter(Account.user_id == uuid.UUID(user_id)).delete()
                db.query(User).filter(User.id == uuid.UUID(user_id)).delete()
                db.commit()
            print("[Cleanup] Cleanup completed successfully.")
        except Exception as e:  # noqa: BLE001
            print(f"[Cleanup Error] {e}")


if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
