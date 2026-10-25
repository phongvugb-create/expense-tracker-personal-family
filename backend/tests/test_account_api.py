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
from app.models.family_member import FamilyMember
from app.models.transaction import Transaction
from app.models.transfer import Transfer
from app.models.user import User
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Tạo isolated in-memory SQLite engine cho bộ test API Account
# Sử dụng StaticPool để chia sẻ in-memory database giữa các connection trong cùng test runner
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


def create_user_and_session(email: str, display_name: str = "Test User") -> tuple[User, str]:
    """Helper tạo User và AuthSession, trả về (User, raw_token)."""
    db = TestingSessionLocal()
    now = datetime.now(UTC)
    user = User(
        id=uuid.uuid4(),
        email=email,
        password_hash="argon2id_mock_hash",
        display_name=display_name,
        is_active=True,
        email_verified_at=now,
        created_at=now,
        updated_at=now,
    )
    db.add(user)

    raw_token = f"session_token_{uuid.uuid4().hex}"
    session = AuthSession(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=hash_session_token(raw_token),
        ip_address="127.0.0.1",
        user_agent="pytest-agent",
        revoked_at=None,
        expires_at=now + timedelta_hours(24),
        created_at=now,
        last_used_at=now,
    )
    db.add(session)
    db.commit()
    db.refresh(user)
    db.close()
    return user, raw_token


def timedelta_hours(hours: int):
    from datetime import timedelta
    return timedelta(hours=hours)


# ==============================================================================
# 1. Chưa đăng nhập không được gọi API cần xác thực
# ==============================================================================
def test_unauthenticated_request_rejected():
    res = client.get("/api/v1/accounts")
    assert res.status_code == 401
    assert "Yêu cầu đăng nhập" in res.json()["detail"]


# ==============================================================================
# 2. Tạo ví cá nhân và xác nhận user sở hữu
# ==============================================================================
def test_create_personal_account_success():
    user, token = create_user_and_session("alice@example.com", "Alice")
    client.cookies.set(settings.SESSION_COOKIE_NAME, token)

    payload = {
        "name": "Ví tiền mặt",
        "scope": "personal",
        "account_type": "cash",
        "currency": "VND",
        "initial_balance": "500000.00",
    }
    res = client.post("/api/v1/accounts", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Ví tiền mặt"
    assert data["scope"] == "personal"
    assert data["currency"] == "VND"
    assert data["initial_balance"] == "500000.00"
    assert data["current_balance"] == "500000.00"
    assert data["family_id"] is None

    # Kiểm tra trong DB
    db = TestingSessionLocal()
    acc = db.get(Account, uuid.UUID(data["id"]))
    assert acc is not None
    assert acc.user_id == user.id
    assert acc.family_id is None
    db.close()


# ==============================================================================
# 3. Tạo ví cá nhân nhưng gửi kèm family_id bị từ chối
# ==============================================================================
def test_create_personal_account_with_family_id_fails():
    _, token = create_user_and_session("alice@example.com")
    client.cookies.set(settings.SESSION_COOKIE_NAME, token)

    payload = {
        "name": "Ví lỗi",
        "scope": "personal",
        "family_id": str(uuid.uuid4()),
    }
    res = client.post("/api/v1/accounts", json=payload)
    assert res.status_code == 400
    assert "không được gắn family_id" in res.json()["detail"]


# ==============================================================================
# 4. Danh sách chỉ chứa ví người dùng được xem
# ==============================================================================
def test_get_accounts_isolation_between_users():
    _, token_alice = create_user_and_session("alice@example.com", "Alice")
    _, token_bob = create_user_and_session("bob@example.com", "Bob")

    # Alice tạo ví
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_alice)
    res_a = client.post(
        "/api/v1/accounts",
        json={"name": "Ví Alice", "scope": "personal", "initial_balance": "100000"},
    )
    assert res_a.status_code == 201

    # Bob tạo ví
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_bob)
    res_b = client.post(
        "/api/v1/accounts",
        json={"name": "Ví Bob", "scope": "personal", "initial_balance": "200000"},
    )
    assert res_b.status_code == 201

    # Bob chỉ thấy ví của Bob
    list_res_b = client.get("/api/v1/accounts")
    assert list_res_b.status_code == 200
    b_accounts = list_res_b.json()
    assert len(b_accounts) == 1
    assert b_accounts[0]["name"] == "Ví Bob"

    # Alice chỉ thấy ví của Alice
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_alice)
    list_res_a = client.get("/api/v1/accounts")
    assert list_res_a.status_code == 200
    a_accounts = list_res_a.json()
    assert len(a_accounts) == 1
    assert a_accounts[0]["name"] == "Ví Alice"


# ==============================================================================
# 5. User khác không được xem hoặc sửa ví cá nhân trái phép (404 Not Found)
# ==============================================================================
def test_user_cannot_view_or_edit_other_personal_account():
    _, token_alice = create_user_and_session("alice@example.com")
    _, token_bob = create_user_and_session("bob@example.com")

    # Alice tạo ví
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_alice)
    res = client.post(
        "/api/v1/accounts",
        json={"name": "Ví bí mật của Alice", "scope": "personal"},
    )
    alice_acc_id = res.json()["id"]

    # Bob cố xem -> 404
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_bob)
    get_res = client.get(f"/api/v1/accounts/{alice_acc_id}")
    assert get_res.status_code == 404

    # Bob cố sửa -> 404
    patch_res = client.patch(
        f"/api/v1/accounts/{alice_acc_id}",
        json={"name": "Bob hack ví"},
    )
    assert patch_res.status_code == 404

    # Bob cố archive -> 404
    archive_res = client.post(f"/api/v1/accounts/{alice_acc_id}/archive")
    assert archive_res.status_code == 404


# ==============================================================================
# 6. Người có quyền tạo ví gia đình (Owner / Editor)
# ==============================================================================
def test_family_wallet_permissions_owner_and_editor():
    user_owner, token_owner = create_user_and_session("owner@family.com", "Owner")
    user_editor, token_editor = create_user_and_session("editor@family.com", "Editor")

    db = TestingSessionLocal()
    family = Family(
        id=uuid.uuid4(),
        name="Gia Đình Hạnh Phúc",
        owner_user_id=user_owner.id,
    )
    db.add(family)

    # Thêm editor vào FamilyMember
    editor_member = FamilyMember(
        id=uuid.uuid4(),
        family_id=family.id,
        user_id=user_editor.id,
        role="editor",
    )
    db.add(editor_member)
    family_id = family.id
    db.commit()
    db.close()

    # Owner tạo ví gia đình
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_owner)
    res_owner = client.post(
        "/api/v1/accounts",
        json={
            "name": "Quỹ chung gia đình",
            "scope": "family",
            "family_id": str(family_id),
            "initial_balance": "5000000",
        },
    )
    assert res_owner.status_code == 201
    fam_acc_id = res_owner.json()["id"]

    # Editor cũng có quyền xem và sửa ví này
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_editor)
    res_get = client.get(f"/api/v1/accounts/{fam_acc_id}")
    assert res_get.status_code == 200
    assert res_get.json()["name"] == "Quỹ chung gia đình"

    # Editor sửa ví
    res_patch = client.patch(
        f"/api/v1/accounts/{fam_acc_id}",
        json={"name": "Quỹ chung đổi tên bởi Editor"},
    )
    assert res_patch.status_code == 200
    assert res_patch.json()["name"] == "Quỹ chung đổi tên bởi Editor"


# ==============================================================================
# 7. Viewer không được tạo, sửa, lưu trữ hoặc khôi phục ví gia đình
# ==============================================================================
def test_viewer_cannot_create_update_archive_restore():
    user_owner, token_owner = create_user_and_session("owner2@family.com")
    user_viewer, token_viewer = create_user_and_session("viewer@family.com")

    db = TestingSessionLocal()
    family = Family(
        id=uuid.uuid4(),
        name="Gia Đình Số 2",
        owner_user_id=user_owner.id,
    )
    db.add(family)
    member = FamilyMember(
        id=uuid.uuid4(),
        family_id=family.id,
        user_id=user_viewer.id,
        role="viewer",
    )
    db.add(member)
    family_id = family.id
    db.commit()
    db.close()

    # Viewer cố tạo ví -> 403 Forbidden
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_viewer)
    res_create = client.post(
        "/api/v1/accounts",
        json={
            "name": "Ví viewer tạo",
            "scope": "family",
            "family_id": str(family_id),
        },
    )
    assert res_create.status_code == 403

    # Owner tạo ví hợp lệ
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_owner)
    res_acc = client.post(
        "/api/v1/accounts",
        json={
            "name": "Ví chung do Owner tạo",
            "scope": "family",
            "family_id": str(family_id),
        },
    )
    acc_id = res_acc.json()["id"]

    # Viewer xem được (200)
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_viewer)
    get_res = client.get(f"/api/v1/accounts/{acc_id}")
    assert get_res.status_code == 200

    # Viewer cố sửa -> 403 Forbidden
    patch_res = client.patch(
        f"/api/v1/accounts/{acc_id}",
        json={"name": "Viewer cố sửa"},
    )
    assert patch_res.status_code == 403

    # Viewer cố archive -> 403 Forbidden
    archive_res = client.post(f"/api/v1/accounts/{acc_id}/archive")
    assert archive_res.status_code == 403

    # Viewer cố restore -> 403 Forbidden
    restore_res = client.post(f"/api/v1/accounts/{acc_id}/restore")
    assert restore_res.status_code == 403


# ==============================================================================
# 8. Thành viên đã rời nhóm (left_at IS NOT NULL) mất quyền truy cập
# ==============================================================================
def test_left_family_member_has_no_access():
    user_owner, token_owner = create_user_and_session("owner3@family.com")
    user_ex_member, token_ex = create_user_and_session("ex@family.com")

    db = TestingSessionLocal()
    family = Family(
        id=uuid.uuid4(),
        name="Gia Đình Cũ",
        owner_user_id=user_owner.id,
    )
    db.add(family)
    member = FamilyMember(
        id=uuid.uuid4(),
        family_id=family.id,
        user_id=user_ex_member.id,
        role="editor",
        left_at=datetime.now(UTC),  # Đã rời nhóm
    )
    db.add(member)
    family_id = family.id
    db.commit()
    db.close()

    # Owner tạo ví gia đình
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_owner)
    res_acc = client.post(
        "/api/v1/accounts",
        json={
            "name": "Ví gia đình bí mật",
            "scope": "family",
            "family_id": str(family_id),
        },
    )
    acc_id = res_acc.json()["id"]

    # Ex-member cố xem ví -> 404 Not Found
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_ex)
    get_res = client.get(f"/api/v1/accounts/{acc_id}")
    assert get_res.status_code == 404

    # Ex-member xem danh sách -> không có ví gia đình này
    list_res = client.get("/api/v1/accounts")
    assert list_res.status_code == 200
    assert len(list_res.json()) == 0


# ==============================================================================
# 9. Lưu trữ và khôi phục ví hoạt động đúng (Archive / Restore)
# ==============================================================================
def test_archive_and_restore_account():
    _, token = create_user_and_session("alice2@example.com")
    client.cookies.set(settings.SESSION_COOKIE_NAME, token)

    # 1. Tạo ví
    res = client.post(
        "/api/v1/accounts",
        json={"name": "Ví dự phòng", "scope": "personal"},
    )
    acc_id = res.json()["id"]
    assert res.json()["is_archived"] is False

    # 2. Archive ví
    arch_res = client.post(f"/api/v1/accounts/{acc_id}/archive")
    assert arch_res.status_code == 200
    assert arch_res.json()["is_archived"] is True

    # 3. Mặc định GET /accounts không trả ví đã lưu trữ
    list_res = client.get("/api/v1/accounts")
    assert len(list_res.json()) == 0

    # 4. Khi truyền include_archived=true thì trả về
    list_arch_res = client.get("/api/v1/accounts?include_archived=true")
    assert len(list_arch_res.json()) == 1
    assert list_arch_res.json()[0]["id"] == acc_id

    # 5. Restore ví
    rest_res = client.post(f"/api/v1/accounts/{acc_id}/restore")
    assert rest_res.status_code == 200
    assert rest_res.json()["is_archived"] is False

    # 6. Mặc định GET lại thấy ví
    list_res_again = client.get("/api/v1/accounts")
    assert len(list_res_again.json()) == 1


# ==============================================================================
# 10. Tính toán số dư chính xác theo công thức và loại trừ soft-delete, voided transfer
# ==============================================================================
def test_current_balance_calculation_with_all_transaction_types():
    user, token = create_user_and_session("charlie@example.com")
    client.cookies.set(settings.SESSION_COOKIE_NAME, token)

    # Tạo 2 ví: Ví chính (initial 1.000.000) và Ví phụ (initial 0)
    res_acc1 = client.post(
        "/api/v1/accounts",
        json={"name": "Ví chính", "scope": "personal", "initial_balance": "1000000.00"},
    )
    acc1_id = uuid.UUID(res_acc1.json()["id"])

    res_acc2 = client.post(
        "/api/v1/accounts",
        json={"name": "Ví phụ", "scope": "personal", "initial_balance": "0.00"},
    )
    acc2_id = uuid.UUID(res_acc2.json()["id"])

    db = TestingSessionLocal()
    now = datetime.now(UTC)

    # Tạo Category phục vụ quy tắc check constraint của Transaction
    cat_income = Category(
        id=uuid.uuid4(),
        name="Lương",
        type="income",
        scope="personal",
        user_id=user.id,
    )
    cat_expense = Category(
        id=uuid.uuid4(),
        name="Ăn uống",
        type="expense",
        scope="personal",
        user_id=user.id,
    )
    cat_fee = Category(
        id=uuid.uuid4(),
        name="Phí ngân hàng",
        type="expense",
        scope="personal",
        user_id=user.id,
    )
    db.add_all([cat_income, cat_expense, cat_fee])
    db.flush()

    # 1. Income vào ví 1: + 500.000
    tx_income = Transaction(
        id=uuid.uuid4(),
        account_id=acc1_id,
        user_id=user.id,
        category_id=cat_income.id,
        type="income",
        amount=Decimal("500000.00"),
        occurred_at=now,
    )
    db.add(tx_income)

    # 2. Expense từ ví 1: - 200.000
    tx_expense = Transaction(
        id=uuid.uuid4(),
        account_id=acc1_id,
        user_id=user.id,
        category_id=cat_expense.id,
        type="expense",
        amount=Decimal("200000.00"),
        occurred_at=now,
    )
    db.add(tx_expense)

    # 3. Chuyển tiền từ ví 1 sang ví 2: 300.000, phí 5.000
    transfer_valid = Transfer(
        id=uuid.uuid4(),
        from_account_id=acc1_id,
        to_account_id=acc2_id,
        created_by=user.id,
        amount=Decimal("300000.00"),
        fee_amount=Decimal("5000.00"),
    )
    db.add(transfer_valid)
    db.flush()

    tx_transfer_out = Transaction(
        id=uuid.uuid4(),
        account_id=acc1_id,
        user_id=user.id,
        transfer_id=transfer_valid.id,
        type="transfer_out",
        amount=Decimal("300000.00"),
        occurred_at=now,
    )
    tx_transfer_fee = Transaction(
        id=uuid.uuid4(),
        account_id=acc1_id,
        user_id=user.id,
        category_id=cat_fee.id,
        transfer_id=transfer_valid.id,
        type="transfer_fee",
        amount=Decimal("5000.00"),
        occurred_at=now,
    )
    tx_transfer_in = Transaction(
        id=uuid.uuid4(),
        account_id=acc2_id,
        user_id=user.id,
        transfer_id=transfer_valid.id,
        type="transfer_in",
        amount=Decimal("300000.00"),
        occurred_at=now,
    )
    db.add_all([tx_transfer_out, tx_transfer_fee, tx_transfer_in])

    # 4. Giao dịch Chi tiêu bị xóa mềm: - 100.000 (KHÔNG ĐƯỢC TÍNH)
    tx_deleted = Transaction(
        id=uuid.uuid4(),
        account_id=acc1_id,
        user_id=user.id,
        category_id=cat_expense.id,
        type="expense",
        amount=Decimal("100000.00"),
        occurred_at=now,
        deleted_at=now,
    )
    db.add(tx_deleted)

    # 5. Chuyển tiền bị HỦY (voided_at IS NOT NULL): 150.000, phí 2.000 (KHÔNG ĐƯỢC TÍNH)
    transfer_voided = Transfer(
        id=uuid.uuid4(),
        from_account_id=acc1_id,
        to_account_id=acc2_id,
        created_by=user.id,
        amount=Decimal("150000.00"),
        fee_amount=Decimal("2000.00"),
        voided_at=now,
    )
    db.add(transfer_voided)
    db.flush()

    tx_voided_out = Transaction(
        id=uuid.uuid4(),
        account_id=acc1_id,
        user_id=user.id,
        transfer_id=transfer_voided.id,
        type="transfer_out",
        amount=Decimal("150000.00"),
        occurred_at=now,
    )
    tx_voided_fee = Transaction(
        id=uuid.uuid4(),
        account_id=acc1_id,
        user_id=user.id,
        category_id=cat_fee.id,
        transfer_id=transfer_voided.id,
        type="transfer_fee",
        amount=Decimal("2000.00"),
        occurred_at=now,
    )
    tx_voided_in = Transaction(
        id=uuid.uuid4(),
        account_id=acc2_id,
        user_id=user.id,
        transfer_id=transfer_voided.id,
        type="transfer_in",
        amount=Decimal("150000.00"),
        occurred_at=now,
    )
    db.add_all([tx_voided_out, tx_voided_fee, tx_voided_in])
    db.commit()
    db.close()

    # Tính toán kỳ vọng cho Ví 1:
    # Initial: 1.000.000
    # + Income: 500.000
    # - Expense: 200.000
    # - Transfer_out: 300.000
    # - Transfer_fee: 5.000
    # Total = 1.000.000 + 500.000 - 200.000 - 300.000 - 5.000 = 995.000
    res_get_1 = client.get(f"/api/v1/accounts/{acc1_id}")
    assert res_get_1.status_code == 200
    assert Decimal(str(res_get_1.json()["current_balance"])) == Decimal("995000.00")

    # Tính toán kỳ vọng cho Ví 2:
    # Initial: 0
    # + Transfer_in: 300.000
    # Total = 300.000
    res_get_2 = client.get(f"/api/v1/accounts/{acc2_id}")
    assert res_get_2.status_code == 200
    assert Decimal(str(res_get_2.json()["current_balance"])) == Decimal("300000.00")
