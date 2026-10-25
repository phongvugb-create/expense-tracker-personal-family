import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings
from app.db.session import SessionLocal, engine
from app.models.category import Category
from sqlalchemy import func, select, text


def verify_target_db():
    print("=" * 60)
    print("XÁC MINH CƠ SỞ DỮ LIỆU ĐÍCH TRƯỚC KHI SEED")
    print("=" * 60)
    print(f"Host: {settings.POSTGRES_HOST}")
    print(f"Port: {settings.POSTGRES_PORT}")
    print(f"Database: {settings.POSTGRES_DB}")
    print(f"User: {settings.POSTGRES_USER}")

    # Kiểm tra tính đúng đắn với yêu cầu
    assert settings.POSTGRES_HOST in ("127.0.0.1", "localhost"), "Host không đúng localhost!"
    assert settings.POSTGRES_PORT == 5434, f"Port {settings.POSTGRES_PORT} không đúng 5434!"
    assert settings.POSTGRES_DB == "expense_tracker", f"DB {settings.POSTGRES_DB} không đúng expense_tracker!"
    assert settings.POSTGRES_USER == "expense_app", f"User {settings.POSTGRES_USER} không đúng expense_app!"

    with engine.connect() as conn:
        version = conn.execute(text("SELECT version();")).scalar()
        print(f"PostgreSQL Version: {version[:65]}...")
        assert "PostgreSQL 18" in version, "Phiên bản không phải PostgreSQL 18!"

        table_exists = conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = 'categories';"
            )
        ).scalar()
        print(f"Bảng 'categories' tồn tại: {bool(table_exists)}")
        assert table_exists == 1, "Bảng 'categories' không tồn tại!"

        current_rev = conn.execute(text("SELECT version_num FROM alembic_version;")).scalar()
        print(f"Alembic Current Revision: {current_rev}")

    with SessionLocal() as db:
        total_cats = db.scalar(select(func.count(Category.id)))
        sys_cats = db.scalar(select(func.count(Category.id)).where(Category.scope == "system"))
        personal_cats = db.scalar(select(func.count(Category.id)).where(Category.scope == "personal"))
        family_cats = db.scalar(select(func.count(Category.id)).where(Category.scope == "family"))
        print("-" * 60)
        print("SỐ LƯỢNG DANH MỤC HIỆN TẠI:")
        print(f"  - Tổng số danh mục: {total_cats}")
        print(f"  - Danh mục Hệ thống (system): {sys_cats}")
        print(f"  - Danh mục Cá nhân (personal): {personal_cats}")
        print(f"  - Danh mục Gia đình (family): {family_cats}")
        print("=" * 60)
        print("✅ XÁC MINH CƠ SỞ DỮ LIỆU ĐÍCH THÀNH CÔNG VÀ AN TOÀN!")


if __name__ == "__main__":
    verify_target_db()
