"""Align interaction constraints, indexes, and timestamp defaults.

Revision ID: 20260529_0001
Revises: 20260515_0002
Create Date: 2026-05-29 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260529_0001"
down_revision: str | None = "20260515_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

FK_NAME = "fk_participant_interactions_post"
POST_INDEX = "ix_participant_interactions_post_id"
CALIBRATION_CHECK = "ck_surveys_calibration_points_supported"


def _table_exists(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _column_exists(table_name: str, column_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    return column_name in {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)
    }


def _index_exists(table_name: str, index_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    return index_name in {
        index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)
    }


def _constraint_exists(table_name: str, constraint_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    inspector = sa.inspect(op.get_bind())
    constraints = inspector.get_foreign_keys(table_name) + inspector.get_check_constraints(
        table_name
    )
    return constraint_name in {constraint["name"] for constraint in constraints}


def upgrade() -> None:
    if _table_exists("participant_interactions"):
        if _constraint_exists("participant_interactions", FK_NAME):
            op.drop_constraint(FK_NAME, "participant_interactions", type_="foreignkey")
        op.create_foreign_key(
            FK_NAME,
            "participant_interactions",
            "survey_posts",
            ["post_id"],
            ["id"],
            ondelete="CASCADE",
        )
        if _column_exists("participant_interactions", "timestamp"):
            op.alter_column("participant_interactions", "timestamp", server_default=None)
        if not _index_exists("participant_interactions", POST_INDEX):
            op.create_index(POST_INDEX, "participant_interactions", ["post_id"])

    for table_name in ("gaze_records", "click_records"):
        if _column_exists(table_name, "received_at"):
            op.alter_column(table_name, "received_at", server_default=None)

    if _column_exists("surveys", "calibration_points"):
        op.execute(
            sa.text(
                "UPDATE surveys SET calibration_points = 9 WHERE calibration_points IS NULL OR calibration_points > 9"
            )
        )
        if not _constraint_exists("surveys", CALIBRATION_CHECK):
            op.create_check_constraint(
                CALIBRATION_CHECK,
                "surveys",
                "calibration_points BETWEEN 1 AND 9",
            )


def downgrade() -> None:
    if _constraint_exists("surveys", CALIBRATION_CHECK):
        op.drop_constraint(CALIBRATION_CHECK, "surveys", type_="check")

    for table_name in ("gaze_records", "click_records"):
        if _column_exists(table_name, "received_at"):
            op.alter_column(table_name, "received_at", server_default=sa.func.now())

    if _table_exists("participant_interactions"):
        if _index_exists("participant_interactions", POST_INDEX):
            op.drop_index(POST_INDEX, table_name="participant_interactions")
        if _column_exists("participant_interactions", "timestamp"):
            op.alter_column("participant_interactions", "timestamp", server_default=sa.func.now())
        if _constraint_exists("participant_interactions", FK_NAME):
            op.drop_constraint(FK_NAME, "participant_interactions", type_="foreignkey")
        op.create_foreign_key(
            FK_NAME,
            "participant_interactions",
            "survey_posts",
            ["post_id"],
            ["id"],
        )
