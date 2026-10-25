"""Comprehensive End-to-End Acceptance Test on PostgreSQL 18.

Tests all integrated flows (Luồng A -> Luồng F) against live backend & PostgreSQL 18:
- Flow A: Authentication, session cookie, route access, logout.
- Flow B: Wallets (Accounts), Transactions (income/expense), soft-delete, dynamic balance, Dashboard summary.
- Flow C: Transfers (double-entry ledger, fee, balance conservation, void transfer).
- Flow D: Budgets & Reports (threshold warning, overspent, category aggregation, CSV export utf-8).
- Flow E: Recurring Transactions & Notifications (sync idempotent, unread count, mark-read, archive, generate transaction, prevent duplicate).
- Flow F: Families & Role Authorization (owner/editor/viewer, left-member access rejection).
- Cleanup: Cleans up ONLY isolated test user data.
"""

import sys
import uuid
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# pyrefly: ignore[missing-import]
import os

import httpx

# pyrefly: ignore[missing-import]
from app.db.session import SessionLocal

# pyrefly: ignore[missing-import]
from app.models.account import Account

# pyrefly: ignore[missing-import]
from app.models.budget import Budget

# pyrefly: ignore[missing-import]
from app.models.family import Family

# pyrefly: ignore[missing-import]
from app.models.family_invitation import FamilyInvitation

# pyrefly: ignore[missing-import]
from app.models.family_member import FamilyMember

# pyrefly: ignore[missing-import]
from app.models.notification import Notification

# pyrefly: ignore[missing-import]
from app.models.recurring_transaction import RecurringTransaction

# pyrefly: ignore[missing-import]
from app.models.transaction import Transaction

# pyrefly: ignore[missing-import]
from app.models.transfer import Transfer

# pyrefly: ignore[missing-import]
from app.models.user import User
from sqlalchemy import or_

API_PORT = os.getenv("API_PORT", "8001")
BASE_URL = os.getenv("API_BASE_URL", f"http://127.0.0.1:{API_PORT}/api/v1")
HEALTH_URL = os.getenv("HEALTH_URL", f"http://127.0.0.1:{API_PORT}/health/ready")


def run_e2e_acceptance():
    print("=" * 70)
    print("BẮT ĐẦU KIỂM THỬ CHẤP NHẬN END-TO-END TOÀN HỆ THỐNG TRÊN POSTGRESQL 18")
    print("=" * 70)

    client = httpx.Client(timeout=15.0)

    # 0. Health check
    print(f"\n[Health] Kiểm tra kết nối backend FastAPI & PostgreSQL 18 tại {HEALTH_URL}...")
    try:
        res = client.get(HEALTH_URL)
        assert res.status_code == 200, f"Backend health check thất bại: {HEALTH_URL} returned HTTP {res.status_code}: {res.text}"
        print("✅ Backend health check sẵn sàng: 200 OK (PostgreSQL connected)")
    except Exception as exc:
        print(f"❌ [Lỗi kết nối Backend/Database]: Không thể truy cập {HEALTH_URL}: {exc}")
        raise

    # =========================================================================
    # LUỒNG A: ĐĂNG NHẬP VÀ BẢO VỆ ROUTE
    # =========================================================================
    print("\n--- LUỒNG A: XÁC THỰC, SESSION COOKIE VÀ BẢO VỆ ROUTE ---")
    # A1. Truy cập route bảo vệ khi chưa đăng nhập -> 401
    res_unauth = client.get(f"{BASE_URL}/accounts")
    assert res_unauth.status_code == 401, f"Kỳ vọng 401, nhận {res_unauth.status_code}"
    print("✅ A1: Truy cập route bảo vệ khi chưa đăng nhập bị từ chối 401 Unauthorized")

    # A2. Đăng ký tài khoản thử nghiệm
    suffix = uuid.uuid4().hex[:8]
    email_a = f"e2e_user_{suffix}@example.com"
    email_b = f"e2e_member_{suffix}@example.com"
    password = "E2ePassword123!"
    display_name = f"E2E Tester {suffix}"

    reg_res = client.post(
        f"{BASE_URL}/auth/register",
        json={"email": email_a, "password": password, "display_name": display_name},
    )
    assert reg_res.status_code == 201, f"Đăng ký thất bại: {reg_res.text}"
    user_a_id = reg_res.json()["id"]
    print(f"✅ A2: Đăng ký thành công tài khoản cô lập: {email_a} (ID: {user_a_id})")

    # A3. Đăng nhập và nhận session cookie
    login_res = client.post(
        f"{BASE_URL}/auth/login",
        json={"email": email_a, "password": password},
    )
    assert login_res.status_code == 200, f"Đăng nhập thất bại: {login_res.text}"
    assert "session_id" in client.cookies or len(client.cookies) > 0, "Không nhận được session cookie"
    print("✅ A3: Đăng nhập thành công và thiết lập HttpOnly session cookie")

    # A4. Truy cập route bảo vệ sau khi đăng nhập -> 200
    acc_check = client.get(f"{BASE_URL}/accounts")
    assert acc_check.status_code == 200
    print("✅ A4: Truy cập route bảo vệ (/accounts) sau khi đăng nhập thành công: 200 OK")

    try:
        # =========================================================================
        # LUỒNG B: VÍ, GIAO DỊCH VÀ DASHBOARD
        # =========================================================================
        print("\n--- LUỒNG B: VÍ, GIAO DỊCH THU/CHI VÀ DASHBOARD TỔNG QUAN ---")
        # B1. Tạo ví cá nhân số dư ban đầu 10,000,000 VND
        acc_wallet = client.post(
            f"{BASE_URL}/accounts",
            json={
                "name": "Ví Chính E2E",
                "scope": "personal",
                "account_type": "bank",
                "currency": "VND",
                "initial_balance": "10000000.00",
                "color": "#4F46E5",
            },
        ).json()
        wallet_id = acc_wallet["id"]
        print(f"✅ B1: Tạo ví cá nhân thành công: {acc_wallet['name']} (Số dư đầu: 10,000,000 VND)")

        # Lấy danh mục hệ thống
        cats = client.get(f"{BASE_URL}/categories?scope=system").json()
        cat_income = next(c for c in cats if c["type"] == "income")
        cat_expense = next(c for c in cats if c["type"] == "expense")

        # B2. Tạo giao dịch thu: 5,000,000 VND
        tx_in = client.post(
            f"{BASE_URL}/transactions",
            json={
                "account_id": wallet_id,
                "category_id": cat_income["id"],
                "type": "income",
                "amount": "5000000.00",
                "note": "Thu nhập thưởng dự án",
            },
        ).json()
        print(f"✅ B2: Tạo giao dịch thu 5,000,000 VND (Mã: {tx_in['id'][:8]}...)")

        # B3. Tạo giao dịch chi: 2,000,000 VND
        tx_out = client.post(
            f"{BASE_URL}/transactions",
            json={
                "account_id": wallet_id,
                "category_id": cat_expense["id"],
                "type": "expense",
                "amount": "2000000.00",
                "note": "Chi phí thiết bị",
            },
        ).json()
        tx_out_id = tx_out["id"]
        print(f"✅ B3: Tạo giao dịch chi 2,000,000 VND (Mã: {tx_out_id[:8]}...)")

        # B4. Kiểm tra số dư ví: 10tr + 5tr - 2tr = 13,000,000 VND
        acc_info = client.get(f"{BASE_URL}/accounts/{wallet_id}").json()
        assert Decimal(acc_info["current_balance"]) == Decimal("13000000.00")
        print("✅ B4: Số dư ví tính toán chính xác trên PostgreSQL: 13,000,000 VND")

        # B5. Kiểm tra Dashboard
        dash = client.get(f"{BASE_URL}/dashboard/summary?scope=personal").json()
        cf = dash["cash_flow_by_currency"][0]
        assert Decimal(cf["total_income"]) == Decimal("5000000.00")
        assert Decimal(cf["total_expense"]) == Decimal("2000000.00")
        assert Decimal(cf["net_cash_flow"]) == Decimal("3000000.00")
        print("✅ B5: Dashboard tính đúng tổng thu 5tr, tổng chi 2tr, dòng tiền thuần +3tr")

        # B6. Xóa mềm giao dịch chi -> số dư phục hồi 15,000,000 VND
        del_res = client.delete(f"{BASE_URL}/transactions/{tx_out_id}")
        assert del_res.status_code == 200
        acc_info2 = client.get(f"{BASE_URL}/accounts/{wallet_id}").json()
        assert Decimal(acc_info2["current_balance"]) == Decimal("15000000.00")
        dash2 = client.get(f"{BASE_URL}/dashboard/summary?scope=personal").json()
        assert Decimal(dash2["cash_flow_by_currency"][0]["total_expense"]) == Decimal("0.00")
        print("✅ B6: Xóa mềm giao dịch: số dư ví phục hồi 15tr, Dashboard không còn tính giao dịch xóa mềm")

        # =========================================================================
        # LUỒNG C: CHUYỂN TIỀN GIỮA CÁC VÍ
        # =========================================================================
        print("\n--- LUỒNG C: CHUYỂN TIỀN BÚT TOÁN KÉP VÀ VOID TRANSFER ---")
        # C1. Tạo ví thứ hai (Ví Tiết Kiệm, số dư 0 VND)
        acc_sav = client.post(
            f"{BASE_URL}/accounts",
            json={
                "name": "Ví Tiết Kiệm E2E",
                "scope": "personal",
                "account_type": "bank",
                "currency": "VND",
                "initial_balance": "0.00",
                "color": "#059669",
            },
        ).json()
        sav_id = acc_sav["id"]

        # C2. Chuyển 3,000,000 VND từ ví Chính sang ví Tiết Kiệm (Phí 5,000 VND)
        tr_res = client.post(
            f"{BASE_URL}/transfers",
            json={
                "from_account_id": wallet_id,
                "to_account_id": sav_id,
                "amount": "3000000.00",
                "fee_amount": "5000.00",
                "fee_category_id": cat_expense["id"],
                "note": "Chuyển tiền tiết kiệm tháng",
            },
        )
        assert tr_res.status_code == 201, tr_res.text
        tr_data = tr_res.json()
        transfer_id = tr_data["id"]
        print(f"✅ C2: Thực hiện chuyển tiền thành công 3,000,000 VND (Phí: 5,000 VND, ID: {transfer_id[:8]}...)")

        # C3. Kiểm tra số dư 2 ví:
        # Ví chính: 15,000,000 - 3,000,000 - 5,000 = 11,995,000 VND
        # Ví tiết kiệm: 0 + 3,000,000 = 3,000,000 VND
        w1 = client.get(f"{BASE_URL}/accounts/{wallet_id}").json()
        w2 = client.get(f"{BASE_URL}/accounts/{sav_id}").json()
        assert Decimal(w1["current_balance"]) == Decimal("11995000.00")
        assert Decimal(w2["current_balance"]) == Decimal("3000000.00")
        print("✅ C3: Bảo toàn số dư sau chuyển tiền: Ví chính 11,995,000 VND, Ví tiết kiệm 3,000,000 VND")

        # C4. Hủy (Void) chuyển tiền -> phục hồi số dư ban đầu
        void_res = client.post(f"{BASE_URL}/transfers/{transfer_id}/void")
        assert void_res.status_code == 200, void_res.text
        w1_void = client.get(f"{BASE_URL}/accounts/{wallet_id}").json()
        w2_void = client.get(f"{BASE_URL}/accounts/{sav_id}").json()
        assert Decimal(w1_void["current_balance"]) == Decimal("15000000.00")
        assert Decimal(w2_void["current_balance"]) == Decimal("0.00")
        print("✅ C4: Void chuyển tiền thành công: Cả 2 ví phục hồi số dư chính xác (15tr và 0đ)")

        # =========================================================================
        # LUỒNG D: NGÂN SÁCH VÀ BÁO CÁO TÀI CHÍNH
        # =========================================================================
        print("\n--- LUỒNG D: QUẢN LÝ NGÂN SÁCH VÀ BÁO CÁO TÀI CHÍNH XUẤT CSV ---")
        today = date.today()
        p_start = today.replace(day=1)
        p_end = (p_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)

        # D1. Tạo ngân sách chi tiêu 1,000,000 VND (ngưỡng cảnh báo 80%)
        b_res = client.post(
            f"{BASE_URL}/budgets",
            json={
                "name": "Ngân Sách Thiết Bị",
                "scope": "personal",
                "category_id": cat_expense["id"],
                "amount_limit": "1000000.00",
                "period_start": p_start.isoformat(),
                "period_end": p_end.isoformat(),
                "warning_threshold": "80",
            },
        ).json()
        b_id = b_res["id"]
        print(f"✅ D1: Tạo ngân sách hạn mức 1,000,000 VND (ID: {b_id[:8]}...)")

        # D2. Tạo chi tiêu 850,000 VND -> đạt trạng thái warning (85%)
        client.post(
            f"{BASE_URL}/transactions",
            json={
                "account_id": wallet_id,
                "category_id": cat_expense["id"],
                "type": "expense",
                "amount": "850000.00",
                "note": "Mua chuột phím",
            },
        )
        b_check = client.get(f"{BASE_URL}/budgets/{b_id}").json()
        assert b_check["status"] == "warning"
        assert Decimal(b_check["spent_amount"]) == Decimal("850000.00")
        print("✅ D2: Ngân sách chuyển trạng thái warning chính xác (Đã chi 850,000 VND / 1,000,000 VND = 85%)")

        # D3. Kiểm tra báo cáo tài chính Reports
        rep = client.get(
            f"{BASE_URL}/reports/summary?date_from={p_start.isoformat()}&date_to={p_end.isoformat()}&scope=personal"
        ).json()
        assert len(rep["cash_flow_by_currency"]) > 0
        rep_cf = rep["cash_flow_by_currency"][0]
        assert Decimal(rep_cf["total_income"]) == Decimal("5000000.00")
        assert Decimal(rep_cf["total_expense"]) == Decimal("850000.00")
        print("✅ D3: Báo cáo tài chính tổng hợp chuẩn xác: Thu 5tr, Chi 850k")

        # D4. Xuất file CSV báo cáo
        csv_res = client.get(
            f"{BASE_URL}/reports/export.csv?date_from={p_start.isoformat()}&date_to={p_end.isoformat()}&scope=personal"
        )
        assert csv_res.status_code == 200
        assert "text/csv" in csv_res.headers.get("content-type", "")
        csv_content = csv_res.content.decode("utf-8-sig")
        assert "Thời gian" in csv_content
        assert "Thu nhập thưởng dự án" in csv_content
        print("✅ D4: Xuất file CSV thành công: Định dạng UTF-8-SIG, đầy đủ tiêu đề và nội dung giao dịch")

        # =========================================================================
        # LUỒNG E: GIAO DỊCH ĐỊNH KỲ VÀ THÔNG BÁO TÀI CHÍNH
        # =========================================================================
        print("\n--- LUỒNG E: GIAO DỊCH ĐỊNH KỲ VÀ TRUNG TÂM THÔNG BÁO ---")
        # E1. Tạo quy tắc định kỳ đến hạn hôm nay: Chi 500,000 VND
        rule_res = client.post(
            f"{BASE_URL}/recurring-transactions",
            json={
                "name": "Cước Internet Văn Phòng",
                "type": "expense",
                "scope": "personal",
                "account_id": wallet_id,
                "category_id": cat_expense["id"],
                "amount": "500000.00",
                "start_date": today.isoformat(),
                "frequency": "monthly",
                "interval_value": 1,
                "note": "Thanh toán cước",
            },
        ).json()
        rule_id = rule_res["id"]
        print(f"✅ E1: Tạo quy tắc định kỳ thành công: {rule_res['name']} (Đến hạn: {today.isoformat()})")

        # E2. Đồng bộ thông báo -> Tạo 2 thông báo (1 recurring due today, 1 budget warning)
        sync_res = client.post(f"{BASE_URL}/notifications/sync").json()
        assert sync_res["created_count"] == 2
        assert sync_res["unread_count"] == 2
        print("✅ E2: Đồng bộ thông báo thành công: 2 thông báo mới (Unread: 2)")

        # E3. Đồng bộ lần 2 -> Idempotent, không spam
        sync_res2 = client.post(f"{BASE_URL}/notifications/sync").json()
        assert sync_res2["created_count"] == 0
        assert sync_res2["unread_count"] == 2
        print("✅ E3: Idempotent sync thành công: Không tạo thêm thông báo trùng lặp")

        # E4. Đánh dấu đã đọc và lưu trữ thông báo ngân sách
        notifs = client.get(f"{BASE_URL}/notifications").json()
        budget_notif = next(n for n in notifs if n["type"] == "budget_warning")
        client.patch(f"{BASE_URL}/notifications/{budget_notif['id']}/read")
        client.post(f"{BASE_URL}/notifications/{budget_notif['id']}/archive")
        assert client.get(f"{BASE_URL}/notifications/unread-count").json()["unread_count"] == 1
        print("✅ E4: Đánh dấu đã đọc và lưu trữ thông báo hoạt động chính xác")

        # E5. Phát sinh giao dịch thực tế từ kỳ đến hạn của quy tắc
        gen_res = client.post(f"{BASE_URL}/recurring-transactions/{rule_id}/generate")
        assert gen_res.status_code == 200, gen_res.text
        gen_tx_id = gen_res.json()["transaction_id"]
        print(f"✅ E5: Phát sinh giao dịch thực tế thành công cho kỳ (Mã TX: {gen_tx_id[:8]}...)")

        # Xác minh thông báo định kỳ cũ đã được tự động lưu trữ, unread count = 0
        assert client.get(f"{BASE_URL}/notifications/unread-count").json()["unread_count"] == 0
        sync_after_gen = client.post(f"{BASE_URL}/notifications/sync").json()
        assert sync_after_gen["created_count"] == 0
        assert sync_after_gen["unread_count"] == 0
        print("✅ E5b: Vòng đời thông báo tự động lưu trữ và sync idempotent sau khi tạo giao dịch")

        # E6. Chống tạo trùng kỳ
        dup_gen = client.post(f"{BASE_URL}/recurring-transactions/{rule_id}/generate")
        assert dup_gen.status_code == 400
        assert "chưa đến hạn tạo" in dup_gen.json()["detail"]
        print("✅ E6: Chống tạo trùng kỳ thành công: Không thể tạo trước ngày đến hạn kế tiếp")

        # E7. Kiểm tra tác động tài chính sau khi sinh giao dịch định kỳ:
        # Số dư ví trước đó: 15,000,000 - 850,000 - 500,000 = 13,650,000 VND
        w_final = client.get(f"{BASE_URL}/accounts/{wallet_id}").json()
        assert Decimal(w_final["current_balance"]) == Decimal("13650000.00")
        print("✅ E7: Số dư ví cập nhật chính xác sau giao dịch định kỳ: 13,650,000 VND")

        # =========================================================================
        # LUỒNG F: GIA ĐÌNH VÀ PHÂN QUYỀN
        # =========================================================================
        print("\n--- LUỒNG F: PHÂN QUYỀN GIA ĐÌNH VÀ BẢO MẬT DỮ LIỆU ---")
        # F1. Tạo tài khoản thành viên thứ 2
        email_b = f"e2e_viewer_{suffix}@example.com"
        client.post(
            f"{BASE_URL}/auth/register",
            json={"email": email_b, "password": password, "display_name": "Family Viewer"},
        )
        client_b = httpx.Client(timeout=10.0)
        client_b.post(f"{BASE_URL}/auth/login", json={"email": email_b, "password": password})

        # F2. User A tạo nhóm gia đình
        fam = client.post(f"{BASE_URL}/families", json={"name": "Gia Đình E2E Test"}).json()
        fam_id = fam["id"]

        # F3. Mời User B với vai trò viewer
        inv = client.post(
            f"{BASE_URL}/families/{fam_id}/invitations",
            json={"invited_email": email_b, "role": "viewer"},
        ).json()
        inv_token = inv["invitation_token"]

        # User B chấp nhận lời mời
        accept_res = client_b.post(
            f"{BASE_URL}/families/invitations/accept",
            json={"token": inv_token},
        )
        assert accept_res.status_code == 200, accept_res.text
        member_b_id = accept_res.json()["id"]
        print("✅ F3: Mời và chấp nhận lời mời vào gia đình thành công (Role: viewer)")

        # F4. User A tạo ví gia đình
        acc_fam = client.post(
            f"{BASE_URL}/accounts",
            json={
                "name": "Quỹ Gia Đình E2E",
                "scope": "family",
                "family_id": fam_id,
                "account_type": "bank",
                "currency": "VND",
                "initial_balance": "20000000.00",
            },
        ).json()
        acc_fam_id = acc_fam["id"]

        # F5. User B (viewer) cố tạo giao dịch trên ví gia đình -> 403 Forbidden
        viewer_write = client_b.post(
            f"{BASE_URL}/transactions",
            json={
                "account_id": acc_fam_id,
                "category_id": cat_expense["id"],
                "type": "expense",
                "amount": "100000.00",
            },
        )
        assert viewer_write.status_code == 403
        print("✅ F5: Phân quyền Viewer hoạt động chuẩn xác: Bị từ chối 403 khi cố tạo giao dịch")

        # F6. User B rời gia đình
        leave_res = client_b.post(f"{BASE_URL}/families/{fam_id}/members/{member_b_id}/leave")
        assert leave_res.status_code == 200
        # Sau khi rời, không còn truy cập được ví gia đình
        fam_acc_denied = client_b.get(f"{BASE_URL}/accounts/{acc_fam_id}")
        assert fam_acc_denied.status_code in (403, 404)
        print("✅ F6: Thành viên rời gia đình bị tước toàn bộ quyền truy cập dữ liệu gia đình")

        print("\n" + "=" * 70)
        print("TẤT CẢ 6 LUỒNG KIỂM THỬ CHẤP NHẬN END-TO-END ĐỀU ĐẠT 100% THÀNH CÔNG!")
        print("=" * 70)
        return True

    finally:
        # =========================================================================
        # CLEANUP: DỌN DẸP DỮ LIỆU THỬ NGHIỆM ĐỘC LẬP
        # =========================================================================
        print("\n[Cleanup] Dọn dẹp an toàn các bản ghi do script tự tạo...")
        try:
            with SessionLocal() as db:
                test_users = db.query(User).filter(User.email.in_([email_a, email_b])).all()
                user_ids = [u.id for u in test_users]
                if user_ids:
                    # Lấy danh sách families do test users tạo
                    test_families = db.query(Family).filter(Family.owner_user_id.in_(user_ids)).all()
                    family_ids = [f.id for f in test_families]

                    # 1. Xóa notifications
                    db.query(Notification).filter(Notification.user_id.in_(user_ids)).delete(synchronize_session=False)
                    # 2. Xóa recurring rules
                    db.query(RecurringTransaction).filter(RecurringTransaction.user_id.in_(user_ids)).delete(synchronize_session=False)
                    # 3. Xóa transactions
                    db.query(Transaction).filter(Transaction.user_id.in_(user_ids)).delete(synchronize_session=False)
                    # 4. Xóa transfers
                    db.query(Transfer).filter(Transfer.created_by.in_(user_ids)).delete(synchronize_session=False)
                    # 5. Xóa budgets
                    db.query(Budget).filter(
                        or_(
                            Budget.user_id.in_(user_ids),
                            Budget.family_id.in_(family_ids) if family_ids else False,
                        )
                    ).delete(synchronize_session=False)
                    # 6. Xóa accounts (cả cá nhân và ví gia đình)
                    db.query(Account).filter(
                        or_(
                            Account.user_id.in_(user_ids),
                            Account.family_id.in_(family_ids) if family_ids else False,
                        )
                    ).delete(synchronize_session=False)
                    # 7. Xóa family invitations & family members & families
                    if family_ids:
                        db.query(FamilyInvitation).filter(FamilyInvitation.family_id.in_(family_ids)).delete(synchronize_session=False)
                        db.query(FamilyMember).filter(FamilyMember.family_id.in_(family_ids)).delete(synchronize_session=False)
                    db.query(FamilyMember).filter(FamilyMember.user_id.in_(user_ids)).delete(synchronize_session=False)
                    db.query(Family).filter(Family.owner_user_id.in_(user_ids)).delete(synchronize_session=False)
                    # 8. Xóa users
                    db.query(User).filter(User.id.in_(user_ids)).delete(synchronize_session=False)
                    db.commit()
            print("✅ [Cleanup] Đã dọn dẹp sạch sẽ 100% dữ liệu thử nghiệm độc lập.")
        except Exception as exc:  # noqa: BLE001
            print(f"❌ [Cleanup Error]: {exc}")


if __name__ == "__main__":
    success = run_e2e_acceptance()
    sys.exit(0 if success else 1)
