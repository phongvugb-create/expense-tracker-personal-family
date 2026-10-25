"""
Script khởi tạo (seed) danh mục hệ thống mặc định (System Categories).

Quy tắc kỹ thuật:
- Tính Idempotent: Chạy lại nhiều lần không tạo bản ghi trùng lặp (dựa trên type, scope='system', name).
- Chỉ tạo các danh mục có scope='system', is_default=True, user_id=None, family_id=None.
- Tuyệt đối không xóa, sửa hoặc ghi đè danh mục của người dùng hay các bản ghi khác.
- Phục vụ việc hiển thị danh mục mặc định cho thu chi ở các bước tiếp theo.

LƯU Ý: Không tự động chạy script này khi khởi động ứng dụng!
"""

import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

# Thêm đường dẫn backend vào sys.path để import model và db session
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.db.session import SessionLocal
from app.models.category import Category

# Định nghĩa cây danh mục hệ thống chuẩn
SYSTEM_CATEGORIES_DATA: list[dict] = [
    # --- DANH MỤC CHI TIÊU (EXPENSE) ---
    {
        "name": "Ăn uống",
        "type": "expense",
        "icon": "utensils",
        "color": "#EF4444",  # Đỏ cam
        "children": [
            {"name": "Nhà hàng & Quán ăn", "type": "expense", "icon": "utensils", "color": "#F87171"},
            {"name": "Đi chợ & Siêu thị", "type": "expense", "icon": "shopping-cart", "color": "#F87171"},
            {"name": "Cà phê & Đồ uống", "type": "expense", "icon": "coffee", "color": "#F87171"},
        ],
    },
    {
        "name": "Di chuyển",
        "type": "expense",
        "icon": "car",
        "color": "#F59E0B",  # Vàng hổ phách
        "children": [
            {"name": "Xăng xe", "type": "expense", "icon": "fuel", "color": "#FBBF24"},
            {"name": "Bảo dưỡng & Sửa xe", "type": "expense", "icon": "wrench", "color": "#FBBF24"},
            {"name": "Taxi & Xe công nghệ", "type": "expense", "icon": "car", "color": "#FBBF24"},
        ],
    },
    {
        "name": "Nhà ở & Tiện ích",
        "type": "expense",
        "icon": "home",
        "color": "#3B82F6",  # Xanh dương
        "children": [
            {"name": "Tiền thuê nhà", "type": "expense", "icon": "home", "color": "#60A5FA"},
            {"name": "Điện nước & Internet", "type": "expense", "icon": "zap", "color": "#60A5FA"},
            {"name": "Đồ dùng gia đình", "type": "expense", "icon": "box", "color": "#60A5FA"},
        ],
    },
    {
        "name": "Mua sắm",
        "type": "expense",
        "icon": "shopping-bag",
        "color": "#EC4899",  # Hồng tím
        "children": [
            {"name": "Quần áo & Phụ kiện", "type": "expense", "icon": "shirt", "color": "#F472B6"},
            {"name": "Thiết bị điện tử", "type": "expense", "icon": "smartphone", "color": "#F472B6"},
        ],
    },
    {
        "name": "Y tế & Sức khỏe",
        "type": "expense",
        "icon": "activity",
        "color": "#10B981",  # Xanh lá
        "children": [
            {"name": "Thuốc men & Khám bệnh", "type": "expense", "icon": "heart", "color": "#34D399"},
            {"name": "Thể thao & Rèn luyện", "type": "expense", "icon": "dumbbell", "color": "#34D399"},
        ],
    },
    {
        "name": "Giáo dục",
        "type": "expense",
        "icon": "book-open",
        "color": "#8B5CF6",  # Tím
        "children": [
            {"name": "Học phí & Khóa học", "type": "expense", "icon": "graduation-cap", "color": "#A78BFA"},
            {"name": "Sách vở & Tài liệu", "type": "expense", "icon": "book", "color": "#A78BFA"},
        ],
    },
    {
        "name": "Giải trí & Du lịch",
        "type": "expense",
        "icon": "film",
        "color": "#06B6D4",  # Xanh ngọc
        "children": [
            {"name": "Vé xem phim & Sự kiện", "type": "expense", "icon": "ticket", "color": "#22D3EE"},
            {"name": "Du lịch & Nghỉ dưỡng", "type": "expense", "icon": "plane", "color": "#22D3EE"},
        ],
    },
    # --- DANH MỤC THU NHẬP (INCOME) ---
    {
        "name": "Lương chính",
        "type": "income",
        "icon": "dollar-sign",
        "color": "#10B981",
        "children": [],
    },
    {
        "name": "Thưởng & Phụ cấp",
        "type": "income",
        "icon": "gift",
        "color": "#3B82F6",
        "children": [],
    },
    {
        "name": "Kinh doanh & Đầu tư",
        "type": "income",
        "icon": "trending-up",
        "color": "#F59E0B",
        "children": [
            {"name": "Lợi nhuận kinh doanh", "type": "income", "icon": "briefcase", "color": "#FBBF24"},
            {"name": "Cổ tức & Lãi suất", "type": "income", "icon": "percent", "color": "#FBBF24"},
        ],
    },
    {
        "name": "Thu nhập khác",
        "type": "income",
        "icon": "plus-circle",
        "color": "#6B7280",
        "children": [],
    },
]


def seed_system_categories(db: Session) -> dict[str, int]:
    """
    Thực hiện nạp danh mục hệ thống vào cơ sở dữ liệu một cách idempotent.
    Trả về số lượng danh mục đã tạo mới và số lượng đã tồn tại.
    """
    created_count = 0
    existing_count = 0

    for item in SYSTEM_CATEGORIES_DATA:
        parent_name = item["name"].strip()
        category_type = item["type"]

        # Kiểm tra xem danh mục cha hệ thống đã tồn tại chưa
        parent_cat = db.scalar(
            select(Category).where(
                Category.scope == "system",
                Category.type == category_type,
                Category.name == parent_name,
                Category.deleted_at.is_(None),
            )
        )

        if parent_cat is None:
            parent_cat = Category(
                name=parent_name,
                type=category_type,
                scope="system",
                user_id=None,
                family_id=None,
                parent_id=None,
                icon=item.get("icon"),
                color=item.get("color"),
                is_default=True,
                is_archived=False,
            )
            db.add(parent_cat)
            db.flush()  # Sinh ID để gắn cho các danh mục con
            created_count += 1
        else:
            existing_count += 1

        # Xử lý danh mục con nếu có
        for child in item.get("children", []):
            child_name = child["name"].strip()
            child_cat = db.scalar(
                select(Category).where(
                    Category.scope == "system",
                    Category.type == category_type,
                    Category.name == child_name,
                    Category.parent_id == parent_cat.id,
                    Category.deleted_at.is_(None),
                )
            )

            if child_cat is None:
                child_cat = Category(
                    name=child_name,
                    type=category_type,
                    scope="system",
                    user_id=None,
                    family_id=None,
                    parent_id=parent_cat.id,
                    icon=child.get("icon"),
                    color=child.get("color"),
                    is_default=True,
                    is_archived=False,
                )
                db.add(child_cat)
                created_count += 1
            else:
                existing_count += 1

    db.commit()
    return {"created": created_count, "existing": existing_count}


def main():
    print("=" * 60)
    print("BẮT ĐẦU SEED DANH MỤC HỆ THỐNG MẶC ĐỊNH")
    print("=" * 60)

    with SessionLocal() as db:
        stats = seed_system_categories(db)
        print(f"✅ Đã tạo mới: {stats['created']} danh mục")
        print(f"ℹ️ Đã tồn tại: {stats['existing']} danh mục")
        print("=" * 60)
        print("HOÀN THÀNH SEED DANH MỤC HỆ THỐNG AN TOÀN!")


if __name__ == "__main__":
    main()
