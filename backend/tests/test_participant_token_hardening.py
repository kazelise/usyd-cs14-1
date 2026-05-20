"""Regression tests: every public participant endpoint must validate the session token.

Prior review found that only the tracking endpoints validated `participant_token`,
while interact/like/comment/state/complete and the question-response endpoints
relied on `response_id` alone. These tests pin down the new contract:

- Missing/empty token → request schema validation rejects the call.
- Wrong token → 404 (we don't disclose response existence).
- Correct token → call succeeds.
"""

from datetime import datetime

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.models.participant import (
    ParticipantComment,
    ParticipantInteraction,
    ParticipantLike,
    SurveyResponse,
)
from app.models.researcher import Researcher
from app.routers.surveys import (
    CompleteResponseRequest,
    ParticipantCommentIn,
    ParticipantCommentPatch,
    ToggleLikeRequest,
    complete_response,
    create_participant_comment,
    delete_participant_comment,
    get_response_state,
    list_question_responses,
    record_interaction,
    submit_question_response,
    toggle_like,
    update_participant_comment,
)
from app.schemas.survey import InteractionRequest, SubmitQuestionResponseRequest

NOW = datetime(2026, 5, 15, 12, 0, 0)


# ── Test doubles ──────────────────────────────────────


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


def make_response(token: str = "right-token", status: str = "in_progress") -> SurveyResponse:
    return SurveyResponse(
        id=10,
        survey_id=1,
        participant_token=token,
        assigned_group=1,
        status=status,
        started_at=NOW,
    )


class SequenceDB:
    """Replays a queue of `execute()` results in order."""

    def __init__(self, results):
        self.results = list(results)
        self.execute_count = 0
        self.added = []
        self.deleted = []
        self.flushed = False
        self.committed = False

    async def execute(self, _statement):
        self.execute_count += 1
        if not self.results:
            raise AssertionError("Unexpected database query")
        return self.results.pop(0)

    def add(self, item):
        self.added.append(item)

    async def delete(self, item):
        self.deleted.append(item)

    async def flush(self):
        self.flushed = True
        for item in self.added:
            if isinstance(item, ParticipantInteraction) and item.id is None:
                item.id = 999
                item.timestamp = NOW
            if isinstance(item, ParticipantComment) and item.id is None:
                item.id = 555
                item.created_at = NOW

    async def commit(self):
        self.committed = True

    async def refresh(self, _item):
        return None


# ── Schema-level: missing/empty tokens are 422 at parse time ──────────


@pytest.mark.parametrize(
    "model, kwargs",
    [
        (InteractionRequest, {"post_id": 99, "action_type": "like"}),
        (ToggleLikeRequest, {"post_id": 99}),
        (ParticipantCommentIn, {"post_id": 99, "text": "hi"}),
        (ParticipantCommentPatch, {"text": "hi"}),
        (CompleteResponseRequest, {}),
        (SubmitQuestionResponseRequest, {"question_id": 5}),
    ],
)
def test_schema_requires_participant_token(model, kwargs):
    with pytest.raises(ValidationError):
        model(**kwargs)
    with pytest.raises(ValidationError):
        model(participant_token="", **kwargs)


# ── Endpoint-level: wrong token → 404 ─────────────────


@pytest.mark.asyncio
async def test_record_interaction_rejects_wrong_token():
    db = SequenceDB([ScalarOneResult(make_response(token="right-token"))])

    with pytest.raises(HTTPException) as exc_info:
        await record_interaction(
            10,
            InteractionRequest(post_id=99, action_type="like", participant_token="wrong-token"),
            db,
        )

    assert exc_info.value.status_code == 404
    assert db.added == []
    assert db.flushed is False


@pytest.mark.asyncio
async def test_toggle_like_rejects_wrong_token():
    db = SequenceDB([ScalarOneResult(make_response(token="right-token"))])

    with pytest.raises(HTTPException) as exc_info:
        await toggle_like(10, ToggleLikeRequest(post_id=99, participant_token="wrong-token"), db)

    assert exc_info.value.status_code == 404
    assert db.added == []


@pytest.mark.asyncio
async def test_get_response_state_rejects_wrong_token():
    db = SequenceDB([ScalarOneResult(make_response(token="right-token"))])

    with pytest.raises(HTTPException) as exc_info:
        await get_response_state(10, x_participant_token="wrong-token", db=db)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_complete_response_rejects_wrong_token():
    db = SequenceDB([ScalarOneResult(make_response(token="right-token"))])

    with pytest.raises(HTTPException) as exc_info:
        await complete_response(10, CompleteResponseRequest(participant_token="wrong-token"), db)

    assert exc_info.value.status_code == 404
    assert db.committed is False


@pytest.mark.asyncio
async def test_create_participant_comment_rejects_wrong_token():
    db = SequenceDB([ScalarOneResult(make_response(token="right-token"))])

    with pytest.raises(HTTPException) as exc_info:
        await create_participant_comment(
            10,
            ParticipantCommentIn(post_id=99, text="hi", participant_token="wrong-token"),
            db,
        )

    assert exc_info.value.status_code == 404
    assert db.added == []


@pytest.mark.asyncio
async def test_update_participant_comment_rejects_wrong_token():
    db = SequenceDB([ScalarOneResult(make_response(token="right-token"))])

    with pytest.raises(HTTPException) as exc_info:
        await update_participant_comment(
            10,
            555,
            ParticipantCommentPatch(text="edit", participant_token="wrong-token"),
            db,
        )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_participant_comment_rejects_wrong_token():
    db = SequenceDB([ScalarOneResult(make_response(token="right-token"))])

    with pytest.raises(HTTPException) as exc_info:
        await delete_participant_comment(10, 555, x_participant_token="wrong-token", db=db)

    assert exc_info.value.status_code == 404
    assert db.deleted == []


# ── Endpoint-level: correct token → succeeds ──────────


@pytest.mark.asyncio
async def test_record_interaction_accepts_correct_token():
    db = SequenceDB(
        [
            ScalarOneResult(make_response(token="right-token")),
            ScalarOneResult(99),  # ensure_post_belongs_to_survey
        ]
    )

    interaction = await record_interaction(
        10,
        InteractionRequest(post_id=99, action_type="like", participant_token="right-token"),
        db,
    )

    assert db.flushed is True
    assert interaction is not None
    assert db.added == [interaction]


@pytest.mark.asyncio
async def test_toggle_like_accepts_correct_token_and_creates_like():
    db = SequenceDB(
        [
            ScalarOneResult(make_response(token="right-token")),
            ScalarOneResult(99),
            ScalarOneResult(None),  # no existing like
        ]
    )

    result = await toggle_like(
        10, ToggleLikeRequest(post_id=99, participant_token="right-token"), db
    )

    assert result == {"liked": True}
    assert any(isinstance(item, ParticipantLike) for item in db.added)
    assert any(
        isinstance(item, ParticipantInteraction) and item.action_type == "like" for item in db.added
    )


@pytest.mark.asyncio
async def test_get_response_state_accepts_correct_token():
    db = SequenceDB(
        [
            ScalarOneResult(make_response(token="right-token", status="completed")),
            ScalarListResult([42]),  # liked_post_ids
            ScalarListResult([]),  # comments
        ]
    )

    state = await get_response_state(10, x_participant_token="right-token", db=db)

    assert state.liked_post_ids == [42]
    assert state.comments_by_post == {}


# ── Endpoint-level: status enforcement ─────────────────


@pytest.mark.asyncio
async def test_record_interaction_rejects_completed_response():
    db = SequenceDB([ScalarOneResult(make_response(status="completed"))])

    with pytest.raises(HTTPException) as exc_info:
        await record_interaction(
            10,
            InteractionRequest(post_id=99, action_type="like", participant_token="right-token"),
            db,
        )

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_get_response_state_allows_completed_response():
    """State retrieval is read-only and may be needed after completion."""
    db = SequenceDB(
        [
            ScalarOneResult(make_response(status="completed")),
            ScalarListResult([]),
            ScalarListResult([]),
        ]
    )

    state = await get_response_state(10, x_participant_token="right-token", db=db)

    assert state.liked_post_ids == []


# ── submit_question_response ───────────────────────────


class SubmitQuestionResponseDB:
    """Mimics the ad-hoc db.get/db.execute pattern of submit_question_response."""

    def __init__(self, response: SurveyResponse | None, question=None, existing_answer=None):
        self.response = response
        self.question = question
        self.existing_answer = existing_answer
        self.added = []
        self.committed = False

    async def get(self, model, _id):
        if model.__name__ == "SurveyResponse":
            return self.response
        return self.question

    async def execute(self, _statement):
        return ScalarOneResult(self.existing_answer)

    def add(self, item):
        self.added.append(item)

    async def commit(self):
        self.committed = True

    async def refresh(self, _item):
        return None


@pytest.mark.asyncio
async def test_submit_question_response_rejects_wrong_token():
    db = SubmitQuestionResponseDB(response=make_response(token="right-token"))

    with pytest.raises(HTTPException) as exc_info:
        await submit_question_response(
            10,
            5,
            SubmitQuestionResponseRequest(
                question_id=5, participant_token="wrong-token", answer_text="x"
            ),
            db,
        )

    assert exc_info.value.status_code == 404
    assert db.added == []
    assert db.committed is False


@pytest.mark.asyncio
async def test_submit_question_response_rejects_missing_response():
    db = SubmitQuestionResponseDB(response=None)

    with pytest.raises(HTTPException) as exc_info:
        await submit_question_response(
            10,
            5,
            SubmitQuestionResponseRequest(
                question_id=5, participant_token="any-token", answer_text="x"
            ),
            db,
        )

    assert exc_info.value.status_code == 404


# ── list_question_responses: researcher ownership ──────


def make_researcher(researcher_id: int = 7) -> Researcher:
    return Researcher(
        id=researcher_id,
        email="owner@example.com",
        password_hash="hash",
        name="Owner",
        created_at=NOW,
    )


@pytest.mark.asyncio
async def test_list_question_responses_rejects_non_owner():
    db = SequenceDB([ScalarOneResult(None)])  # ownership query returns no row

    with pytest.raises(HTTPException) as exc_info:
        await list_question_responses(10, db, make_researcher())

    assert exc_info.value.status_code == 404
    # We must not fall through to fetch the answers when ownership fails.
    assert db.execute_count == 1


@pytest.mark.asyncio
async def test_list_question_responses_returns_answers_for_owner():
    db = SequenceDB(
        [
            ScalarOneResult(10),  # ownership query: response.id matched
            ScalarListResult([]),  # answers query
        ]
    )

    result = await list_question_responses(10, db, make_researcher())

    assert result == []
    assert db.execute_count == 2
