"""Completion integrity checks for participant responses."""

from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException

from app.models.participant import (
    ParticipantComment,
    ParticipantInteraction,
    ParticipantLike,
    SurveyResponse,
)
from app.models.survey import Survey
from app.models.tracking import CalibrationSession
from app.routers.surveys import CompleteResponseRequest, complete_response


class ScalarOneResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class ScalarListResult:
    def __init__(self, values):
        self.values = list(values)

    def scalars(self):
        return self

    def all(self):
        return self.values


class CompletionDB:
    def __init__(self, results):
        self.results = list(results)
        self.committed = False

    async def execute(self, _statement):
        if not self.results:
            raise AssertionError("Unexpected database query")
        return self.results.pop(0)

    async def commit(self):
        self.committed = True


def make_response() -> SurveyResponse:
    return SurveyResponse(
        id=10,
        survey_id=7,
        participant_token="participant-token",
        assigned_group=1,
        shown_post_order=[31],
        status="in_progress",
        is_preview=False,
        started_at=datetime.utcnow() - timedelta(minutes=5),
    )


def make_survey(*, calibration_enabled: bool) -> Survey:
    return Survey(
        id=7,
        researcher_id=1,
        title="Completion survey",
        status="published",
        share_code="COMPLETE",
        num_groups=1,
        gaze_tracking_enabled=True,
        gaze_interval_ms=1000,
        click_tracking_enabled=True,
        calibration_enabled=calibration_enabled,
        calibration_points=9,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.mark.asyncio
async def test_complete_response_requires_completed_calibration_for_real_sessions():
    db = CompletionDB(
        [
            ScalarOneResult(make_response()),
            ScalarOneResult(make_survey(calibration_enabled=True)),
            ScalarOneResult(None),
        ]
    )

    with pytest.raises(HTTPException) as exc_info:
        await complete_response(
            10, CompleteResponseRequest(participant_token="participant-token"), db
        )

    assert exc_info.value.status_code == 422
    assert db.committed is False


@pytest.mark.asyncio
async def test_complete_response_requires_answers_for_configured_questions():
    db = CompletionDB(
        [
            ScalarOneResult(make_response()),
            ScalarOneResult(make_survey(calibration_enabled=False)),
            ScalarListResult([51]),
            ScalarListResult([]),
        ]
    )

    with pytest.raises(HTTPException) as exc_info:
        await complete_response(
            10, CompleteResponseRequest(participant_token="participant-token"), db
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail["code"] == "missing_required_answers"
    assert exc_info.value.detail["missing_question_ids"] == [51]
    assert db.committed is False


@pytest.mark.asyncio
async def test_complete_response_accepts_real_session_with_answered_questions():
    response = make_response()
    db = CompletionDB(
        [
            ScalarOneResult(response),
            ScalarOneResult(make_survey(calibration_enabled=True)),
            ScalarOneResult(
                CalibrationSession(
                    response_id=10,
                    status="completed",
                    passed=True,
                    quality="good",
                )
            ),
            ScalarListResult([51]),
            ScalarListResult([51]),
        ]
    )

    result = await complete_response(
        10, CompleteResponseRequest(participant_token="participant-token"), db
    )

    assert result["status"] == "completed"
    assert response.status == "completed"
    assert db.committed is True


@pytest.mark.asyncio
async def test_complete_response_requires_some_engagement_when_no_questions_exist():
    db = CompletionDB(
        [
            ScalarOneResult(make_response()),
            ScalarOneResult(make_survey(calibration_enabled=False)),
            ScalarListResult([]),
            ScalarOneResult(None),
            ScalarOneResult(None),
            ScalarOneResult(None),
        ]
    )

    with pytest.raises(HTTPException) as exc_info:
        await complete_response(
            10, CompleteResponseRequest(participant_token="participant-token"), db
        )

    assert exc_info.value.status_code == 422
    assert "post interaction" in exc_info.value.detail
    assert db.committed is False


@pytest.mark.asyncio
async def test_complete_response_accepts_any_post_interaction_when_no_questions_exist():
    response = make_response()
    db = CompletionDB(
        [
            ScalarOneResult(response),
            ScalarOneResult(make_survey(calibration_enabled=False)),
            ScalarListResult([]),
            ScalarOneResult(ParticipantInteraction(response_id=10, post_id=31, action_type="click")),
        ]
    )

    result = await complete_response(
        10, CompleteResponseRequest(participant_token="participant-token"), db
    )

    assert result["status"] == "completed"
    assert response.status == "completed"
    assert db.committed is True


@pytest.mark.asyncio
async def test_complete_response_accepts_liked_post_when_no_questions_exist():
    response = make_response()
    db = CompletionDB(
        [
            ScalarOneResult(response),
            ScalarOneResult(make_survey(calibration_enabled=False)),
            ScalarListResult([]),
            ScalarOneResult(None),
            ScalarOneResult(ParticipantLike(response_id=10, post_id=31)),
        ]
    )

    result = await complete_response(
        10, CompleteResponseRequest(participant_token="participant-token"), db
    )

    assert result["status"] == "completed"
    assert response.status == "completed"
    assert db.committed is True


@pytest.mark.asyncio
async def test_complete_response_accepts_participant_comment_when_no_questions_exist():
    response = make_response()
    db = CompletionDB(
        [
            ScalarOneResult(response),
            ScalarOneResult(make_survey(calibration_enabled=False)),
            ScalarListResult([]),
            ScalarOneResult(None),
            ScalarOneResult(None),
            ScalarOneResult(ParticipantComment(response_id=10, post_id=31, text="Useful")),
        ]
    )

    result = await complete_response(
        10, CompleteResponseRequest(participant_token="participant-token"), db
    )

    assert result["status"] == "completed"
    assert response.status == "completed"
    assert db.committed is True
