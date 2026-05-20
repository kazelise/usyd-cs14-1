"""Add survey-time attention quality columns to survey_responses.

Revision ID: 20260515_0001
Revises: 20260504_0008
Create Date: 2026-05-15 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260515_0001"
down_revision: str | None = "20260504_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


ATTENTION_COLUMNS = [
    ("attention_active_ms", sa.Integer()),
    ("attention_expected_samples", sa.Integer()),
    ("attention_detected_samples", sa.Integer()),
    ("attention_missing_ms", sa.Integer()),
    ("attention_no_face_periods", sa.Integer()),
    ("attention_coverage", sa.Float()),
    ("attention_confidence", sa.Float()),
    ("attention_quality", sa.String(length=20)),
    ("attention_quality_reason", sa.Text()),
]


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return False
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    for name, sa_type in ATTENTION_COLUMNS:
        if not _column_exists("survey_responses", name):
            op.add_column("survey_responses", sa.Column(name, sa_type, nullable=True))


def downgrade() -> None:
    for name, _ in reversed(ATTENTION_COLUMNS):
        if _column_exists("survey_responses", name):
            op.drop_column("survey_responses", name)
