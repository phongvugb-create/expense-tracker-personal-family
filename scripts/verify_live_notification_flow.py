"""Verify live Notification flow on PostgreSQL 18.

This script tests the Notifications API against a running FastAPI backend
and PostgreSQL 18 database with an isolated test user.
"""

import concurrent.futures
import sys
import uuid
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import os

import httpx
from app.db.session import SessionLocal
from app.models.account import Account
from app.models.budget import Budget
from app.models.notification import Notification
from app.models.recurring_transaction import RecurringTransaction
from app.models.transaction import Transaction
from app.models.user import User

API_PORT = os.getenv("API_PORT", "8001")
BASE_URL = os.getenv("API_BASE_URL", f"http://127.0.0.1:{API_PORT}/api/v1")
HEALTH_URL = os.getenv("HEALTH_URL", f"http://127.0.0.1:{API_PORT}/health/ready")


def run_verification() -> bool:
    client = httpx.Client(timeout=10.0)

    print(f"[1] Checking backend health at {HEALTH_URL}...")
    try:
        resp = client.get(HEALTH_URL)
        if resp.status_code != 200:
            print(f"FAILED [Health Check]: URL {HEALTH_URL} returned HTTP {resp.status_code}: {resp.text}")
            return False
        print("Backend health check PASSED (database connected)")
    except Exception as exc:  # noqa: BLE001
        print(f"FAILED [Connection Error]: Could not connect to {HEALTH_URL}: {exc}")
        return False

    print("\n[2] Testing unauthenticated access to /notifications...")
    resp = client.get(f"{BASE_URL}/notifications")
    if resp.status_code != 401:
        print(f"FAILED: Expected 401 Unauthenticated, got {resp.status_code}")
        return False

    sync_unauth = client.post(f"{BASE_URL}/notifications/sync")
    if sync_unauth.status_code != 401:
        print(f"FAILED: Expected 401 on /notifications/sync, got {sync_unauth.status_code}")
        return False
    print("401 Unauthenticated check PASSED")

    # 3. Register and login isolated user
    suffix = uuid.uuid4().hex[:8]
    email = f"notif_live_{suffix}@example.com"
    password = "LivePassword123!"
    display_name = f"Notification Test User {suffix}"

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
        # 4. Check initial unread count = 0
        print("\n[4] Checking initial empty unread count...")
        c_res = client.get(f"{BASE_URL}/notifications/unread-count")
        assert c_res.status_code == 200
        assert c_res.json()["unread_count"] == 0
        print("Initial unread count = 0 PASSED")

        # 5. Create wallet and budget
        print("\n[5] Setting up wallet, recurring rule, and budget...")
        acc_resp = client.post(
            f"{BASE_URL}/accounts",
            json={
                "name": "Live Notif Wallet",
                "scope": "personal",
                "account_type": "bank",
                "currency": "VND",
                "initial_balance": "10000000.00",
                "color": "#10B981",
            },
        )
        assert acc_resp.status_code == 201, acc_resp.text
        acc_id = acc_resp.json()["id"]

        cat_resp = client.get(f"{BASE_URL}/categories?scope=system")
        assert cat_resp.status_code == 200, cat_resp.text
        cats = [c for c in cat_resp.json() if c["type"] == "expense"]
        cat_id = cats[0]["id"]

        # Tạo rule định kỳ đến hạn hôm nay
        rule_payload = {
            "name": "Tiền mạng FPT Live",
            "type": "expense",
            "scope": "personal",
            "account_id": acc_id,
            "category_id": cat_id,
            "amount": "330000.00",
            "start_date": today.isoformat(),
            "frequency": "monthly",
            "interval_value": 1,
            "note": "Cước mạng",
        }
        r_resp = client.post(f"{BASE_URL}/recurring-transactions", json=rule_payload)
        assert r_resp.status_code == 201, r_resp.text
        rule_id = r_resp.json()["id"]

        # Tạo ngân sách tháng này: 1,000,000 VND (ngưỡng 80%)
        p_start = today.replace(day=1)
        p_end = (p_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        budget_payload = {
            "name": "Ngân sách sinh hoạt Live",
            "scope": "personal",
            "category_id": cat_id,
            "amount_limit": "1000000.00",
            "period_start": p_start.isoformat(),
            "period_end": p_end.isoformat(),
            "warning_threshold": "80",
        }
        b_resp = client.post(f"{BASE_URL}/budgets", json=budget_payload)
        assert b_resp.status_code == 201, b_resp.text

        # Ghi nhận giao dịch chi 850,000 VND (85% -> chạm warning)
        tx_payload = {
            "account_id": acc_id,
            "category_id": cat_id,
            "type": "expense",
            "amount": "850000.00",
            "note": "Chi tiêu dùng thử",
        }
        tx_resp = client.post(f"{BASE_URL}/transactions", json=tx_payload)
        assert tx_resp.status_code == 201, tx_resp.text

        # 6. Test Sync Notifications
        print("\n[6] Calling POST /notifications/sync...")
        sync1 = client.post(f"{BASE_URL}/notifications/sync")
        assert sync1.status_code == 200, sync1.text
        s_data = sync1.json()
        print(f"Sync Result: Created={s_data['created_count']}, Unread={s_data['unread_count']}")
        assert s_data["created_count"] == 2
        assert s_data["unread_count"] == 2

        # 7. Test Idempotency on Sync (calling multiple times)
        print("\n[7] Testing idempotent sync (calling repeatedly)...")
        sync2 = client.post(f"{BASE_URL}/notifications/sync")
        assert sync2.status_code == 200
        assert sync2.json()["created_count"] == 0
        assert sync2.json()["unread_count"] == 2
        print("Idempotent sync PASSED: No duplicates created")

        # 8. Test Concurrent Sync requests (multithreaded race)
        print("\n[8] Testing concurrent sync requests...")
        def concurrent_sync():
            c = httpx.Client(timeout=10.0, cookies=client.cookies)
            return c.post(f"{BASE_URL}/notifications/sync")

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            fut1 = executor.submit(concurrent_sync)
            fut2 = executor.submit(concurrent_sync)
            res1 = fut1.result()
            res2 = fut2.result()

        assert res1.status_code == 200
        assert res2.status_code == 200

        with SessionLocal() as db:
            count_in_db = db.query(Notification).filter(Notification.user_id == uuid.UUID(user_id)).count()
            assert count_in_db == 2
        print("Concurrent sync PASSED: Database unique constraint preserved exactly 2 notifications")

        # 9. Verify Notification list and actions
        print("\n[9] Testing mark-read and archive actions...")
        n_list = client.get(f"{BASE_URL}/notifications").json()
        assert len(n_list) == 2
        target_id = n_list[0]["id"]

        # Mark 1 as read
        read_resp = client.patch(f"{BASE_URL}/notifications/{target_id}/read")
        assert read_resp.status_code == 200
        assert read_resp.json()["read_at"] is not None

        c_now = client.get(f"{BASE_URL}/notifications/unread-count").json()["unread_count"]
        assert c_now == 1

        # Mark all read
        all_read = client.post(f"{BASE_URL}/notifications/mark-all-read")
        assert all_read.status_code == 200
        assert client.get(f"{BASE_URL}/notifications/unread-count").json()["unread_count"] == 0

        # Archive target_id
        arc_resp = client.post(f"{BASE_URL}/notifications/{target_id}/archive")
        assert arc_resp.status_code == 200
        assert arc_resp.json()["archived_at"] is not None

        active_notifs = client.get(f"{BASE_URL}/notifications").json()
        assert len(active_notifs) == 1
        print("Notification lifecycle (sync, read, mark-all-read, archive) PASSED")

        # 10. Verify no side-effect financial transactions
        print("\n[10] Verifying financial isolation (no auto-transactions created during sync)...")
        acc_check = client.get(f"{BASE_URL}/accounts/{acc_id}").json()
        # 10,000,000 - 850,000 = 9,150,000 VND
        assert Decimal(acc_check["current_balance"]) == Decimal("9150000.00")
        print("Financial isolation PASSED: Balance is exact, no auto transactions created")

        # 11. Verify recurring generation automatically archives period notification
        print("\n[11] Verifying recurring transaction generation archives notification...")
        gen_res = client.post(f"{BASE_URL}/recurring-transactions/{rule_id}/generate")
        assert gen_res.status_code == 200, gen_res.text
        gen_data = gen_res.json()
        assert "transaction_id" in gen_data
        print(f"Generated recurring transaction: {gen_data['transaction_id']}")

        # Sync lại sau khi đã phát sinh giao dịch
        sync_after_gen = client.post(f"{BASE_URL}/notifications/sync")
        assert sync_after_gen.status_code == 200
        assert sync_after_gen.json()["created_count"] == 0

        # Kiểm tra danh sách thông báo active: không còn nhắc nhở của kỳ đã phát sinh
        active_after_gen = client.get(f"{BASE_URL}/notifications").json()
        for an in active_after_gen:
            assert an["type"] != "recurring_due_today", f"Thông báo kỳ cũ vẫn còn trong active: {an}"

        # Kiểm tra danh sách lưu trữ: vẫn giữ nguyên thông báo kỳ cũ
        all_notifs_after_gen = client.get(f"{BASE_URL}/notifications?include_archived=true").json()
        old_period_notif = next(
            (n for n in all_notifs_after_gen if n["source_key"] == f"recurring:{rule_id}:{today.isoformat()}"),
            None,
        )
        assert old_period_notif is not None, "Thông báo kỳ cũ phải được giữ lại trong lịch sử lưu trữ"
        assert old_period_notif["archived_at"] is not None

        # Kiểm tra tài chính: sau generate trừ đúng 330k (9,150,000 - 330,000 = 8,820,000 VND), sync không làm thay đổi số dư
        acc_check_after_sync = client.get(f"{BASE_URL}/accounts/{acc_id}").json()
        assert Decimal(acc_check_after_sync["current_balance"]) == Decimal("8820000.00")
        print("Recurring generation notification archive & idempotency PASSED")

        print("\nAll assertions in Live Notification verification PASSED!")
        return True

    finally:
        print("\n[Cleanup] Cleaning up isolated test user data from PostgreSQL...")
        try:
            with SessionLocal() as db:
                db.query(Notification).filter(Notification.user_id == uuid.UUID(user_id)).delete()
                db.query(Transaction).filter(Transaction.user_id == uuid.UUID(user_id)).delete()
                db.query(Budget).filter(Budget.user_id == uuid.UUID(user_id)).delete()
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
