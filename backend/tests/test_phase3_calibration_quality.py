"""Phase 3 calibration quality scoring and storage tests."""

from datetime import datetime

import pytest

from app.models.participant import SurveyResponse
from app.models.tracking import CalibrationPoint, CalibrationSession
from app.routers.tracking import complete_calibration
from app.schemas.tracking import CompleteCalibrationRequest


class ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class CompleteCalibrationDB:
    def __init__(self, session: CalibrationSession, response: SurveyResponse):
        self.session = session
        self.response = response
        self.execute_count = 0
        self.flushed = False

    async def execute(self, _statement):
        self.execute_count += 1
        if self.execute_count == 1:
            return ScalarResult(self.session)
        return ScalarResult(self.response)

    async def flush(self):
        self.flushed = True

    async def refresh(self, _item):
        return None


def make_samples(count: int = 12, *, face_ratio: float = 1.0, unstable: bool = False):
    detected_count = int(count * face_ratio)
    return [
        {
            "timestamp_ms": index * 100,
            "left_iris_x": 0.45,
            "left_iris_y": 0.52,
            "right_iris_x": 0.55,
            "right_iris_y": 0.48,
            "face_detected": index < detected_count,
            "head_rotation": {
                "yaw": -15 if unstable and index % 2 == 0 else 15 if unstable else 1,
                "pitch": -12 if unstable and index % 2 == 0 else 12 if unstable else 1,
            },
        }
        for index in range(count)
    ]


def make_point(point_index: int, samples: list[dict]) -> CalibrationPoint:
    return CalibrationPoint(
        id=point_index,
        session_id=1,
        point_index=point_index,
        target_screen_x=100,
        target_screen_y=100,
        samples=samples,
        samples_count=len(samples),
        created_at=datetime.utcnow(),
    )


@pytest.mark.asyncio
async def test_complete_calibration_stores_score_and_passed():
    session = CalibrationSession(
        id=1,
        response_id=10,
        status="in_progress",
        screen_width=1440,
        screen_height=900,
        expected_points=9,
        started_at=datetime.utcnow(),
    )
    session.points = [make_point(index, make_samples()) for index in range(1, 10)]
    response = SurveyResponse(
        id=10,
        survey_id=1,
        participant_token="participant-token",
        assigned_group=1,
        status="in_progress",
        started_at=datetime.utcnow(),
    )
    db = CompleteCalibrationDB(session, response)

    result = await complete_calibration(
        1,
        CompleteCalibrationRequest(participant_token="participant-token"),
        db,
    )

    assert db.flushed is True
    assert result.quality.passed is True
    assert result.quality.quality_score >= 85
    assert session.passed is True
    assert session.quality_score == result.quality.quality_score
    assert session.stability_score == result.quality.stability_score
    assert session.quality == result.quality.overall_quality
    assert session.quality_reason == result.quality.quality_reason
