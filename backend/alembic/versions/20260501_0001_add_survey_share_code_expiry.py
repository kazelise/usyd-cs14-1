"""Add missing survey share code expiry column.

Revision ID: 20260501_0001
Revises: 20260425_0002
Create Date: 2026-05-01 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260501_0001"
down_revision: str | None = "20260425_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return False
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    if not _column_exists("surveys", "share_code_expires_at"):
        op.add_column("surveys", sa.Column("share_code_expires_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    if _column_exists("surveys", "share_code_expires_at"):
        op.drop_column("surveys", "share_code_expires_at")
