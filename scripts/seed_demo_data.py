"""
Script tạo dữ liệu mẫu (Seed Demo Data) an toàn phục vụ buổi thuyết trình/đánh giá đồ án.

Quy tắc kỹ thuật & an toàn:
1. KHÔNG tự động chạy script này khi khởi động server hoặc ứng dụng.
2. TÍNH IDEMPOTENT: Nếu tài khoản demo đã tồn tại, script sẽ kiểm tra và không tạo lại hay ghi đè.
3. KHÔNG XÓA DỮ LIỆU HIỆN CÓ: Tuyệt đối không gọi reset database, drop table hay truncate.
4. TÀI KHOẢN CÔ LẬP: Sử dụng tài khoản demo chuyên biệt `demo@expensetracker-demo.com`.
5. TOÀN DIỆN DỮ LIỆU:
   - 1 Người dùng demo: `demo@expensetracker-demo.com` (mật khẩu: `DemoPassword123@`)
   - 2 Ví tài chính cá nhân: "Ví Tiền Mặt" (Số dư ban đầu: 2.000.000đ) & "Tài Khoản Techcombank" (Số dư ban đầu: 25.000.000đ)
   - 1 Không gian gia đình: "Gia Đình Hạnh Phúc" (User đóng vai trò Owner)
   - 1 Ví gia đình: "Quỹ Chung Gia Đình" (Số dư ban đầu: 15.000.000đ)
   - 1 Ngân sách tháng: Ngân sách "Ăn uống" hạn mức 5.000.000đ
   - Các giao dịch mẫu thu/chi thực tế
   - 1 Giao dịch chuyển tiền nội bộ giữa ví tiền mặt và ngân hàng (kèm bút toán kép)
   - 1 Quy tắc giao dịch định kỳ: "Tiền Internet Hàng Tháng"
"""

import sys
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

# Thêm đường dẫn backend vào sys.path để import model và db session
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.account import Account
from app.models.budget import Budget
from app.models.category import Category
from app.models.family import Family
from app.models.family_member import FamilyMember
from app.models.recurring_transaction import RecurringTransaction
from app.models.transaction import Transaction
from app.models.transfer import Transfer
from app.models.user import User

OLD_DEMO_EMAIL = "demo@expensetracker.local"
DEMO_EMAIL = "demo@expensetracker-demo.com"
DEMO_PASSWORD = "DemoPassword123@"
DEMO_NAME = "Người Dùng Demo"


def seed_demo_data() -> None:
    print("=" * 65)
    print("BẮT ĐẦU KHỞI TẠO DỮ LIỆU MẪU (SEED DEMO DATA)")
    print("=" * 65)

    db: Session = SessionLocal()
    try:
        # 1. Kiểm tra tài khoản demo mới đã tồn tại chưa
        existing_user = db.execute(select(User).where(User.email == DEMO_EMAIL)).scalar_one_or_none()
        if existing_user:
            print(f"[*] Tài khoản demo '{DEMO_EMAIL}' đã tồn tại trong cơ sở dữ liệu.")
            print("[*] Giữ nguyên dữ liệu hiện có (idempotent), không tạo đè.")
            print(f"[*] Thông tin đăng nhập: Email={DEMO_EMAIL} | Mật khẩu={DEMO_PASSWORD}")
            return

        # 2. Kiểm tra nếu có tài khoản demo cũ (demo@expensetracker.local) -> cập nhật sang email mới
        old_user = db.execute(select(User).where(User.email == OLD_DEMO_EMAIL)).scalar_one_or_none()
        if old_user:
            print(f"[*] Tìm thấy tài khoản demo cũ '{OLD_DEMO_EMAIL}'. Đang di chuyển sang '{DEMO_EMAIL}'...")
            old_user.email = DEMO_EMAIL
            db.commit()
            print(f"[✓] Đã cập nhật thành công email tài khoản demo sang '{DEMO_EMAIL}'.")
            print("[*] Giữ nguyên toàn bộ UUID, số dư ví, gia đình, ngân sách và giao dịch.")
            print(f"[*] Thông tin đăng nhập: Email={DEMO_EMAIL} | Mật khẩu={DEMO_PASSWORD}")
            return

        # 3. Tạo tài khoản demo mới hoàn toàn nếu chưa từng tồn tại
        print(f"[1/7] Tạo người dùng demo: {DEMO_EMAIL}...")
        user = User(
            email=DEMO_EMAIL,
            display_name=DEMO_NAME,
            password_hash=hash_password(DEMO_PASSWORD),
            is_active=True,
            email_verified_at=datetime.now(UTC),
        )
        db.add(user)
        db.flush()

        # 3. Tạo ví cá nhân
        print("[2/7] Tạo ví cá nhân (Tiền mặt & Ngân hàng)...")
        cash_wallet = Account(
            user_id=user.id,
            name="Ví Tiền Mặt",
            scope="personal",
            account_type="cash",
            initial_balance=Decimal(2000000),
            currency="VND",
            is_archived=False,
        )
        bank_wallet = Account(
            user_id=user.id,
            name="Tài Khoản Techcombank",
            scope="personal",
            account_type="bank",
            initial_balance=Decimal(25000000),
            currency="VND",
            is_archived=False,
        )
        db.add_all([cash_wallet, bank_wallet])
        db.flush()

        # 4. Tạo nhóm gia đình và ví chung gia đình
        print("[3/7] Tạo không gian gia đình & ví chung...")
        family = Family(
            name="Gia Đình Hạnh Phúc",
            owner_user_id=user.id,
        )
        db.add(family)
        db.flush()

        member = FamilyMember(
            family_id=family.id,
            user_id=user.id,
            role="owner",
        )
        db.add(member)
        db.flush()

        family_wallet = Account(
            user_id=None,
            family_id=family.id,
            name="Quỹ Chung Gia Đình",
            scope="family",
            account_type="bank",
            initial_balance=Decimal(15000000),
            currency="VND",
            is_archived=False,
        )
        db.add(family_wallet)
        db.flush()

        # 5. Lấy danh mục hệ thống để gán cho giao dịch mẫu
        print("[4/7] Tra cứu danh mục chi tiêu/thu nhập...")
        food_cat = db.execute(
            select(Category).where(
                Category.scope == "system",
                Category.type == "expense",
                Category.name == "Ăn uống",
            )
        ).scalar_one_or_none()

        salary_cat = db.execute(
            select(Category).where(
                Category.scope == "system",
                Category.type == "income",
                Category.name == "Lương chính",
            )
        ).scalar_one_or_none()

        transport_cat = db.execute(
            select(Category).where(
                Category.scope == "system",
                Category.type == "expense",
                Category.name == "Di chuyển",
            )
        ).scalar_one_or_none()

        today = date.today()
        now = datetime.now(UTC)

        # 6. Tạo các giao dịch mẫu
        print("[5/7] Tạo các giao dịch thu chi mẫu...")
        tx_salary = Transaction(
            user_id=user.id,
            account_id=bank_wallet.id,
            category_id=salary_cat.id if salary_cat else None,
            type="income",
            amount=Decimal(35000000),
            occurred_at=now - timedelta(days=10),
            note="Lương tháng hiện tại chuyển khoản",
        )
        tx_food = Transaction(
            user_id=user.id,
            account_id=cash_wallet.id,
            category_id=food_cat.id if food_cat else None,
            type="expense",
            amount=Decimal(650000),
            occurred_at=now - timedelta(days=3),
            note="Tiệc tối cuối tuần",
        )
        tx_transport = Transaction(
            user_id=user.id,
            account_id=bank_wallet.id,
            category_id=transport_cat.id if transport_cat else None,
            type="expense",
            amount=Decimal(250000),
            occurred_at=now - timedelta(days=1),
            note="Đổ xăng và phí cầu đường",
        )
        db.add_all([tx_salary, tx_food, tx_transport])
        db.flush()

        # 7. Tạo giao dịch chuyển tiền mẫu (Bút toán kép)
        print("[6/7] Tạo bút toán chuyển tiền từ Techcombank sang Ví Tiền Mặt...")
        transfer_tx = Transfer(
            created_by=user.id,
            from_account_id=bank_wallet.id,
            to_account_id=cash_wallet.id,
            amount=Decimal(3000000),
            fee_amount=Decimal(5000),
            occurred_at=now - timedelta(days=5),
            note="Rút tiền mặt tại cây ATM Techcombank",
        )
        db.add(transfer_tx)
        db.flush()

        # Tạo hai bút toán kép liên kết transfer
        tx_out = Transaction(
            user_id=user.id,
            account_id=bank_wallet.id,
            transfer_id=transfer_tx.id,
            type="transfer_out",
            amount=Decimal(3000000),
            occurred_at=now - timedelta(days=5),
            note="Chuyển tiền sang Ví Tiền Mặt",
        )
        tx_in = Transaction(
            user_id=user.id,
            account_id=cash_wallet.id,
            transfer_id=transfer_tx.id,
            type="transfer_in",
            amount=Decimal(3000000),
            occurred_at=now - timedelta(days=5),
            note="Nhận tiền từ Tài Khoản Techcombank",
        )
        db.add_all([tx_out, tx_in])

        # Phí chuyển tiền nếu có
        if transport_cat:  # hoặc danh mục chi phí khác
            tx_fee = Transaction(
                user_id=user.id,
                account_id=bank_wallet.id,
                category_id=transport_cat.id,
                transfer_id=transfer_tx.id,
                type="transfer_fee",
                amount=Decimal(5000),
                occurred_at=now - timedelta(days=5),
                note="Phí rút tiền ATM",
            )
            db.add(tx_fee)
        db.flush()

        # 8. Tạo ngân sách mẫu và quy tắc định kỳ
        print("[7/7] Thiết lập ngân sách 'Ăn uống' và khoản định kỳ...")
        if food_cat:
            first_day = today.replace(day=1)
            next_month = (first_day + timedelta(days=32)).replace(day=1)
            last_day = next_month - timedelta(days=1)
            budget = Budget(
                name="Ngân sách Ăn uống tháng này",
                scope="personal",
                user_id=user.id,
                category_id=food_cat.id,
                amount_limit=Decimal(5000000),
                period_start=first_day,
                period_end=last_day,
                warning_threshold=Decimal("80.0"),
            )
            db.add(budget)

        if food_cat:
            recurring = RecurringTransaction(
                name="Tiền Internet Cáp Quang",
                type="expense",
                scope="personal",
                user_id=user.id,
                created_by=user.id,
                account_id=bank_wallet.id,
                category_id=food_cat.id,
                amount=Decimal(350000),
                frequency="monthly",
                interval_value=1,
                start_date=today - timedelta(days=30),
                next_due_date=today,
                note="Cước Internet Viettel hàng tháng",
                is_active=True,
            )
            db.add(recurring)

        db.commit()
        print("=" * 65)
        print("ĐÃ TẠO DỮ LIỆU MẪU THÀNH CÔNG CHO BUỔI TRÌNH DIỄN!")
        print(f"[*] Tài khoản đăng nhập demo: {DEMO_EMAIL}")
        print(f"[*] Mật khẩu đăng nhập:      {DEMO_PASSWORD}")
        print(f"[*] Họ và tên:               {DEMO_NAME}")
        print("=" * 65)

    except Exception as e:
        db.rollback()
        print(f"[!] Lỗi khi khởi tạo dữ liệu mẫu: {e}", file=sys.stderr)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_data()
