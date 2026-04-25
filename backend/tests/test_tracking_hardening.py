"""Regression tests for participant tracking and interaction hardening."""

from datetime import datetime

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.models.participant import ParticipantInteraction, SurveyResponse
from app.models.survey import Survey
from app.models.tracking import CalibrationSession
from app.routers.surveys import record_interaction
from app.routers.tracking import (
    complete_calibration,
    create_calibration_session,
    record_click_batch,
    record_gaze_batch,
)
from app.schemas.survey import InteractionRequest
from app.schemas.tracking import (
    ClickBatchRequest,
    ClickDataPoint,
    CompleteCalibrationRequest,
    CreateCalibrationRequest,
    GazeBatchRequest,
)

NOW = datetime(2026, 4, 25, 10, 0, 0)


class ScalarOneResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class ScalarListResult:
    def __init__(self, values):
        self.values = values

    def scalars(self):
        return self

    def all(self):
        return self.values


class RaceCalibrationDB:
    def __init__(self):
        self.execute_count = 0
        self.rolled_back = False
        self.added = []

    async def execute(self, _statement):
        self.execute_count += 1
        if self.execute_count == 1:
            return ScalarOneResult(
                SurveyResponse(
                    id=10,
                    survey_id=1,
                    participant_token="participant-token",
                    assigned_group=1,
                    status="in_progress",
                    started_at=NOW,
                )
            )
        return ScalarOneResult(None)

    async def get(self, _model, _id):
        return Survey(id=1, researcher_id=1, title="Survey", share_code="code")

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        raise IntegrityError("insert calibration session", {}, Exception("duplicate"))

    async def rollback(self):
        self.rolled_back = True


class CompleteEmptyCalibrationDB:
    def __init__(self):
        self.execute_count = 0
        self.flushed = False
        self.session = CalibrationSession(
            id=1,
            response_id=10,
            status="in_progress",
            screen_width=1440,
            screen_height=900,
            expected_points=9,
            started_at=NOW,
        )
        self.session.points = []
        self.response = SurveyResponse(
            id=10,
            survey_id=1,
            participant_token="participant-token",
            assigned_group=1,
            status="in_progress",
            started_at=NOW,
        )

    async def execute(self, _statement):
        self.execute_count += 1
        if self.execute_count == 1:
            return ScalarOneResult(self.session)
        return ScalarOneResult(self.response)

    async def flush(self):
        self.flushed = True


class TrackingPostDB:
    def __init__(self, valid_post_ids: list[int]):
        self.valid_post_ids = valid_post_ids
        self.execute_count = 0
        self.added = []

    async def execute(self, _statement):
        self.execute_count += 1
        if self.execute_count == 1:
            return ScalarOneResult(
                SurveyResponse(
                    id=10,
                    survey_id=1,
                    participant_token="participant-token",
                    assigned_group=1,
                    status="in_progress",
                    started_at=NOW,
                )
            )
        return ScalarListResult(self.valid_post_ids)

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        return None


class InteractionDB:
    def __init__(self, post_exists: bool = True):
        self.post_exists = post_exists
        self.execute_count = 0
        self.added = []
        self.flushed = False
        self.refreshed = False

    async def execute(self, _statement):
        self.execute_count += 1
        if self.execute_count == 1:
            return ScalarOneResult(
                SurveyResponse(
                    id=10,
                    survey_id=1,
                    participant_token="participant-token",
                    assigned_group=1,
                    status="in_progress",
                    started_at=NOW,
                )
            )
        return ScalarOneResult(99 if self.post_exists else None)

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        self.flushed = True
        for item in self.added:
            if isinstance(item, ParticipantInteraction):
                item.id = 123
                item.timestamp = NOW

    async def refresh(self, _item):
        self.refreshed = True


@pytest.mark.asyncio
async def test_create_calibration_session_race_returns_conflict():
    db = RaceCalibrationDB()

    with pytest.raises(HTTPException) as exc_info:
        await create_calibration_session(
            CreateCalibrationRequest(
                response_id=10,
                participant_token="participant-token",
                screen_width=1440,
                screen_height=900,
            ),
            db,
        )

    assert exc_info.value.status_code == 409
    assert db.rolled_back is True


@pytest.mark.asyncio
async def test_complete_calibration_rejects_empty_point_set():
    db = CompleteEmptyCalibrationDB()

    with pytest.raises(HTTPException) as exc_info:
        await complete_calibration(
            1,
            CompleteCalibrationRequest(participant_token="participant-token"),
            db,
        )

    assert exc_info.value.status_code == 409
    assert db.session.status == "in_progress"
    assert db.flushed is False


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("endpoint", "body"),
    [
        (
            record_gaze_batch,
            GazeBatchRequest(
                response_id=10,
                participant_token="participant-token",
                data=[{"post_id": 99, "timestamp_ms": 1000, "screen_x": 10, "screen_y": 20}],
            ),
        ),
        (
            record_click_batch,
            ClickBatchRequest(
                response_id=10,
                participant_token="participant-token",
                data=[
                    {
                        "post_id": 99,
                        "timestamp_ms": 1000,
                        "screen_x": 10,
                        "screen_y": 20,
                        "target_element": "headline",
                    }
                ],
            ),
        ),
    ],
)
async def test_tracking_batches_reject_cross_survey_post_ids(endpoint, body):
    db = TrackingPostDB(valid_post_ids=[])

    with pytest.raises(HTTPException) as exc_info:
        await endpoint(body, db)

    assert exc_info.value.status_code == 422
    assert db.added == []


def test_click_target_element_rejects_empty_string():
    with pytest.raises(ValidationError):
        ClickDataPoint(
            post_id=1,
            timestamp_ms=1000,
            screen_x=10,
            screen_y=20,
            target_element="",
        )


@pytest.mark.asyncio
async def test_record_interaction_persists_in_request_session():
    db = InteractionDB(post_exists=True)

    interaction = await record_interaction(
        10,
        InteractionRequest(post_id=99, action_type="share"),
        db,
    )

    assert db.flushed is True
    assert db.refreshed is True
    assert interaction.id == 123
    assert db.added == [interaction]


@pytest.mark.asyncio
async def test_record_interaction_rejects_cross_survey_post_id():
    db = InteractionDB(post_exists=False)

    with pytest.raises(HTTPException) as exc_info:
        await record_interaction(
            10,
            InteractionRequest(post_id=99, action_type="share"),
            db,
        )

    assert exc_info.value.status_code == 422
    assert db.added == []
