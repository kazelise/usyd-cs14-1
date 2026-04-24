"""Phase 2 schema hardening baseline.

Revision ID: 20260425_0001
Revises:
Create Date: 2026-04-25 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260425_0001"
down_revision: str | None = None
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


def _constraint_exists(table_name: str, constraint_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    constraints = _inspector().get_unique_constraints(table_name)
    return constraint_name in {constraint["name"] for constraint in constraints}


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    if not _column_exists(table_name, column.name):
        op.add_column(table_name, column)


def _create_index_if_missing(
    index_name: str, table_name: str, columns: list[str], unique: bool = False
) -> None:
    if not _table_exists(table_name):
        return
    if not _index_exists(table_name, index_name):
        op.create_index(index_name, table_name, columns, unique=unique)


def _create_unique_if_missing(
    constraint_name: str, table_name: str, columns: list[str]
) -> None:
    if not _constraint_exists(table_name, constraint_name):
        op.create_unique_constraint(constraint_name, table_name, columns)


def _replace_fk(
    table_name: str,
    columns: list[str],
    referred_table: str,
    referred_columns: list[str],
    constraint_name: str,
    ondelete: str,
) -> None:
    if not _table_exists(table_name):
        return

    for fk in _inspector().get_foreign_keys(table_name):
        if fk["constrained_columns"] == columns and fk["referred_table"] == referred_table:
            if (fk.get("options") or {}).get("ondelete") == ondelete:
                return
            if fk["name"]:
                op.drop_constraint(fk["name"], table_name, type_="foreignkey")
            break

    op.create_foreign_key(
        constraint_name,
        table_name,
        referred_table,
        columns,
        referred_columns,
        ondelete=ondelete,
    )


def _create_core_tables() -> None:
    if not _table_exists("researchers"):
        op.create_table(
            "researchers",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("password_hash", sa.String(length=255), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("email", name="uq_researchers_email"),
        )

    if not _table_exists("surveys"):
        op.create_table(
            "surveys",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("researcher_id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=20), server_default="draft", nullable=False),
            sa.Column("share_code", sa.String(length=20), nullable=False),
            sa.Column("share_code_expires_at", sa.DateTime(), nullable=True),
            sa.Column("num_groups", sa.SmallInteger(), server_default="1", nullable=False),
            sa.Column("group_names", sa.JSON(), nullable=True),
            sa.Column("gaze_tracking_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column("gaze_interval_ms", sa.Integer(), server_default="1000", nullable=False),
            sa.Column("click_tracking_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column("calibration_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column("calibration_points", sa.SmallInteger(), server_default="9", nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(
                ["researcher_id"], ["researchers.id"], name="fk_surveys_researcher"
            ),
            sa.UniqueConstraint("share_code", name="uq_surveys_share_code"),
        )

    if not _table_exists("survey_posts"):
        op.create_table(
            "survey_posts",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("survey_id", sa.Integer(), nullable=False),
            sa.Column("order", sa.Integer(), nullable=False),
            sa.Column("original_url", sa.Text(), nullable=False),
            sa.Column("fetched_title", sa.Text(), nullable=True),
            sa.Column("fetched_image_url", sa.Text(), nullable=True),
            sa.Column("fetched_description", sa.Text(), nullable=True),
            sa.Column("fetched_source", sa.String(length=255), nullable=True),
            sa.Column("display_title", sa.Text(), nullable=True),
            sa.Column("display_image_url", sa.Text(), nullable=True),
            sa.Column("display_likes", sa.Integer(), server_default="0", nullable=False),
            sa.Column("display_comments_count", sa.Integer(), server_default="0", nullable=False),
            sa.Column("display_shares", sa.Integer(), server_default="0", nullable=False),
            sa.Column("show_likes", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column("show_comments", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column("show_shares", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column("visible_to_groups", sa.JSON(), nullable=True),
            sa.Column("group_overrides", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(
                ["survey_id"], ["surveys.id"], name="fk_survey_posts_survey", ondelete="CASCADE"
            ),
        )

    if not _table_exists("post_comments"):
        op.create_table(
            "post_comments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("post_id", sa.Integer(), nullable=False),
            sa.Column("order", sa.Integer(), nullable=False),
            sa.Column("author_name", sa.String(length=100), nullable=False),
            sa.Column("author_avatar_url", sa.Text(), nullable=True),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(
                ["post_id"], ["survey_posts.id"], name="fk_post_comments_post", ondelete="CASCADE"
            ),
        )

    if not _table_exists("questions"):
        op.create_table(
            "questions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("post_id", sa.Integer(), nullable=False),
            sa.Column("order", sa.Integer(), nullable=False),
            sa.Column("question_type", sa.String(length=20), nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("config", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(
                ["post_id"], ["survey_posts.id"], name="fk_questions_post", ondelete="CASCADE"
            ),
        )

    if not _table_exists("survey_responses"):
        op.create_table(
            "survey_responses",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("survey_id", sa.Integer(), nullable=False),
            sa.Column("participant_token", sa.String(length=64), nullable=False),
            sa.Column("assigned_group", sa.SmallInteger(), server_default="1", nullable=False),
            sa.Column("user_agent", sa.Text(), nullable=True),
            sa.Column("screen_width", sa.Integer(), nullable=True),
            sa.Column("screen_height", sa.Integer(), nullable=True),
            sa.Column("language", sa.String(length=10), nullable=True),
            sa.Column("participant_fingerprint", sa.String(length=128), nullable=True),
            sa.Column("status", sa.String(length=20), server_default="in_progress", nullable=False),
            sa.Column("is_speed_test_failed", sa.Boolean(), server_default=sa.false(), nullable=False),
            sa.Column("started_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("extra_metadata", sa.JSON(), nullable=True),
            sa.ForeignKeyConstraint(
                ["survey_id"], ["surveys.id"], name="fk_survey_responses_survey", ondelete="CASCADE"
            ),
            sa.UniqueConstraint("participant_token", name="uq_survey_responses_participant_token"),
        )

    if not _table_exists("participant_interactions"):
        op.create_table(
            "participant_interactions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("response_id", sa.Integer(), nullable=False),
            sa.Column("post_id", sa.Integer(), nullable=False),
            sa.Column("action_type", sa.String(length=20), nullable=False),
            sa.Column("comment_text", sa.Text(), nullable=True),
            sa.Column("dwell_time_ms", sa.Integer(), nullable=True),
            sa.Column("click_x", sa.Float(), nullable=True),
            sa.Column("click_y", sa.Float(), nullable=True),
            sa.Column("timestamp", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(
                ["response_id"],
                ["survey_responses.id"],
                name="fk_participant_interactions_response",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["post_id"], ["survey_posts.id"], name="fk_participant_interactions_post"
            ),
        )

    if not _table_exists("participant_likes"):
        op.create_table(
            "participant_likes",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("response_id", sa.Integer(), nullable=False),
            sa.Column("post_id", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(
                ["response_id"],
                ["survey_responses.id"],
                name="fk_participant_likes_response",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["post_id"], ["survey_posts.id"], name="fk_participant_likes_post", ondelete="CASCADE"
            ),
            sa.UniqueConstraint("response_id", "post_id", name="uq_participant_like_response_post"),
        )

    if not _table_exists("participant_comments"):
        op.create_table(
            "participant_comments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("response_id", sa.Integer(), nullable=False),
            sa.Column("post_id", sa.Integer(), nullable=False),
            sa.Column("author_name", sa.String(length=100), nullable=True),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(
                ["response_id"],
                ["survey_responses.id"],
                name="fk_participant_comments_response",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["post_id"],
                ["survey_posts.id"],
                name="fk_participant_comments_post",
                ondelete="CASCADE",
            ),
        )

    if not _table_exists("question_responses"):
        op.create_table(
            "question_responses",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("response_id", sa.Integer(), nullable=False),
            sa.Column("question_id", sa.Integer(), nullable=False),
            sa.Column("answer_text", sa.Text(), nullable=True),
            sa.Column("answer_value", sa.Integer(), nullable=True),
            sa.Column("answer_choices", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(
                ["response_id"],
                ["survey_responses.id"],
                name="fk_question_responses_response",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["question_id"], ["questions.id"], name="fk_question_responses_question", ondelete="CASCADE"
            ),
        )


def _create_tracking_tables() -> None:
    if not _table_exists("calibration_sessions"):
        op.create_table(
            "calibration_sessions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("response_id", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=20), server_default="in_progress", nullable=False),
            sa.Column("screen_width", sa.Integer(), nullable=False),
            sa.Column("screen_height", sa.Integer(), nullable=False),
            sa.Column("camera_width", sa.Integer(), nullable=True),
            sa.Column("camera_height", sa.Integer(), nullable=True),
            sa.Column("expected_points", sa.SmallInteger(), server_default="9", nullable=False),
            sa.Column("face_detection_rate", sa.Float(), nullable=True),
            sa.Column("quality_score", sa.Float(), nullable=True),
            sa.Column("passed", sa.Boolean(), nullable=True),
            sa.Column("stability_score", sa.Float(), nullable=True),
            sa.Column("quality_reason", sa.String(length=255), nullable=True),
            sa.Column("model_type", sa.String(length=80), nullable=True),
            sa.Column("model_params", sa.JSON(), nullable=True),
            sa.Column("validation_error_px", sa.Float(), nullable=True),
            sa.Column("quality", sa.String(length=20), nullable=True),
            sa.Column("started_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(
                ["response_id"],
                ["survey_responses.id"],
                name="fk_calib_sessions_response",
                ondelete="CASCADE",
            ),
            sa.UniqueConstraint("response_id", name="uq_calibration_sessions_response_id"),
        )

    if not _table_exists("calibration_points"):
        op.create_table(
            "calibration_points",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("session_id", sa.Integer(), nullable=False),
            sa.Column("point_index", sa.SmallInteger(), nullable=False),
            sa.Column("target_screen_x", sa.Integer(), nullable=False),
            sa.Column("target_screen_y", sa.Integer(), nullable=False),
            sa.Column("samples", sa.JSON(), nullable=False),
            sa.Column("samples_count", sa.Integer(), nullable=False),
            sa.Column("face_detection_rate", sa.Float(), nullable=True),
            sa.Column("stability_score", sa.Float(), nullable=True),
            sa.Column("valid", sa.Boolean(), nullable=True),
            sa.Column("median_left_iris_x", sa.Float(), nullable=True),
            sa.Column("median_left_iris_y", sa.Float(), nullable=True),
            sa.Column("median_right_iris_x", sa.Float(), nullable=True),
            sa.Column("median_right_iris_y", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(
                ["session_id"],
                ["calibration_sessions.id"],
                name="fk_calibration_points_session",
                ondelete="CASCADE",
            ),
            sa.UniqueConstraint("session_id", "point_index", name="uq_session_point"),
        )

    if not _table_exists("gaze_records"):
        op.create_table(
            "gaze_records",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("response_id", sa.Integer(), nullable=False),
            sa.Column("post_id", sa.Integer(), nullable=True),
            sa.Column("timestamp_ms", sa.BigInteger(), nullable=False),
            sa.Column("screen_x", sa.Float(), nullable=False),
            sa.Column("screen_y", sa.Float(), nullable=False),
            sa.Column("left_iris_x", sa.Float(), nullable=True),
            sa.Column("left_iris_y", sa.Float(), nullable=True),
            sa.Column("right_iris_x", sa.Float(), nullable=True),
            sa.Column("right_iris_y", sa.Float(), nullable=True),
            sa.Column("received_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(
                ["response_id"],
                ["survey_responses.id"],
                name="fk_gaze_records_response",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["post_id"],
                ["survey_posts.id"],
                name="fk_gaze_records_post",
                ondelete="SET NULL",
            ),
        )

    if not _table_exists("click_records"):
        op.create_table(
            "click_records",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("response_id", sa.Integer(), nullable=False),
            sa.Column("post_id", sa.Integer(), nullable=True),
            sa.Column("timestamp_ms", sa.BigInteger(), nullable=False),
            sa.Column("screen_x", sa.Float(), nullable=False),
            sa.Column("screen_y", sa.Float(), nullable=False),
            sa.Column("target_element", sa.String(length=50), nullable=True),
            sa.Column("received_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(
                ["response_id"],
                ["survey_responses.id"],
                name="fk_click_records_response",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["post_id"],
                ["survey_posts.id"],
                name="fk_click_records_post",
                ondelete="SET NULL",
            ),
        )


def _create_translation_tables() -> None:
    json_default = sa.text("'{}'::json")

    if not _table_exists("survey_translations"):
        op.create_table(
            "survey_translations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("survey_id", sa.Integer(), nullable=False),
            sa.Column("language_code", sa.String(length=10), nullable=False),
            sa.Column("translated_fields", sa.JSON(), server_default=json_default, nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(
                ["survey_id"],
                ["surveys.id"],
                name="fk_survey_translations_survey",
                ondelete="CASCADE",
            ),
            sa.UniqueConstraint("survey_id", "language_code", name="uq_survey_translation_language"),
        )

    if not _table_exists("post_translations"):
        op.create_table(
            "post_translations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("survey_id", sa.Integer(), nullable=False),
            sa.Column("post_id", sa.Integer(), nullable=False),
            sa.Column("language_code", sa.String(length=10), nullable=False),
            sa.Column("translated_fields", sa.JSON(), server_default=json_default, nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(
                ["survey_id"],
                ["surveys.id"],
                name="fk_post_translations_survey",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["post_id"],
                ["survey_posts.id"],
                name="fk_post_translations_post",
                ondelete="CASCADE",
            ),
            sa.UniqueConstraint("post_id", "language_code", name="uq_post_translation_language"),
        )

    if not _table_exists("question_translations"):
        op.create_table(
            "question_translations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("survey_id", sa.Integer(), nullable=False),
            sa.Column("question_id", sa.Integer(), nullable=False),
            sa.Column("language_code", sa.String(length=10), nullable=False),
            sa.Column("translated_fields", sa.JSON(), server_default=json_default, nullable=False),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(
                ["survey_id"],
                ["surveys.id"],
                name="fk_question_translations_survey",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["question_id"],
                ["questions.id"],
                name="fk_question_translations_question",
                ondelete="CASCADE",
            ),
            sa.UniqueConstraint(
                "question_id", "language_code", name="uq_question_translation_language"
            ),
        )


def _harden_existing_tables() -> None:
    for table_name, columns in {
        "calibration_sessions": [
            sa.Column("quality_score", sa.Float(), nullable=True),
            sa.Column("passed", sa.Boolean(), nullable=True),
            sa.Column("stability_score", sa.Float(), nullable=True),
            sa.Column("quality_reason", sa.String(length=255), nullable=True),
            sa.Column("model_type", sa.String(length=80), nullable=True),
            sa.Column("model_params", sa.JSON(), nullable=True),
            sa.Column("validation_error_px", sa.Float(), nullable=True),
        ],
        "calibration_points": [
            sa.Column("face_detection_rate", sa.Float(), nullable=True),
            sa.Column("stability_score", sa.Float(), nullable=True),
            sa.Column("valid", sa.Boolean(), nullable=True),
        ],
        "gaze_records": [
            sa.Column("received_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        ],
        "click_records": [
            sa.Column("received_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        ],
    }.items():
        if _table_exists(table_name):
            for column in columns:
                _add_column_if_missing(table_name, column)

    _replace_fk(
        "survey_responses",
        ["survey_id"],
        "surveys",
        ["id"],
        "fk_survey_responses_survey",
        "CASCADE",
    )
    _replace_fk(
        "calibration_sessions",
        ["response_id"],
        "survey_responses",
        ["id"],
        "fk_calib_sessions_response",
        "CASCADE",
    )
    _replace_fk(
        "gaze_records",
        ["post_id"],
        "survey_posts",
        ["id"],
        "fk_gaze_records_post",
        "SET NULL",
    )
    _replace_fk(
        "click_records",
        ["post_id"],
        "survey_posts",
        ["id"],
        "fk_click_records_post",
        "SET NULL",
    )


def _ensure_indexes() -> None:
    _create_index_if_missing("ix_survey_responses_survey_id", "survey_responses", ["survey_id"])
    _create_index_if_missing(
        "ix_survey_responses_assigned_group", "survey_responses", ["assigned_group"]
    )
    _create_index_if_missing("ix_survey_responses_language", "survey_responses", ["language"])
    _create_index_if_missing("ix_survey_responses_status", "survey_responses", ["status"])
    _create_index_if_missing(
        "ix_participant_interactions_response_post",
        "participant_interactions",
        ["response_id", "post_id"],
    )
    _create_index_if_missing("ix_gaze_records_response_id", "gaze_records", ["response_id"])
    _create_index_if_missing(
        "ix_gaze_records_response_timestamp", "gaze_records", ["response_id", "timestamp_ms"]
    )
    _create_index_if_missing(
        "ix_gaze_records_post_timestamp", "gaze_records", ["post_id", "timestamp_ms"]
    )
    _create_index_if_missing("ix_click_records_response_id", "click_records", ["response_id"])
    _create_index_if_missing(
        "ix_click_records_response_timestamp", "click_records", ["response_id", "timestamp_ms"]
    )
    _create_index_if_missing(
        "ix_click_records_post_timestamp", "click_records", ["post_id", "timestamp_ms"]
    )
    _create_index_if_missing(
        "ix_survey_translations_survey_language",
        "survey_translations",
        ["survey_id", "language_code"],
    )
    _create_index_if_missing(
        "ix_post_translations_survey_language",
        "post_translations",
        ["survey_id", "language_code"],
    )
    _create_index_if_missing(
        "ix_post_translations_post_language",
        "post_translations",
        ["post_id", "language_code"],
    )
    _create_index_if_missing(
        "ix_question_translations_survey_language",
        "question_translations",
        ["survey_id", "language_code"],
    )
    _create_index_if_missing(
        "ix_question_translations_question_language",
        "question_translations",
        ["question_id", "language_code"],
    )


def upgrade() -> None:
    _create_core_tables()
    _create_tracking_tables()
    _create_translation_tables()
    _harden_existing_tables()
    _ensure_indexes()


def downgrade() -> None:
    op.drop_table("question_translations")
    op.drop_table("post_translations")
    op.drop_table("survey_translations")
    op.drop_table("click_records")
    op.drop_table("gaze_records")
    op.drop_table("calibration_points")
    op.drop_table("calibration_sessions")
    op.drop_table("question_responses")
    op.drop_table("participant_comments")
    op.drop_table("participant_likes")
    op.drop_table("participant_interactions")
    op.drop_table("survey_responses")
    op.drop_table("questions")
    op.drop_table("post_comments")
    op.drop_table("survey_posts")
    op.drop_table("surveys")
    op.drop_table("researchers")
