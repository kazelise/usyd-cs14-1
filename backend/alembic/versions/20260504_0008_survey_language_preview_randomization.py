"""Add survey language and preview randomization metadata.

Revision ID: 20260504_0008
Revises: 20260504_0007
Create Date: 2026-05-04 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260504_0008"
down_revision: str | None = "20260504_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return False
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def _index_exists(table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return False
    return index_name in {index["name"] for index in inspector.get_indexes(table_name)}


def upgrade() -> None:
    if not _column_exists("surveys", "default_language"):
        op.add_column(
            "surveys",
            sa.Column(
                "default_language", sa.String(length=10), nullable=False, server_default="en"
            ),
        )
    if not _column_exists("surveys", "supported_languages"):
        op.add_column("surveys", sa.Column("supported_languages", sa.JSON(), nullable=True))
        op.execute(
            sa.text(
                """UPDATE surveys SET supported_languages = '["en", "ar", "zh"]' """
                "WHERE supported_languages IS NULL"
            )
        )
    if not _column_exists("surveys", "published_at"):
        op.add_column("surveys", sa.Column("published_at", sa.DateTime(), nullable=True))

    if not _column_exists("survey_responses", "is_preview"):
        op.add_column(
            "survey_responses",
            sa.Column("is_preview", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
    if not _index_exists("survey_responses", "ix_survey_responses_is_preview"):
        op.create_index("ix_survey_responses_is_preview", "survey_responses", ["is_preview"])
    if not _column_exists("survey_responses", "randomization_seed"):
        op.add_column(
            "survey_responses", sa.Column("randomization_seed", sa.String(length=64), nullable=True)
        )
    if not _column_exists("survey_responses", "shown_post_order"):
        op.add_column("survey_responses", sa.Column("shown_post_order", sa.JSON(), nullable=True))


def downgrade() -> None:
    if _column_exists("survey_responses", "shown_post_order"):
        op.drop_column("survey_responses", "shown_post_order")
    if _column_exists("survey_responses", "randomization_seed"):
        op.drop_column("survey_responses", "randomization_seed")
    if _index_exists("survey_responses", "ix_survey_responses_is_preview"):
        op.drop_index("ix_survey_responses_is_preview", table_name="survey_responses")
    if _column_exists("survey_responses", "is_preview"):
        op.drop_column("survey_responses", "is_preview")

    if _column_exists("surveys", "published_at"):
        op.drop_column("surveys", "published_at")
    if _column_exists("surveys", "supported_languages"):
        op.drop_column("surveys", "supported_languages")
    if _column_exists("surveys", "default_language"):
        op.drop_column("surveys", "default_language")
