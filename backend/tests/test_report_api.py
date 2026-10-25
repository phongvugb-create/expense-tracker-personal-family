import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from app.core.config import settings
from app.core.security import hash_session_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.account import Account
from app.models.auth_session import AuthSession
from app.models.category import Category
from app.models.family import Family
from app.models.transaction import Transaction
from app.models.transfer import Transfer
from app.models.user import User
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Tạo SQLite in-memory độc lập cho Report API
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


def create_user_and_session(email: str = "report_user@example.com") -> tuple[User, str]:
    db = TestingSessionLocal()
    user = User(
        id=uuid.uuid4(),
        email=email,
        password_hash="hashed_pw_test",
        display_name=email.split("@")[0],
        is_active=True,
    )
    db.add(user)

    raw_token = f"tok_{uuid.uuid4().hex}"
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


def test_reports_unauthenticated_fails():
    """1. Kiểm tra chưa đăng nhập bị từ chối 401."""
    # Tạo test client mới không có cookie
    unauth_client = TestClient(app)

    r_summary = unauth_client.get("/api/v1/reports/summary?date_from=2026-10-01&date_to=2026-10-31")
    assert r_summary.status_code == 401

    r_csv = unauth_client.get("/api/v1/reports/export.csv?date_from=2026-10-01&date_to=2026-10-31")
    assert r_csv.status_code == 401


def test_reports_invalid_date_range():
    """2. Ngày không hợp lệ: date_from > date_to -> 400 Bad Request."""
    _user, token = create_user_and_session()
    client.cookies.set(settings.SESSION_COOKIE_NAME, token)

    res = client.get("/api/v1/reports/summary?date_from=2026-10-31&date_to=2026-10-01")
    assert res.status_code == 400
    assert "date_from" in res.json()["detail"]


def test_reports_empty_data():
    """3. Khoảng thời gian không có dữ liệu trả response hợp lệ với số tổng = 0."""
    _user, token = create_user_and_session()
    client.cookies.set(settings.SESSION_COOKIE_NAME, token)

    res = client.get("/api/v1/reports/summary?date_from=2026-10-01&date_to=2026-10-31")
    assert res.status_code == 200
    data = res.json()
    assert data["period"]["days_count"] == 31
    assert len(data["cash_flow_by_currency"]) == 0
    assert len(data["category_breakdown"]) == 0
    assert len(data["top_expenses"]) == 0


def test_reports_cash_flow_soft_delete_and_void():
    """4. Kiểm tra dòng tiền, phân tách tiền tệ VND/USD, loại trừ soft-delete và transfer void."""
    user, token = create_user_and_session()
    user_id = user.id
    db = TestingSessionLocal()

    # Tạo 2 ví cá nhân: VND và USD
    acc_vnd = Account(
        id=uuid.uuid4(),
        user_id=user_id,
        name="Ví Tiền Mặt",
        account_type="cash",
        currency="VND",
        scope="personal",
        initial_balance=Decimal("1000000.00"),
    )
    acc_usd = Account(
        id=uuid.uuid4(),
        user_id=user_id,
        name="Ví USD",
        account_type="bank",
        currency="USD",
        scope="personal",
        initial_balance=Decimal("100.00"),
    )
    db.add_all([acc_vnd, acc_usd])
    db.commit()

    cat_food = Category(
        id=uuid.uuid4(),
        user_id=user_id,
        name="Ăn uống",
        type="expense",
        scope="personal",
    )
    cat_salary = Category(
        id=uuid.uuid4(),
        user_id=user_id,
        name="Tiền lương",
        type="income",
        scope="personal",
    )
    db.add_all([cat_food, cat_salary])
    db.commit()

    d1 = datetime(2026, 10, 5, 10, 0, tzinfo=UTC)
    d2 = datetime(2026, 10, 10, 12, 0, tzinfo=UTC)

    # 1. Income VND 3,000,000
    tx1 = Transaction(
        id=uuid.uuid4(),
        account_id=acc_vnd.id,
        user_id=user_id,
        category_id=cat_salary.id,
        type="income",
        amount=Decimal("3000000.00"),
        occurred_at=d1,
    )
    # 2. Expense VND 600,000
    tx2 = Transaction(
        id=uuid.uuid4(),
        account_id=acc_vnd.id,
        user_id=user_id,
        category_id=cat_food.id,
        type="expense",
        amount=Decimal("600000.00"),
        occurred_at=d2,
    )
    # 3. Soft-deleted expense VND 999,999 (phải bị loại)
    tx3_del = Transaction(
        id=uuid.uuid4(),
        account_id=acc_vnd.id,
        user_id=user_id,
        category_id=cat_food.id,
        type="expense",
        amount=Decimal("999999.00"),
        occurred_at=d2,
        deleted_at=datetime.now(UTC),
    )
    # 4. Income USD 50
    tx4_usd = Transaction(
        id=uuid.uuid4(),
        account_id=acc_usd.id,
        user_id=user_id,
        category_id=cat_salary.id,
        type="income",
        amount=Decimal("50.00"),
        occurred_at=d1,
    )
    # 5. Transfer voided fee VND 5,000 (phải bị loại)
    tr_void = Transfer(
        id=uuid.uuid4(),
        created_by=user_id,
        from_account_id=acc_vnd.id,
        to_account_id=acc_usd.id,
        amount=Decimal("100000.00"),
        fee_amount=Decimal("5000.00"),
        occurred_at=d2,
        voided_at=datetime.now(UTC),
    )
    db.add(tr_void)
    db.commit()

    tx_fee_void = Transaction(
        id=uuid.uuid4(),
        account_id=acc_vnd.id,
        user_id=user_id,
        category_id=cat_food.id,
        transfer_id=tr_void.id,
        type="transfer_fee",
        amount=Decimal("5000.00"),
        occurred_at=d2,
    )

    db.add_all([tx1, tx2, tx3_del, tx4_usd, tx_fee_void])
    db.commit()
    db.close()

    client.cookies.set(settings.SESSION_COOKIE_NAME, token)

    res = client.get("/api/v1/reports/summary?date_from=2026-10-01&date_to=2026-10-31")
    assert res.status_code == 200
    data = res.json()

    # Kiểm tra dòng tiền phân tách theo Currency
    cf_map = {c["currency"]: c for c in data["cash_flow_by_currency"]}
    assert "VND" in cf_map
    assert "USD" in cf_map

    vnd_cf = cf_map["VND"]
    assert Decimal(vnd_cf["total_income"]) == Decimal("3000000.00")
    assert Decimal(vnd_cf["total_expense"]) == Decimal("600000.00")
    assert Decimal(vnd_cf["total_transfer_fee"]) == Decimal("0.00")  # Fee của voided transfer bị loại
    assert Decimal(vnd_cf["net_cash_flow"]) == Decimal("2400000.00")

    usd_cf = cf_map["USD"]
    assert Decimal(usd_cf["total_income"]) == Decimal("50.00")
    assert Decimal(usd_cf["total_expense"]) == Decimal("0.00")
    assert Decimal(usd_cf["net_cash_flow"]) == Decimal("50.00")

    # Kiểm tra danh mục
    cats = data["category_breakdown"]
    assert len(cats) == 1
    assert cats[0]["category_name"] == "Ăn uống"
    assert Decimal(cats[0]["total_amount"]) == Decimal("600000.00")
    assert Decimal(cats[0]["percentage"]) == Decimal("100.00")

    # Kiểm tra Top expenses (chỉ có 1 bản ghi hợp lệ, tx3_del đã bị loại)
    top_exps = data["top_expenses"]
    assert len(top_exps) == 1
    assert Decimal(top_exps[0]["amount"]) == Decimal("600000.00")


def test_reports_family_permissions_and_export_csv():
    """5. Kiểm tra phân quyền gia đình và xuất file CSV."""
    owner, token_owner = create_user_and_session("fam_owner@example.com")
    _stranger, token_stranger = create_user_and_session("fam_stranger@example.com")
    owner_id = owner.id

    db = TestingSessionLocal()
    fam = Family(id=uuid.uuid4(), name="Gia Đình Hạnh Phúc", owner_user_id=owner_id)
    db.add(fam)
    db.commit()
    fam_id = str(fam.id)

    fam_acc = Account(
        id=uuid.uuid4(),
        user_id=None,
        family_id=fam.id,
        name="Quỹ Chung Gia Đình",
        account_type="bank",
        currency="VND",
        scope="family",
        initial_balance=Decimal("20000000.00"),
    )
    db.add(fam_acc)

    cat_fam = Category(
        id=uuid.uuid4(),
        user_id=None,
        family_id=fam.id,
        name="Mua sắm gia đình",
        type="expense",
        scope="family",
    )
    db.add(cat_fam)
    db.commit()

    tx = Transaction(
        id=uuid.uuid4(),
        account_id=fam_acc.id,
        user_id=owner_id,
        category_id=cat_fam.id,
        type="expense",
        amount=Decimal("1500000.00"),
        occurred_at=datetime(2026, 10, 15, 8, 30, tzinfo=UTC),
        note="Đi siêu thị cả nhà",
    )
    db.add(tx)
    db.commit()
    db.close()

    # 1. Người lạ truy vấn gia đình này -> 403 Forbidden
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_stranger)
    res_forbidden = client.get(
        f"/api/v1/reports/summary?date_from=2026-10-01&date_to=2026-10-31&scope=family&family_id={fam_id}"
    )
    assert res_forbidden.status_code == 403

    # 2. Chủ gia đình truy vấn thành công
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_owner)
    res_ok = client.get(
        f"/api/v1/reports/summary?date_from=2026-10-01&date_to=2026-10-31&scope=family&family_id={fam_id}"
    )
    assert res_ok.status_code == 200
    assert len(res_ok.json()["top_expenses"]) == 1

    # 3. Xuất CSV
    res_csv = client.get(
        f"/api/v1/reports/export.csv?date_from=2026-10-01&date_to=2026-10-31&scope=family&family_id={fam_id}"
    )
    assert res_csv.status_code == 200
    assert res_csv.headers["content-type"].startswith("text/csv")
    csv_text = res_csv.text
    assert "Mã giao dịch" in csv_text
    assert "Đi siêu thị cả nhà" in csv_text
    assert "1500000.00" in csv_text
