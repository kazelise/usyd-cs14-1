"""Widen tracking timestamp columns.

Revision ID: 20260504_0006
Revises: 20260504_0005
Create Date: 2026-05-04 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260504_0006"
down_revision: str | None = "20260504_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_type(table_name: str, column_name: str) -> sa.types.TypeEngine | None:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return None
    for column in inspector.get_columns(table_name):
        if column["name"] == column_name:
            return column["type"]
    return None


def _widen_timestamp_ms(table_name: str) -> None:
    column_type = _column_type(table_name, "timestamp_ms")
    if column_type is None or isinstance(column_type, sa.BigInteger):
        return
    op.alter_column(
        table_name,
        "timestamp_ms",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
        postgresql_using="timestamp_ms::bigint",
    )


def upgrade() -> None:
    _widen_timestamp_ms("gaze_records")
    _widen_timestamp_ms("click_records")


def downgrade() -> None:
    for table_name in ("click_records", "gaze_records"):
        if isinstance(_column_type(table_name, "timestamp_ms"), sa.BigInteger):
            op.alter_column(
                table_name,
                "timestamp_ms",
                existing_type=sa.BigInteger(),
                type_=sa.Integer(),
                existing_nullable=False,
                postgresql_using="timestamp_ms::integer",
            )
