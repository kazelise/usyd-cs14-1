"""Backfill non-positive num_groups and enforce num_groups >= 1.

Revision ID: 20260515_0002
Revises: 20260515_0001
Create Date: 2026-05-26 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260515_0002"
down_revision: str | None = "20260515_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CONSTRAINT_NAME = "ck_surveys_num_groups_positive"


def _column_exists(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return False
    return column_name in {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    if not _column_exists("surveys", "num_groups"):
        return

    # Repair any historical rows that would crash participant start
    # (random.randint(1, num_groups) requires num_groups >= 1).
    op.execute(
        sa.text("UPDATE surveys SET num_groups = 1 WHERE num_groups IS NULL OR num_groups < 1")
    )

    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_check_constraints("surveys")}
    if CONSTRAINT_NAME not in existing:
        op.create_check_constraint(CONSTRAINT_NAME, "surveys", "num_groups >= 1")


def downgrade() -> None:
    if not _column_exists("surveys", "num_groups"):
        return
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_check_constraints("surveys")}
    if CONSTRAINT_NAME in existing:
        op.drop_constraint(CONSTRAINT_NAME, "surveys", type_="check")
