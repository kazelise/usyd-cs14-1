"""Phase 1 participant session and tracking security contract tests."""

from datetime import datetime

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.models.participant import SurveyResponse
from app.models.survey import Survey, SurveyPost
from app.models.tracking import CalibrationSession
from app.routers import surveys
from app.routers.surveys import start_survey
from app.routers.tracking import (
    create_calibration_session,
    record_click_batch,
    record_gaze_batch,
)
from app.schemas.survey import StartSurveyRequest
from app.schemas.tracking import (
    ClickBatchRequest,
    CreateCalibrationRequest,
    GazeBatchRequest,
)


class ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class StartSurveyDB:
    def __init__(self, survey: Survey):
        self.survey = survey
        self.added = []

    async def execute(self, _statement):
        return ScalarResult(self.survey)

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        for item in self.added:
            if isinstance(item, SurveyResponse):
                item.id = 321
                item.participant_token = "participant-token"

    async def refresh(self, _item):
        return None


class TrackingDB:
    def __init__(self, response: SurveyResponse):
        self.response = response
        self.added = []

    async def execute(self, _statement):
        return ScalarResult(self.response)

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        return None


def make_post(
    post_id: int,
    *,
    order: int,
    visible_to_groups: list[int] | None = None,
    group_overrides: dict | None = None,
) -> SurveyPost:
    post = SurveyPost(
        id=post_id,
        survey_id=10,
        order=order,
        original_url=f"https://example.com/{post_id}",
        fetched_title=f"Post {post_id}",
        fetched_image_url=None,
        fetched_description=None,
        fetched_source="example.com",
        display_title=None,
        display_image_url=None,
        display_likes=10,
        display_comments_count=2,
        display_shares=1,
        show_likes=True,
        show_comments=True,
        show_shares=True,
        visible_to_groups=visible_to_groups,
        group_overrides=group_overrides,
        created_at=datetime.utcnow(),
    )
    post.comments = []
    post.questions = []
    return post


def make_survey(posts: list[SurveyPost]) -> Survey:
    survey = Survey(
        id=10,
        researcher_id=1,
        title="Phase 1 Survey",
        description="Contract test survey",
        status="published",
        share_code="share-code",
        num_groups=2,
        group_names=None,
        gaze_tracking_enabled=True,
        gaze_interval_ms=750,
        click_tracking_enabled=True,
        calibration_enabled=True,
        calibration_points=5,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    survey.posts = posts
    return survey


@pytest.mark.asyncio
async def test_start_survey_returns_token_and_calibration_points_and_saves_metadata(monkeypatch):
    monkeypatch.setattr(surveys.random, "randint", lambda _start, _end: 2)
    post = make_post(1, order=1)
    db = StartSurveyDB(make_survey([post]))
    body = StartSurveyRequest(
        language="zh",
        screen_width=1440,
        screen_height=900,
        user_agent="pytest-browser",
    )

    response = await start_survey("share-code", body, db)

    created_response = db.added[0]
    assert response.participant_token == "participant-token"
    assert response.calibration_points == 5
    assert created_response.language == "zh"
    assert created_response.screen_width == 1440
    assert created_response.screen_height == 900
    assert created_response.user_agent == "pytest-browser"


@pytest.mark.asyncio
async def test_group_overrides_apply_to_payload_without_mutating_persisted_post(monkeypatch):
    monkeypatch.setattr(surveys.random, "randint", lambda _start, _end: 2)
    post = make_post(
        1,
        order=1,
        visible_to_groups=[2],
        group_overrides={"2": {"display_likes": 999, "display_shares": 42}},
    )
    db = StartSurveyDB(make_survey([post]))

    response = await start_survey("share-code", StartSurveyRequest(), db)

    assert response.posts[0].display_likes == 999
    assert response.posts[0].display_shares == 42
    assert post.display_likes == 10
    assert post.display_shares == 1


@pytest.mark.asyncio
async def test_start_survey_still_filters_visible_posts(monkeypatch):
    monkeypatch.setattr(surveys.random, "randint", lambda _start, _end: 2)
    group_one_post = make_post(1, order=1, visible_to_groups=[1])
    group_two_post = make_post(2, order=2, visible_to_groups=[2])
    all_groups_post = make_post(3, order=3, visible_to_groups=None)
    db = StartSurveyDB(make_survey([group_one_post, group_two_post, all_groups_post]))

    response = await start_survey("share-code", StartSurveyRequest(), db)

    assert [post.id for post in response.posts] == [2, 3]


def test_tracking_schemas_require_participant_token():
    with pytest.raises(ValidationError):
        CreateCalibrationRequest(response_id=1, screen_width=1440, screen_height=900)
    with pytest.raises(ValidationError):
        GazeBatchRequest(response_id=1, data=[])
    with pytest.raises(ValidationError):
        ClickBatchRequest(response_id=1, data=[])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("endpoint", "body"),
    [
        (
            create_calibration_session,
            CreateCalibrationRequest(
                response_id=1,
                participant_token="wrong-token",
                screen_width=1440,
                screen_height=900,
            ),
        ),
        (
            record_gaze_batch,
            GazeBatchRequest(response_id=1, participant_token="wrong-token", data=[]),
        ),
        (
            record_click_batch,
            ClickBatchRequest(response_id=1, participant_token="wrong-token", data=[]),
        ),
    ],
)
async def test_tracking_endpoints_reject_wrong_participant_token(endpoint, body):
    response = SurveyResponse(
        id=1,
        survey_id=10,
        participant_token="right-token",
        assigned_group=1,
        status="in_progress",
        started_at=datetime.utcnow(),
    )
    db = TrackingDB(response)

    with pytest.raises(HTTPException) as exc_info:
        await endpoint(body, db)

    assert exc_info.value.status_code == 404
    assert db.added == []


class ResumeStartSurveyDB:
    """Mock DB that returns a survey on the first execute, a configurable
    response on the second (resume lookup by participant_token), and a
    configurable calibration session on the third (only reached on resume hit).
    """

    def __init__(
        self,
        survey: Survey,
        existing_response: SurveyResponse | None,
        existing_calibration: CalibrationSession | None = None,
    ):
        self.survey = survey
        self.existing_response = existing_response
        self.existing_calibration = existing_calibration
        self.execute_count = 0
        self.added = []
        self.deleted = []
        self.flushed = False

    async def execute(self, _statement):
        self.execute_count += 1
        if self.execute_count == 1:
            return ScalarResult(self.survey)
        if self.execute_count == 2:
            return ScalarResult(self.existing_response)
        return ScalarResult(self.existing_calibration)

    def add(self, item):
        self.added.append(item)

    async def delete(self, item):
        self.deleted.append(item)

    async def flush(self):
        self.flushed = True
        for item in self.added:
            if isinstance(item, SurveyResponse):
                item.id = 999
                item.participant_token = "fresh-token"

    async def refresh(self, _item):
        return None


@pytest.mark.asyncio
async def test_start_survey_resumes_existing_in_progress_response(monkeypatch):
    """Token matches an in_progress response for this survey → reuse, don't create."""
    monkeypatch.setattr(surveys.random, "randint", lambda _start, _end: 99)
    existing = SurveyResponse(
        id=42,
        survey_id=10,
        assigned_group=2,
        participant_token="resume-token",
        status="in_progress",
        language="zh",
        started_at=datetime.utcnow(),
    )
    db = ResumeStartSurveyDB(make_survey([make_post(1, order=1)]), existing)

    response = await start_survey(
        "share-code",
        StartSurveyRequest(participant_token="resume-token"),
        db,
    )

    assert response.response_id == 42
    assert response.participant_token == "resume-token"
    assert response.assigned_group == 2  # group preserved, NOT re-randomized
    assert response.language == "zh"
    assert response.calibration_completed is False  # no prior calibration
    assert db.added == []  # no new SurveyResponse inserted
    assert db.flushed is False
    assert db.deleted == []


@pytest.mark.asyncio
async def test_start_survey_resume_signals_completed_calibration(monkeypatch):
    """Token hits, prior CalibrationSession is completed → flag set, session kept."""
    monkeypatch.setattr(surveys.random, "randint", lambda _start, _end: 99)
    existing = SurveyResponse(
        id=42,
        survey_id=10,
        assigned_group=2,
        participant_token="resume-token",
        status="in_progress",
        language="en",
        started_at=datetime.utcnow(),
    )
    completed_calib = CalibrationSession(
        id=7,
        response_id=42,
        status="completed",
        screen_width=1440,
        screen_height=900,
        expected_points=5,
        started_at=datetime.utcnow(),
    )
    db = ResumeStartSurveyDB(
        make_survey([make_post(1, order=1)]), existing, completed_calib
    )

    response = await start_survey(
        "share-code",
        StartSurveyRequest(participant_token="resume-token"),
        db,
    )

    assert response.calibration_completed is True
    assert db.deleted == []  # completed session preserved


@pytest.mark.asyncio
async def test_start_survey_resume_drops_in_progress_calibration(monkeypatch):
    """Token hits, prior CalibrationSession is mid-way → drop it for a clean restart."""
    monkeypatch.setattr(surveys.random, "randint", lambda _start, _end: 99)
    existing = SurveyResponse(
        id=42,
        survey_id=10,
        assigned_group=2,
        participant_token="resume-token",
        status="in_progress",
        language="en",
        started_at=datetime.utcnow(),
    )
    abandoned_calib = CalibrationSession(
        id=8,
        response_id=42,
        status="in_progress",
        screen_width=1440,
        screen_height=900,
        expected_points=5,
        started_at=datetime.utcnow(),
    )
    db = ResumeStartSurveyDB(
        make_survey([make_post(1, order=1)]), existing, abandoned_calib
    )

    response = await start_survey(
        "share-code",
        StartSurveyRequest(participant_token="resume-token"),
        db,
    )

    assert response.calibration_completed is False
    assert db.deleted == [abandoned_calib]
    assert db.flushed is True  # delete was flushed


@pytest.mark.asyncio
async def test_start_survey_ignores_token_from_different_survey(monkeypatch):
    """Token does not match any response under THIS survey_id → create new."""
    monkeypatch.setattr(surveys.random, "randint", lambda _start, _end: 1)
    db = ResumeStartSurveyDB(make_survey([make_post(1, order=1)]), None)

    response = await start_survey(
        "share-code",
        StartSurveyRequest(participant_token="someone-elses-token"),
        db,
    )

    assert response.response_id == 999  # created fresh via mock
    assert response.participant_token == "fresh-token"
    assert response.assigned_group == 1
    assert len(db.added) == 1
    assert isinstance(db.added[0], SurveyResponse)


@pytest.mark.asyncio
async def test_start_survey_ignores_completed_response_token(monkeypatch):
    """Token matches a row but status != in_progress → create new (no resume)."""
    monkeypatch.setattr(surveys.random, "randint", lambda _start, _end: 1)
    # The router filters by status == "in_progress" in the WHERE clause, so a
    # completed row will not match the SELECT and we get None back.
    db = ResumeStartSurveyDB(make_survey([make_post(1, order=1)]), None)

    response = await start_survey(
        "share-code",
        StartSurveyRequest(participant_token="stale-token"),
        db,
    )

    assert response.response_id == 999
    assert len(db.added) == 1


@pytest.mark.asyncio
async def test_start_survey_without_token_creates_new_response(monkeypatch):
    """No token provided → skip resume lookup entirely, single execute call."""
    monkeypatch.setattr(surveys.random, "randint", lambda _start, _end: 1)
    db = ResumeStartSurveyDB(make_survey([make_post(1, order=1)]), None)

    await start_survey("share-code", StartSurveyRequest(), db)

    assert db.execute_count == 1  # only the survey lookup, no resume SELECT
    assert len(db.added) == 1
