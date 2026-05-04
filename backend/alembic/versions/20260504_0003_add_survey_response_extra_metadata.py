"""Add survey response extra metadata.

Revision ID: 20260504_0003
Revises: 20260504_0002
Create Date: 2026-05-04 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260504_0003"
down_revision: str | None = "20260504_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return False
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    if not _column_exists("survey_responses", "extra_metadata"):
        op.add_column("survey_responses", sa.Column("extra_metadata", sa.JSON(), nullable=True))


def downgrade() -> None:
    if _column_exists("survey_responses", "extra_metadata"):
        op.drop_column("survey_responses", "extra_metadata")
