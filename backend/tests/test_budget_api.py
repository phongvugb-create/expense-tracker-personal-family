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
from app.models.family_member import FamilyMember
from app.models.transaction import Transaction
from app.models.transfer import Transfer
from app.models.user import User
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Tạo in-memory SQLite engine độc lập cho bộ test Budget API
sqlite_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sqlite_engine)

# Tạo bảng từ Base metadata trên SQLite in-memory
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
    """Làm sạch dữ liệu in-memory trước mỗi test case mà không chạm tới PostgreSQL."""
    app.dependency_overrides[get_db] = override_get_db
    db = TestingSessionLocal()
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()
    db.close()


def create_user_and_session(email: str = "budget_user@example.com") -> tuple[User, str]:
    """Helper tạo User và AuthSession hợp lệ."""
    db = TestingSessionLocal()
    user = User(
        id=uuid.uuid4(),
        email=email,
        password_hash="hashed_pw_test",
        display_name=email.split("@")[0],
        is_active=True,
    )
    db.add(user)

    raw_token = f"test_session_token_{uuid.uuid4().hex}"
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


def create_test_category(
    name: str = "Ăn uống",
    scope: str = "system",
    user_id: uuid.UUID | None = None,
    family_id: uuid.UUID | None = None,
    type_: str = "expense",
    is_archived: bool = False,
) -> Category:
    """Helper tạo Category cho test."""
    db = TestingSessionLocal()
    cat = Category(
        id=uuid.uuid4(),
        name=name,
        type=type_,
        scope=scope,
        user_id=user_id,
        family_id=family_id,
        is_archived=is_archived,
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    db.close()
    return cat


def create_test_account(
    user_id: uuid.UUID | None = None,
    family_id: uuid.UUID | None = None,
    scope: str = "personal",
    name: str = "Ví tiền mặt",
    initial_balance: Decimal = Decimal("5000000.00"),
) -> Account:
    """Helper tạo Account cho test."""
    db = TestingSessionLocal()
    acc = Account(
        id=uuid.uuid4(),
        name=name,
        scope=scope,
        user_id=user_id,
        family_id=family_id,
        account_type="cash",
        currency="VND",
        initial_balance=initial_balance,
    )
    db.add(acc)
    db.commit()
    db.refresh(acc)
    db.close()
    return acc


def create_test_family(owner: User, name: str = "Gia đình Hạnh Phúc") -> Family:
    """Helper tạo Family."""
    db = TestingSessionLocal()
    fam = Family(
        id=uuid.uuid4(),
        name=name,
        owner_user_id=owner.id,
    )
    db.add(fam)
    db.commit()
    db.refresh(fam)
    db.close()
    return fam


# ==============================================================================
# 1. TEST XÁC THỰC VÀ PHÂN QUYỀN TRUY CẬP (CRUD, AUTHENTICATION, ROLES)
# ==============================================================================


def test_unauthenticated_request_rejected():
    """1. Chưa đăng nhập bị từ chối 401 Unauthorized."""
    resp = client.get("/api/v1/budgets")
    assert resp.status_code == 401


def test_create_personal_budget_success():
    """2. Tạo ngân sách cá nhân hợp lệ."""
    u1, token1 = create_user_and_session("u1@example.com")
    cat = create_test_category("Ăn uống", scope="system", type_="expense")

    payload = {
        "name": "Ngân sách ăn uống tháng 10",
        "scope": "personal",
        "category_id": str(cat.id),
        "amount_limit": "2000000.00",
        "period_start": "2026-10-01",
        "period_end": "2026-10-31",
        "warning_threshold": "80.00",
    }
    client.cookies.set(settings.SESSION_COOKIE_NAME, token1)
    resp = client.post("/api/v1/budgets", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Ngân sách ăn uống tháng 10"
    assert data["scope"] == "personal"
    assert data["user_id"] == str(u1.id)
    assert data["family_id"] is None
    assert data["amount_limit"] == "2000000.00"
    assert data["spent_amount"] == "0.00"
    assert data["remaining_amount"] == "2000000.00"
    assert data["overspent_amount"] == "0.00"
    assert data["usage_percentage"] == "0.00"
    assert data["status"] == "normal"
    assert data["is_archived"] is False


def test_cannot_forge_user_id():
    """4. Không thể giả mạo user_id (hệ thống tự lấy từ session)."""
    u1, token1 = create_user_and_session("u1@example.com")
    fake_user_id = str(uuid.uuid4())
    cat = create_test_category("Ăn uống", scope="system", type_="expense")

    payload = {
        "name": "Ngân sách cá nhân",
        "scope": "personal",
        "category_id": str(cat.id),
        "amount_limit": "1000000.00",
        "period_start": "2026-10-01",
        "period_end": "2026-10-31",
        "user_id": fake_user_id,  # client cố tình gửi user_id
    }
    client.cookies.set(settings.SESSION_COOKIE_NAME, token1)
    resp = client.post("/api/v1/budgets", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["user_id"] == str(u1.id)
    assert data["user_id"] != fake_user_id


def test_create_family_budget_roles_and_restrictions():
    """3 & 5 & 6. Phân quyền ngân sách gia đình: Owner/Editor được tạo, Viewer bị từ chối 403."""
    owner, token_owner = create_user_and_session("fam_owner@example.com")
    editor, token_editor = create_user_and_session("fam_editor@example.com")
    viewer, token_viewer = create_user_and_session("fam_viewer@example.com")
    _stranger, token_stranger = create_user_and_session("stranger@example.com")

    fam = create_test_family(owner, "Gia đình Tuấn")
    cat = create_test_category("Mua sắm gia đình", scope="family", family_id=fam.id, type_="expense")

    db = TestingSessionLocal()
    # Add editor & viewer members
    mem_editor = FamilyMember(
        id=uuid.uuid4(),
        family_id=fam.id,
        user_id=editor.id,
        role="editor",
    )
    mem_viewer = FamilyMember(
        id=uuid.uuid4(),
        family_id=fam.id,
        user_id=viewer.id,
        role="viewer",
    )
    db.add_all([mem_editor, mem_viewer])
    db.commit()
    db.close()

    budget_payload = {
        "name": "Ngân sách mua sắm chung",
        "scope": "family",
        "family_id": str(fam.id),
        "category_id": str(cat.id),
        "amount_limit": "5000000.00",
        "period_start": "2026-10-01",
        "period_end": "2026-10-31",
    }

    # 1. Viewer cố tạo -> 403 Forbidden
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_viewer)
    resp = client.post("/api/v1/budgets", json=budget_payload)
    assert resp.status_code == 403
    assert "không có quyền" in resp.json()["detail"]

    # 2. Người ngoài (stranger) cố tạo -> 404 Not Found (che giấu nhóm)
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_stranger)
    resp = client.post("/api/v1/budgets", json=budget_payload)
    assert resp.status_code == 404

    # 3. Editor tạo -> 201 Thành công
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_editor)
    resp = client.post("/api/v1/budgets", json=budget_payload)
    assert resp.status_code == 201
    b_id = resp.json()["id"]

    # 4. Viewer xem -> 200 Thành công
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_viewer)
    resp_view = client.get(f"/api/v1/budgets/{b_id}")
    assert resp_view.status_code == 200
    assert resp_view.json()["name"] == "Ngân sách mua sắm chung"

    # 5. Viewer cố sửa hoặc archive -> 403 Forbidden
    resp_update = client.patch(f"/api/v1/budgets/{b_id}", json={"name": "Hacking"})
    assert resp_update.status_code == 403

    resp_arch = client.post(f"/api/v1/budgets/{b_id}/archive")
    assert resp_arch.status_code == 403

    # 6. Owner sửa và archive -> 200 Thành công
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_owner)
    resp_update_owner = client.patch(f"/api/v1/budgets/{b_id}", json={"amount_limit": "6000000.00"})
    assert resp_update_owner.status_code == 200
    assert resp_update_owner.json()["amount_limit"] == "6000000.00"

    resp_arch_owner = client.post(f"/api/v1/budgets/{b_id}/archive")
    assert resp_arch_owner.status_code == 200
    assert resp_arch_owner.json()["is_archived"] is True

    # 7. Khôi phục (restore)
    resp_rest_owner = client.post(f"/api/v1/budgets/{b_id}/restore")
    assert resp_rest_owner.status_code == 200
    assert resp_rest_owner.json()["is_archived"] is False


def test_member_left_family_cannot_access():
    """7. Thành viên đã rời nhóm (left_at IS NOT NULL) không còn quyền truy cập."""
    owner, _token_owner = create_user_and_session("owner_left@example.com")
    ex_member, token_ex = create_user_and_session("ex_member@example.com")
    fam = create_test_family(owner, "Gia đình Cũ")
    cat = create_test_category("Đi chợ", scope="family", family_id=fam.id)

    db = TestingSessionLocal()
    mem = FamilyMember(
        id=uuid.uuid4(),
        family_id=fam.id,
        user_id=ex_member.id,
        role="editor",
        left_at=datetime.now(UTC),  # Đã rời nhóm
    )
    b = Budget(
        id=uuid.uuid4(),
        name="Ngân sách chợ",
        scope="family",
        family_id=fam.id,
        category_id=cat.id,
        amount_limit=Decimal("3000000.00"),
        period_start=date(2026, 10, 1),
        period_end=date(2026, 10, 31),
    )
    db.add_all([mem, b])
    db.commit()
    b_id = str(b.id)
    db.close()

    client.cookies.set(settings.SESSION_COOKIE_NAME, token_ex)
    resp = client.get(f"/api/v1/budgets/{b_id}")
    assert resp.status_code == 404


def test_validation_rules_and_restrictions():
    """8, 9, 10, 11. Các ràng buộc validation: amount_limit <= 0, period_end < period_start, threshold range, category validation."""
    _u1, token1 = create_user_and_session("valid_u1@example.com")
    cat_exp = create_test_category("Tiền điện", scope="system", type_="expense")
    cat_inc = create_test_category("Lương", scope="system", type_="income")
    cat_arch = create_test_category("Giải trí cũ", scope="system", type_="expense", is_archived=True)

    client.cookies.set(settings.SESSION_COOKIE_NAME, token1)

    # 8. amount_limit <= 0
    resp1 = client.post(
        "/api/v1/budgets",
        json={
            "name": "Lỗi tiền âm",
            "scope": "personal",
            "category_id": str(cat_exp.id),
            "amount_limit": "-100.00",
            "period_start": "2026-10-01",
            "period_end": "2026-10-31",
        },
    )
    assert resp1.status_code == 422

    # 9. period_end < period_start
    resp2 = client.post(
        "/api/v1/budgets",
        json={
            "name": "Lỗi ngày",
            "scope": "personal",
            "category_id": str(cat_exp.id),
            "amount_limit": "1000000.00",
            "period_start": "2026-10-31",
            "period_end": "2026-10-01",
        },
    )
    assert resp2.status_code == 422

    # 10. warning_threshold > 100 hoặc <= 0
    resp3 = client.post(
        "/api/v1/budgets",
        json={
            "name": "Lỗi ngưỡng",
            "scope": "personal",
            "category_id": str(cat_exp.id),
            "amount_limit": "1000000.00",
            "period_start": "2026-10-01",
            "period_end": "2026-10-31",
            "warning_threshold": "105.00",
        },
    )
    assert resp3.status_code == 422

    # 11a. Danh mục income -> 400
    resp4 = client.post(
        "/api/v1/budgets",
        json={
            "name": "Lỗi danh mục thu nhập",
            "scope": "personal",
            "category_id": str(cat_inc.id),
            "amount_limit": "1000000.00",
            "period_start": "2026-10-01",
            "period_end": "2026-10-31",
        },
    )
    assert resp4.status_code == 400
    assert "chỉ áp dụng cho danh mục loại 'expense'" in resp4.json()["detail"]

    # 11b. Danh mục lưu trữ -> 400
    resp5 = client.post(
        "/api/v1/budgets",
        json={
            "name": "Lỗi danh mục lưu trữ",
            "scope": "personal",
            "category_id": str(cat_arch.id),
            "amount_limit": "1000000.00",
            "period_start": "2026-10-01",
            "period_end": "2026-10-31",
        },
    )
    assert resp5.status_code == 400
    assert "đang bị lưu trữ" in resp5.json()["detail"]


# ==============================================================================
# 2. TEST TÍNH CHI TIÊU THỰC TẾ & CẢNH BÁO (SPENDING COMPUTATION & WARNINGS)
# ==============================================================================


def test_spending_computation_rules():
    """13-19. Kiểm tra toàn bộ quy tắc tính chi tiêu:
    - Expense đúng category + kỳ được tính.
    - Income không được tính.
    - Ví khác / user khác không được tính.
    - Soft-deleted transaction không được tính.
    - Giao dịch ngoài kỳ không được tính.
    - Transfer void bị loại trừ (kể cả transfer_fee).
    """
    u1, token1 = create_user_and_session("calc_u1@example.com")
    u2, _ = create_user_and_session("calc_u2@example.com")

    cat_food = create_test_category("Cơm trưa", scope="system", type_="expense")
    cat_other = create_test_category("Khác", scope="system", type_="expense")

    acc_u1_a = create_test_account(user_id=u1.id, name="Ví U1 A")
    acc_u1_b = create_test_account(user_id=u1.id, name="Ví U1 B")
    acc_u2 = create_test_account(user_id=u2.id, name="Ví U2")

    # Tạo budget từ 2026-10-01 đến 2026-10-31 với limit 1.000.000 VND
    db = TestingSessionLocal()
    b = Budget(
        id=uuid.uuid4(),
        name="Ngân sách ăn trưa",
        scope="personal",
        user_id=u1.id,
        category_id=cat_food.id,
        amount_limit=Decimal("1000000.00"),
        period_start=date(2026, 10, 1),
        period_end=date(2026, 10, 31),
        warning_threshold=Decimal("80.00"),
    )
    db.add(b)
    db.commit()

    # 1. Giao dịch hợp lệ 1: 300.000 VND trên Ví A (trong kỳ)
    tx1 = Transaction(
        id=uuid.uuid4(),
        account_id=acc_u1_a.id,
        category_id=cat_food.id,
        user_id=u1.id,
        type="expense",
        amount=Decimal("300000.00"),
        occurred_at=datetime(2026, 10, 5, 12, 0, 0, tzinfo=UTC),
    )
    # 2. Giao dịch hợp lệ 2: 200.000 VND trên Ví B (trong kỳ)
    tx2 = Transaction(
        id=uuid.uuid4(),
        account_id=acc_u1_b.id,
        category_id=cat_food.id,
        user_id=u1.id,
        type="expense",
        amount=Decimal("200000.00"),
        occurred_at=datetime(2026, 10, 15, 19, 30, 0, tzinfo=UTC),
    )
    # 3. Giao dịch income: 500.000 VND (KHÔNG ĐƯỢC TÍNH)
    tx3 = Transaction(
        id=uuid.uuid4(),
        account_id=acc_u1_a.id,
        category_id=cat_food.id,
        user_id=u1.id,
        type="income",
        amount=Decimal("500000.00"),
        occurred_at=datetime(2026, 10, 10, 10, 0, 0, tzinfo=UTC),
    )
    # 4. Giao dịch danh mục khác: 150.000 VND (KHÔNG ĐƯỢC TÍNH)
    tx4 = Transaction(
        id=uuid.uuid4(),
        account_id=acc_u1_a.id,
        category_id=cat_other.id,
        user_id=u1.id,
        type="expense",
        amount=Decimal("150000.00"),
        occurred_at=datetime(2026, 10, 12, 10, 0, 0, tzinfo=UTC),
    )
    # 5. Giao dịch của User 2 trên ví U2: 400.000 VND (KHÔNG ĐƯỢC TÍNH)
    tx5 = Transaction(
        id=uuid.uuid4(),
        account_id=acc_u2.id,
        category_id=cat_food.id,
        user_id=u2.id,
        type="expense",
        amount=Decimal("400000.00"),
        occurred_at=datetime(2026, 10, 14, 10, 0, 0, tzinfo=UTC),
    )
    # 6. Giao dịch soft-deleted: 100.000 VND (KHÔNG ĐƯỢC TÍNH)
    tx6 = Transaction(
        id=uuid.uuid4(),
        account_id=acc_u1_a.id,
        category_id=cat_food.id,
        user_id=u1.id,
        type="expense",
        amount=Decimal("100000.00"),
        occurred_at=datetime(2026, 10, 20, 10, 0, 0, tzinfo=UTC),
        deleted_at=datetime(2026, 10, 21, 10, 0, 0, tzinfo=UTC),
    )
    # 7. Giao dịch ngoài kỳ: tháng 9 (100k) và tháng 11 (200k) (KHÔNG ĐƯỢC TÍNH)
    tx7_before = Transaction(
        id=uuid.uuid4(),
        account_id=acc_u1_a.id,
        category_id=cat_food.id,
        user_id=u1.id,
        type="expense",
        amount=Decimal("100000.00"),
        occurred_at=datetime(2026, 9, 30, 23, 59, 59, tzinfo=UTC),
    )
    tx7_after = Transaction(
        id=uuid.uuid4(),
        account_id=acc_u1_a.id,
        category_id=cat_food.id,
        user_id=u1.id,
        type="expense",
        amount=Decimal("200000.00"),
        occurred_at=datetime(2026, 11, 1, 0, 0, 0, tzinfo=UTC),
    )

    # 8. Phí chuyển tiền hợp lệ (transfer_fee): 10.000 VND (ĐƯỢC TÍNH)
    tr_valid = Transfer(
        id=uuid.uuid4(),
        from_account_id=acc_u1_a.id,
        to_account_id=acc_u1_b.id,
        created_by=u1.id,
        amount=Decimal("50000.00"),
        fee_amount=Decimal("10000.00"),
        occurred_at=datetime(2026, 10, 16, 10, 0, 0, tzinfo=UTC),
    )
    tx_fee_valid = Transaction(
        id=uuid.uuid4(),
        account_id=acc_u1_a.id,
        category_id=cat_food.id,
        transfer_id=tr_valid.id,
        user_id=u1.id,
        type="transfer_fee",
        amount=Decimal("10000.00"),
        occurred_at=datetime(2026, 10, 16, 10, 0, 0, tzinfo=UTC),
    )

    # 9. Phí chuyển tiền của Transfer đã VOID: 5.000 VND (KHÔNG ĐƯỢC TÍNH)
    tr_voided = Transfer(
        id=uuid.uuid4(),
        from_account_id=acc_u1_a.id,
        to_account_id=acc_u1_b.id,
        created_by=u1.id,
        amount=Decimal("50000.00"),
        fee_amount=Decimal("5000.00"),
        occurred_at=datetime(2026, 10, 17, 10, 0, 0, tzinfo=UTC),
        voided_at=datetime(2026, 10, 18, 10, 0, 0, tzinfo=UTC),
    )
    tx_fee_voided = Transaction(
        id=uuid.uuid4(),
        account_id=acc_u1_a.id,
        category_id=cat_food.id,
        transfer_id=tr_voided.id,
        user_id=u1.id,
        type="transfer_fee",
        amount=Decimal("5000.00"),
        occurred_at=datetime(2026, 10, 17, 10, 0, 0, tzinfo=UTC),
    )

    db.add_all([
        tx1, tx2, tx3, tx4, tx5, tx6, tx7_before, tx7_after,
        tr_valid, tx_fee_valid, tr_voided, tx_fee_voided
    ])
    db.commit()
    b_id = str(b.id)
    db.close()

    # Tổng chi kỳ vọng:
    # tx1 (300k) + tx2 (200k) + tx_fee_valid (10k) = 510.000 VND
    client.cookies.set(settings.SESSION_COOKIE_NAME, token1)
    resp = client.get(f"/api/v1/budgets/{b_id}")
    assert resp.status_code == 200
    data = resp.json()

    assert data["spent_amount"] == "510000.00"
    assert data["remaining_amount"] == "490000.00"  # 1.000.000 - 510.000
    assert data["overspent_amount"] == "0.00"
    assert data["usage_percentage"] == "51.00"
    assert data["status"] == "normal"


def test_warning_threshold_states_and_exceeded():
    """22-26. Kiểm tra các trạng thái cảnh báo: normal, warning đúng 80%, warning > 80% < 100%, exceeded đúng 100%, exceeded > 100%."""
    u, token = create_user_and_session("alert_u@example.com")
    cat = create_test_category("Cảnh báo test", scope="system", type_="expense")
    acc = create_test_account(user_id=u.id)

    db = TestingSessionLocal()
    # Hạn mức 1.000.000 VND, ngưỡng 80% (tức 800.000 VND)
    b = Budget(
        id=uuid.uuid4(),
        name="Ngân sách test cảnh báo",
        scope="personal",
        user_id=u.id,
        category_id=cat.id,
        amount_limit=Decimal("1000000.00"),
        period_start=date(2026, 10, 1),
        period_end=date(2026, 10, 31),
        warning_threshold=Decimal("80.00"),
    )
    db.add(b)
    db.commit()
    b_id = str(b.id)
    db.close()

    client.cookies.set(settings.SESSION_COOKIE_NAME, token)

    # 1. Chi 799.999 VND -> Dưới ngưỡng 80% -> 'normal'
    db = TestingSessionLocal()
    tx = Transaction(
        id=uuid.uuid4(),
        account_id=acc.id,
        category_id=cat.id,
        user_id=u.id,
        type="expense",
        amount=Decimal("799999.00"),
        occurred_at=datetime(2026, 10, 2, 10, 0, 0, tzinfo=UTC),
    )
    db.add(tx)
    db.commit()
    db.close()

    resp1 = client.get(f"/api/v1/budgets/{b_id}")
    d1 = resp1.json()
    assert d1["spent_amount"] == "799999.00"
    assert d1["status"] == "normal"

    # 2. Chi thêm 1 VND -> Đạt chính xác 800.000 VND (80.00%) -> 'warning'
    db = TestingSessionLocal()
    tx_add1 = Transaction(
        id=uuid.uuid4(),
        account_id=acc.id,
        category_id=cat.id,
        user_id=u.id,
        type="expense",
        amount=Decimal("1.00"),
        occurred_at=datetime(2026, 10, 3, 10, 0, 0, tzinfo=UTC),
    )
    db.add(tx_add1)
    db.commit()
    db.close()

    resp2 = client.get(f"/api/v1/budgets/{b_id}")
    d2 = resp2.json()
    assert d2["spent_amount"] == "800000.00"
    assert d2["usage_percentage"] == "80.00"
    assert d2["status"] == "warning"

    # 3. Chi thêm 150.000 VND -> Tổng 950.000 VND (95.00%) -> 'warning'
    db = TestingSessionLocal()
    tx_add2 = Transaction(
        id=uuid.uuid4(),
        account_id=acc.id,
        category_id=cat.id,
        user_id=u.id,
        type="expense",
        amount=Decimal("150000.00"),
        occurred_at=datetime(2026, 10, 4, 10, 0, 0, tzinfo=UTC),
    )
    db.add(tx_add2)
    db.commit()
    db.close()

    resp3 = client.get(f"/api/v1/budgets/{b_id}")
    d3 = resp3.json()
    assert d3["spent_amount"] == "950000.00"
    assert d3["usage_percentage"] == "95.00"
    assert d3["status"] == "warning"

    # 4. Chi thêm 50.000 VND -> Tổng 1.000.000 VND (100.00%) -> 'exceeded'
    db = TestingSessionLocal()
    tx_add3 = Transaction(
        id=uuid.uuid4(),
        account_id=acc.id,
        category_id=cat.id,
        user_id=u.id,
        type="expense",
        amount=Decimal("50000.00"),
        occurred_at=datetime(2026, 10, 5, 10, 0, 0, tzinfo=UTC),
    )
    db.add(tx_add3)
    db.commit()
    db.close()

    resp4 = client.get(f"/api/v1/budgets/{b_id}")
    d4 = resp4.json()
    assert d4["spent_amount"] == "1000000.00"
    assert d4["remaining_amount"] == "0.00"
    assert d4["overspent_amount"] == "0.00"
    assert d4["usage_percentage"] == "100.00"
    assert d4["status"] == "exceeded"

    # 5. Chi thêm 250.000 VND -> Tổng 1.250.000 VND (125.00%) -> 'exceeded'
    db = TestingSessionLocal()
    tx_add4 = Transaction(
        id=uuid.uuid4(),
        account_id=acc.id,
        category_id=cat.id,
        user_id=u.id,
        type="expense",
        amount=Decimal("250000.00"),
        occurred_at=datetime(2026, 10, 6, 10, 0, 0, tzinfo=UTC),
    )
    db.add(tx_add4)
    db.commit()
    db.close()

    resp5 = client.get(f"/api/v1/budgets/{b_id}")
    d5 = resp5.json()
    assert d5["spent_amount"] == "1250000.00"
    assert d5["remaining_amount"] == "0.00"
    assert d5["overspent_amount"] == "250000.00"
    assert d5["usage_percentage"] == "125.00"
    assert d5["status"] == "exceeded"


def test_get_budgets_filtering():
    """Kiểm tra bộ lọc danh sách ngân sách: scope, category_id, active_on, include_archived."""
    u, token = create_user_and_session("filter_u@example.com")
    cat1 = create_test_category("Cat 1", scope="system")
    cat2 = create_test_category("Cat 2", scope="system")

    db = TestingSessionLocal()
    b_oct = Budget(
        id=uuid.uuid4(),
        name="Tháng 10",
        scope="personal",
        user_id=u.id,
        category_id=cat1.id,
        amount_limit=Decimal("1000000.00"),
        period_start=date(2026, 10, 1),
        period_end=date(2026, 10, 31),
    )
    b_nov = Budget(
        id=uuid.uuid4(),
        name="Tháng 11",
        scope="personal",
        user_id=u.id,
        category_id=cat2.id,
        amount_limit=Decimal("2000000.00"),
        period_start=date(2026, 11, 1),
        period_end=date(2026, 11, 30),
    )
    b_arch = Budget(
        id=uuid.uuid4(),
        name="Đã lưu trữ",
        scope="personal",
        user_id=u.id,
        category_id=cat1.id,
        amount_limit=Decimal("500000.00"),
        period_start=date(2026, 10, 1),
        period_end=date(2026, 10, 31),
        is_archived=True,
    )
    db.add_all([b_oct, b_nov, b_arch])
    db.commit()
    db.close()

    client.cookies.set(settings.SESSION_COOKIE_NAME, token)

    # 1. Mặc định chỉ lấy active (không lấy archived) -> 2 bản ghi
    resp1 = client.get("/api/v1/budgets")
    assert resp1.status_code == 200
    assert len(resp1.json()) == 2

    # 2. include_archived=true -> 3 bản ghi
    resp2 = client.get("/api/v1/budgets?include_archived=true")
    assert resp2.status_code == 200
    assert len(resp2.json()) == 3

    # 3. Lọc theo category_id -> 1 bản ghi
    resp3 = client.get(f"/api/v1/budgets?category_id={cat2.id}")
    assert resp3.status_code == 200
    assert len(resp3.json()) == 1
    assert resp3.json()[0]["name"] == "Tháng 11"

    # 4. Lọc theo active_on=2026-10-15 -> chỉ có Tháng 10
    resp4 = client.get("/api/v1/budgets?active_on=2026-10-15")
    assert resp4.status_code == 200
    assert len(resp4.json()) == 1
    assert resp4.json()[0]["name"] == "Tháng 10"
