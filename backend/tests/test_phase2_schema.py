"""Phase 2 database schema hardening tests."""

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import ForeignKeyConstraint, UniqueConstraint

from app import models  # noqa: F401
from app.models.participant import SurveyResponse
from app.models.tracking import CalibrationPoint, CalibrationSession, ClickRecord, GazeRecord
from app.models.translation import PostTranslation, QuestionTranslation, SurveyTranslation


def _fk_for_column(table, column_name: str) -> ForeignKeyConstraint:
    for constraint in table.constraints:
        if isinstance(constraint, ForeignKeyConstraint):
            if [column.name for column in constraint.columns] == [column_name]:
                return constraint
    raise AssertionError(f"No foreign key found for {table.name}.{column_name}")


def _index_names(table) -> set[str]:
    return {index.name for index in table.indexes}


def _unique_names(table) -> set[str]:
    return {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }


def test_alembic_head_revision_is_configured():
    backend_root = Path(__file__).resolve().parents[1]
    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("script_location", str(backend_root / "alembic"))

    script = ScriptDirectory.from_config(config)

    assert script.get_current_head() == "20260425_0001"


def test_tracking_schema_hardening_columns_and_relationships():
    session_table = CalibrationSession.__table__
    point_table = CalibrationPoint.__table__
    gaze_table = GazeRecord.__table__
    click_table = ClickRecord.__table__

    for column_name in {
        "quality_score",
        "passed",
        "stability_score",
        "quality_reason",
        "model_type",
        "model_params",
        "validation_error_px",
    }:
        assert column_name in session_table.c
    assert _fk_for_column(session_table, "response_id").ondelete == "CASCADE"

    assert {"face_detection_rate", "stability_score", "valid"}.issubset(point_table.c.keys())
    assert "uq_session_point" in _unique_names(point_table)

    assert gaze_table.c.received_at.server_default is not None
    assert click_table.c.received_at.server_default is not None
    assert _fk_for_column(gaze_table, "post_id").ondelete == "SET NULL"
    assert _fk_for_column(click_table, "post_id").ondelete == "SET NULL"
    assert {
        "ix_gaze_records_response_timestamp",
        "ix_gaze_records_post_timestamp",
    }.issubset(_index_names(gaze_table))
    assert {
        "ix_click_records_response_timestamp",
        "ix_click_records_post_timestamp",
    }.issubset(_index_names(click_table))


def test_survey_response_indexes_and_cascade_relationship():
    table = SurveyResponse.__table__

    assert _fk_for_column(table, "survey_id").ondelete == "CASCADE"
    assert {
        "ix_survey_responses_survey_id",
        "ix_survey_responses_assigned_group",
        "ix_survey_responses_language",
        "ix_survey_responses_status",
    }.issubset(_index_names(table))


def test_translation_tables_have_required_fields_and_constraints():
    expected_common = {"id", "survey_id", "language_code", "translated_fields", "created_at", "updated_at"}

    survey_table = SurveyTranslation.__table__
    post_table = PostTranslation.__table__
    question_table = QuestionTranslation.__table__

    assert expected_common.issubset(survey_table.c.keys())
    assert expected_common.union({"post_id"}).issubset(post_table.c.keys())
    assert expected_common.union({"question_id"}).issubset(question_table.c.keys())

    assert _fk_for_column(survey_table, "survey_id").ondelete == "CASCADE"
    assert _fk_for_column(post_table, "survey_id").ondelete == "CASCADE"
    assert _fk_for_column(post_table, "post_id").ondelete == "CASCADE"
    assert _fk_for_column(question_table, "survey_id").ondelete == "CASCADE"
    assert _fk_for_column(question_table, "question_id").ondelete == "CASCADE"

    assert "uq_survey_translation_language" in _unique_names(survey_table)
    assert "uq_post_translation_language" in _unique_names(post_table)
    assert "uq_question_translation_language" in _unique_names(question_table)


def test_tracking_schema_does_not_add_camera_media_columns():
    forbidden_fragments = ("image", "video", "frame", "blob")
    tracking_tables = [
        CalibrationSession.__table__,
        CalibrationPoint.__table__,
        GazeRecord.__table__,
        ClickRecord.__table__,
    ]

    for table in tracking_tables:
        for column in table.c:
            assert not any(fragment in column.name for fragment in forbidden_fragments)
