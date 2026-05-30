"""Regression tests for survey router authorization and URL fetching hardening."""

from datetime import datetime

import httpx
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.models.participant import ParticipantLike, SurveyResponse
from app.models.researcher import Researcher
from app.models.survey import Survey
from app.routers.surveys import (
    CompleteResponseRequest,
    ParticipantCommentIn,
    ParticipantCommentPatch,
    ToggleLikeRequest,
    add_comment,
    complete_response,
    create_participant_comment,
    delete_participant_comment,
    delete_post,
    get_response_state,
    list_question_responses,
    record_interaction,
    submit_question_response,
    toggle_like,
    update_participant_comment,
    update_post,
)
from app.schemas.survey import (
    CommentIn,
    InteractionRequest,
    SubmitQuestionResponseRequest,
    UpdatePostRequest,
)
from app.services.og_fetcher import _safe_get, fetch_og_metadata


class ScalarOneResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class SequenceDB:
    def __init__(self, results):
        self.results = list(results)
        self.execute_count = 0
        self.added = []
        self.deleted = []
        self.flushed = False
        self.refreshed = []

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

    async def refresh(self, item):
        self.refreshed.append(item)


def make_researcher() -> Researcher:
    return Researcher(
        id=7,
        email="owner@example.com",
        password_hash="hash",
        name="Owner",
        created_at=datetime(2026, 5, 15, 12, 0, 0),
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("endpoint", "args"),
    [
        (update_post, (10, 99, UpdatePostRequest(display_title="Changed"))),
        (delete_post, (10, 99)),
        (
            add_comment,
            (10, 99, CommentIn(author_name="Researcher", text="Fake baseline comment")),
        ),
    ],
)
async def test_post_mutation_endpoints_require_survey_ownership(endpoint, args):
    db = SequenceDB([ScalarOneResult(None)])

    with pytest.raises(HTTPException) as exc_info:
        await endpoint(*args, make_researcher(), db)

    assert exc_info.value.status_code == 404
    assert db.execute_count == 1
    assert db.added == []
    assert db.deleted == []
    assert db.flushed is False


@pytest.mark.asyncio
async def test_toggle_like_unlike_flushes_delete_and_interaction():
    existing_like = ParticipantLike(id=20, response_id=30, post_id=40)
    db = SequenceDB(
        [
            ScalarOneResult(
                SurveyResponse(
                    id=30,
                    survey_id=10,
                    participant_token="token",
                    assigned_group=1,
                    status="in_progress",
                    started_at=datetime(2026, 5, 15, 12, 0, 0),
                )
            ),
            ScalarOneResult(40),
            ScalarOneResult(existing_like),
        ]
    )

    result = await toggle_like(30, ToggleLikeRequest(post_id=40, participant_token="token"), db)

    assert result == {"liked": False}
    assert db.deleted == [existing_like]
    assert db.flushed is True
    assert len(db.added) == 1
    assert db.added[0].action_type == "unlike"


@pytest.mark.asyncio
async def test_participant_comment_rejects_cross_survey_post_id():
    db = SequenceDB(
        [
            ScalarOneResult(
                SurveyResponse(
                    id=30,
                    survey_id=10,
                    participant_token="token",
                    assigned_group=1,
                    status="in_progress",
                    started_at=datetime(2026, 5, 15, 12, 0, 0),
                )
            ),
            ScalarOneResult(None),
        ]
    )

    with pytest.raises(HTTPException) as exc_info:
        await create_participant_comment(
            30,
            ParticipantCommentIn(post_id=99, text="Nope", participant_token="token"),
            db,
        )

    assert exc_info.value.status_code == 422
    assert db.added == []
    assert db.flushed is False


def test_survey_response_relationship_cascades_from_survey():
    relationship = Survey.responses.property

    assert "delete-orphan" in relationship.cascade
    assert relationship.passive_deletes is True


def _make_in_progress_response(token: str = "right-token") -> SurveyResponse:
    return SurveyResponse(
        id=30,
        survey_id=10,
        participant_token=token,
        assigned_group=1,
        status="in_progress",
        started_at=datetime(2026, 5, 15, 12, 0, 0),
    )


# ── Participant-token enforcement on mutation endpoints ─────────────


def test_participant_request_schemas_require_token():
    """Schema-level guard: requests must carry participant_token."""
    with pytest.raises(ValidationError):
        InteractionRequest(post_id=1, action_type="like")
    with pytest.raises(ValidationError):
        ToggleLikeRequest(post_id=1)
    with pytest.raises(ValidationError):
        ParticipantCommentIn(post_id=1, text="hi")
    with pytest.raises(ValidationError):
        ParticipantCommentPatch(text="hi")
    with pytest.raises(ValidationError):
        CompleteResponseRequest()
    with pytest.raises(ValidationError):
        SubmitQuestionResponseRequest(question_id=1)


@pytest.mark.asyncio
async def test_record_interaction_rejects_wrong_token():
    db = SequenceDB([ScalarOneResult(_make_in_progress_response("right-token"))])

    with pytest.raises(HTTPException) as exc_info:
        await record_interaction(
            30,
            InteractionRequest(post_id=40, action_type="like", participant_token="wrong-token"),
            db,
        )

    assert exc_info.value.status_code == 404
    assert db.added == []


@pytest.mark.asyncio
async def test_toggle_like_rejects_wrong_token():
    db = SequenceDB([ScalarOneResult(_make_in_progress_response("right-token"))])

    with pytest.raises(HTTPException) as exc_info:
        await toggle_like(
            30,
            ToggleLikeRequest(post_id=40, participant_token="wrong-token"),
            db,
        )

    assert exc_info.value.status_code == 404
    assert db.added == []


@pytest.mark.asyncio
async def test_get_response_state_rejects_wrong_token():
    db = SequenceDB([ScalarOneResult(_make_in_progress_response("right-token"))])

    with pytest.raises(HTTPException) as exc_info:
        await get_response_state(30, x_participant_token="wrong-token", db=db)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_complete_response_rejects_wrong_token():
    db = SequenceDB([ScalarOneResult(_make_in_progress_response("right-token"))])

    with pytest.raises(HTTPException) as exc_info:
        await complete_response(30, CompleteResponseRequest(participant_token="wrong-token"), db)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_create_participant_comment_rejects_wrong_token():
    db = SequenceDB([ScalarOneResult(_make_in_progress_response("right-token"))])

    with pytest.raises(HTTPException) as exc_info:
        await create_participant_comment(
            30,
            ParticipantCommentIn(post_id=40, text="hi", participant_token="wrong-token"),
            db,
        )

    assert exc_info.value.status_code == 404
    assert db.added == []


@pytest.mark.asyncio
async def test_update_participant_comment_rejects_wrong_token():
    db = SequenceDB([ScalarOneResult(_make_in_progress_response("right-token"))])

    with pytest.raises(HTTPException) as exc_info:
        await update_participant_comment(
            30,
            5,
            ParticipantCommentPatch(text="edited", participant_token="wrong-token"),
            db,
        )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_participant_comment_rejects_wrong_token():
    db = SequenceDB([ScalarOneResult(_make_in_progress_response("right-token"))])

    with pytest.raises(HTTPException) as exc_info:
        await delete_participant_comment(30, 5, x_participant_token="wrong-token", db=db)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_submit_question_response_rejects_wrong_token():
    """Direct ORM lookup path (db.get) still requires a token match."""

    class GetDB:
        def __init__(self):
            self.added = []

        async def get(self, _model, _id):
            return _make_in_progress_response("right-token")

        def add(self, item):
            self.added.append(item)

        async def commit(self):
            pass

        async def refresh(self, _item):
            pass

    db = GetDB()
    with pytest.raises(HTTPException) as exc_info:
        await submit_question_response(
            30,
            51,
            SubmitQuestionResponseRequest(
                question_id=51, participant_token="wrong-token", answer_text="A"
            ),
            db,
        )

    assert exc_info.value.status_code == 404
    assert db.added == []


@pytest.mark.asyncio
async def test_list_question_responses_requires_researcher_ownership():
    """A researcher querying answers must own the survey behind the response."""
    # First DB query is the ownership join: returning None means "not yours."
    db = SequenceDB([ScalarOneResult(None)])

    with pytest.raises(HTTPException) as exc_info:
        await list_question_responses(30, db, make_researcher())

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_og_fetcher_rejects_private_targets_before_request(monkeypatch):
    async def fail_get(*_args, **_kwargs):
        raise AssertionError("private URL should not be fetched")

    monkeypatch.setattr(httpx.AsyncClient, "get", fail_get)

    metadata = await fetch_og_metadata("http://127.0.0.1:8000/admin")

    assert metadata.source == "127.0.0.1"
    assert metadata.title is None


class IntegrityErrorOnInsertDB(SequenceDB):
    """SequenceDB whose flush raises IntegrityError once, simulating a lost
    unique-constraint race between two concurrent inserts."""

    def __init__(self, results):
        super().__init__(results)
        self.rolled_back = False

    async def flush(self):
        self.flushed = True
        raise IntegrityError("INSERT", {}, Exception("duplicate key"))

    async def rollback(self):
        self.rolled_back = True


@pytest.mark.asyncio
async def test_toggle_like_treats_concurrent_insert_race_as_already_liked():
    """Two concurrent like taps both see no existing row; the second insert
    violates the (response_id, post_id) unique constraint. The endpoint should
    return liked=True rather than surfacing an unhandled 500."""
    db = IntegrityErrorOnInsertDB(
        [
            ScalarOneResult(_make_in_progress_response("token")),  # response lookup
            ScalarOneResult(40),  # ensure_post_belongs_to_survey
            ScalarOneResult(None),  # no existing like → take the insert branch
        ]
    )

    result = await toggle_like(30, ToggleLikeRequest(post_id=40, participant_token="token"), db)

    assert result == {"liked": True}
    assert db.rolled_back is True


class _async_ctx:
    """Minimal async context manager wrapping a fake httpx client."""

    def __init__(self, client):
        self._client = client

    async def __aenter__(self):
        return self._client

    async def __aexit__(self, *_exc):
        return False


@pytest.mark.asyncio
async def test_og_fetcher_rejects_non_http_image_scheme(monkeypatch):
    """A page advertising a javascript:/data: og:image must not have that value
    stored as the post image; relative paths are resolved against the page URL."""

    async def fake_is_fetchable(_url: str) -> bool:
        return True

    html = (
        '<html><head>'
        '<meta property="og:title" content="Story">'
        '<meta property="og:image" content="javascript:alert(1)">'
        '</head><body></body></html>'
    )

    class HtmlClient:
        async def get(self, url, **_kwargs):
            return httpx.Response(200, text=html, request=httpx.Request("GET", url))

    monkeypatch.setattr("app.services.og_fetcher._is_fetchable_url", fake_is_fetchable)
    monkeypatch.setattr(
        "app.services.og_fetcher.httpx.AsyncClient",
        lambda *a, **k: _async_ctx(HtmlClient()),
    )

    metadata = await fetch_og_metadata("https://example.com/story")

    assert metadata.title == "Story"
    assert metadata.image_url is None  # javascript: scheme rejected


@pytest.mark.asyncio
async def test_og_fetcher_resolves_relative_image_against_page_url(monkeypatch):
    async def fake_is_fetchable(_url: str) -> bool:
        return True

    html = (
        '<html><head>'
        '<meta property="og:image" content="/img/card.jpg">'
        '</head><body></body></html>'
    )

    class HtmlClient:
        async def get(self, url, **_kwargs):
            return httpx.Response(200, text=html, request=httpx.Request("GET", url))

    monkeypatch.setattr("app.services.og_fetcher._is_fetchable_url", fake_is_fetchable)
    monkeypatch.setattr(
        "app.services.og_fetcher.httpx.AsyncClient",
        lambda *a, **k: _async_ctx(HtmlClient()),
    )

    metadata = await fetch_og_metadata("https://example.com/news/story")

    assert metadata.image_url == "https://example.com/img/card.jpg"


@pytest.mark.asyncio
async def test_og_fetcher_validates_redirect_targets(monkeypatch):
    calls = []

    async def fake_is_fetchable(url: str) -> bool:
        return "169.254.169.254" not in url

    class RedirectClient:
        async def get(self, url, **_kwargs):
            calls.append(url)
            return httpx.Response(
                302,
                headers={"location": "http://169.254.169.254/latest/meta-data"},
                request=httpx.Request("GET", url),
            )

    monkeypatch.setattr("app.services.og_fetcher._is_fetchable_url", fake_is_fetchable)

    response = await _safe_get(RedirectClient(), "https://example.com/story", {})

    assert response is None
    assert calls == ["https://example.com/story"]
