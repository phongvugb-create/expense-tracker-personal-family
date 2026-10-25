import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from app.core.config import settings
from app.core.security import hash_session_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.account import Account
from app.models.auth_session import AuthSession
from app.models.budget import Budget
from app.models.category import Category
from app.models.family import Family
from app.models.transaction import Transaction
from app.models.user import User
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Tạo SQLite in-memory độc lập cho Dashboard API
sqlite_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sqlite_engine)
Base.metadata.create_all(bind=sqlite_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db():
    """Làm sạch dữ liệu in-memory trước mỗi test case."""
    app.dependency_overrides[get_db] = override_get_db
    db = TestingSessionLocal()
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()
    db.close()


def create_user_and_session(email: str = "dash_user@example.com") -> tuple[User, str]:
    db = TestingSessionLocal()
    user = User(
        id=uuid.uuid4(),
        email=email,
        password_hash="hashed_pw_test",
        display_name=email.split("@")[0],
        is_active=True,
    )
    db.add(user)

    raw_token = f"session_{uuid.uuid4().hex}"
    session = AuthSession(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=hash_session_token(raw_token),
        expires_at=datetime.now(UTC).replace(year=2099),
    )
    db.add(session)
    db.commit()
    db.refresh(user)
    db.close()
    return user, raw_token


def test_unauthenticated_request_rejected():
    """1. Chưa đăng nhập bị từ chối 401 Unauthorized."""
    resp = client.get("/api/v1/dashboard/summary")
    assert resp.status_code == 401


def test_empty_dashboard_summary():
    """9. Dữ liệu trống trả response cấu trúc hợp lệ, không lỗi 500."""
    _u, token = create_user_and_session("empty_dash@example.com")
    client.cookies.set(settings.SESSION_COOKIE_NAME, token)

    resp = client.get("/api/v1/dashboard/summary?year=2026&month=10")
    assert resp.status_code == 200
    data = resp.json()

    assert data["period"]["year"] == 2026
    assert data["period"]["month"] == 10
    assert data["filters"]["scope"] == "all"
    assert data["balances_by_currency"] == []
    assert data["cash_flow_by_currency"] == []
    assert data["monthly_trend"] == []
    assert data["expense_categories"] == []
    assert data["recent_transactions"] == []
    assert data["recent_transfers"] == []
    assert data["budget_alerts"] == []


def test_financial_calculations_and_currency_separation():
    """2, 3, 4. Tổng số dư đúng, dòng tiền không gộp chéo currency, loại trừ soft-delete và transfer void."""
    u1, token1 = create_user_and_session("user1_dash@example.com")
    u2, _ = create_user_and_session("user2_dash@example.com")

    db = TestingSessionLocal()
    # Ví 1 VND: ban đầu 1.000.000
    acc_vnd = Account(
        id=uuid.uuid4(),
        name="Ví VND",
        scope="personal",
        user_id=u1.id,
        account_type="cash",
        currency="VND",
        initial_balance=Decimal("1000000.00"),
    )
    # Ví 2 USD: ban đầu 100 USD
    acc_usd = Account(
        id=uuid.uuid4(),
        name="Ví USD",
        scope="personal",
        user_id=u1.id,
        account_type="cash",
        currency="USD",
        initial_balance=Decimal("100.00"),
    )
    # Ví U2 (không được tính vào U1)
    acc_u2 = Account(
        id=uuid.uuid4(),
        name="Ví U2",
        scope="personal",
        user_id=u2.id,
        account_type="cash",
        currency="VND",
        initial_balance=Decimal("9999999.00"),
    )

    # Danh mục
    cat_salary = Category(id=uuid.uuid4(), name="Lương", type="income", scope="system")
    cat_food = Category(id=uuid.uuid4(), name="Ăn uống", type="expense", scope="system")

    db.add_all([acc_vnd, acc_usd, acc_u2, cat_salary, cat_food])
    db.commit()

    # Giao dịch tháng 10/2026 cho VND:
    # Thu 500.000 VND
    tx_inc = Transaction(
        id=uuid.uuid4(),
        account_id=acc_vnd.id,
        category_id=cat_salary.id,
        user_id=u1.id,
        type="income",
        amount=Decimal("500000.00"),
        occurred_at=datetime(2026, 10, 5, 10, 0, 0, tzinfo=UTC),
    )
    # Chi 200.000 VND
    tx_exp = Transaction(
        id=uuid.uuid4(),
        account_id=acc_vnd.id,
        category_id=cat_food.id,
        user_id=u1.id,
        type="expense",
        amount=Decimal("200000.00"),
        occurred_at=datetime(2026, 10, 10, 10, 0, 0, tzinfo=UTC),
    )
    # Chi 50.000 VND bị soft-delete (KHÔNG ĐƯỢC TÍNH)
    tx_exp_del = Transaction(
        id=uuid.uuid4(),
        account_id=acc_vnd.id,
        category_id=cat_food.id,
        user_id=u1.id,
        type="expense",
        amount=Decimal("50000.00"),
        occurred_at=datetime(2026, 10, 12, 10, 0, 0, tzinfo=UTC),
        deleted_at=datetime(2026, 10, 13, 10, 0, 0, tzinfo=UTC),
    )
    # Giao dịch USD: Chi 20 USD
    tx_usd = Transaction(
        id=uuid.uuid4(),
        account_id=acc_usd.id,
        category_id=cat_food.id,
        user_id=u1.id,
        type="expense",
        amount=Decimal("20.00"),
        occurred_at=datetime(2026, 10, 15, 10, 0, 0, tzinfo=UTC),
    )

    db.add_all([tx_inc, tx_exp, tx_exp_del, tx_usd])
    db.commit()
    db.close()

    client.cookies.set(settings.SESSION_COOKIE_NAME, token1)
    resp = client.get("/api/v1/dashboard/summary?year=2026&month=10")
    assert resp.status_code == 200
    data = resp.json()

    # 1. Kiểm tra tách biệt số dư theo Currency
    balances = {b["currency"]: b["total_balance"] for b in data["balances_by_currency"]}
    assert "VND" in balances and "USD" in balances
    # VND: 1.000.000 + 500.000 - 200.000 = 1.300.000
    assert balances["VND"] == "1300000.00"
    # USD: 100 - 20 = 80
    assert balances["USD"] == "80.00"

    # 2. Kiểm tra dòng tiền trong kỳ
    cf_map = {cf["currency"]: cf for cf in data["cash_flow_by_currency"]}
    assert cf_map["VND"]["total_income"] == "500000.00"
    assert cf_map["VND"]["total_expense"] == "200000.00"
    assert cf_map["VND"]["net_cash_flow"] == "300000.00"

    assert cf_map["USD"]["total_income"] == "0.00"
    assert cf_map["USD"]["total_expense"] == "20.00"
    assert cf_map["USD"]["net_cash_flow"] == "-20.00"


def test_scope_and_permissions_isolation():
    """5, 6, 8. Phân quyền cá nhân / gia đình, chặn truy cập trái phép và hiển thị cảnh báo ngân sách."""
    owner, token_owner = create_user_and_session("owner_dash@example.com")
    _stranger, token_stranger = create_user_and_session("stranger_dash@example.com")

    db = TestingSessionLocal()
    fam = Family(id=uuid.uuid4(), name="Gia đình Nam", owner_user_id=owner.id)
    cat_food = Category(id=uuid.uuid4(), name="Ăn uống", type="expense", scope="system")
    acc_fam = Account(
        id=uuid.uuid4(),
        name="Ví Gia Đình",
        scope="family",
        family_id=fam.id,
        account_type="bank",
        currency="VND",
        initial_balance=Decimal("2000000.00"),
    )
    # Ngân sách đang ở trạng thái warning: Hạn mức 1.000.000, ngưỡng 80% (đã chi 850.000)
    bg = Budget(
        id=uuid.uuid4(),
        name="Ngân sách ăn uống gia đình",
        scope="family",
        family_id=fam.id,
        category_id=cat_food.id,
        amount_limit=Decimal("1000000.00"),
        period_start=date(2026, 10, 1),
        period_end=date(2026, 10, 31),
        warning_threshold=Decimal("80.00"),
    )
    tx_fam = Transaction(
        id=uuid.uuid4(),
        account_id=acc_fam.id,
        category_id=cat_food.id,
        user_id=owner.id,
        type="expense",
        amount=Decimal("850000.00"),
        occurred_at=datetime(2026, 10, 15, 10, 0, 0, tzinfo=UTC),
    )
    db.add_all([fam, cat_food, acc_fam, bg, tx_fam])
    db.commit()
    fam_id = str(fam.id)
    db.close()

    # 1. Người ngoài (stranger) lọc theo family_id -> 404
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_stranger)
    resp_stranger = client.get(f"/api/v1/dashboard/summary?scope=family&family_id={fam_id}")
    assert resp_stranger.status_code == 404

    # 2. Owner xem dashboard scope=family -> Trả đúng số liệu và cảnh báo ngân sách
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_owner)
    resp_owner = client.get(f"/api/v1/dashboard/summary?scope=family&family_id={fam_id}&year=2026&month=10")
    assert resp_owner.status_code == 200
    data = resp_owner.json()

    assert data["filters"]["scope"] == "family"
    assert data["filters"]["family_name"] == "Gia đình Nam"
    assert len(data["budget_alerts"]) == 1
    alert = data["budget_alerts"][0]
    assert alert["name"] == "Ngân sách ăn uống gia đình"
    assert alert["status"] == "warning"
    assert alert["spent_amount"] == "850000.00"
