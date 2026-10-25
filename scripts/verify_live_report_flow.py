"""Verify live reports flow on PostgreSQL 18.

This script tests the GET /api/v1/reports/summary and GET /api/v1/reports/export.csv
endpoints against a running FastAPI backend and PostgreSQL 18 database with an isolated test user.
"""

import sys
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import httpx
from app.db.session import SessionLocal
from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction
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

    print("\n[2] Testing unauthenticated access to /reports/summary and /reports/export.csv...")
    resp = client.get(f"{BASE_URL}/reports/summary?date_from=2026-10-01&date_to=2026-10-31")
    if resp.status_code != 401:
        print(f"FAILED: Expected 401 Unauthenticated for summary, got {resp.status_code}")
        return False

    resp_csv = client.get(f"{BASE_URL}/reports/export.csv?date_from=2026-10-01&date_to=2026-10-31")
    if resp_csv.status_code != 401:
        print(f"FAILED: Expected 401 Unauthenticated for CSV export, got {resp_csv.status_code}")
        return False
    print("401 Unauthenticated checks PASSED")

    # 3. Register and login isolated user
    suffix = uuid.uuid4().hex[:8]
    email = f"report_live_{suffix}@example.com"
    password = "LivePassword123!"
    display_name = f"Report Test User {suffix}"

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

    now = datetime.now(UTC)
    date_from_str = (now - timedelta(days=15)).strftime("%Y-%m-%d")
    date_to_str = now.strftime("%Y-%m-%d")

    try:
        # 4. Check initial empty report
        print(f"\n[4] Querying empty report summary from {date_from_str} to {date_to_str}...")
        resp = client.get(
            f"{BASE_URL}/reports/summary?date_from={date_from_str}&date_to={date_to_str}&scope=all"
        )
        if resp.status_code != 200:
            print(f"FAILED: Initial report returned {resp.status_code}: {resp.text}")
            return False
        data = resp.json()
        assert len(data["cash_flow_by_currency"]) == 0
        assert len(data["category_breakdown"]) == 0
        assert len(data["top_expenses"]) == 0
        print("Initial empty report PASSED")

        # 5. Create wallets: VND and USD
        print("\n[5] Creating VND and USD wallets...")
        acc_vnd_resp = client.post(
            f"{BASE_URL}/accounts",
            json={
                "name": "Live Report VND Wallet",
                "scope": "personal",
                "account_type": "cash",
                "currency": "VND",
                "initial_balance": "2000000.00",
                "color": "#10B981",
            },
        )
        assert acc_vnd_resp.status_code == 201, acc_vnd_resp.text
        vnd_acc_id = acc_vnd_resp.json()["id"]

        acc_usd_resp = client.post(
            f"{BASE_URL}/accounts",
            json={
                "name": "Live Report USD Wallet",
                "scope": "personal",
                "account_type": "bank",
                "currency": "USD",
                "initial_balance": "150.00",
                "color": "#3B82F6",
            },
        )
        assert acc_usd_resp.status_code == 201, acc_usd_resp.text
        usd_acc_id = acc_usd_resp.json()["id"]
        print("Wallets created successfully")

        # 6. Fetch categories
        cat_resp = client.get(f"{BASE_URL}/categories?scope=system")
        assert cat_resp.status_code == 200, cat_resp.text
        categories = cat_resp.json()
        income_cats = [c for c in categories if c["type"] == "income"]
        expense_cats = [c for c in categories if c["type"] == "expense"]

        salary_cat_id = income_cats[0]["id"] if income_cats else None
        food_cat_id = expense_cats[0]["id"] if expense_cats else None

        # 7. Add Income (VND 10,000,000) and Expense (VND 1,200,000) and USD Income ($50)
        print("\n[7] Creating transactions (VND Income 10,000,000, Expense 1,200,000, USD Income 50)...")
        tx_in = client.post(
            f"{BASE_URL}/transactions",
            json={
                "account_id": vnd_acc_id,
                "category_id": salary_cat_id,
                "type": "income",
                "amount": "10000000.00",
                "occurred_at": now.isoformat(),
                "note": "Tiền thưởng dự án",
            },
        )
        assert tx_in.status_code == 201, tx_in.text

        tx_out = client.post(
            f"{BASE_URL}/transactions",
            json={
                "account_id": vnd_acc_id,
                "category_id": food_cat_id,
                "type": "expense",
                "amount": "1200000.00",
                "occurred_at": now.isoformat(),
                "note": "Ăn liên hoan công ty",
            },
        )
        assert tx_out.status_code == 201, tx_out.text

        tx_usd_in = client.post(
            f"{BASE_URL}/transactions",
            json={
                "account_id": usd_acc_id,
                "category_id": salary_cat_id,
                "type": "income",
                "amount": "50.00",
                "occurred_at": now.isoformat(),
                "note": "Freelance payment",
            },
        )
        assert tx_usd_in.status_code == 201, tx_usd_in.text

        # 8. Soft-deleted transaction (phải bị loại khỏi báo cáo)
        tx_del = client.post(
            f"{BASE_URL}/transactions",
            json={
                "account_id": vnd_acc_id,
                "category_id": food_cat_id,
                "type": "expense",
                "amount": "888888.00",
                "occurred_at": now.isoformat(),
                "note": "Khoản chi nhầm đã xóa",
            },
        )
        assert tx_del.status_code == 201
        del_id = tx_del.json()["id"]
        del_resp = client.delete(f"{BASE_URL}/transactions/{del_id}")
        assert del_resp.status_code in (200, 204)

        # 9. Query Report Summary and verify
        print("\n[9] Querying Report Summary with active data...")
        report_resp = client.get(
            f"{BASE_URL}/reports/summary?date_from={date_from_str}&date_to={date_to_str}&scope=all"
        )
        assert report_resp.status_code == 200, report_resp.text
        summary = report_resp.json()

        # Check cash flow by currency
        cash_flow = {cf["currency"]: cf for cf in summary["cash_flow_by_currency"]}
        print(f"Cash flow by currency: {cash_flow}")
        assert "VND" in cash_flow
        assert "USD" in cash_flow

        vnd_cf = cash_flow["VND"]
        assert Decimal(vnd_cf["total_income"]) == Decimal("10000000.00")
        assert Decimal(vnd_cf["total_expense"]) == Decimal("1200000.00")
        assert Decimal(vnd_cf["net_cash_flow"]) == Decimal("8800000.00")

        usd_cf = cash_flow["USD"]
        assert Decimal(usd_cf["total_income"]) == Decimal("50.00")
        assert Decimal(usd_cf["total_expense"]) == Decimal("0.00")
        assert Decimal(usd_cf["net_cash_flow"]) == Decimal("50.00")

        # Check Top expenses (chỉ có 1 khoản hợp lệ, khoản bị xóa đã loại trừ)
        top_exps = summary["top_expenses"]
        assert len(top_exps) == 1
        assert Decimal(top_exps[0]["amount"]) == Decimal("1200000.00")
        assert top_exps[0]["description"] == "Ăn liên hoan công ty"

        # Check category breakdown
        cats = summary["category_breakdown"]
        assert len(cats) == 1
        assert Decimal(cats[0]["total_amount"]) == Decimal("1200000.00")
        assert Decimal(cats[0]["percentage"]) == Decimal("100.00")

        # Check account breakdown
        accs = summary["account_breakdown"]
        assert len(accs) == 2

        # 10. Test CSV Export
        print("\n[10] Testing GET /api/v1/reports/export.csv...")
        csv_resp = client.get(
            f"{BASE_URL}/reports/export.csv?date_from={date_from_str}&date_to={date_to_str}&scope=all"
        )
        assert csv_resp.status_code == 200, csv_resp.text
        assert "text/csv" in csv_resp.headers["content-type"]
        csv_text = csv_resp.text
        print("CSV Header & Sample rows:")
        print("\n".join(csv_text.splitlines()[:5]))

        assert "Mã giao dịch" in csv_text
        assert "Ăn liên hoan công ty" in csv_text
        assert "1200000.00" in csv_text
        assert "Freelance payment" in csv_text
        assert "Khoản chi nhầm đã xóa" not in csv_text

        print("\nAll financial assertions in Live Report verification PASSED!")
        return True

    finally:
        # Cleanup
        print("\n[Cleanup] Cleaning up isolated test user data from PostgreSQL...")
        try:
            with SessionLocal() as db:
                db.query(Transaction).filter(Transaction.user_id == uuid.UUID(user_id)).delete()
                db.query(Account).filter(Account.user_id == uuid.UUID(user_id)).delete()
                db.query(Category).filter(Category.user_id == uuid.UUID(user_id)).delete()
                db.query(User).filter(User.id == uuid.UUID(user_id)).delete()
                db.commit()
            print("[Cleanup] Cleanup completed successfully.")
        except Exception as e:  # noqa: BLE001
            print(f"[Cleanup Error] {e}")


if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
