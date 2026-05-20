"""Add survey platform UI style.

Revision ID: 20260504_0004
Revises: 20260504_0003
Create Date: 2026-05-04 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260504_0004"
down_revision: str | None = "20260504_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return False
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    if not _column_exists("surveys", "platform_ui_style"):
        op.add_column(
            "surveys",
            sa.Column(
                "platform_ui_style", sa.String(length=40), server_default="twitter", nullable=False
            ),
        )
        op.alter_column("surveys", "platform_ui_style", server_default=None)


def downgrade() -> None:
    if _column_exists("surveys", "platform_ui_style"):
        op.drop_column("surveys", "platform_ui_style")
