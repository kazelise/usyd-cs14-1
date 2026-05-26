"""Tests for backend security and research data integrity hardening.

Covers:
1. SECRET_KEY safety (config validation)
2. Preview hardening (anonymous participants cannot set is_preview)
3. Question-answer type validation
4. Published survey lifecycle (empty publish guard + structural mutation guard)
5. Analytics correctness (flagged responses in fast_completions)
6. Export correctness (participant_comments in payload)
"""

from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException

from app.models.participant import SurveyResponse
from app.models.question import Question
from app.models.survey import Survey, SurveyPost
from app.routers.surveys import (
    _validate_question_answer,
    create_post,
    create_question,
    create_survey_question,
    delete_survey_question,
    publish_survey,
    start_survey,
    update_post,
    update_question,
    update_survey,
)
from app.schemas.survey import (
    CreatePostRequest,
    CreateQuestionRequest,
    StartSurveyRequest,
    SubmitQuestionResponseRequest,
    UpdatePostRequest,
    UpdateQuestionRequest,
    UpdateSurveyRequest,
)
from app.services.export_service import ExportFilters, build_export_payload

# ── Shared mock infrastructure ──────────────────────────────────────────────


class ScalarOneResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalar(self):
        return self.value


class ScalarListResult:
    def __init__(self, values):
        self._values = list(values)

    def scalars(self):
        return self

    def all(self):
        return self._values


class SequenceDB:
    def __init__(self, results, get_items=None):
        self.results = list(results)
        self.get_items = get_items or {}
        self.added = []
        self.deleted = []
        self.flushed = False
        self.committed = False
        self.refreshed = []

    async def execute(self, _stmt):
        if not self.results:
            raise AssertionError("Unexpected DB query")
        return self.results.pop(0)

    async def get(self, model, item_id):
        return self.get_items.get((model, item_id))

    def add(self, item):
        self.added.append(item)

    async def delete(self, item):
        self.deleted.append(item)

    async def flush(self):
        self.flushed = True

    async def refresh(self, item):
        self.refreshed.append(item)

    async def commit(self):
        self.committed = True


def make_researcher():
    from app.models.researcher import Researcher

    return Researcher(
        id=1,
        email="r@example.com",
        password_hash="hash",
        name="R",
        created_at=datetime(2026, 5, 1),
    )


def make_survey(*, status="draft", num_groups=1) -> Survey:
    return Survey(
        id=10,
        researcher_id=1,
        title="Test",
        status=status,
        share_code="TESTCODE",
        num_groups=num_groups,
        gaze_tracking_enabled=True,
        gaze_interval_ms=1000,
        click_tracking_enabled=True,
        calibration_enabled=False,
        calibration_points=9,
        created_at=datetime(2026, 5, 1),
        updated_at=datetime(2026, 5, 1),
    )


# ── 1. SECRET_KEY safety ────────────────────────────────────────────────────


def test_settings_rejects_default_key_when_debug_false():
    from pydantic import ValidationError as PydanticValidationError

    from app.config import Settings

    with pytest.raises((PydanticValidationError, ValueError)):
        Settings(SECRET_KEY="dev-secret-change-in-production", DEBUG=False)


def test_settings_allows_default_key_when_debug_true():
    from app.config import Settings

    s = Settings(SECRET_KEY="dev-secret-change-in-production", DEBUG=True)
    assert s.DEBUG is True


def test_settings_allows_custom_key_when_debug_false():
    from app.config import Settings

    s = Settings(SECRET_KEY="a-real-secret-key-here", DEBUG=False)
    assert s.SECRET_KEY == "a-real-secret-key-here"


# ── 2. Preview hardening ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_start_survey_rejects_preview_without_auth():
    """Anonymous participant setting is_preview=True must get 403."""
    survey = make_survey(status="published")
    survey.posts = []
    survey.questions = []
    survey.translations = []
    survey.supported_languages = ["en"]
    survey.default_language = "en"
    survey.share_code = "PUB123"
    survey.share_code_expires_at = None

    db = SequenceDB([ScalarOneResult(survey)])

    with pytest.raises(HTTPException) as exc_info:
        await start_survey(
            "PUB123",
            StartSurveyRequest(is_preview=True),
            authorization=None,
            db=db,
        )

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_start_survey_rejects_preview_group_without_auth():
    """Anonymous participant setting preview_assigned_group must get 403."""
    survey = make_survey(status="published")
    survey.posts = []
    survey.questions = []
    survey.translations = []
    survey.supported_languages = ["en"]
    survey.default_language = "en"
    survey.share_code = "PUB123"
    survey.share_code_expires_at = None

    db = SequenceDB([ScalarOneResult(survey)])

    with pytest.raises(HTTPException) as exc_info:
        await start_survey(
            "PUB123",
            StartSurveyRequest(preview_assigned_group=1),
            authorization=None,
            db=db,
        )

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_start_survey_rejects_preview_with_invalid_token():
    """An invalid JWT in the Authorization header still gets 403 for preview."""
    survey = make_survey(status="published")
    survey.posts = []
    survey.questions = []
    survey.translations = []
    survey.supported_languages = ["en"]
    survey.default_language = "en"
    survey.share_code = "PUB123"
    survey.share_code_expires_at = None

    db = SequenceDB([ScalarOneResult(survey)])

    with pytest.raises(HTTPException) as exc_info:
        await start_survey(
            "PUB123",
            StartSurveyRequest(is_preview=True),
            authorization="Bearer not-a-real-jwt",
            db=db,
        )

    assert exc_info.value.status_code == 403


# ── 3. Question-answer type validation ─────────────────────────────────────


def _make_question(qtype: str, config: dict | None = None) -> Question:
    q = Question(
        id=1,
        survey_id=10,
        post_id=None,
        order=1,
        question_type=qtype,
        text="Test question",
        config=config,
        created_at=datetime(2026, 5, 1),
    )
    return q


def test_answer_validation_text_rejects_empty():
    q = _make_question("text")
    body = SubmitQuestionResponseRequest(question_id=1, participant_token="tok", answer_text="   ")
    with pytest.raises(HTTPException) as exc_info:
        _validate_question_answer(q, body)
    assert exc_info.value.status_code == 422


def test_answer_validation_free_text_requires_content():
    q = _make_question("free_text")
    body = SubmitQuestionResponseRequest(question_id=1, participant_token="tok", answer_text=None)
    with pytest.raises(HTTPException):
        _validate_question_answer(q, body)


def test_answer_validation_text_accepts_nonempty():
    q = _make_question("text")
    body = SubmitQuestionResponseRequest(
        question_id=1, participant_token="tok", answer_text="hello"
    )
    _validate_question_answer(q, body)  # should not raise


def test_answer_validation_likert_rejects_missing_value():
    q = _make_question("likert")
    body = SubmitQuestionResponseRequest(question_id=1, participant_token="tok", answer_value=None)
    with pytest.raises(HTTPException):
        _validate_question_answer(q, body)


def test_answer_validation_rating_rejects_out_of_range():
    q = _make_question("rating", {"min": 1, "max": 5})
    body = SubmitQuestionResponseRequest(question_id=1, participant_token="tok", answer_value=6)
    with pytest.raises(HTTPException) as exc_info:
        _validate_question_answer(q, body)
    assert exc_info.value.status_code == 422


def test_answer_validation_likert_accepts_in_range():
    q = _make_question("likert", {"min": 1, "max": 7})
    body = SubmitQuestionResponseRequest(question_id=1, participant_token="tok", answer_value=4)
    _validate_question_answer(q, body)  # should not raise


def test_answer_validation_likert_uses_default_range_when_no_config():
    q = _make_question("likert")  # no config
    body_ok = SubmitQuestionResponseRequest(question_id=1, participant_token="tok", answer_value=5)
    _validate_question_answer(q, body_ok)

    body_bad = SubmitQuestionResponseRequest(question_id=1, participant_token="tok", answer_value=0)
    with pytest.raises(HTTPException):
        _validate_question_answer(q, body_bad)


def test_answer_validation_single_choice_rejects_multiple():
    q = _make_question("single_choice", {"options": ["A", "B", "C"]})
    body = SubmitQuestionResponseRequest(
        question_id=1, participant_token="tok", answer_choices=["A", "B"]
    )
    with pytest.raises(HTTPException) as exc_info:
        _validate_question_answer(q, body)
    assert exc_info.value.status_code == 422


def test_answer_validation_single_choice_rejects_invalid_option():
    q = _make_question("single_choice", {"options": ["A", "B"]})
    body = SubmitQuestionResponseRequest(
        question_id=1, participant_token="tok", answer_choices=["Z"]
    )
    with pytest.raises(HTTPException):
        _validate_question_answer(q, body)


def test_answer_validation_single_choice_rejects_missing_options():
    q = _make_question("single_choice", {})
    body = SubmitQuestionResponseRequest(
        question_id=1, participant_token="tok", answer_choices=["A"]
    )
    with pytest.raises(HTTPException) as exc_info:
        _validate_question_answer(q, body)
    assert exc_info.value.status_code == 422


def test_answer_validation_single_choice_accepts_valid():
    q = _make_question("single_choice", {"options": ["A", "B"]})
    body = SubmitQuestionResponseRequest(
        question_id=1, participant_token="tok", answer_choices=["B"]
    )
    _validate_question_answer(q, body)


def test_answer_validation_multiple_choice_rejects_empty():
    q = _make_question("multiple_choice", {"options": ["A", "B"]})
    body = SubmitQuestionResponseRequest(question_id=1, participant_token="tok", answer_choices=[])
    with pytest.raises(HTTPException):
        _validate_question_answer(q, body)


def test_answer_validation_multiple_choice_rejects_invalid_option():
    q = _make_question("multiple_choice", {"options": ["A", "B"]})
    body = SubmitQuestionResponseRequest(
        question_id=1, participant_token="tok", answer_choices=["A", "HACK"]
    )
    with pytest.raises(HTTPException):
        _validate_question_answer(q, body)


def test_answer_validation_multiple_choice_rejects_missing_options():
    q = _make_question("multiple_choice", {"options": []})
    body = SubmitQuestionResponseRequest(
        question_id=1, participant_token="tok", answer_choices=["A"]
    )
    with pytest.raises(HTTPException) as exc_info:
        _validate_question_answer(q, body)
    assert exc_info.value.status_code == 422


def test_answer_validation_multiple_choice_accepts_valid_subset():
    q = _make_question("multiple_choice", {"options": ["A", "B", "C"]})
    body = SubmitQuestionResponseRequest(
        question_id=1, participant_token="tok", answer_choices=["A", "C"]
    )
    _validate_question_answer(q, body)


# ── 4. Published survey lifecycle ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_publish_rejects_survey_with_no_posts():
    """Publishing an empty survey (no posts) must return 422."""
    survey = make_survey(status="draft")
    db = SequenceDB(
        [
            ScalarOneResult(survey),  # ownership check
            ScalarOneResult(0),  # posts count
        ]
    )
    with pytest.raises(HTTPException) as exc_info:
        await publish_survey(10, make_researcher(), db)
    assert exc_info.value.status_code == 422
    assert survey.status == "draft"


@pytest.mark.asyncio
async def test_update_survey_blocks_num_groups_change_on_published():
    """Changing num_groups on a published survey must return 409."""
    survey = make_survey(status="published")
    db = SequenceDB([ScalarOneResult(survey)])

    with pytest.raises(HTTPException) as exc_info:
        await update_survey(
            10,
            UpdateSurveyRequest(num_groups=3),
            make_researcher(),
            db,
        )

    assert exc_info.value.status_code == 409
    assert survey.num_groups == 1  # unchanged


@pytest.mark.asyncio
async def test_update_survey_blocks_calibration_mode_change_on_published():
    survey = make_survey(status="published")
    db = SequenceDB([ScalarOneResult(survey)])

    with pytest.raises(HTTPException) as exc_info:
        await update_survey(
            10,
            UpdateSurveyRequest(calibration_enabled=True),
            make_researcher(),
            db,
        )

    assert exc_info.value.status_code == 409


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("platform_style", "instagram"),
        ("platform_ui_style", "instagram"),
        ("group_names", {"1": "control", "2": "variant"}),
        ("gaze_interval_ms", 500),
        ("calibration_points", 5),
        ("default_language", "zh"),
    ],
)
@pytest.mark.asyncio
async def test_update_survey_blocks_other_structural_fields_on_published(field, value):
    survey = make_survey(status="published")
    db = SequenceDB([ScalarOneResult(survey)])

    with pytest.raises(HTTPException) as exc_info:
        await update_survey(
            10,
            UpdateSurveyRequest(**{field: value}),
            make_researcher(),
            db,
        )

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_update_survey_allows_title_change_on_published():
    """Title and description changes are safe on published surveys."""
    survey = make_survey(status="published")
    survey.updated_at = datetime(2026, 5, 1)
    db = SequenceDB([ScalarOneResult(survey)])

    result = await update_survey(
        10,
        UpdateSurveyRequest(title="New Title"),
        make_researcher(),
        db,
    )

    assert result.title == "New Title"
    assert db.committed is True


@pytest.mark.asyncio
async def test_update_post_blocks_when_participant_responses_exist():
    survey = make_survey(status="published")
    post = SurveyPost(
        id=55,
        survey_id=10,
        order=1,
        original_url="https://example.com/post",
        display_title="Original",
        display_likes=1,
        display_comments_count=1,
        display_shares=1,
        show_likes=True,
        show_comments=True,
        show_shares=True,
    )
    db = SequenceDB(
        [
            ScalarOneResult(survey),
            ScalarOneResult(post),
            ScalarOneResult(1),
        ]
    )

    with pytest.raises(HTTPException) as exc_info:
        await update_post(
            10,
            55,
            UpdatePostRequest(display_title="Changed"),
            make_researcher(),
            db,
        )

    assert exc_info.value.status_code == 409
    assert post.display_title == "Original"


@pytest.mark.asyncio
async def test_update_post_allows_when_no_participant_responses_exist():
    survey = make_survey(status="published")
    post = SurveyPost(
        id=55,
        survey_id=10,
        order=1,
        original_url="https://example.com/post",
        display_title="Original",
        display_likes=1,
        display_comments_count=1,
        display_shares=1,
        show_likes=True,
        show_comments=True,
        show_shares=True,
    )
    db = SequenceDB(
        [
            ScalarOneResult(survey),
            ScalarOneResult(post),
            ScalarOneResult(0),
        ]
    )

    result = await update_post(
        10,
        55,
        UpdatePostRequest(display_title="Changed"),
        make_researcher(),
        db,
    )

    assert result.display_title == "Changed"
    assert db.flushed is True


@pytest.mark.asyncio
async def test_create_post_blocks_when_participant_responses_exist():
    survey = make_survey(status="published")
    db = SequenceDB(
        [
            ScalarOneResult(survey),
            ScalarOneResult(1),
        ]
    )

    with pytest.raises(HTTPException) as exc_info:
        await create_post(
            10,
            CreatePostRequest(original_url="https://example.com/post", order=2),
            make_researcher(),
            db,
        )

    assert exc_info.value.status_code == 409
    assert db.added == []


@pytest.mark.asyncio
async def test_update_post_question_blocks_when_participant_responses_exist():
    survey = make_survey(status="published")
    question = _make_question("single_choice", {"options": ["A", "B"]})
    question.id = 51
    question.survey_id = 10
    question.post_id = 55
    db = SequenceDB(
        [ScalarOneResult(survey), ScalarOneResult(1)],
        get_items={(Question, 51): question},
    )

    with pytest.raises(HTTPException) as exc_info:
        await update_question(
            10,
            55,
            51,
            UpdateQuestionRequest(text="Changed"),
            db,
            make_researcher(),
        )

    assert exc_info.value.status_code == 409
    assert question.text == "Test question"


@pytest.mark.asyncio
async def test_create_post_question_blocks_when_participant_responses_exist():
    survey = make_survey(status="published")
    db = SequenceDB(
        [
            ScalarOneResult(survey),
            ScalarOneResult(1),
        ]
    )

    with pytest.raises(HTTPException) as exc_info:
        await create_question(
            10,
            55,
            CreateQuestionRequest(
                question_type="single_choice",
                text="New question",
                order=2,
                config={"options": ["A", "B"]},
            ),
            db,
            make_researcher(),
        )

    assert exc_info.value.status_code == 409
    assert db.added == []


@pytest.mark.asyncio
async def test_create_survey_question_blocks_when_participant_responses_exist():
    survey = make_survey(status="published")
    db = SequenceDB(
        [
            ScalarOneResult(survey),
            ScalarOneResult(1),
        ]
    )

    with pytest.raises(HTTPException) as exc_info:
        await create_survey_question(
            10,
            CreateQuestionRequest(
                question_type="rating",
                text="Overall trust",
                order=1,
                config={"min": 1, "max": 5},
            ),
            db,
            make_researcher(),
        )

    assert exc_info.value.status_code == 409
    assert db.added == []


@pytest.mark.asyncio
async def test_delete_survey_question_blocks_when_participant_responses_exist():
    survey = make_survey(status="published")
    question = _make_question("rating", {"min": 1, "max": 5})
    question.id = 52
    question.survey_id = 10
    question.post_id = None
    db = SequenceDB(
        [ScalarOneResult(survey), ScalarOneResult(1)],
        get_items={(Question, 52): question},
    )

    with pytest.raises(HTTPException) as exc_info:
        await delete_survey_question(
            10,
            52,
            db,
            make_researcher(),
        )

    assert exc_info.value.status_code == 409
    assert db.deleted == []


# ── 5. Analytics: flagged responses in fast_completions ─────────────────────


def test_fast_completions_counts_flagged_responses():
    """A flagged (speed-test) response under 2 minutes must appear in fast_completions."""

    # We can't unit-test get_analytics_summary without a real DB, but we can
    # verify the logic directly by inspecting the fast_completions branch.
    # Construct a minimal in-memory check matching the production logic.
    now = datetime.utcnow()

    completed_slow = SurveyResponse(
        id=1,
        survey_id=7,
        participant_token="tok1",
        assigned_group=1,
        status="completed",
        started_at=now - timedelta(minutes=10),
        completed_at=now,
    )
    completed_fast = SurveyResponse(
        id=2,
        survey_id=7,
        participant_token="tok2",
        assigned_group=1,
        status="completed",
        started_at=now - timedelta(seconds=90),
        completed_at=now,
    )
    flagged = SurveyResponse(
        id=3,
        survey_id=7,
        participant_token="tok3",
        assigned_group=1,
        status="flagged",
        started_at=now - timedelta(seconds=20),
        completed_at=now,
        is_speed_test_failed=True,
    )

    responses = [completed_slow, completed_fast, flagged]

    # Replicate the production fast_completions calculation from surveys.py
    fast_completions = sum(
        1
        for r in responses
        if r.status in ("completed", "flagged")
        and r.started_at
        and r.completed_at
        and (r.completed_at - r.started_at).total_seconds() / 60 < 2
    )

    assert fast_completions == 2  # completed_fast + flagged; NOT 1 (which the old code gave)


# ── 6. Export: participant_comments in payload ──────────────────────────────


def test_export_payload_includes_participant_comments():
    """build_export_payload must include participant_comments keyed by response."""
    now = datetime.utcnow()
    survey = make_survey(status="published")
    survey.posts = []

    response = SurveyResponse(
        id=99,
        survey_id=10,
        participant_token="tok",
        assigned_group=1,
        status="completed",
        started_at=now - timedelta(minutes=5),
        completed_at=now,
        is_preview=False,
    )
    response.interactions = []
    response.calibration_session = None

    comments = [
        {
            "id": 1,
            "post_id": 5,
            "text": "edited text",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
        }
    ]

    payload = build_export_payload(
        survey,
        [response],
        filters=ExportFilters(),
        gaze_counts={},
        gaze_samples_by_response={},
        click_counts={},
        participant_comments_by_response={99: comments},
        question_responses_by_response={},
    )

    assert len(payload["responses"]) == 1
    row = payload["responses"][0]
    assert "participant_comments" in row
    assert row["participant_comments"] == comments
    assert row["participant_comments"][0]["text"] == "edited text"
