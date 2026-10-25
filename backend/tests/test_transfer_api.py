import uuid
from datetime import UTC, datetime, timedelta
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

# Tạo in-memory SQLite engine độc lập cho bộ test Transfer API
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


def create_user_and_session(email: str = "transfer_user@example.com") -> tuple[User, str]:
    """Helper tạo User và AuthSession hợp lệ."""
    db = TestingSessionLocal()
    user = User(
        id=uuid.uuid4(),
        email=email,
        password_hash="fakehash",
        display_name="Transfer Tester",
        is_active=True,
    )
    db.add(user)
    db.commit()

    raw_token = f"test_token_{uuid.uuid4().hex}"
    token_hash = hash_session_token(raw_token)
    session = AuthSession(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db.add(session)
    db.commit()
    db.refresh(user)
    db.close()
    return user, raw_token


def create_account_helper(
    user_id: uuid.UUID | None = None,
    family_id: uuid.UUID | None = None,
    scope: str = "personal",
    name: str = "Ví Thử Nghiệm",
    currency: str = "VND",
    initial_balance: Decimal = Decimal("1000000.00"),
    is_archived: bool = False,
) -> Account:
    """Helper tạo ví tài chính."""
    db = TestingSessionLocal()
    acc = Account(
        id=uuid.uuid4(),
        name=name,
        scope=scope,
        user_id=user_id,
        family_id=family_id,
        account_type="bank",
        currency=currency,
        initial_balance=initial_balance,
        is_archived=is_archived,
    )
    db.add(acc)
    db.commit()
    db.refresh(acc)
    db.close()
    return acc


def create_category_helper(
    name: str = "Phí ngân hàng",
    type_: str = "expense",
    scope: str = "system",
    user_id: uuid.UUID | None = None,
    family_id: uuid.UUID | None = None,
    is_archived: bool = False,
) -> Category:
    """Helper tạo danh mục."""
    db = TestingSessionLocal()
    cat = Category(
        id=uuid.uuid4(),
        name=name,
        type=type_,
        scope=scope,
        user_id=user_id,
        family_id=family_id,
        is_archived=is_archived,
        is_default=scope == "system",
    )
    db.add(cat)
    db.commit()
    db.refresh(cat)
    db.close()
    return cat


def create_family_helper(owner_id: uuid.UUID, name: str = "Gia đình Thử Nghiệm") -> Family:
    """Helper tạo nhóm gia đình."""
    db = TestingSessionLocal()
    fam = Family(
        id=uuid.uuid4(),
        name=name,
        owner_user_id=owner_id,
    )
    db.add(fam)
    db.commit()
    db.refresh(fam)
    db.close()
    return fam


def add_family_member_helper(
    family_id: uuid.UUID,
    user_id: uuid.UUID,
    role: str = "editor",
    left_at: datetime | None = None,
) -> FamilyMember:
    """Helper thêm thành viên vào nhóm gia đình."""
    db = TestingSessionLocal()
    member = FamilyMember(
        id=uuid.uuid4(),
        family_id=family_id,
        user_id=user_id,
        role=role,
        left_at=left_at,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    db.close()
    return member


# ==============================================================================
# NHÓM TEST 1: XÁC THỰC VÀ TẠO CHUYỂN TIỀN CƠ BẢN (KHÔNG PHÍ / CÓ PHÍ)
# ==============================================================================
def test_unauthenticated_requests_rejected():
    """1. Chưa đăng nhập bị từ chối 401."""
    res = client.get("/api/v1/transfers")
    assert res.status_code == 401

    res_post = client.post(
        "/api/v1/transfers",
        json={
            "from_account_id": str(uuid.uuid4()),
            "to_account_id": str(uuid.uuid4()),
            "amount": "100000.00",
        },
    )
    assert res_post.status_code == 401


def test_create_transfer_valid_no_fee():
    """2. Tạo chuyển tiền hợp lệ không phí: tạo transfer_out, transfer_in, không tạo transfer_fee."""
    user, token = create_user_and_session()
    acc_from = create_account_helper(user_id=user.id, name="Ví nguồn A", initial_balance=Decimal("1000000.00"))
    acc_to = create_account_helper(user_id=user.id, name="Ví đích B", initial_balance=Decimal("200000.00"))

    res = client.post(
        "/api/v1/transfers",
        json={
            "from_account_id": str(acc_from.id),
            "to_account_id": str(acc_to.id),
            "amount": "300000.00",
            "fee_amount": "0.00",
            "note": "Chuyển tiền sang ví B",
        },
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["amount"] == "300000.00"
    assert data["fee_amount"] == "0.00"
    assert data["from_account_name"] == "Ví nguồn A"
    assert data["to_account_name"] == "Ví đích B"
    assert data["is_voided"] is False

    # Kiểm tra database: 1 transfer, 2 transactions (transfer_out, transfer_in)
    db = TestingSessionLocal()
    txs = db.query(Transaction).filter(Transaction.transfer_id == uuid.UUID(data["id"])).all()
    assert len(txs) == 2
    types = {tx.type for tx in txs}
    assert types == {"transfer_out", "transfer_in"}

    tx_out = next(t for t in txs if t.type == "transfer_out")
    tx_in = next(t for t in txs if t.type == "transfer_in")
    assert tx_out.account_id == acc_from.id and tx_out.amount == Decimal("300000.00") and tx_out.category_id is None
    assert tx_in.account_id == acc_to.id and tx_in.amount == Decimal("300000.00") and tx_in.category_id is None
    db.close()

    # Kiểm tra số dư 2 ví qua Account API
    res_acc_a = client.get(f"/api/v1/accounts/{acc_from.id}", cookies={settings.SESSION_COOKIE_NAME: token})
    res_acc_b = client.get(f"/api/v1/accounts/{acc_to.id}", cookies={settings.SESSION_COOKIE_NAME: token})
    assert Decimal(res_acc_a.json()["current_balance"]) == Decimal("700000.00")
    assert Decimal(res_acc_b.json()["current_balance"]) == Decimal("500000.00")


def test_create_transfer_valid_with_fee():
    """3. Tạo chuyển tiền hợp lệ có phí: tạo transfer_out, transfer_in, transfer_fee."""
    user, token = create_user_and_session()
    acc_from = create_account_helper(user_id=user.id, name="Ví nguồn A", initial_balance=Decimal("1000000.00"))
    acc_to = create_account_helper(user_id=user.id, name="Ví đích B", initial_balance=Decimal("300000.00"))
    cat_fee = create_category_helper(name="Phí chuyển khoản", type_="expense", scope="system")

    res = client.post(
        "/api/v1/transfers",
        json={
            "from_account_id": str(acc_from.id),
            "to_account_id": str(acc_to.id),
            "amount": "500000.00",
            "fee_amount": "2000.00",
            "fee_category_id": str(cat_fee.id),
            "note": "Chuyển tiền liên ngân hàng",
        },
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert res.status_code == 201
    data = res.json()
    assert data["amount"] == "500000.00"
    assert data["fee_amount"] == "2000.00"
    assert data["fee_category_id"] == str(cat_fee.id)

    # Database: 3 transactions (transfer_out, transfer_in, transfer_fee)
    db = TestingSessionLocal()
    txs = db.query(Transaction).filter(Transaction.transfer_id == uuid.UUID(data["id"])).all()
    assert len(txs) == 3
    types = {tx.type for tx in txs}
    assert types == {"transfer_out", "transfer_in", "transfer_fee"}

    tx_fee = next(t for t in txs if t.type == "transfer_fee")
    assert tx_fee.account_id == acc_from.id
    assert tx_fee.amount == Decimal("2000.00")
    assert tx_fee.category_id == cat_fee.id
    db.close()

    # Kiểm tra số dư ví A: 1.000.000 - 500.000 - 2.000 = 498.000 VND
    # Số dư ví B: 300.000 + 500.000 = 800.000 VND
    res_acc_a = client.get(f"/api/v1/accounts/{acc_from.id}", cookies={settings.SESSION_COOKIE_NAME: token})
    res_acc_b = client.get(f"/api/v1/accounts/{acc_to.id}", cookies={settings.SESSION_COOKIE_NAME: token})
    assert Decimal(res_acc_a.json()["current_balance"]) == Decimal("498000.00")
    assert Decimal(res_acc_b.json()["current_balance"]) == Decimal("800000.00")


# ==============================================================================
# NHÓM TEST 2: VALIDATION ĐẦU VÀO VÀ RÀNG BUỘC DỮ LIỆU
# ==============================================================================
def test_validation_rules_and_restrictions():
    """Kiểm tra các ràng buộc: ví giống nhau, amount <= 0, fee < 0, ví lưu trữ, khác currency."""
    user, token = create_user_and_session()
    acc_a = create_account_helper(user_id=user.id, name="Ví A", currency="VND")
    acc_b = create_account_helper(user_id=user.id, name="Ví B", currency="VND")
    acc_usd = create_account_helper(user_id=user.id, name="Ví USD", currency="USD")
    acc_archived = create_account_helper(user_id=user.id, name="Ví Archived", is_archived=True)
    create_category_helper(name="Phí", type_="expense", scope="system")

    # 4 & 5. Từ chối hai ví giống nhau
    res_same = client.post(
        "/api/v1/transfers",
        json={"from_account_id": str(acc_a.id), "to_account_id": str(acc_a.id), "amount": "50000.00"},
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert res_same.status_code == 422

    # 6. Từ chối amount <= 0
    res_zero = client.post(
        "/api/v1/transfers",
        json={"from_account_id": str(acc_a.id), "to_account_id": str(acc_b.id), "amount": "0.00"},
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert res_zero.status_code == 422

    res_neg = client.post(
        "/api/v1/transfers",
        json={"from_account_id": str(acc_a.id), "to_account_id": str(acc_b.id), "amount": "-1000.00"},
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert res_neg.status_code == 422

    # 7. Từ chối fee âm
    res_fee_neg = client.post(
        "/api/v1/transfers",
        json={
            "from_account_id": str(acc_a.id),
            "to_account_id": str(acc_b.id),
            "amount": "10000.00",
            "fee_amount": "-500.00",
        },
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert res_fee_neg.status_code == 422

    # 8. Từ chối ví không tồn tại hoặc ví đã lưu trữ
    res_non_exist = client.post(
        "/api/v1/transfers",
        json={"from_account_id": str(uuid.uuid4()), "to_account_id": str(acc_b.id), "amount": "10000.00"},
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert res_non_exist.status_code == 404

    res_archived = client.post(
        "/api/v1/transfers",
        json={"from_account_id": str(acc_archived.id), "to_account_id": str(acc_b.id), "amount": "10000.00"},
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert res_archived.status_code == 400

    # 9. Từ chối khác currency (VND != USD)
    res_curr = client.post(
        "/api/v1/transfers",
        json={"from_account_id": str(acc_a.id), "to_account_id": str(acc_usd.id), "amount": "10000.00"},
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert res_curr.status_code == 400

    # 15. Từ chối danh mục phí không hợp lệ (ví dụ danh mục thu nhập hoặc không tồn tại)
    cat_income = create_category_helper(name="Lương", type_="income", scope="system")
    res_bad_cat = client.post(
        "/api/v1/transfers",
        json={
            "from_account_id": str(acc_a.id),
            "to_account_id": str(acc_b.id),
            "amount": "10000.00",
            "fee_amount": "1000.00",
            "fee_category_id": str(cat_income.id),
        },
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert res_bad_cat.status_code == 400


# ==============================================================================
# NHÓM TEST 3: PHÂN QUYỀN VÍ CÁ NHÂN VÀ VÍ GIA ĐÌNH
# ==============================================================================
def test_ownership_and_family_permissions():
    """Kiểm tra phân quyền: ví người khác, viewer, thành viên rời nhóm, chuyển chéo gia đình."""
    user1, token1 = create_user_and_session("user1@example.com")
    user2, _token2 = create_user_and_session("user2@example.com")

    acc_u1_a = create_account_helper(user_id=user1.id, name="Ví U1 A")
    create_account_helper(user_id=user1.id, name="Ví U1 B")
    acc_u2 = create_account_helper(user_id=user2.id, name="Ví U2")

    # 10. Từ chối chuyển giữa ví cá nhân và ví gia đình
    fam1 = create_family_helper(owner_id=user1.id, name="Gia đình 1")
    acc_fam1_a = create_account_helper(family_id=fam1.id, scope="family", name="Ví Fam1 A")
    acc_fam1_b = create_account_helper(family_id=fam1.id, scope="family", name="Ví Fam1 B")

    res_cross_scope = client.post(
        "/api/v1/transfers",
        json={"from_account_id": str(acc_u1_a.id), "to_account_id": str(acc_fam1_a.id), "amount": "10000.00"},
        cookies={settings.SESSION_COOKIE_NAME: token1},
    )
    assert res_cross_scope.status_code == 400

    # 11. Từ chối chuyển tiền từ/đến ví cá nhân của người khác
    res_cross_user = client.post(
        "/api/v1/transfers",
        json={"from_account_id": str(acc_u1_a.id), "to_account_id": str(acc_u2.id), "amount": "10000.00"},
        cookies={settings.SESSION_COOKIE_NAME: token1},
    )
    assert res_cross_user.status_code == 404

    # 12. Viewer không được tạo transfer trong ví gia đình -> 403
    viewer_user, viewer_token = create_user_and_session("viewer@example.com")
    add_family_member_helper(family_id=fam1.id, user_id=viewer_user.id, role="viewer")

    res_viewer = client.post(
        "/api/v1/transfers",
        json={"from_account_id": str(acc_fam1_a.id), "to_account_id": str(acc_fam1_b.id), "amount": "50000.00"},
        cookies={settings.SESSION_COOKIE_NAME: viewer_token},
    )
    assert res_viewer.status_code == 403

    # 13. Owner hoặc Editor tạo transfer trong gia đình thành công
    editor_user, editor_token = create_user_and_session("editor@example.com")
    add_family_member_helper(family_id=fam1.id, user_id=editor_user.id, role="editor")

    res_editor = client.post(
        "/api/v1/transfers",
        json={"from_account_id": str(acc_fam1_a.id), "to_account_id": str(acc_fam1_b.id), "amount": "50000.00"},
        cookies={settings.SESSION_COOKIE_NAME: editor_token},
    )
    assert res_editor.status_code == 201

    # 14. Thành viên đã rời nhóm mất quyền ghi -> 404
    left_user, left_token = create_user_and_session("left@example.com")
    add_family_member_helper(family_id=fam1.id, user_id=left_user.id, role="editor", left_at=datetime.now(UTC))

    res_left = client.post(
        "/api/v1/transfers",
        json={"from_account_id": str(acc_fam1_a.id), "to_account_id": str(acc_fam1_b.id), "amount": "50000.00"},
        cookies={settings.SESSION_COOKIE_NAME: left_token},
    )
    assert res_left.status_code == 404


# ==============================================================================
# NHÓM TEST 4: VOID CHUYỂN TIỀN VÀ PHỤC HỒI SỐ DƯ
# ==============================================================================
def test_void_transfer_and_balance_restoration():
    """Kiểm tra hủy hiệu lực (void): số dư phục hồi, bảo toàn bản ghi, từ chối void lại."""
    user, token = create_user_and_session()
    acc_a = create_account_helper(user_id=user.id, name="Ví A", initial_balance=Decimal("1000000.00"))
    acc_b = create_account_helper(user_id=user.id, name="Ví B", initial_balance=Decimal("300000.00"))
    cat_fee = create_category_helper(name="Phí", type_="expense", scope="system")

    # 1. Tạo transfer 500k + phí 2k
    res_create = client.post(
        "/api/v1/transfers",
        json={
            "from_account_id": str(acc_a.id),
            "to_account_id": str(acc_b.id),
            "amount": "500000.00",
            "fee_amount": "2000.00",
            "fee_category_id": str(cat_fee.id),
        },
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert res_create.status_code == 201
    transfer_id = res_create.json()["id"]

    # Số dư tạm thời: A=498k, B=800k
    res_acc_a1 = client.get(f"/api/v1/accounts/{acc_a.id}", cookies={settings.SESSION_COOKIE_NAME: token})
    res_acc_b1 = client.get(f"/api/v1/accounts/{acc_b.id}", cookies={settings.SESSION_COOKIE_NAME: token})
    assert Decimal(res_acc_a1.json()["current_balance"]) == Decimal("498000.00")
    assert Decimal(res_acc_b1.json()["current_balance"]) == Decimal("800000.00")

    # 2. Người khác không có quyền void -> 404
    _other_user, other_token = create_user_and_session("other@example.com")
    res_other_void = client.post(
        f"/api/v1/transfers/{transfer_id}/void",
        cookies={settings.SESSION_COOKIE_NAME: other_token},
    )
    assert res_other_void.status_code == 404

    # 3. User chính chủ void hợp lệ
    res_void = client.post(
        f"/api/v1/transfers/{transfer_id}/void",
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert res_void.status_code == 200
    void_data = res_void.json()
    assert void_data["is_voided"] is True
    assert void_data["voided_at"] is not None

    # 4. Kiểm tra số dư 2 ví được hoàn nguyên 100%
    res_acc_a2 = client.get(f"/api/v1/accounts/{acc_a.id}", cookies={settings.SESSION_COOKIE_NAME: token})
    res_acc_b2 = client.get(f"/api/v1/accounts/{acc_b.id}", cookies={settings.SESSION_COOKIE_NAME: token})
    assert Decimal(res_acc_a2.json()["current_balance"]) == Decimal("1000000.00")
    assert Decimal(res_acc_b2.json()["current_balance"]) == Decimal("300000.00")

    # 5. Bản ghi Transfer và Transaction vẫn còn nguyên trong database (không xóa cứng)
    db = TestingSessionLocal()
    tr = db.get(Transfer, uuid.UUID(transfer_id))
    assert tr is not None and tr.voided_at is not None
    txs = db.query(Transaction).filter(Transaction.transfer_id == tr.id).all()
    assert len(txs) == 3
    db.close()

    # 6. Từ chối void lại lần thứ 2 -> 400
    res_void_again = client.post(
        f"/api/v1/transfers/{transfer_id}/void",
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert res_void_again.status_code == 400


# ==============================================================================
# NHÓM TEST 5: TÍNH NGUYÊN TỬ (ATOMICITY) VÀ ROLLBACK KHI GẶP LỖI GIỮA CHỪNG
# ==============================================================================
def test_atomicity_and_rollback_on_failure(monkeypatch):
    """27. Một lỗi phát sinh giữa quá trình tạo phải rollback toàn bộ transfer và transactions."""
    user, token = create_user_and_session()
    acc_a = create_account_helper(user_id=user.id, name="Ví A", initial_balance=Decimal("500000.00"))
    acc_b = create_account_helper(user_id=user.id, name="Ví B", initial_balance=Decimal("100000.00"))

    from sqlalchemy.orm import Session as OrmSession

    original_add = OrmSession.add

    # Giả lập lỗi khi thêm Transaction thứ 2 (transfer_in)
    call_count = {"count": 0}

    def flaky_add(self, instance):
        call_count["count"] += 1
        # instance đầu tiên là Transfer, thứ hai là tx_out, thứ ba là tx_in
        if isinstance(instance, Transaction) and instance.type == "transfer_in":
            raise RuntimeError("Database connection interrupted abruptly!")
        return original_add(self, instance)

    monkeypatch.setattr(OrmSession, "add", flaky_add)

    res = client.post(
        "/api/v1/transfers",
        json={
            "from_account_id": str(acc_a.id),
            "to_account_id": str(acc_b.id),
            "amount": "100000.00",
        },
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert res.status_code == 400

    # Phải rollback hoàn toàn: không có Transfer nào, không có Transaction nào được lưu
    db = TestingSessionLocal()
    assert db.query(Transfer).count() == 0
    assert db.query(Transaction).count() == 0
    db.close()

    # Số dư 2 ví không thay đổi
    res_acc_a = client.get(f"/api/v1/accounts/{acc_a.id}", cookies={settings.SESSION_COOKIE_NAME: token})
    res_acc_b = client.get(f"/api/v1/accounts/{acc_b.id}", cookies={settings.SESSION_COOKIE_NAME: token})
    assert Decimal(res_acc_a.json()["current_balance"]) == Decimal("500000.00")
    assert Decimal(res_acc_b.json()["current_balance"]) == Decimal("100000.00")


# ==============================================================================
# NHÓM TEST 6: XEM DANH SÁCH VÀ BỘ LỌC CHUYỂN TIỀN
# ==============================================================================
def test_get_transfers_list_and_filters():
    """Kiểm tra GET /transfers: lọc theo account_id, date range, include_voided và phân trang."""
    user, token = create_user_and_session()
    acc_a = create_account_helper(user_id=user.id, name="Ví A")
    acc_b = create_account_helper(user_id=user.id, name="Ví B")
    acc_c = create_account_helper(user_id=user.id, name="Ví C")

    # Tạo 3 transfer: A->B, B->C, A->C
    now = datetime.now(UTC)
    res1 = client.post(
        "/api/v1/transfers",
        json={
            "from_account_id": str(acc_a.id),
            "to_account_id": str(acc_b.id),
            "amount": "10000.00",
            "occurred_at": (now - timedelta(days=3)).isoformat(),
        },
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    res2 = client.post(
        "/api/v1/transfers",
        json={
            "from_account_id": str(acc_b.id),
            "to_account_id": str(acc_c.id),
            "amount": "20000.00",
            "occurred_at": (now - timedelta(days=2)).isoformat(),
        },
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    res3 = client.post(
        "/api/v1/transfers",
        json={
            "from_account_id": str(acc_a.id),
            "to_account_id": str(acc_c.id),
            "amount": "30000.00",
            "occurred_at": (now - timedelta(days=1)).isoformat(),
        },
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert res1.status_code == 201 and res2.status_code == 201 and res3.status_code == 201

    # Void lượt thứ 3 (A->C)
    client.post(f"/api/v1/transfers/{res3.json()['id']}/void", cookies={settings.SESSION_COOKIE_NAME: token})

    # 1. Mặc định loại trừ voided -> Chỉ còn 2 bản ghi (lượt 1 và 2)
    res_default = client.get("/api/v1/transfers", cookies={settings.SESSION_COOKIE_NAME: token})
    assert len(res_default.json()) == 2
    # Sắp xếp occurred_at DESC -> lượt 2 trước lượt 1
    assert res_default.json()[0]["id"] == res2.json()["id"]

    # 2. include_voided = true -> Trả đủ 3 bản ghi
    res_all = client.get("/api/v1/transfers?include_voided=true", cookies={settings.SESSION_COOKIE_NAME: token})
    assert len(res_all.json()) == 3

    # 3. Lọc theo account_id = Ví B (xuất hiện cả ở lượt 1 là đích, lượt 2 là nguồn)
    res_b = client.get(f"/api/v1/transfers?account_id={acc_b.id}", cookies={settings.SESSION_COOKIE_NAME: token})
    assert len(res_b.json()) == 2

    # 4. Lọc theo date_from
    date_from = (now - timedelta(days=2, hours=12)).isoformat()
    res_date = client.get(
        "/api/v1/transfers",
        params={"date_from": date_from, "include_voided": "true"},
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert len(res_date.json()) == 2
