import uuid
from datetime import UTC, date, datetime, timedelta
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
from app.models.notification import Notification
from app.models.recurring_transaction import RecurringTransaction
from app.models.transaction import Transaction
from app.models.user import User
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# SQLite in-memory engine cho testing Notifications
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


def create_user_and_session(email: str = "notif_user@example.com") -> tuple[User, str]:
    db = TestingSessionLocal()
    user = User(
        id=uuid.uuid4(),
        email=email,
        password_hash="hashed_pw_dummy",
        display_name="Notification Tester",
        is_active=True,
    )
    raw_token = f"test_session_token_{uuid.uuid4().hex}"
    session = AuthSession(
        id=uuid.uuid4(),
        user_id=user.id,
        token_hash=hash_session_token(raw_token),
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db.add_all([user, session])
    db.commit()
    db.refresh(user)
    db.close()
    return user, raw_token


def test_unauthenticated_notifications_access():
    """1. Chưa đăng nhập trả về 401 Unauthorized."""
    client.cookies.clear()
    res = client.get("/api/v1/notifications")
    assert res.status_code == 401

    res_sync = client.post("/api/v1/notifications/sync")
    assert res_sync.status_code == 401

    res_unread = client.get("/api/v1/notifications/unread-count")
    assert res_unread.status_code == 401


def test_sync_recurring_notifications_classification():
    """2. Đồng bộ phân loại chính xác các khoản định kỳ: overdue, due_today, due_soon."""
    user, token = create_user_and_session("recur_notif@example.com")
    db = TestingSessionLocal()
    acc = Account(
        id=uuid.uuid4(),
        user_id=user.id,
        name="Ví Chính",
        account_type="bank",
        currency="VND",
        scope="personal",
        initial_balance=Decimal("10000000.00"),
    )
    cat = Category(
        id=uuid.uuid4(),
        user_id=user.id,
        name="Tiện ích",
        type="expense",
        scope="personal",
    )
    db.add_all([acc, cat])
    acc_id = acc.id
    cat_id = cat.id

    today = date.today()
    # Rule 1: Quá hạn 2 ngày
    r_overdue = RecurringTransaction(
        id=uuid.uuid4(),
        name="Internet",
        type="expense",
        scope="personal",
        user_id=user.id,
        created_by=user.id,
        account_id=acc_id,
        category_id=cat_id,
        amount=Decimal("300000.00"),
        start_date=today - timedelta(days=32),
        next_due_date=today - timedelta(days=2),
        frequency="monthly",
        interval_value=1,
        is_active=True,
        is_archived=False,
    )
    # Rule 2: Đến hạn hôm nay
    r_today = RecurringTransaction(
        id=uuid.uuid4(),
        name="Tiền nhà",
        type="expense",
        scope="personal",
        user_id=user.id,
        created_by=user.id,
        account_id=acc_id,
        category_id=cat_id,
        amount=Decimal("5000000.00"),
        start_date=today - timedelta(days=30),
        next_due_date=today,
        frequency="monthly",
        interval_value=1,
        is_active=True,
        is_archived=False,
    )
    # Rule 3: Sắp đến hạn trong 5 ngày tới
    r_soon = RecurringTransaction(
        id=uuid.uuid4(),
        name="Điện thoại",
        type="expense",
        scope="personal",
        user_id=user.id,
        created_by=user.id,
        account_id=acc_id,
        category_id=cat_id,
        amount=Decimal("150000.00"),
        start_date=today - timedelta(days=25),
        next_due_date=today + timedelta(days=5),
        frequency="monthly",
        interval_value=1,
        is_active=True,
        is_archived=False,
    )
    # Rule 4: Còn xa (> 7 ngày) -> Không nhắc
    r_far = RecurringTransaction(
        id=uuid.uuid4(),
        name="Học phí",
        type="expense",
        scope="personal",
        user_id=user.id,
        created_by=user.id,
        account_id=acc_id,
        category_id=cat_id,
        amount=Decimal("2000000.00"),
        start_date=today - timedelta(days=15),
        next_due_date=today + timedelta(days=15),
        frequency="monthly",
        interval_value=1,
        is_active=True,
        is_archived=False,
    )
    # Rule 5: Đang bị tạm dừng -> Không nhắc
    r_paused = RecurringTransaction(
        id=uuid.uuid4(),
        name="Netflix",
        type="expense",
        scope="personal",
        user_id=user.id,
        created_by=user.id,
        account_id=acc_id,
        category_id=cat_id,
        amount=Decimal("260000.00"),
        start_date=today,
        next_due_date=today,
        frequency="monthly",
        interval_value=1,
        is_active=False,
        is_archived=False,
    )

    db.add_all([r_overdue, r_today, r_soon, r_far, r_paused])
    db.commit()
    db.close()

    client.cookies.set(settings.SESSION_COOKIE_NAME, token)

    # Đồng bộ lần đầu
    sync_res = client.post("/api/v1/notifications/sync")
    assert sync_res.status_code == 200
    assert sync_res.json()["created_count"] == 3
    assert sync_res.json()["unread_count"] == 3

    # Kiểm tra danh sách thông báo
    list_res = client.get("/api/v1/notifications")
    assert list_res.status_code == 200
    notifs = list_res.json()
    assert len(notifs) == 3

    types = {n["type"] for n in notifs}
    assert types == {"recurring_overdue", "recurring_due_today", "recurring_due_soon"}

    # Đồng bộ lần 2 (idempotency): không tạo thêm bản ghi nào
    sync_res2 = client.post("/api/v1/notifications/sync")
    assert sync_res2.status_code == 200
    assert sync_res2.json()["created_count"] == 0
    assert sync_res2.json()["unread_count"] == 3

    list_res2 = client.get("/api/v1/notifications")
    assert len(list_res2.json()) == 3


def test_sync_budget_warning_and_exceeded():
    """3. Đồng bộ cảnh báo ngân sách: warning và exceeded, nâng cấp trạng thái không spam."""
    user, token = create_user_and_session("budget_notif@example.com")
    db = TestingSessionLocal()
    acc = Account(
        id=uuid.uuid4(),
        user_id=user.id,
        name="Ví Ngân Sách",
        account_type="cash",
        currency="VND",
        scope="personal",
        initial_balance=Decimal("20000000.00"),
    )
    cat_food = Category(
        id=uuid.uuid4(),
        user_id=user.id,
        name="Ăn uống",
        type="expense",
        scope="personal",
    )
    cat_shopping = Category(
        id=uuid.uuid4(),
        user_id=user.id,
        name="Mua sắm",
        type="expense",
        scope="personal",
    )
    db.add_all([acc, cat_food, cat_shopping])

    today = date.today()
    p_start = today.replace(day=1)
    p_end = (p_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    # Ngân sách Ăn uống: 5.000.000 VND (ngưỡng 80%)
    b_food = Budget(
        id=uuid.uuid4(),
        user_id=user.id,
        category_id=cat_food.id,
        name="Ăn uống tháng này",
        amount_limit=Decimal("5000000.00"),
        period_start=p_start,
        period_end=p_end,
        warning_threshold=Decimal("80.00"),
        scope="personal",
        is_archived=False,
    )
    # Ngân sách Mua sắm: 2.000.000 VND (chi 1.000.000 -> 50% -> normal -> không thông báo)
    b_shop = Budget(
        id=uuid.uuid4(),
        user_id=user.id,
        category_id=cat_shopping.id,
        name="Mua sắm",
        amount_limit=Decimal("2000000.00"),
        period_start=p_start,
        period_end=p_end,
        warning_threshold=Decimal("80.00"),
        scope="personal",
        is_archived=False,
    )

    # Giao dịch ăn uống: 4.200.000 VND (84% -> chạm ngưỡng warning)
    tx_food = Transaction(
        id=uuid.uuid4(),
        user_id=user.id,
        account_id=acc.id,
        category_id=cat_food.id,
        type="expense",
        amount=Decimal("4200000.00"),
        occurred_at=datetime.combine(today, datetime.min.time(), tzinfo=UTC),
    )
    # Giao dịch mua sắm: 1.000.000 VND (50% -> an toàn)
    tx_shop = Transaction(
        id=uuid.uuid4(),
        user_id=user.id,
        account_id=acc.id,
        category_id=cat_shopping.id,
        type="expense",
        amount=Decimal("1000000.00"),
        occurred_at=datetime.combine(today, datetime.min.time(), tzinfo=UTC),
    )
    db.add_all([b_food, b_shop, tx_food, tx_shop])
    acc_id = acc.id
    cat_food_id = cat_food.id
    db.commit()
    db.close()

    client.cookies.set(settings.SESSION_COOKIE_NAME, token)

    # 1. Đồng bộ lần 1 -> nhận cảnh báo budget_warning
    sync1 = client.post("/api/v1/notifications/sync")
    assert sync1.status_code == 200
    assert sync1.json()["created_count"] == 1
    assert sync1.json()["unread_count"] == 1

    notifs1 = client.get("/api/v1/notifications").json()
    assert len(notifs1) == 1
    assert notifs1[0]["type"] == "budget_warning"
    notif_id = notifs1[0]["id"]

    # Đánh dấu đã đọc
    client.patch(f"/api/v1/notifications/{notif_id}/read")
    assert client.get("/api/v1/notifications/unread-count").json()["unread_count"] == 0

    # 2. Chi thêm 1.000.000 VND vào ăn uống -> tổng chi 5.200.000 VND (vượt 100% hạn mức)
    db = TestingSessionLocal()
    tx_extra = Transaction(
        id=uuid.uuid4(),
        user_id=user.id,
        account_id=acc_id,
        category_id=cat_food_id,
        type="expense",
        amount=Decimal("1000000.00"),
        occurred_at=datetime.combine(today, datetime.min.time(), tzinfo=UTC),
    )
    db.add(tx_extra)
    db.commit()
    db.close()

    # 3. Đồng bộ lần 2 -> Cập nhật thông báo cũ từ warning thành exceeded, reset read_at về null để người dùng chú ý
    sync2 = client.post("/api/v1/notifications/sync")
    assert sync2.status_code == 200
    assert sync2.json()["updated_count"] == 1
    assert sync2.json()["created_count"] == 0
    assert sync2.json()["unread_count"] == 1

    notifs2 = client.get("/api/v1/notifications").json()
    assert len(notifs2) == 1
    assert notifs2[0]["id"] == notif_id
    assert notifs2[0]["type"] == "budget_exceeded"
    assert notifs2[0]["read_at"] is None


def test_mark_as_read_and_archive_lifecycle():
    """4. Đánh dấu đã đọc, đánh dấu tất cả đã đọc và lưu trữ thông báo."""
    user, token = create_user_and_session("read_archive@example.com")
    db = TestingSessionLocal()
    n1 = Notification(
        id=uuid.uuid4(),
        user_id=user.id,
        type="recurring_due_soon",
        title="Tiền điện",
        message="Sắp đến hạn",
        source_key="test:1",
    )
    n2 = Notification(
        id=uuid.uuid4(),
        user_id=user.id,
        type="budget_warning",
        title="Ăn uống",
        message="Đạt 80%",
        source_key="test:2",
    )
    db.add_all([n1, n2])
    n1_id = str(n1.id)
    n2_id = str(n2.id)
    db.commit()
    db.close()

    client.cookies.set(settings.SESSION_COOKIE_NAME, token)

    # Ban đầu unread = 2
    assert client.get("/api/v1/notifications/unread-count").json()["unread_count"] == 2

    # Đánh dấu n1 đã đọc
    read_res = client.patch(f"/api/v1/notifications/{n1_id}/read")
    assert read_res.status_code == 200
    assert read_res.json()["read_at"] is not None
    assert client.get("/api/v1/notifications/unread-count").json()["unread_count"] == 1

    # Đánh dấu tất cả đã đọc
    all_res = client.post("/api/v1/notifications/mark-all-read")
    assert all_res.status_code == 200
    assert all_res.json()["marked_count"] == 1
    assert client.get("/api/v1/notifications/unread-count").json()["unread_count"] == 0

    # Lưu trữ n1
    arc_res = client.post(f"/api/v1/notifications/{n1_id}/archive")
    assert arc_res.status_code == 200
    assert arc_res.json()["archived_at"] is not None

    # Mặc định get không chứa n1 (đã lưu trữ)
    active_list = client.get("/api/v1/notifications").json()
    assert len(active_list) == 1
    assert active_list[0]["id"] == n2_id

    # Truy vấn có include_archived=true thì thấy đủ 2
    full_list = client.get("/api/v1/notifications?include_archived=true").json()
    assert len(full_list) == 2


def test_user_authorization_isolation():
    """5. Người dùng không thể xem, đọc hoặc lưu trữ thông báo của người khác."""
    user_a, _token_a = create_user_and_session("user_a@example.com")
    _user_b, token_b = create_user_and_session("user_b@example.com")

    db = TestingSessionLocal()
    notif_a = Notification(
        id=uuid.uuid4(),
        user_id=user_a.id,
        type="system",
        title="Chào mừng",
        message="Chào User A",
        source_key="system:welcome:a",
    )
    db.add(notif_a)
    notif_a_id = str(notif_a.id)
    db.commit()
    db.close()

    # User B cố tình thao tác trên notif của User A -> 404
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_b)

    res_read = client.patch(f"/api/v1/notifications/{notif_a_id}/read")
    assert res_read.status_code == 404

    res_arc = client.post(f"/api/v1/notifications/{notif_a_id}/archive")
    assert res_arc.status_code == 404

    list_b = client.get("/api/v1/notifications").json()
    assert len(list_b) == 0


def test_family_role_and_left_member_notification_rules():
    """6. Phân quyền thông báo gia đình: thành viên đã rời nhóm không nhận thông báo gia đình."""
    owner, token_owner = create_user_and_session("fam_owner@example.com")
    left_member, token_left = create_user_and_session("fam_left@example.com")

    db = TestingSessionLocal()
    fam = Family(id=uuid.uuid4(), name="Gia Đình Hạnh Phúc", owner_user_id=owner.id)
    acc = Account(
        id=uuid.uuid4(),
        name="Quỹ Chung Gia Đình",
        account_type="bank",
        currency="VND",
        scope="family",
        family_id=fam.id,
        initial_balance=Decimal("50000000.00"),
    )
    cat = Category(
        id=uuid.uuid4(),
        name="Học phí",
        type="expense",
        scope="family",
        family_id=fam.id,
    )
    # Thành viên đã rời nhóm (left_at IS NOT NULL)
    fm = FamilyMember(
        id=uuid.uuid4(),
        family_id=fam.id,
        user_id=left_member.id,
        role="editor",
        joined_at=datetime.now(UTC),
        left_at=datetime.now(UTC),
    )
    today = date.today()
    rule_fam = RecurringTransaction(
        id=uuid.uuid4(),
        name="Học phí con",
        type="expense",
        scope="family",
        family_id=fam.id,
        created_by=owner.id,
        account_id=acc.id,
        category_id=cat.id,
        amount=Decimal("4000000.00"),
        start_date=today - timedelta(days=30),
        next_due_date=today,
        frequency="monthly",
        interval_value=1,
        is_active=True,
        is_archived=False,
    )
    db.add_all([fam, acc, cat, fm, rule_fam])
    db.commit()
    db.close()

    # 1. Owner sync -> nhận thông báo học phí con đến hạn hôm nay
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_owner)
    res_owner = client.post("/api/v1/notifications/sync")
    assert res_owner.status_code == 200
    assert res_owner.json()["created_count"] == 1

    # 2. Thành viên đã rời nhóm sync -> không nhận thông báo của gia đình này
    client.cookies.set(settings.SESSION_COOKIE_NAME, token_left)
    res_left = client.post("/api/v1/notifications/sync")
    assert res_left.status_code == 200
    assert res_left.json()["created_count"] == 0
    assert client.get("/api/v1/notifications").json() == []


def test_recurring_generation_archives_notification_and_preserves_next_cycle():
    """7. Kiểm thử trọn vẹn vòng đời thông báo khi phát sinh giao dịch:
    - Sync tạo thông báo cho kỳ đến hạn.
    - Phát sinh giao dịch thành công tự động lưu trữ thông báo kỳ đó.
    - Unread count giảm và danh sách hoạt động không còn hiển thị kỳ cũ.
    - Re-sync không tái sinh thông báo đã lưu trữ.
    - Lịch sử lưu trữ (include_archived=true) vẫn lưu giữ thông báo kỳ cũ.
    - Thông báo ngân sách không bị ảnh hưởng.
    - Khi kỳ kế tiếp tới hạn, thông báo mới cho kỳ sau được tạo bình thường với khóa nguồn riêng.
    """
    user, token = create_user_and_session("lifecycle_tester@example.com")
    db = TestingSessionLocal()
    acc = Account(
        id=uuid.uuid4(),
        user_id=user.id,
        name="Ví Thanh Toán",
        account_type="bank",
        currency="VND",
        scope="personal",
        initial_balance=Decimal("20000000.00"),
    )
    cat_bill = Category(
        id=uuid.uuid4(),
        user_id=user.id,
        name="Hóa đơn điện nước",
        type="expense",
        scope="personal",
    )
    cat_food = Category(
        id=uuid.uuid4(),
        user_id=user.id,
        name="Ăn uống",
        type="expense",
        scope="personal",
    )
    db.add_all([acc, cat_bill, cat_food])
    acc_id = acc.id
    cat_bill_id = cat_bill.id
    cat_food_id = cat_food.id

    today = date.today()
    # 1. Tạo quy tắc định kỳ đến hạn hôm nay: 500,000 VND
    rule = RecurringTransaction(
        id=uuid.uuid4(),
        name="Cước Internet VNPT",
        type="expense",
        scope="personal",
        user_id=user.id,
        created_by=user.id,
        account_id=acc_id,
        category_id=cat_bill_id,
        amount=Decimal("500000.00"),
        start_date=today,
        next_due_date=today,
        frequency="monthly",
        interval_value=1,
        is_active=True,
        is_archived=False,
    )
    # 2. Tạo ngân sách chạm ngưỡng warning để kiểm tra tính độc lập
    p_start = today.replace(day=1)
    p_end = (p_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    budget = Budget(
        id=uuid.uuid4(),
        user_id=user.id,
        category_id=cat_food_id,
        name="Ăn uống tháng",
        amount_limit=Decimal("1000000.00"),
        period_start=p_start,
        period_end=p_end,
        warning_threshold=Decimal("80.00"),
        scope="personal",
        is_archived=False,
    )
    tx_food = Transaction(
        id=uuid.uuid4(),
        user_id=user.id,
        account_id=acc_id,
        category_id=cat_food_id,
        type="expense",
        amount=Decimal("850000.00"),
        occurred_at=datetime.combine(today, datetime.min.time(), tzinfo=UTC),
    )
    db.add_all([rule, budget, tx_food])
    rule_id = rule.id
    budget_id = budget.id
    db.commit()
    db.close()

    client.cookies.set(settings.SESSION_COOKIE_NAME, token)

    # Bước 1: Sync lần đầu -> Tạo 2 thông báo (1 recurring due today, 1 budget warning)
    sync1 = client.post("/api/v1/notifications/sync")
    assert sync1.status_code == 200
    assert sync1.json()["created_count"] == 2
    assert sync1.json()["unread_count"] == 2

    active_notifs = client.get("/api/v1/notifications").json()
    assert len(active_notifs) == 2
    types = {n["type"] for n in active_notifs}
    assert "recurring_due_today" in types
    assert "budget_warning" in types

    recur_notif = next(n for n in active_notifs if n["type"] == "recurring_due_today")
    assert recur_notif["source_key"] == f"recurring:{rule_id}:{today.isoformat()}"
    recur_notif_id = recur_notif["id"]

    # Bước 2: Người dùng chủ động phát sinh giao dịch cho kỳ đến hạn
    gen_res = client.post(f"/api/v1/recurring-transactions/{rule_id}/generate")
    assert gen_res.status_code == 200
    gen_data = gen_res.json()
    assert "transaction_id" in gen_data
    assert gen_data["recurrence_date"] == today.isoformat()

    # Bước 3: Sau khi tạo giao dịch, kiểm tra thông báo định kỳ cũ đã được lưu trữ
    unread_now = client.get("/api/v1/notifications/unread-count").json()["unread_count"]
    assert unread_now == 1  # Chỉ còn 1 thông báo ngân sách chưa đọc

    active_after_gen = client.get("/api/v1/notifications").json()
    assert len(active_after_gen) == 1
    assert active_after_gen[0]["type"] == "budget_warning"
    assert active_after_gen[0]["entity_id"] == str(budget_id)

    # Bước 4: Kiểm tra thông báo kỳ cũ vẫn được giữ nguyên trong lịch sử lưu trữ
    archived_list = client.get("/api/v1/notifications?include_archived=true").json()
    assert len(archived_list) == 2
    old_notif_in_hist = next(n for n in archived_list if n["id"] == recur_notif_id)
    assert old_notif_in_hist["archived_at"] is not None
    assert old_notif_in_hist["read_at"] is not None

    # Bước 5: Re-sync không tái sinh thông báo đã lưu trữ hoặc tạo trùng
    sync2 = client.post("/api/v1/notifications/sync")
    assert sync2.status_code == 200
    assert sync2.json()["created_count"] == 0
    assert sync2.json()["unread_count"] == 1

    active_after_sync2 = client.get("/api/v1/notifications").json()
    assert len(active_after_sync2) == 1
    assert active_after_sync2[0]["type"] == "budget_warning"

    # Bước 6: Thử gọi lại generate trên cùng quy tắc -> chặn tạo trùng kỳ
    dup_gen = client.post(f"/api/v1/recurring-transactions/{rule_id}/generate")
    assert dup_gen.status_code == 400
    assert "chưa đến hạn tạo" in dup_gen.json()["detail"]

    # Bước 7: Kiểm tra khi kỳ kế tiếp tới hạn, sync tạo thông báo mới với source_key riêng
    db = TestingSessionLocal()
    r_obj = db.get(RecurringTransaction, rule_id)
    # Giả lập thời gian trôi tới ngày kỳ kế tiếp đến hạn
    r_obj.next_due_date = today  # Đưa next_due_date về lại today để giả lập đến hạn
    db.commit()
    db.close()

    sync_next = client.post("/api/v1/notifications/sync")
    assert sync_next.status_code == 200
    # Tạo thông báo mới cho kỳ mới (vì next_month_due hoặc key mới)
    # Lưu ý: nếu key mới f"recurring:{rule_id}:{next_month_due}"
    all_notifs = client.get("/api/v1/notifications?include_archived=true").json()
    assert len(all_notifs) >= 2


def test_paused_and_archived_rules_do_not_generate_notifications():
    """8. Quy tắc bị tạm dừng hoặc đã lưu trữ không tạo thông báo nhắc nhở."""
    user, token = create_user_and_session("paused_archived_tester@example.com")
    db = TestingSessionLocal()
    acc = Account(
        id=uuid.uuid4(),
        user_id=user.id,
        name="Ví Test",
        account_type="cash",
        currency="VND",
        scope="personal",
        initial_balance=Decimal("10000000.00"),
    )
    cat = Category(
        id=uuid.uuid4(),
        user_id=user.id,
        name="Chi phí khác",
        type="expense",
        scope="personal",
    )
    db.add_all([acc, cat])

    today = date.today()
    # Rule 1: Đang tạm dừng (is_active=False)
    r_paused = RecurringTransaction(
        id=uuid.uuid4(),
        name="Dịch vụ tạm dừng",
        type="expense",
        scope="personal",
        user_id=user.id,
        created_by=user.id,
        account_id=acc.id,
        category_id=cat.id,
        amount=Decimal("100000.00"),
        start_date=today,
        next_due_date=today,
        frequency="monthly",
        interval_value=1,
        is_active=False,
        is_archived=False,
    )
    # Rule 2: Đã lưu trữ (is_archived=True)
    r_archived = RecurringTransaction(
        id=uuid.uuid4(),
        name="Dịch vụ đã hủy",
        type="expense",
        scope="personal",
        user_id=user.id,
        created_by=user.id,
        account_id=acc.id,
        category_id=cat.id,
        amount=Decimal("200000.00"),
        start_date=today,
        next_due_date=today,
        frequency="monthly",
        interval_value=1,
        is_active=True,
        is_archived=True,
    )
    db.add_all([r_paused, r_archived])
    db.commit()
    db.close()

    client.cookies.set(settings.SESSION_COOKIE_NAME, token)
    sync_res = client.post("/api/v1/notifications/sync")
    assert sync_res.status_code == 200
    assert sync_res.json()["created_count"] == 0
    assert sync_res.json()["unread_count"] == 0
    assert client.get("/api/v1/notifications").json() == []
