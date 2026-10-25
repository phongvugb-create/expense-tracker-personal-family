"""Verify live dashboard flow on PostgreSQL 18.

This script tests the GET /api/v1/dashboard/summary endpoint against a running
FastAPI backend and PostgreSQL 18 database with an isolated test user.
"""

import sys
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import httpx
from app.db.session import SessionLocal
from app.models.account import Account
from app.models.budget import Budget
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

    print("\n[2] Testing unauthenticated access to /dashboard/summary...")
    resp = client.get(f"{BASE_URL}/dashboard/summary")
    if resp.status_code != 401:
        print(f"FAILED: Expected 401 Unauthenticated, got {resp.status_code}")
        return False
    print("401 Unauthenticated check PASSED")

    # 3. Register and login isolated user
    suffix = uuid.uuid4().hex[:8]
    email = f"dash_test_{suffix}@example.com"
    password = "LivePassword123!"
    display_name = f"Dashboard Test User {suffix}"

    print(f"\n[3] Registering isolated user: {email}...")
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
    current_year = now.year
    current_month = now.month

    try:
        # 4. Check initial empty dashboard
        print(f"\n[4] Querying empty dashboard summary for {current_year}/{current_month}...")
        resp = client.get(f"{BASE_URL}/dashboard/summary?year={current_year}&month={current_month}&scope=all")
        if resp.status_code != 200:
            print(f"FAILED: Initial dashboard returned {resp.status_code}: {resp.text}")
            return False
        data = resp.json()
        assert len(data["balances_by_currency"]) == 0
        assert len(data["cash_flow_by_currency"]) == 0
        assert len(data["recent_transactions"]) == 0
        print("Initial empty dashboard PASSED")

        # 5. Create accounts: 1 VND (initial 1,000,000) and 1 USD (initial 50)
        print("\n[5] Creating VND and USD wallets...")
        acc_vnd_resp = client.post(
            f"{BASE_URL}/accounts",
            json={
                "name": "Live VND Wallet",
                "scope": "personal",
                "account_type": "cash",
                "currency": "VND",
                "initial_balance": "1000000.00",
                "color": "#10B981",
            },
        )
        assert acc_vnd_resp.status_code == 201, acc_vnd_resp.text
        vnd_acc_id = acc_vnd_resp.json()["id"]

        acc_usd_resp = client.post(
            f"{BASE_URL}/accounts",
            json={
                "name": "Live USD Wallet",
                "scope": "personal",
                "account_type": "bank",
                "currency": "USD",
                "initial_balance": "50.00",
                "color": "#3B82F6",
            },
        )
        assert acc_usd_resp.status_code == 201, acc_usd_resp.text
        acc_usd_resp.json()["id"]
        print("Wallets created successfully")

        # 6. Fetch categories
        cat_resp = client.get(f"{BASE_URL}/categories?scope=system")
        assert cat_resp.status_code == 200, cat_resp.text
        categories = cat_resp.json()
        income_cats = [c for c in categories if c["type"] == "income"]
        expense_cats = [c for c in categories if c["type"] == "expense"]

        salary_cat_id = income_cats[0]["id"] if income_cats else None
        food_cat_id = expense_cats[0]["id"] if expense_cats else None

        # 7. Add Income transaction (VND 5,000,000) and Expense (VND 500,000)
        print("\n[7] Creating transactions (Income 5,000,000 & Expense 500,000 VND)...")
        tx_in = client.post(
            f"{BASE_URL}/transactions",
            json={
                "account_id": vnd_acc_id,
                "category_id": salary_cat_id,
                "type": "income",
                "amount": "5000000.00",
                "occurred_at": now.isoformat(),
                "description": "Salary deposit",
            },
        )
        assert tx_in.status_code == 201, tx_in.text

        tx_out = client.post(
            f"{BASE_URL}/transactions",
            json={
                "account_id": vnd_acc_id,
                "category_id": food_cat_id,
                "type": "expense",
                "amount": "500000.00",
                "occurred_at": now.isoformat(),
                "description": "Grocery shopping",
            },
        )
        assert tx_out.status_code == 201, tx_out.text

        # 8. Add a soft-deleted transaction (should be excluded)
        tx_del = client.post(
            f"{BASE_URL}/transactions",
            json={
                "account_id": vnd_acc_id,
                "category_id": food_cat_id,
                "type": "expense",
                "amount": "999999.00",
                "occurred_at": now.isoformat(),
                "description": "Deleted expense",
            },
        )
        assert tx_del.status_code == 201
        del_id = tx_del.json()["id"]
        del_resp = client.delete(f"{BASE_URL}/transactions/{del_id}")
        assert del_resp.status_code == 200 or del_resp.status_code == 204

        # 9. Create a Budget with warning/exceeded threshold
        print("\n[9] Creating a budget with limit 400,000 (spent 500,000 -> exceeded)...")
        b_resp = client.post(
            f"{BASE_URL}/budgets",
            json={
                "name": "Live Test Food Budget",
                "scope": "personal",
                "category_id": food_cat_id,
                "amount_limit": "400000.00",
                "period_start": f"{current_year}-{current_month:02d}-01",
                "period_end": f"{current_year}-{current_month:02d}-28",
                "warning_threshold": "80.00",
            },
        )
        assert b_resp.status_code == 201, b_resp.text

        # 10. Query Dashboard Summary and verify calculations
        print("\n[10] Querying Dashboard Summary with active data...")
        dash_resp = client.get(f"{BASE_URL}/dashboard/summary?year={current_year}&month={current_month}&scope=all")
        assert dash_resp.status_code == 200, dash_resp.text
        summary = dash_resp.json()

        # Check balances
        balances = {b["currency"]: Decimal(b["total_balance"]) for b in summary["balances_by_currency"]}
        print(f"Balances by currency: {balances}")
        # VND: 1,000,000 + 5,000,000 - 500,000 = 5,500,000
        assert balances["VND"] == Decimal("5500000.00"), f"Expected VND 5500000, got {balances.get('VND')}"
        assert balances["USD"] == Decimal("50.00"), f"Expected USD 50, got {balances.get('USD')}"

        # Check cash flow
        cash_flow = {cf["currency"]: cf for cf in summary["cash_flow_by_currency"]}
        vnd_cf = cash_flow["VND"]
        print(f"VND Cash Flow: {vnd_cf}")
        assert Decimal(vnd_cf["total_income"]) == Decimal("5000000.00")
        assert Decimal(vnd_cf["total_expense"]) == Decimal("500000.00")
        assert Decimal(vnd_cf["net_cash_flow"]) == Decimal("4500000.00")

        # Check budget alert
        alerts = summary["budget_alerts"]
        print(f"Budget alerts count: {len(alerts)}")
        assert len(alerts) >= 1
        assert alerts[0]["status"] == "exceeded"

        # Check recent transactions
        recents = summary["recent_transactions"]
        print(f"Recent transactions count: {len(recents)}")
        assert len(recents) == 2
        # Deleted transaction should NOT be in recent_transactions
        assert all(t["id"] != del_id for t in recents)

        # Check expense categories
        exp_cats = summary["expense_categories"]
        assert len(exp_cats) == 1
        assert Decimal(exp_cats[0]["total_amount"]) == Decimal("500000.00")
        assert Decimal(exp_cats[0]["percentage"]) == Decimal("100.00")

        print("\nAll financial assertions in Live Dashboard verification PASSED!")
        return True

    finally:
        # Cleanup
        print("\n[Cleanup] Cleaning up isolated test user data from PostgreSQL...")
        try:
            with SessionLocal() as db:
                # Delete transactions
                db.query(Transaction).filter(Transaction.user_id == uuid.UUID(user_id)).delete()
                # Delete budgets
                db.query(Budget).filter(Budget.user_id == uuid.UUID(user_id)).delete()
                # Delete accounts
                db.query(Account).filter(Account.user_id == uuid.UUID(user_id)).delete()
                # Delete user
                db.query(User).filter(User.id == uuid.UUID(user_id)).delete()
                db.commit()
            print("[Cleanup] Cleanup completed successfully.")
        except Exception as e:  # noqa: BLE001
            print(f"[Cleanup Error] {e}")


if __name__ == "__main__":
    success = run_verification()
    sys.exit(0 if success else 1)
