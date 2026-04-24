"""Phase 6 survey blocks and question completeness.

Revision ID: 20260425_0002
Revises: 20260425_0001
Create Date: 2026-04-25 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260425_0002"
down_revision: str | None = "20260425_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _inspector():
    return sa.inspect(op.get_bind())


def _table_exists(table_name: str) -> bool:
    return table_name in _inspector().get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    return column_name in {column["name"] for column in _inspector().get_columns(table_name)}


def _index_exists(table_name: str, index_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    return index_name in {index["name"] for index in _inspector().get_indexes(table_name)}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if not _column_exists(table_name, column.name):
        op.add_column(table_name, column)


def _create_index_if_missing(index_name: str, table_name: str, columns: list[str]) -> None:
    if _table_exists(table_name) and not _index_exists(table_name, index_name):
        op.create_index(index_name, table_name, columns)


def _foreign_key_exists(table_name: str, constrained_columns: list[str], referred_table: str) -> bool:
    if not _table_exists(table_name):
        return False
    for fk in _inspector().get_foreign_keys(table_name):
        if fk["constrained_columns"] == constrained_columns and fk["referred_table"] == referred_table:
            return True
    return False


def upgrade() -> None:
    _add_column_if_missing("survey_posts", sa.Column("display_description", sa.Text(), nullable=True))
    _add_column_if_missing("survey_posts", sa.Column("source_label", sa.String(length=255), nullable=True))
    _add_column_if_missing("survey_posts", sa.Column("more_info_label", sa.String(length=80), nullable=True))

    _add_column_if_missing("questions", sa.Column("survey_id", sa.Integer(), nullable=True))
    if _column_exists("questions", "survey_id"):
        op.execute(
            """
            UPDATE questions
            SET survey_id = survey_posts.survey_id
            FROM survey_posts
            WHERE questions.post_id = survey_posts.id
              AND questions.survey_id IS NULL
            """
        )
        if not _foreign_key_exists("questions", ["survey_id"], "surveys"):
            op.create_foreign_key(
                "fk_questions_survey",
                "questions",
                "surveys",
                ["survey_id"],
                ["id"],
                ondelete="CASCADE",
            )
        op.alter_column("questions", "survey_id", existing_type=sa.Integer(), nullable=False)

    if _column_exists("questions", "post_id"):
        op.alter_column("questions", "post_id", existing_type=sa.Integer(), nullable=True)
    if _column_exists("questions", "question_type"):
        op.alter_column(
            "questions",
            "question_type",
            existing_type=sa.String(length=20),
            type_=sa.String(length=30),
            existing_nullable=False,
        )

    _create_index_if_missing("ix_questions_survey_id", "questions", ["survey_id"])
    _create_index_if_missing("ix_questions_post_id", "questions", ["post_id"])


def downgrade() -> None:
    if _index_exists("questions", "ix_questions_post_id"):
        op.drop_index("ix_questions_post_id", table_name="questions")
    if _index_exists("questions", "ix_questions_survey_id"):
        op.drop_index("ix_questions_survey_id", table_name="questions")
    if _column_exists("questions", "question_type"):
        op.alter_column(
            "questions",
            "question_type",
            existing_type=sa.String(length=30),
            type_=sa.String(length=20),
            existing_nullable=False,
        )
    if _column_exists("questions", "post_id"):
        op.execute("DELETE FROM questions WHERE post_id IS NULL")
        op.alter_column("questions", "post_id", existing_type=sa.Integer(), nullable=False)
    if _foreign_key_exists("questions", ["survey_id"], "surveys"):
        for fk in _inspector().get_foreign_keys("questions"):
            if fk["constrained_columns"] == ["survey_id"] and fk["referred_table"] == "surveys":
                op.drop_constraint(fk["name"], "questions", type_="foreignkey")
                break
    if _column_exists("questions", "survey_id"):
        op.drop_column("questions", "survey_id")

    for column_name in ("more_info_label", "source_label", "display_description"):
        if _column_exists("survey_posts", column_name):
            op.drop_column("survey_posts", column_name)
