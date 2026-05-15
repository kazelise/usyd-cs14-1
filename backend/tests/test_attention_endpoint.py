"""Tests for the survey-time attention summary endpoint and complete-response wiring."""

from datetime import datetime, timedelta

import pytest

from app.models.participant import SurveyResponse
from app.models.tracking import CalibrationSession
from app.routers.surveys import (
    AttentionSummaryRequest,
    CompleteResponseRequest,
    complete_response,
    submit_attention_summary,
)
from app.schemas.survey import AttentionSummaryIn


class ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class AttentionDB:
    """Minimal AsyncSession-shaped fake.

    The router does two reads:
      1. lookup the SurveyResponse by id (token-checked in the helper)
      2. lookup the CalibrationSession by response_id

    We hand out a queue of scalar results in that exact order.
    """

    def __init__(self, response: SurveyResponse, calibration: CalibrationSession | None):
        self.response = response
        self.calibration = calibration
        self._queue = [response, calibration]
        self.committed = False

    async def execute(self, _statement):
        return ScalarResult(self._queue.pop(0))

    async def commit(self):
        self.committed = True


def make_response(token: str = "good-token") -> SurveyResponse:
    return SurveyResponse(
        id=42,
        survey_id=7,
        participant_token=token,
        assigned_group=1,
        status="in_progress",
        is_preview=False,
        started_at=datetime(2026, 5, 15, 10, 0, 0),
    )


def make_calibration(passed: bool = True, quality: str = "good") -> CalibrationSession:
    return CalibrationSession(
        id=99,
        response_id=42,
        status="completed",
        screen_width=1440,
        screen_height=900,
        expected_points=9,
        quality_score=88.0 if passed else 40.0,
        passed=passed,
        quality=quality,
        started_at=datetime(2026, 5, 15, 9, 59, 0),
        completed_at=datetime(2026, 5, 15, 10, 0, 0),
    )


@pytest.mark.asyncio
async def test_submit_attention_summary_persists_computed_quality():
    response = make_response()
    db = AttentionDB(response, make_calibration())

    body = AttentionSummaryRequest(
        participant_token="good-token",
        summary=AttentionSummaryIn(
            active_ms=60_000,
            expected_samples=60,
            detected_samples=58,
            missing_ms=2_000,
            no_face_periods=1,
        ),
    )

    result = await submit_attention_summary(42, body, db)  # type: ignore[arg-type]

    assert db.committed is True
    assert result["quality"] == "high"
    assert result["confidence"] >= 0.9
    assert response.attention_quality == "high"
    assert response.attention_detected_samples == 58
    assert response.attention_expected_samples == 60
    assert response.attention_coverage >= 0.95


@pytest.mark.asyncio
async def test_submit_attention_summary_downgrades_when_face_missing():
    response = make_response()
    db = AttentionDB(response, make_calibration())

    body = AttentionSummaryRequest(
        participant_token="good-token",
        summary=AttentionSummaryIn(
            active_ms=60_000,
            expected_samples=60,
            detected_samples=10,
            missing_ms=45_000,
            no_face_periods=6,
        ),
    )

    result = await submit_attention_summary(42, body, db)  # type: ignore[arg-type]

    assert result["quality"] == "low"
    assert result["confidence"] < 0.5
    assert response.attention_no_face_periods == 6


@pytest.mark.asyncio
async def test_complete_response_attaches_attention_summary_when_provided():
    response = make_response()
    # complete_response start time is in the past so it does not get flagged.
    response.started_at = datetime.utcnow() - timedelta(minutes=5)
    db = AttentionDB(response, make_calibration())

    body = CompleteResponseRequest(
        participant_token="good-token",
        attention_summary=AttentionSummaryIn(
            active_ms=60_000,
            expected_samples=60,
            detected_samples=58,
            missing_ms=2_000,
            no_face_periods=0,
        ),
    )

    result = await complete_response(42, body, db)  # type: ignore[arg-type]

    assert result["status"] == "completed"
    assert result["attention_confidence"] >= 0.9
    assert result["attention_quality"] == "high"
    assert response.attention_quality == "high"
