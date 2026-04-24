"""Phase 4 research data export tests."""

import csv
import json
from datetime import datetime, timedelta
from io import StringIO

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.auth import get_current_researcher
from app.database import get_db
from app.main import app
from app.models.participant import ParticipantInteraction, SurveyResponse
from app.models.researcher import Researcher
from app.models.survey import Survey, SurveyPost
from app.models.tracking import CalibrationSession
from app.services.export_service import (
    CSV_HEADERS,
    ExportFilters,
    build_export_payload,
    export_payload_to_csv,
    load_survey_export,
    response_matches_filters,
)


class ScalarResult:
    def scalar_one_or_none(self):
        return None


class ScalarList:
    def __init__(self, values):
        self.values = values

    def all(self):
        return self.values


class ExecuteResult:
    def __init__(self, *, scalar=None, scalars=None, rows=None):
        self.scalar = scalar
        self.scalar_values = scalars or []
        self.rows = rows or []

    def scalar_one_or_none(self):
        return self.scalar

    def scalars(self):
        return ScalarList(self.scalar_values)

    def all(self):
        return self.rows


class NoSurveyDB:
    async def execute(self, _statement):
        return ScalarResult()


class ExportEndpointDB:
    def __init__(self):
        self.calls = 0
        self.survey = make_survey()
        self.response = make_response(101)

    async def execute(self, _statement):
        self.calls += 1
        if self.calls == 1:
            return ExecuteResult(scalar=self.survey)
        if self.calls == 2:
            return ExecuteResult(scalars=[self.response])
        if self.calls == 3:
            return ExecuteResult(rows=[(101, 12)])
        if self.calls == 4:
            return ExecuteResult(rows=[(101, 3)])
        return ExecuteResult(rows=[])


def make_survey() -> Survey:
    now = datetime(2026, 4, 25, 10, 0, 0)
    survey = Survey(
        id=7,
        researcher_id=99,
        title="Export Survey",
        description="Research export test",
        status="published",
        share_code="export-share",
        num_groups=2,
        group_names={"1": "control", "2": "treatment"},
        gaze_tracking_enabled=True,
        gaze_interval_ms=1000,
        click_tracking_enabled=True,
        calibration_enabled=True,
        calibration_points=9,
        created_at=now,
        updated_at=now,
    )
    post = SurveyPost(
        id=11,
        survey_id=7,
        order=1,
        original_url="https://example.com/story",
        fetched_title="Fetched title",
        fetched_image_url="https://example.com/image.jpg",
        fetched_description="Fetched description",
        fetched_source="example.com",
        display_title="Displayed title",
        display_image_url=None,
        display_likes=10,
        display_comments_count=2,
        display_shares=1,
        show_likes=True,
        show_comments=True,
        show_shares=True,
        visible_to_groups=[1, 2],
        group_overrides={"2": {"display_likes": 999, "display_title": "Treatment title"}},
        created_at=now,
    )
    post.comments = []
    post.questions = []
    survey.posts = [post]
    return survey


def make_response(
    response_id: int,
    *,
    group: int = 2,
    language: str = "en",
    status: str = "completed",
    calibration_passed: bool = True,
) -> SurveyResponse:
    started_at = datetime(2026, 4, 25, 10, 5, 0)
    response = SurveyResponse(
        id=response_id,
        survey_id=7,
        participant_token=f"secret-token-{response_id}",
        assigned_group=group,
        language=language,
        status=status,
        started_at=started_at,
        completed_at=started_at + timedelta(minutes=4),
    )
    response.interactions = [
        ParticipantInteraction(
            id=501,
            response_id=response_id,
            post_id=11,
            action_type="like",
            comment_text=None,
            dwell_time_ms=1200,
            click_x=10.5,
            click_y=20.5,
            timestamp=started_at + timedelta(seconds=30),
        )
    ]
    response.calibration_session = CalibrationSession(
        id=301,
        response_id=response_id,
        status="completed",
        screen_width=1440,
        screen_height=900,
        expected_points=9,
        face_detection_rate=0.96,
        quality_score=92.5 if calibration_passed else 45.0,
        passed=calibration_passed,
        stability_score=0.94,
        quality="good" if calibration_passed else "poor",
        quality_reason="Calibration passed." if calibration_passed else "Calibration failed.",
        started_at=started_at,
        completed_at=started_at + timedelta(minutes=1),
    )
    return response


def make_payload() -> dict:
    return build_export_payload(
        make_survey(),
        [make_response(101)],
        filters=ExportFilters(assigned_group=2, language="en"),
        gaze_counts={101: 12},
        click_counts={101: 3},
        question_responses_by_response={
            101: [
                {
                    "id": 401,
                    "question_id": 21,
                    "post_id": 11,
                    "question_type": "free_text",
                    "question_text": "What did you think?",
                    "answer_text": "Interesting",
                    "answer_value": None,
                    "answer_choices": None,
                    "created_at": "2026-04-25T10:08:00",
                }
            ]
        },
    )


def test_export_endpoint_requires_authentication():
    client = TestClient(app)

    response = client.get("/api/v1/surveys/7/export?format=json")

    assert response.status_code == 401


def install_export_overrides():
    async def override_researcher():
        return Researcher(
            id=99,
            email="researcher@example.com",
            password_hash="hash",
            name="Researcher",
            created_at=datetime(2026, 4, 25, 9, 0, 0),
        )

    async def override_db():
        yield ExportEndpointDB()

    app.dependency_overrides[get_current_researcher] = override_researcher
    app.dependency_overrides[get_db] = override_db


def clear_overrides():
    app.dependency_overrides.clear()


def test_json_export_endpoint_returns_structured_export():
    install_export_overrides()
    try:
        client = TestClient(app)
        response = client.get("/api/v1/surveys/7/export?format=json")
    finally:
        clear_overrides()

    assert response.status_code == 200
    body = response.json()
    assert body["survey_id"] == 7
    assert body["responses"][0]["gaze_count"] == 12
    assert body["responses"][0]["click_count"] == 3
    assert body["responses"][0]["calibration"]["passed"] is True


def test_csv_export_endpoint_streams_csv():
    install_export_overrides()
    try:
        client = TestClient(app)
        response = client.get("/api/v1/surveys/7/export?format=csv")
    finally:
        clear_overrides()

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    rows = list(csv.DictReader(StringIO(response.text)))
    assert rows[0]["gaze_count"] == "12"
    assert rows[0]["click_count"] == "3"


@pytest.mark.asyncio
async def test_export_missing_or_unowned_survey_returns_404():
    with pytest.raises(HTTPException) as exc_info:
        await load_survey_export(
            NoSurveyDB(),
            survey_id=7,
            researcher_id=99,
            filters=ExportFilters(),
        )

    assert exc_info.value.status_code == 404


def test_export_filters_match_condition_language_status_and_calibration():
    matching = make_response(101, group=2, language="zh", status="completed")
    wrong_group = make_response(102, group=1, language="zh", status="completed")
    wrong_language = make_response(103, group=2, language="en", status="completed")
    wrong_status = make_response(104, group=2, language="zh", status="flagged")
    failed_calibration = make_response(
        105, group=2, language="zh", status="completed", calibration_passed=False
    )
    filters = ExportFilters(condition=2, language="zh", response_status="completed", calibration_passed=True)

    assert response_matches_filters(matching, filters) is True
    assert response_matches_filters(wrong_group, filters) is False
    assert response_matches_filters(wrong_language, filters) is False
    assert response_matches_filters(wrong_status, filters) is False
    assert response_matches_filters(failed_calibration, filters) is False


def test_json_export_shape_tracking_summary_and_anonymization():
    payload = make_payload()
    exported = payload["responses"][0]

    assert payload["survey_id"] == 7
    assert exported["survey_id"] == 7
    assert exported["response_id"] == 101
    assert exported["participant_id"].startswith("anon_")
    assert exported["participant_id"] != "secret-token-101"
    assert "secret-token-101" not in json.dumps(payload)
    assert exported["assigned_group"] == 2
    assert exported["language"] == "en"
    assert exported["response_status"] == "completed"
    assert exported["calibration"]["status"] == "completed"
    assert exported["calibration"]["quality"] == "good"
    assert exported["calibration"]["quality_score"] == 92.5
    assert exported["calibration"]["passed"] is True
    assert exported["gaze_count"] == 12
    assert exported["click_count"] == 3
    assert exported["participant_interactions"][0]["action_type"] == "like"
    assert exported["question_responses"][0]["answer_text"] == "Interesting"
    assert exported["displayed_posts"][0]["display_likes"] == 999
    assert exported["displayed_posts"][0]["display_title"] == "Treatment title"


def test_csv_export_headers_and_flattened_summary_fields():
    csv_text = export_payload_to_csv(make_payload())
    reader = csv.DictReader(StringIO(csv_text))
    rows = list(reader)

    assert reader.fieldnames == CSV_HEADERS
    assert len(rows) == 1
    assert rows[0]["participant_id"].startswith("anon_")
    assert rows[0]["calibration_quality"] == "good"
    assert rows[0]["calibration_quality_score"] == "92.5"
    assert rows[0]["calibration_passed"] == "True"
    assert rows[0]["gaze_count"] == "12"
    assert rows[0]["click_count"] == "3"
    assert json.loads(rows[0]["participant_interactions"])[0]["action_type"] == "like"
    assert json.loads(rows[0]["question_responses"])[0]["answer_text"] == "Interesting"
