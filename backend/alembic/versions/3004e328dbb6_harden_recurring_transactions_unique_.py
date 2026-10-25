"""harden_recurring_transactions_unique_index_for_soft_deleted

Revision ID: 3004e328dbb6
Revises: f82c8b7762da
Create Date: 2026-10-24 23:53:19.890313

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '3004e328dbb6'
down_revision: str | Sequence[str] | None = 'f82c8b7762da'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema: Harden recurring transactions unique index to include soft-deleted records."""
    op.drop_index(
        'uq_transactions_recurring_rule_date',
        table_name='transactions',
        postgresql_where=sa.text('recurring_rule_id IS NOT NULL AND deleted_at IS NULL'),
    )
    op.create_index(
        'uq_transactions_recurring_rule_date',
        'transactions',
        ['recurring_rule_id', 'recurrence_date'],
        unique=True,
        postgresql_where=sa.text('recurring_rule_id IS NOT NULL'),
    )


def downgrade() -> None:
    """Downgrade schema: Revert recurring transactions unique index."""
    op.drop_index(
        'uq_transactions_recurring_rule_date',
        table_name='transactions',
        postgresql_where=sa.text('recurring_rule_id IS NOT NULL'),
    )
    op.create_index(
        'uq_transactions_recurring_rule_date',
        'transactions',
        ['recurring_rule_id', 'recurrence_date'],
        unique=True,
        postgresql_where=sa.text('recurring_rule_id IS NOT NULL AND deleted_at IS NULL'),
    )
