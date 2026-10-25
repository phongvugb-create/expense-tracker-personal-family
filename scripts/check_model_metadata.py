import sys
from pathlib import Path

# Thêm backend vào sys.path để import app modules
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import app.models  # noqa: F401 - Nạp toàn bộ models để đăng ký metadata
from app.db.base import Base
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import configure_mappers
from sqlalchemy.schema import CreateTable


def run_metadata_audit() -> None:
    print("=" * 60)
    print("BẮT ĐẦU RÀ SOÁT TOÀN DIỆN METADATA & SCHEMA SQLALCHEMY")
    print("=" * 60)

    # 1. Kiểm tra Mapper Configuration
    try:
        configure_mappers()
        print("✅ 1. configure_mappers(): Thành công, không có xung đột quan hệ ORM.")
    except SQLAlchemyError as e:
        print(f"❌ 1. configure_mappers() THẤT BẠI: {e}")
        sys.exit(1)

    # 2. Kiểm tra danh sách bảng đã đăng ký trong Base.metadata
    tables = Base.metadata.tables
    print(f"✅ 2. Tổng số bảng đăng ký trong Base.metadata: {len(tables)}")
    for tbl_name in sorted(tables.keys()):
        print(f"   - {tbl_name}")

    # 3. Kiểm tra Foreign Keys tính hợp lệ (bảng và cột đích phải tồn tại trong metadata)
    missing_targets = []
    total_fks = 0
    for tbl_name, table in tables.items():
        for fk in table.foreign_keys:
            total_fks += 1
            target_col = fk.target_fullname
            target_tbl_name = (
                fk.column.table.name if hasattr(fk.column, "table") else target_col.split(".")[0]
            )
            if target_tbl_name not in tables:
                missing_targets.append((tbl_name, fk.parent.name, target_col))

    if missing_targets:
        print(f"❌ 3. Phát hiện {len(missing_targets)} Foreign Key trỏ đến bảng chưa đăng ký:")
        for source_tbl, col, target in missing_targets:
            print(f"   - Bảng {source_tbl}.{col} -> {target} (BẢNG ĐÍCH KHÔNG TỒN TẠI)")
        sys.exit(1)
    else:
        print(f"✅ 3. Toàn bộ {total_fks} Foreign Keys đều trỏ đến các bảng và cột hợp lệ trong metadata.")

    # 4. Thử nghiệm biên dịch DDL theo Dialect PostgreSQL (không kết nối database)
    pg_dialect = postgresql.dialect()
    compiled_ddl_count = 0
    try:
        for table in tables.values():
            _ = str(CreateTable(table).compile(dialect=pg_dialect))
            compiled_ddl_count += 1
        print(f"✅ 4. Đã biên dịch DDL PostgreSQL cho toàn bộ {compiled_ddl_count} bảng thành công.")
    except SQLAlchemyError as e:
        print(f"❌ 4. Biên dịch DDL PostgreSQL thất bại: {e}")
        sys.exit(1)

    print("=" * 60)
    print("KẾT LUẬN: TẤT CẢ METADATA SẴN SÀNG CHO ALEMBIC MIGRATION!")
    print("=" * 60)


if __name__ == "__main__":
    run_metadata_audit()
