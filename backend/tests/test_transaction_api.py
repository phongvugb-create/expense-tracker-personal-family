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
from app.models.user import User
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Tạo isolated in-memory SQLite engine cho bộ test Transaction API
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
        email=email.strip().lower(),
        password_hash="test_argon2_hash",
        display_name=display_name,
        is_active=True,
    )
    db.add(user)
    db.flush()

    raw_token = f"test_session_token_{uuid.uuid4().hex}"
    token_hash = hash_session_token(raw_token)
    session = AuthSession(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=token_hash,
        expires_at=now + timedelta(days=1),
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
    name: str = "Ví tiền mặt",
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
        account_type="cash",
        currency="VND",
        initial_balance=initial_balance,
        is_archived=is_archived,
    )
    db.add(acc)
    db.commit()
    db.refresh(acc)
    db.close()
    return acc


def create_category_helper(
    name: str = "Ăn uống",
    type_: str = "expense",
    scope: str = "system",
    user_id: uuid.UUID | None = None,
    family_id: uuid.UUID | None = None,
    is_archived: bool = False,
) -> Category:
    """Helper tạo danh mục thu chi."""
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


def create_family_helper(owner_id: uuid.UUID, name: str = "Gia đình mẫu") -> Family:
    """Helper tạo nhóm gia đình."""
    db = TestingSessionLocal()
    family = Family(
        id=uuid.uuid4(),
        name=name,
        owner_user_id=owner_id,
    )
    db.add(family)
    db.commit()
    db.refresh(family)
    db.close()
    return family


def add_family_member_helper(family_id: uuid.UUID, user_id: uuid.UUID, role: str) -> FamilyMember:
    """Helper thêm thành viên vào nhóm gia đình."""
    db = TestingSessionLocal()
    member = FamilyMember(
        id=uuid.uuid4(),
        family_id=family_id,
        user_id=user_id,
        role=role,
        joined_at=datetime.now(UTC),
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    db.close()
    return member


# ==============================================================================
# 1. Test chưa đăng nhập bị từ chối (HTTP 401)
# ==============================================================================
def test_transactions_unauthenticated():
    res_get = client.get("/api/v1/transactions")
    assert res_get.status_code == 401

    res_post = client.post(
        "/api/v1/transactions",
        json={
            "account_id": str(uuid.uuid4()),
            "category_id": str(uuid.uuid4()),
            "type": "expense",
            "amount": "50000.00",
        },
    )
    assert res_post.status_code == 401


# ==============================================================================
# 2 & 3 & 4. Tạo giao dịch income và expense thành công với danh mục hệ thống
# ==============================================================================
def test_create_income_and_expense_transaction():
    user, token = create_user_and_session("user@example.com")
    acc = create_account_helper(user_id=user.id, scope="personal", initial_balance=Decimal("500000.00"))
    cat_expense = create_category_helper(name="Ăn uống", type_="expense", scope="system")
    cat_income = create_category_helper(name="Lương", type_="income", scope="system")

    # 1. Tạo Expense
    res_exp = client.post(
        "/api/v1/transactions",
        json={
            "account_id": str(acc.id),
            "category_id": str(cat_expense.id),
            "type": "expense",
            "amount": "120000.00",
            "note": "Ăn trưa bún bò",
        },
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert res_exp.status_code == 201
    exp_data = res_exp.json()
    assert exp_data["type"] == "expense"
    assert Decimal(str(exp_data["amount"])) == Decimal("120000.00")
    assert exp_data["note"] == "Ăn trưa bún bò"
    assert exp_data["user_id"] == str(user.id)
    assert exp_data["account_name"] == acc.name
    assert exp_data["category_name"] == "Ăn uống"

    # 2. Tạo Income
    res_inc = client.post(
        "/api/v1/transactions",
        json={
            "account_id": str(acc.id),
            "category_id": str(cat_income.id),
            "type": "income",
            "amount": "5000000.00",
            "note": "Nhận lương tháng",
        },
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert res_inc.status_code == 201
    inc_data = res_inc.json()
    assert inc_data["type"] == "income"
    assert Decimal(str(inc_data["amount"])) == Decimal("5000000.00")


# ==============================================================================
# 5 & 6. Từ chối amount <= 0 và type không hợp lệ
# ==============================================================================
def test_validate_amount_and_type():
    user, token = create_user_and_session("user@example.com")
    acc = create_account_helper(user_id=user.id, scope="personal")
    cat = create_category_helper(name="Ăn uống", type_="expense", scope="system")

    # Amount = 0
    res_zero = client.post(
        "/api/v1/transactions",
        json={
            "account_id": str(acc.id),
            "category_id": str(cat.id),
            "type": "expense",
            "amount": "0",
        },
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert res_zero.status_code == 422  # Pydantic Field(gt=0) validation

    # Amount âm
    res_neg = client.post(
        "/api/v1/transactions",
        json={
            "account_id": str(acc.id),
            "category_id": str(cat.id),
            "type": "expense",
            "amount": "-50000",
        },
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert res_neg.status_code == 422

    # Type không hợp lệ (không phải income hoặc expense)
    res_bad_type = client.post(
        "/api/v1/transactions",
        json={
            "account_id": str(acc.id),
            "category_id": str(cat.id),
            "type": "transfer_in",
            "amount": "50000",
        },
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert res_bad_type.status_code == 422


# ==============================================================================
# 7. Từ chối category không tồn tại, đã lưu trữ hoặc sai loại (mismatch type)
# ==============================================================================
def test_category_validation():
    user, token = create_user_and_session("user@example.com")
    acc = create_account_helper(user_id=user.id, scope="personal")
    cat_income = create_category_helper(name="Lương", type_="income", scope="system")
    cat_archived = create_category_helper(name="Chi phí cũ", type_="expense", scope="system", is_archived=True)

    # 1. Giao dịch expense nhưng gán category income -> 400 Bad Request
    res_mismatch = client.post(
        "/api/v1/transactions",
        json={
            "account_id": str(acc.id),
            "category_id": str(cat_income.id),
            "type": "expense",
            "amount": "50000.00",
        },
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert res_mismatch.status_code == 400

    # 2. Gán category đã bị lưu trữ -> 400 Bad Request
    res_archived = client.post(
        "/api/v1/transactions",
        json={
            "account_id": str(acc.id),
            "category_id": str(cat_archived.id),
            "type": "expense",
            "amount": "50000.00",
        },
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert res_archived.status_code == 400


# ==============================================================================
# 8 & 9. Phân quyền ví cá nhân: User không thể can thiệp ví người khác
# ==============================================================================
def test_personal_account_isolation():
    user1, token1 = create_user_and_session("user1@example.com")
    _user2, token2 = create_user_and_session("user2@example.com")

    acc1 = create_account_helper(user_id=user1.id, scope="personal")
    cat = create_category_helper(name="Ăn uống", type_="expense", scope="system")

    # User 2 cố gắng tạo giao dịch trên ví của User 1 -> 404 Not Found
    res_hack = client.post(
        "/api/v1/transactions",
        json={
            "account_id": str(acc1.id),
            "category_id": str(cat.id),
            "type": "expense",
            "amount": "100000.00",
        },
        cookies={settings.SESSION_COOKIE_NAME: token2},
    )
    assert res_hack.status_code == 404

    # User 1 tạo giao dịch hợp lệ
    res_ok = client.post(
        "/api/v1/transactions",
        json={
            "account_id": str(acc1.id),
            "category_id": str(cat.id),
            "type": "expense",
            "amount": "100000.00",
        },
        cookies={settings.SESSION_COOKIE_NAME: token1},
    )
    assert res_ok.status_code == 201
    tx_id = res_ok.json()["id"]

    # User 2 không thể xem danh sách chứa giao dịch của User 1
    res_u2_list = client.get(
        "/api/v1/transactions",
        cookies={settings.SESSION_COOKIE_NAME: token2},
    )
    assert len(res_u2_list.json()) == 0

    # User 2 không thể xem detail giao dịch của User 1 -> 404
    res_u2_detail = client.get(
        f"/api/v1/transactions/{tx_id}",
        cookies={settings.SESSION_COOKIE_NAME: token2},
    )
    assert res_u2_detail.status_code == 404


# ==============================================================================
# 10 & 11 & 12. Phân quyền ví gia đình: Owner/Editor được ghi, Viewer chỉ được xem
# ==============================================================================
def test_family_account_transaction_permissions():
    owner, owner_token = create_user_and_session("owner@example.com")
    editor, editor_token = create_user_and_session("editor@example.com")
    viewer, viewer_token = create_user_and_session("viewer@example.com")
    _outsider, outsider_token = create_user_and_session("outsider@example.com")

    family = create_family_helper(owner.id, "Gia đình Tuấn Tú")
    add_family_member_helper(family.id, editor.id, "editor")
    add_family_member_helper(family.id, viewer.id, "viewer")

    family_acc = create_account_helper(family_id=family.id, scope="family", name="Quỹ gia đình")
    cat = create_category_helper(name="Tiền chợ", type_="expense", scope="system")

    # 1. Owner tạo giao dịch thành công
    res_owner = client.post(
        "/api/v1/transactions",
        json={
            "account_id": str(family_acc.id),
            "category_id": str(cat.id),
            "type": "expense",
            "amount": "200000.00",
        },
        cookies={settings.SESSION_COOKIE_NAME: owner_token},
    )
    assert res_owner.status_code == 201
    tx_id = res_owner.json()["id"]

    # 2. Editor tạo giao dịch thành công
    res_editor = client.post(
        "/api/v1/transactions",
        json={
            "account_id": str(family_acc.id),
            "category_id": str(cat.id),
            "type": "expense",
            "amount": "150000.00",
        },
        cookies={settings.SESSION_COOKIE_NAME: editor_token},
    )
    assert res_editor.status_code == 201

    # 3. Viewer tạo giao dịch -> 403 Forbidden
    res_viewer = client.post(
        "/api/v1/transactions",
        json={
            "account_id": str(family_acc.id),
            "category_id": str(cat.id),
            "type": "expense",
            "amount": "50000.00",
        },
        cookies={settings.SESSION_COOKIE_NAME: viewer_token},
    )
    assert res_viewer.status_code == 403

    # 4. Viewer xem được danh sách giao dịch
    res_viewer_list = client.get(
        f"/api/v1/transactions?account_id={family_acc.id}",
        cookies={settings.SESSION_COOKIE_NAME: viewer_token},
    )
    assert res_viewer_list.status_code == 200
    assert len(res_viewer_list.json()) == 2

    # 5. Người ngoài không xem hoặc sửa được -> 404
    res_out_get = client.get(
        f"/api/v1/transactions/{tx_id}",
        cookies={settings.SESSION_COOKIE_NAME: outsider_token},
    )
    assert res_out_get.status_code == 404


# ==============================================================================
# 13 & 14 & 15. Cập nhật giao dịch hợp lệ và từ chối khi không đủ quyền
# ==============================================================================
def test_update_transaction():
    user, token = create_user_and_session("user@example.com")
    acc = create_account_helper(user_id=user.id, scope="personal")
    cat1 = create_category_helper(name="Ăn trưa", type_="expense", scope="system")
    cat2 = create_category_helper(name="Cà phê", type_="expense", scope="system")

    # Tạo ban đầu
    res_init = client.post(
        "/api/v1/transactions",
        json={
            "account_id": str(acc.id),
            "category_id": str(cat1.id),
            "type": "expense",
            "amount": "100000.00",
            "note": "Cơm trưa",
        },
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    tx_id = res_init.json()["id"]

    # Chỉnh sửa: đổi category sang Cà phê, tăng amount lên 150000
    res_patch = client.patch(
        f"/api/v1/transactions/{tx_id}",
        json={
            "category_id": str(cat2.id),
            "amount": "150000.00",
            "note": "Cơm trưa và cà phê",
        },
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert res_patch.status_code == 200
    updated = res_patch.json()
    assert Decimal(str(updated["amount"])) == Decimal("150000.00")
    assert updated["category_name"] == "Cà phê"
    assert updated["note"] == "Cơm trưa và cà phê"


# ==============================================================================
# 16 & 17 & 18. Xóa mềm (soft delete) và loại khỏi số dư
# ==============================================================================
def test_soft_delete_and_balance_impact():
    user, token = create_user_and_session("user@example.com")
    # Số dư ban đầu: 1,000,000
    acc = create_account_helper(user_id=user.id, scope="personal", initial_balance=Decimal("1000000.00"))
    cat = create_category_helper(name="Mua sắm", type_="expense", scope="system")

    # Tạo giao dịch chi tiêu: 300,000 -> Số dư còn 700,000
    res_tx = client.post(
        "/api/v1/transactions",
        json={
            "account_id": str(acc.id),
            "category_id": str(cat.id),
            "type": "expense",
            "amount": "300000.00",
        },
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    tx_id = res_tx.json()["id"]

    # Kiểm tra số dư ví hiện tại qua API accounts
    res_acc1 = client.get(
        f"/api/v1/accounts/{acc.id}",
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert Decimal(str(res_acc1.json()["current_balance"])) == Decimal("700000.00")

    # Xóa mềm giao dịch
    res_del = client.delete(
        f"/api/v1/transactions/{tx_id}",
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert res_del.status_code == 200

    # Sau khi xóa mềm: Giao dịch không còn trong danh sách mặc định
    res_list = client.get(
        f"/api/v1/transactions?account_id={acc.id}",
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert len(res_list.json()) == 0

    # Số dư ví tự động phục hồi về 1,000,000
    res_acc2 = client.get(
        f"/api/v1/accounts/{acc.id}",
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert Decimal(str(res_acc2.json()["current_balance"])) == Decimal("1000000.00")

    # Bản ghi vẫn được giữ trong database (kiểm tra deleted_at IS NOT NULL)
    db = TestingSessionLocal()
    db_tx = db.get(Transaction, uuid.UUID(tx_id))
    assert db_tx is not None
    assert db_tx.deleted_at is not None
    db.close()


# ==============================================================================
# 20 & 21 & 22 & 25 & 26. Tính số dư đa chiều, lọc theo khoảng thời gian và phân trang
# ==============================================================================
def test_filter_and_pagination():
    user, token = create_user_and_session("user@example.com")
    acc = create_account_helper(user_id=user.id, scope="personal")
    cat = create_category_helper(name="Ăn uống", type_="expense", scope="system")

    now = datetime.now(UTC)
    # Tạo 5 giao dịch cách nhau 1 ngày
    for i in range(5):
        occurred = now - timedelta(days=i)
        client.post(
            "/api/v1/transactions",
            json={
                "account_id": str(acc.id),
                "category_id": str(cat.id),
                "type": "expense",
                "amount": str(10000 * (i + 1)),
                "occurred_at": occurred.isoformat(),
            },
            cookies={settings.SESSION_COOKIE_NAME: token},
        )

    # 1. Kiểm tra limit=2
    res_page1 = client.get(
        f"/api/v1/transactions?account_id={acc.id}&limit=2&offset=0",
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert len(res_page1.json()) == 2

    # 2. Kiểm tra offset=2
    res_page2 = client.get(
        f"/api/v1/transactions?account_id={acc.id}&limit=2&offset=2",
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert len(res_page2.json()) == 2
    assert res_page1.json()[0]["id"] != res_page2.json()[0]["id"]

    # 3. Lọc theo date_from và date_to
    date_from = (now - timedelta(days=2)).isoformat()
    res_date = client.get(
        "/api/v1/transactions",
        params={"account_id": str(acc.id), "date_from": date_from},
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    # Ngày 0, 1, 2 thỏa mãn >= date_from
    assert len(res_date.json()) == 3

    # 4. Từ chối date_from > date_to
    bad_range = client.get(
        "/api/v1/transactions",
        params={
            "date_from": (now + timedelta(days=1)).isoformat(),
            "date_to": now.isoformat(),
        },
        cookies={settings.SESSION_COOKIE_NAME: token},
    )
    assert bad_range.status_code == 400
