import sys
from pathlib import Path

# Thêm backend vào sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.db.session import engine
from sqlalchemy import text


def verify_schema() -> None:
    with engine.connect() as conn:
        print("=" * 60)
        print("XÁC MINH SCHEMA POSTGRESQL SAU MIGRATION")
        print("=" * 60)

        # 1. Danh sách bảng
        tables = conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_type = 'BASE TABLE' "
                "ORDER BY table_name"
            )
        ).scalars().all()
        print(f"1. Tổng số bảng trong public schema: {len(tables)}")
        for t in tables:
            print(f"   - {t}")

        # 2. Phiên bản Alembic
        alembic_rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        print(f"\n2. Revision trong bảng alembic_version: {alembic_rev}")

        # 3. Foreign Keys
        fk_sql = """
            SELECT
                tc.table_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name,
                rc.delete_rule
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            JOIN information_schema.referential_constraints AS rc
                ON rc.constraint_name = tc.constraint_name
                AND rc.constraint_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public'
            ORDER BY tc.table_name, kcu.column_name
        """
        fks = conn.execute(text(fk_sql)).mappings().all()
        print(f"\n3. Tổng số Foreign Keys: {len(fks)}")
        for fk in fks:
            print(
                f"   - {fk['table_name']}.{fk['column_name']} -> "
                f"{fk['foreign_table_name']}.{fk['foreign_column_name']} "
                f"(ON DELETE {fk['delete_rule']})"
            )

        # 4. Check Constraints
        ck_sql = """
            SELECT
                relname AS table_name,
                conname AS constraint_name,
                pg_get_constraintdef(c.oid) AS definition
            FROM pg_constraint c
            JOIN pg_class t ON c.conrelid = t.oid
            JOIN pg_namespace n ON t.relnamespace = n.oid
            WHERE c.contype = 'c' AND n.nspname = 'public'
            ORDER BY relname, conname
        """
        checks = conn.execute(text(ck_sql)).mappings().all()
        print(f"\n4. Tổng số Check Constraints: {len(checks)}")
        for ck in checks:
            print(f"   - [{ck['table_name']}] {ck['constraint_name']}: {ck['definition']}")

        # 5. Partial Unique Index & Index verification
        idx_sql = """
            SELECT
                tablename,
                indexname,
                indexdef
            FROM pg_indexes
            WHERE schemaname = 'public' AND indexname = 'uq_transactions_transfer_type'
        """
        indices = conn.execute(text(idx_sql)).mappings().all()
        print(f"\n5. Partial Unique Index (uq_transactions_transfer_type): {len(indices)}")
        for idx in indices:
            print(f"   - {idx['tablename']}: {idx['indexdef']}")

        # 6. Dữ liệu trong các bảng
        print("\n6. Số lượng bản ghi trong các bảng:")
        for t in tables:
            count = conn.execute(text(f'SELECT COUNT(*) FROM "{t}"')).scalar()
            print(f"   - {t}: {count} rows")


if __name__ == "__main__":
    verify_schema()
