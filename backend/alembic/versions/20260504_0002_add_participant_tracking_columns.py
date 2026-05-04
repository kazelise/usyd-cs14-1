"""Add participant response and interaction tracking columns.

Revision ID: 20260504_0002
Revises: 20260503_0001
Create Date: 2026-05-04 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260504_0002"
down_revision: str | None = "20260503_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return False
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    if not _column_exists("survey_responses", "participant_fingerprint"):
        op.add_column(
            "survey_responses",
            sa.Column("participant_fingerprint", sa.String(length=128), nullable=True),
        )

    if not _column_exists("survey_responses", "is_speed_test_failed"):
        op.add_column(
            "survey_responses",
            sa.Column("is_speed_test_failed", sa.Boolean(), server_default=sa.false(), nullable=False),
        )
        op.alter_column("survey_responses", "is_speed_test_failed", server_default=None)

    if not _column_exists("participant_interactions", "dwell_time_ms"):
        op.add_column("participant_interactions", sa.Column("dwell_time_ms", sa.Integer(), nullable=True))

    if not _column_exists("participant_interactions", "click_x"):
        op.add_column("participant_interactions", sa.Column("click_x", sa.Float(), nullable=True))

    if not _column_exists("participant_interactions", "click_y"):
        op.add_column("participant_interactions", sa.Column("click_y", sa.Float(), nullable=True))


def downgrade() -> None:
    for column_name in ("click_y", "click_x", "dwell_time_ms"):
        if _column_exists("participant_interactions", column_name):
            op.drop_column("participant_interactions", column_name)

    for column_name in ("is_speed_test_failed", "participant_fingerprint"):
        if _column_exists("survey_responses", column_name):
            op.drop_column("survey_responses", column_name)
