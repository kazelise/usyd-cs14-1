"""Add participant feed platform style.

Revision ID: 20260503_0001
Revises: 20260501_0001
Create Date: 2026-05-03 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260503_0001"
down_revision: str | None = "20260501_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return False
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    if not _column_exists("surveys", "platform_style"):
        op.add_column(
            "surveys",
            sa.Column("platform_style", sa.String(length=32), server_default="x", nullable=False),
        )


def downgrade() -> None:
    if _column_exists("surveys", "platform_style"):
        op.drop_column("surveys", "platform_style")
