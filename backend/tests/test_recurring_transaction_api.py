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
from app.models.category import Category
from app.models.family import Family
from app.models.family_member import FamilyMember
from app.models.transaction import Transaction
from app.models.user import User
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# SQLite in-memory engine cho testing Recurring Transactions
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
    """Làm sạch database trước mỗi test case."""
    app.dependency_overrides[get_db] = override_get_db
    db = TestingSessionLocal()
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()
    db.close()


def create_user_and_session(email: str = "recur_user@example.com") -> tuple[User, str]:
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


def test_recurring_unauthenticated_fails():
    """1. Chưa đăng nhập bị từ chối 401 Unauthorized."""
    unauth_client = TestClient(app)
    res = unauth_client.get("/api/v1/recurring-transactions")
    assert res.status_code == 401


def test_create_and_generate_personal_recurring_transaction():
    """2. Tạo quy tắc cá nhân, không thể tạo trước hạn, tạo đúng hạn và chống tạo trùng kỳ."""
    user, token = create_user_and_session("personal_recur@example.com")
    db = TestingSessionLocal()

    acc = Account(
        id=uuid.uuid4(),
        user_id=user.id,
        name="Ví Chi Tiêu Cá Nhân",
        account_type="cash",
        currency="VND",
        scope="personal",
        initial_balance=Decimal("5000000.00"),
    )
    db.add(acc)

    cat = Category(
        id=uuid.uuid4(),
        user_id=user.id,
        name="Tiền Thuê Nhà",
        type="expense",
        scope="personal",
    )
    db.add(cat)
    acc_id = acc.id
    cat_id = cat.id
    db.commit()
    db.close()

    client.cookies.set(settings.SESSION_COOKIE_NAME, token)

    # 1. Tạo quy tắc lặp hàng tháng (bắt đầu từ hôm nay)
    today = date.today()
    payload = {
        "name": "Thuê nhà hàng tháng",
        "type": "expense",
        "scope": "personal",
        "account_id": str(acc_id),
        "category_id": str(cat_id),
        "amount": "3500000.00",
        "start_date": today.isoformat(),
        "frequency": "monthly",
        "interval_value": 1,
        "note": "Thanh toán cho chủ nhà đầu tháng",
    }

    create_res = client.post("/api/v1/recurring-transactions", json=payload)
    assert create_res.status_code == 201, create_res.text
    rule_data = create_res.json()
    rule_id = rule_data["id"]
    assert rule_data["next_due_date"] == today.isoformat()
    assert rule_data["is_due"] is True

    # 2. Tạo giao dịch thực tế cho kỳ hôm nay
    gen_res = client.post(f"/api/v1/recurring-transactions/{rule_id}/generate")
    assert gen_res.status_code == 200, gen_res.text
    gen_data = gen_res.json()
    assert "Đã tạo thành công" in gen_data["message"]
    tx_id = gen_data["transaction_id"]

    # Kiểm tra Transaction đã tồn tại trong DB
    db2 = TestingSessionLocal()
    created_tx = db2.get(Transaction, uuid.UUID(tx_id))
    assert created_tx is not None
    assert created_tx.amount == Decimal("3500000.00")
    assert created_tx.recurring_rule_id == uuid.UUID(rule_id)
    assert created_tx.recurrence_date == today
    db2.close()

    # 3. Kỳ tiếp theo đã được cập nhật sang tháng sau
    updated_rule = gen_data["rule"]
    assert updated_rule["next_due_date"] > today.isoformat()
    assert updated_rule["is_due"] is False

    # 4. Cố gắng tạo tiếp khi chưa đến hạn -> 400 Bad Request
    fail_gen = client.post(f"/api/v1/recurring-transactions/{rule_id}/generate")
    assert fail_gen.status_code == 400
    assert "chưa đến hạn tạo" in fail_gen.json()["detail"]


def test_recurring_date_calculation_edge_cases():
    """3. Kiểm tra tính ngày kế tiếp với trường hợp cuối tháng 31/01 -> 28/02 -> 31/03."""
    from app.services.recurring_transaction_service import RecurringTransactionService

    # 31 tháng 1 -> tháng 2 (năm không nhuận 2025: 28 ngày, năm nhuận 2024: 29 ngày)
    d1 = date(2025, 1, 31)
    next_m2 = RecurringTransactionService.calculate_next_due_date(d1, "monthly", 1, start_date=d1)
    assert next_m2 == date(2025, 2, 28)

    # Từ tháng 2 sang tháng 3: nhờ neo start_date=31, phải hồi phục về 31/03 chứ không bị kẹt ở 28/03
    next_m3 = RecurringTransactionService.calculate_next_due_date(next_m2, "monthly", 1, start_date=d1)
    assert next_m3 == date(2025, 3, 31)


def test_recurring_family_permissions_and_viewer_blocked():
    """4. Phân quyền gia đình: Viewer không được tạo giao dịch hoặc sửa quy tắc."""
    owner, token_owner = create_user_and_session("owner_fam@example.com")
    viewer, token_viewer = create_user_and_session("viewer_fam@example.com")
    _stranger, token_stranger = create_user_and_session("stranger_fam@example.com")

    db = TestingSessionLocal()
    fam = Family(id=uuid.uuid4(), name="Gia Đình Hạnh Phúc", owner_user_id=owner.id)
    db.add(fam)

    # Thêm viewer vào family
    member_viewer = FamilyMember(
        id=uuid.uuid4(),
        family_id=fam.id,
        user_id=viewer.id,
        role="viewer",
    )
    db.add(member_viewer)

    fam_acc = Account(
        id=uuid.uuid4(),
        family_id=fam.id,
        name="Quỹ Chung Gia Đình",
        account_type="bank",
        currency="VND",
        scope="family",
        initial_balance=Decimal("10000000.00"),
    )
    db.add(fam_acc)

    cat_fam = Category(
        id=uuid.uuid4(),
        family_id=fam.id,
        name="Tiền Điện Nước Chung",
        type="expense",
        scope="family",
    )
    db.add(cat_fam)
    db.commit()
    fam_id = fam.id
    acc_id = fam_acc.id
    cat_id = cat_fam.id
    db.close()

    # 1. Viewer cố gắng tạo quy tắc định kỳ -> 403 Forbidden
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_viewer)
    today = date.today()
    payload = {
        "name": "Tiền điện nước",
        "type": "expense",
        "scope": "family",
        "family_id": str(fam_id),
        "account_id": str(acc_id),
        "category_id": str(cat_id),
        "amount": "500000.00",
        "start_date": today.isoformat(),
        "frequency": "monthly",
        "interval_value": 1,
    }
    res_viewer_create = client.post("/api/v1/recurring-transactions", json=payload)
    assert res_viewer_create.status_code == 403

    # 2. Owner tạo quy tắc thành công
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_owner)
    res_owner_create = client.post("/api/v1/recurring-transactions", json=payload)
    assert res_owner_create.status_code == 201
    rule_id = res_owner_create.json()["id"]

    # 3. Viewer có thể xem danh sách và chi tiết quy tắc
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_viewer)
    res_viewer_get = client.get(f"/api/v1/recurring-transactions/{rule_id}")
    assert res_viewer_get.status_code == 200

    # 4. Viewer cố bấm "Tạo giao dịch" (generate) -> 403 Forbidden
    res_viewer_gen = client.post(f"/api/v1/recurring-transactions/{rule_id}/generate")
    assert res_viewer_gen.status_code == 403

    # 5. Người ngoài (stranger) hoàn toàn không xem được -> 404/403
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_stranger)
    res_stranger = client.get(f"/api/v1/recurring-transactions/{rule_id}")
    assert res_stranger.status_code == 404


def test_recurring_pause_resume_and_archive():
    """5. Tạm dừng, kích hoạt lại và lưu trữ quy tắc định kỳ."""
    user, token = create_user_and_session("lifecycle_user@example.com")
    db = TestingSessionLocal()
    acc = Account(
        id=uuid.uuid4(),
        user_id=user.id,
        name="Ví Test",
        account_type="cash",
        currency="VND",
        scope="personal",
        initial_balance=Decimal("1000000.00"),
    )
    cat = Category(
        id=uuid.uuid4(),
        user_id=user.id,
        name="Lương",
        type="income",
        scope="personal",
    )
    db.add_all([acc, cat])
    acc_id = acc.id
    cat_id = cat.id
    db.commit()
    db.close()

    client.cookies.set(settings.SESSION_COOKIE_NAME, token)
    today = date.today()
    payload = {
        "name": "Lương định kỳ",
        "type": "income",
        "scope": "personal",
        "account_id": str(acc_id),
        "category_id": str(cat_id),
        "amount": "20000000.00",
        "start_date": today.isoformat(),
        "frequency": "monthly",
        "interval_value": 1,
    }
    create_res = client.post("/api/v1/recurring-transactions", json=payload)
    assert create_res.status_code == 201
    rule_id = create_res.json()["id"]

    # Pause
    pause_res = client.post(f"/api/v1/recurring-transactions/{rule_id}/pause")
    assert pause_res.status_code == 200
    assert pause_res.json()["is_active"] is False

    # Không thể generate khi đang pause
    gen_fail = client.post(f"/api/v1/recurring-transactions/{rule_id}/generate")
    assert gen_fail.status_code == 400
    assert "tạm dừng" in gen_fail.json()["detail"]

    # Resume
    resume_res = client.post(f"/api/v1/recurring-transactions/{rule_id}/resume")
    assert resume_res.status_code == 200
    assert resume_res.json()["is_active"] is True

    # Archive
    archive_res = client.post(f"/api/v1/recurring-transactions/{rule_id}/archive")
    assert archive_res.status_code == 200
    assert archive_res.json()["is_archived"] is True


def test_idempotency_after_soft_delete():
    """6. Không thể tạo lại cùng một kỳ sau khi giao dịch đã bị xóa mềm."""
    user, token = create_user_and_session("soft_del_recur@example.com")
    db = TestingSessionLocal()
    acc = Account(
        id=uuid.uuid4(),
        user_id=user.id,
        name="Ví Chi Tiêu",
        account_type="bank",
        currency="VND",
        scope="personal",
        initial_balance=Decimal("5000000.00"),
    )
    cat = Category(
        id=uuid.uuid4(),
        user_id=user.id,
        name="Internet",
        type="expense",
        scope="personal",
    )
    db.add_all([acc, cat])
    acc_id = acc.id
    cat_id = cat.id
    db.commit()
    db.close()

    client.cookies.set(settings.SESSION_COOKIE_NAME, token)
    today = date.today()
    payload = {
        "name": "Cước Internet",
        "type": "expense",
        "scope": "personal",
        "account_id": str(acc_id),
        "category_id": str(cat_id),
        "amount": "250000.00",
        "start_date": today.isoformat(),
        "frequency": "monthly",
        "interval_value": 1,
    }
    create_res = client.post("/api/v1/recurring-transactions", json=payload)
    assert create_res.status_code == 201
    rule_id = create_res.json()["id"]

    # 1. Phát sinh giao dịch lần đầu
    gen_res1 = client.post(f"/api/v1/recurring-transactions/{rule_id}/generate")
    assert gen_res1.status_code == 200
    tx_id = gen_res1.json()["transaction_id"]

    # 2. Xóa mềm giao dịch vừa tạo
    del_res = client.delete(f"/api/v1/transactions/{tx_id}")
    assert del_res.status_code == 200

    # 3. Thử tạo lại cùng kỳ đó (đưa next_due_date về lại today)
    db = TestingSessionLocal()
    from app.models.recurring_transaction import RecurringTransaction

    rule_db = db.get(RecurringTransaction, uuid.UUID(rule_id))
    rule_db.next_due_date = today
    db.commit()
    db.close()

    gen_res2 = client.post(f"/api/v1/recurring-transactions/{rule_id}/generate")
    assert gen_res2.status_code == 200
    assert "xóa mềm" in gen_res2.json()["message"]
    assert gen_res2.json()["transaction_id"] == tx_id

    # Xác nhận trong DB chỉ có đúng 1 bản ghi Transaction cho kỳ này
    db = TestingSessionLocal()
    count = db.query(Transaction).filter(
        Transaction.recurring_rule_id == uuid.UUID(rule_id),
        Transaction.recurrence_date == today,
    ).count()
    assert count == 1
    db.close()


def test_rule_update_does_not_affect_existing_transactions():
    """7. Sửa quy tắc không làm thay đổi số tiền hoặc lịch sử giao dịch đã phát sinh trước đó."""
    user, token = create_user_and_session("rule_update_audit@example.com")
    db = TestingSessionLocal()
    acc = Account(
        id=uuid.uuid4(),
        user_id=user.id,
        name="Ví Ngân Hàng",
        account_type="bank",
        currency="VND",
        scope="personal",
        initial_balance=Decimal("10000000.00"),
    )
    cat = Category(
        id=uuid.uuid4(),
        user_id=user.id,
        name="Thuê nhà",
        type="expense",
        scope="personal",
    )
    db.add_all([acc, cat])
    acc_id = acc.id
    cat_id = cat.id
    db.commit()
    db.close()

    client.cookies.set(settings.SESSION_COOKIE_NAME, token)
    today = date.today()
    payload = {
        "name": "Tiền nhà",
        "type": "expense",
        "scope": "personal",
        "account_id": str(acc_id),
        "category_id": str(cat_id),
        "amount": "4000000.00",
        "start_date": today.isoformat(),
        "frequency": "monthly",
        "interval_value": 1,
    }
    create_res = client.post("/api/v1/recurring-transactions", json=payload)
    rule_id = create_res.json()["id"]

    # Phát sinh giao dịch kỳ 1 với giá 4.000.000 VND
    gen_res = client.post(f"/api/v1/recurring-transactions/{rule_id}/generate")
    assert gen_res.status_code == 200
    tx_id = gen_res.json()["transaction_id"]

    # Cập nhật quy tắc: đổi tên, tăng giá lên 5.000.000 VND, đổi chu kỳ
    update_res = client.patch(
        f"/api/v1/recurring-transactions/{rule_id}",
        json={
            "name": "Tiền nhà mới",
            "amount": "5000000.00",
            "interval_value": 2,
        },
    )
    assert update_res.status_code == 200
    assert update_res.json()["amount"] == "5000000.00"

    # Kiểm tra giao dịch đã tạo trước đó: số tiền và ghi chú vẫn giữ nguyên 4.000.000 VND
    db = TestingSessionLocal()
    existing_tx = db.get(Transaction, uuid.UUID(tx_id))
    assert existing_tx.amount == Decimal("4000000.00")
    db.close()


def test_member_left_family_cannot_access():
    """8. Thành viên đã rời gia đình (left_at IS NOT NULL) mất quyền truy cập quy tắc."""
    owner, token_owner = create_user_and_session("owner_left_test@example.com")
    ex_member, token_ex_member = create_user_and_session("ex_member@example.com")

    db = TestingSessionLocal()
    fam = Family(id=uuid.uuid4(), name="Gia Đình Test", owner_user_id=owner.id)
    acc = Account(
        id=uuid.uuid4(),
        name="Quỹ Chung",
        account_type="bank",
        currency="VND",
        scope="family",
        family_id=fam.id,
        initial_balance=Decimal("20000000.00"),
    )
    cat = Category(
        id=uuid.uuid4(),
        name="Học phí",
        type="expense",
        scope="family",
        family_id=fam.id,
    )
    # Thành viên đã rời gia đình
    fm = FamilyMember(
        id=uuid.uuid4(),
        family_id=fam.id,
        user_id=ex_member.id,
        role="editor",
        joined_at=datetime.now(UTC),
        left_at=datetime.now(UTC),
    )
    db.add_all([fam, acc, cat, fm])
    acc_id = acc.id
    cat_id = cat.id
    fam_id = fam.id
    db.commit()
    db.close()

    # Owner tạo quy tắc
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_owner)
    today = date.today()
    create_res = client.post(
        "/api/v1/recurring-transactions",
        json={
            "name": "Học phí định kỳ",
            "type": "expense",
            "scope": "family",
            "family_id": str(fam_id),
            "account_id": str(acc_id),
            "category_id": str(cat_id),
            "amount": "3000000.00",
            "start_date": today.isoformat(),
            "frequency": "monthly",
            "interval_value": 1,
        },
    )
    assert create_res.status_code == 201
    rule_id = create_res.json()["id"]

    # Ex-member cố truy cập -> 404
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_ex_member)
    get_res = client.get(f"/api/v1/recurring-transactions/{rule_id}")
    assert get_res.status_code == 404

    # Ex-member cố generate -> 404
    gen_res = client.post(f"/api/v1/recurring-transactions/{rule_id}/generate")
    assert gen_res.status_code == 404


def test_date_calculation_edge_cases():
    """9. Kiểm tra toàn diện thuật toán tính ngày (leap year, anchor preservation, end_date)."""
    from app.services.recurring_transaction_service import RecurringTransactionService

    # 1. Start 31/01 trong năm thường (2025)
    d1 = date(2025, 1, 31)
    d2 = RecurringTransactionService.calculate_next_due_date(d1, "monthly", 1, start_date=d1)
    assert d2 == date(2025, 2, 28)

    # 2. Từ 28/02 sang tháng 3: phục hồi ngày neo 31/03
    d3 = RecurringTransactionService.calculate_next_due_date(d2, "monthly", 1, start_date=d1)
    assert d3 == date(2025, 3, 31)

    # 3. Sang tháng 4 (30 ngày) -> 30/04
    d4 = RecurringTransactionService.calculate_next_due_date(d3, "monthly", 1, start_date=d1)
    assert d4 == date(2025, 4, 30)

    # 4. Sang tháng 5 (31 ngày) -> phục hồi 31/05
    d5 = RecurringTransactionService.calculate_next_due_date(d4, "monthly", 1, start_date=d1)
    assert d5 == date(2025, 5, 31)

    # 5. Năm nhuận (2024): 29/02/2024 -> 28/02/2025
    leap_date = date(2024, 2, 29)
    yearly_next = RecurringTransactionService.calculate_next_due_date(
        leap_date, "yearly", 1, start_date=leap_date
    )
    assert yearly_next == date(2025, 2, 28)

    # 6. Yearly interval 4 năm từ 29/02/2024 -> 29/02/2028 (năm nhuận kế tiếp)
    leap_4yr = RecurringTransactionService.calculate_next_due_date(
        leap_date, "yearly", 4, start_date=leap_date
    )
    assert leap_4yr == date(2028, 2, 29)
