"""Backfill platform UI style from existing platform style.

Revision ID: 20260504_0007
Revises: 20260504_0006
Create Date: 2026-05-04 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260504_0007"
down_revision: str | None = "20260504_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return False
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    if not (
        _column_exists("surveys", "platform_style")
        and _column_exists("surveys", "platform_ui_style")
    ):
        return

    op.execute(
        sa.text(
            """
            UPDATE surveys
            SET platform_ui_style = CASE platform_style
                WHEN 'facebook' THEN 'facebook'
                WHEN 'instagram' THEN 'instagram'
                WHEN 'xiaohongshu' THEN 'xiaohongshu'
                ELSE platform_ui_style
            END
            WHERE platform_style IN ('facebook', 'instagram', 'xiaohongshu')
              AND (platform_ui_style IS NULL OR platform_ui_style = 'twitter')
            """
        )
    )


def downgrade() -> None:
    if not _column_exists("surveys", "platform_ui_style"):
        return

    op.execute(
        sa.text(
            """
            UPDATE surveys
            SET platform_ui_style = 'twitter'
            WHERE platform_ui_style = 'xiaohongshu'
            """
        )
    )
