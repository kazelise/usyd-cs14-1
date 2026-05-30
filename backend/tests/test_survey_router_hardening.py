"""Regression tests for survey router authorization and URL fetching hardening."""

from datetime import datetime

import httpx
import pytest
from bs4 import BeautifulSoup
from fastapi import HTTPException
from pydantic import ValidationError

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
from app.services.og_fetcher import (
    _clean_image_url,
    _extract_image_url,
    _safe_get,
    fetch_og_metadata,
)


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


@pytest.mark.asyncio
async def test_og_fetcher_survives_hostile_no_proxy(monkeypatch):
    """A bare IPv6 CIDR in NO_PROXY must not break AsyncClient construction.

    Regression for issue #58: OrbStack injects NO_PROXY entries like
    `fd07:b51a:cc66:f0::/64`, which httpx's URLPattern parses as host:port and
    rejects with InvalidURL. We pass trust_env=False so process-level proxy
    env vars are ignored entirely.
    """
    monkeypatch.setenv(
        "NO_PROXY",
        "localhost,127.0.0.1,fd07:b51a:cc66:f0::/64,*.orb.internal",
    )
    monkeypatch.setenv("no_proxy", "fd07:b51a:cc66:f0::/64")

    call_count = {"n": 0}

    async def fake_safe_get(client, url, headers):
        call_count["n"] += 1
        return None

    async def fake_is_fetchable(url):
        return True

    monkeypatch.setattr("app.services.og_fetcher._safe_get", fake_safe_get)
    monkeypatch.setattr("app.services.og_fetcher._is_fetchable_url", fake_is_fetchable)

    metadata = await fetch_og_metadata("https://example.com")

    # If trust_env were True (the bug), AsyncClient construction would raise
    # httpx.InvalidURL BEFORE the body runs and _safe_get would never be
    # called. With trust_env=False, construction succeeds and _safe_get fires.
    assert call_count["n"] == 1
    assert metadata.source == "example.com"


def test_clean_image_url_resolves_and_rejects():
    base = "https://example.com/article/page.html"
    # Relative paths resolve against the final URL.
    assert _clean_image_url("/hero.jpg", base) == "https://example.com/hero.jpg"
    assert _clean_image_url("img/local.png", base) == "https://example.com/article/img/local.png"
    # Protocol-relative URLs adopt the base scheme.
    assert _clean_image_url("//cdn.example.com/x.jpg", base) == "https://cdn.example.com/x.jpg"
    # Already-absolute http(s) URLs pass through.
    assert _clean_image_url("https://other.com/y.png", base) == "https://other.com/y.png"
    # Non-http(s) schemes are rejected so we can't accidentally render data: URIs.
    assert _clean_image_url("data:image/png;base64,AAAA", base) is None
    assert _clean_image_url("javascript:alert(1)", base) is None
    # Empty / None inputs are rejected.
    assert _clean_image_url(None, base) is None
    assert _clean_image_url("   ", base) is None


def test_extract_image_url_prefers_og_then_twitter_then_img_then_favicon():
    base = "https://news.example/article"

    # 1. og:image wins outright.
    soup = BeautifulSoup(
        '<html><head><meta property="og:image" content="/og.jpg">'
        '<meta name="twitter:image" content="/tw.jpg">'
        '</head><body><img src="/inline.png" width="600" height="400"></body></html>',
        "html.parser",
    )
    assert _extract_image_url(soup, base) == "https://news.example/og.jpg"

    # 2. With no og:image, twitter:image is next.
    soup = BeautifulSoup(
        '<html><head><meta name="twitter:image" content="/tw.jpg"></head>'
        '<body><img src="/inline.png" width="600" height="400"></body></html>',
        "html.parser",
    )
    assert _extract_image_url(soup, base) == "https://news.example/tw.jpg"

    # 3. With no card metadata, fall through to first sane inline <img>;
    # skip the 1x1 tracking pixel that comes first.
    soup = BeautifulSoup(
        "<html><head></head><body>"
        '<img src="/track.gif" width="1" height="1">'
        '<img src="/hero.jpg" width="800" height="450">'
        "</body></html>",
        "html.parser",
    )
    assert _extract_image_url(soup, base) == "https://news.example/hero.jpg"

    # 4. Truly bare page falls back to /favicon.ico at site root.
    soup = BeautifulSoup("<html><body>Hello</body></html>", "html.parser")
    assert _extract_image_url(soup, base) == "https://news.example/favicon.ico"
