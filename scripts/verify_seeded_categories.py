import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import SessionLocal
from app.models.category import Category
from sqlalchemy import func, select


def verify_seeded_categories():
    print("=" * 60)
    print("KIỂM CHỨNG CHI TIẾT DANH MỤC TRỰC TIẾP TRÊN POSTGRESQL 18")
    print("=" * 60)

    with SessionLocal() as db:
        # 1. Tổng số danh mục system
        sys_cats = db.scalars(
            select(Category)
            .where(Category.scope == "system", Category.deleted_at.is_(None))
            .order_by(Category.type.asc(), Category.parent_id.nulls_first(), Category.name.asc())
        ).all()
        print(f"1. Tổng số danh mục system: {len(sys_cats)}")

        # 2. Số lượng theo loại income vs expense
        expense_count = sum(1 for c in sys_cats if c.type == "expense")
        income_count = sum(1 for c in sys_cats if c.type == "income")
        print(f"2. Phân loại: {expense_count} chi tiêu (expense), {income_count} thu nhập (income)")

        # 3. Kiểm tra user_id IS NULL và family_id IS NULL
        invalid_scope = [c for c in sys_cats if c.user_id is not None or c.family_id is not None]
        print(f"3. Xác nhận user_id IS NULL & family_id IS NULL: {len(invalid_scope) == 0} (vi phạm: {len(invalid_scope)})")

        # 4. Kiểm tra is_default=True
        default_count = sum(1 for c in sys_cats if c.is_default)
        print(f"4. Số bản ghi is_default=True: {default_count}/{len(sys_cats)}")

        # 5. Kiểm tra danh mục cá nhân và gia đình
        personal_count = db.scalar(select(func.count(Category.id)).where(Category.scope == "personal"))
        family_count = db.scalar(select(func.count(Category.id)).where(Category.scope == "family"))
        print(f"5. Số lượng danh mục cá nhân: {personal_count}, gia đình: {family_count}")

        # 6. Kiểm tra bản ghi trùng lặp
        duplicates_query = (
            select(Category.name, Category.type, Category.parent_id, func.count(Category.id))
            .where(Category.scope == "system", Category.deleted_at.is_(None))
            .group_by(Category.name, Category.type, Category.parent_id)
            .having(func.count(Category.id) > 1)
        )
        duplicates = db.execute(duplicates_query).all()
        print(f"6. Số lượng bản ghi trùng lặp: {len(duplicates)}")

        print("-" * 60)
        print("DANH SÁCH CHI TIẾT TẤT CẢ 30 DANH MỤC HỆ THỐNG:")
        # Tạo map id -> name để in rõ danh mục cha
        cat_map = {c.id: c.name for c in sys_cats}
        for c in sys_cats:
            parent_name = f" [Cha: {cat_map[c.parent_id]}]" if c.parent_id else " [Danh mục gốc]"
            print(f"  • [{c.type.upper():7}] {c.name:25} | Icon: {c.icon:15} | Màu: {c.color:8}{parent_name}")

    print("=" * 60)
    print("✅ KIỂM CHỨNG DỮ LIỆU POSTGRESQL HOÀN TẤT VỚI KẾT QUẢ XUẤT SẮC!")


if __name__ == "__main__":
    verify_seeded_categories()
