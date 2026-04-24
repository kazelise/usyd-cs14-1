"""Phase 5 multilingual survey pipeline tests."""

import csv
from datetime import datetime
from io import StringIO

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.auth import get_current_researcher
from app.database import get_db
from app.main import app
from app.models.participant import SurveyResponse
from app.models.question import Question
from app.models.researcher import Researcher
from app.models.survey import PostComment, Survey, SurveyPost
from app.models.translation import PostTranslation, QuestionTranslation, SurveyTranslation
from app.routers import surveys
from app.routers.surveys import start_survey
from app.schemas.survey import StartSurveyRequest
from app.services.translation_service import (
    CSV_HEADERS,
    build_translation_export_payload,
    import_translation_payload,
    translation_payload_to_csv,
    validate_translation_import,
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
                item.id = 501
                item.participant_token = "phase5-token"

    async def refresh(self, _item):
        return None


class ImportDB:
    def __init__(self):
        self.added = []

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        return None


class TranslationEndpointDB(ImportDB):
    def __init__(self, survey: Survey):
        super().__init__()
        self.survey = survey

    async def execute(self, _statement):
        return ScalarResult(self.survey)


def make_translation_survey(*, with_translations: bool = False) -> Survey:
    now = datetime(2026, 4, 25, 9, 0, 0)
    survey = Survey(
        id=15,
        researcher_id=9,
        title="Trust Study",
        description="Read the posts and answer the questions.",
        status="published",
        share_code="phase5-share",
        num_groups=1,
        group_names=None,
        gaze_tracking_enabled=True,
        gaze_interval_ms=1000,
        click_tracking_enabled=True,
        calibration_enabled=False,
        calibration_points=5,
        created_at=now,
        updated_at=now,
    )
    post = SurveyPost(
        id=31,
        survey_id=15,
        order=1,
        original_url="https://example.com/story",
        fetched_title="Original headline",
        fetched_image_url=None,
        fetched_description="Original description",
        fetched_source="Example News",
        display_title="Displayed headline",
        display_image_url=None,
        display_likes=10,
        display_comments_count=2,
        display_shares=1,
        show_likes=True,
        show_comments=True,
        show_shares=True,
        visible_to_groups=None,
        group_overrides=None,
        created_at=now,
    )
    comment = PostComment(
        id=41,
        post_id=31,
        order=1,
        author_name="Researcher comment",
        author_avatar_url=None,
        text="This is a preview comment.",
        created_at=now,
    )
    question = Question(
        id=51,
        post_id=31,
        order=1,
        question_type="multiple_choice",
        text="How credible is this post?",
        config={"options": ["Credible", "Not credible"]},
        created_at=now,
    )
    post.comments = [comment]
    post.questions = [question]
    post.translations = []
    question.translations = []
    survey.posts = [post]
    survey.translations = []

    if with_translations:
        survey.translations = [
            SurveyTranslation(
                id=101,
                survey_id=15,
                language_code="zh",
                translated_fields={
                    "title": "信任研究",
                    "description": "阅读帖子并回答问题。",
                },
            )
        ]
        post.translations = [
            PostTranslation(
                id=102,
                survey_id=15,
                post_id=31,
                language_code="zh",
                translated_fields={
                    "display_title": "显示标题",
                    "fetched_description": "中文描述",
                    "fetched_source": "示例新闻",
                    "more_info_label": "更多信息",
                    "comments": {
                        "41": {
                            "author_name": "研究评论",
                            "text": "这是一条预览评论。",
                        }
                    },
                },
            )
        ]
        question.translations = [
            QuestionTranslation(
                id=103,
                survey_id=15,
                question_id=51,
                language_code="zh",
                translated_fields={
                    "text": "你认为这条帖子可信吗？",
                    "config": {"options": ["可信", "不可信"]},
                },
            )
        ]
    return survey


def filled_translation_entries(survey: Survey) -> dict[str, object]:
    payload = build_translation_export_payload(survey, language_code="zh")
    entries: dict[str, object] = {}
    for item in payload["items"]:
        key = item["key"]
        if item["field"] == "config":
            entries[key] = {"options": ["选项 A", "选项 B"]}
        else:
            entries[key] = f"zh:{key}"
    return entries


def install_translation_endpoint_overrides(db: TranslationEndpointDB):
    async def override_researcher():
        return Researcher(
            id=9,
            email="researcher@example.com",
            password_hash="hash",
            name="Researcher",
            created_at=datetime(2026, 4, 25, 9, 0, 0),
        )

    async def override_db():
        yield db

    app.dependency_overrides[get_current_researcher] = override_researcher
    app.dependency_overrides[get_db] = override_db


def clear_overrides():
    app.dependency_overrides.clear()


def test_export_translation_json_contains_all_translatable_fields():
    payload = build_translation_export_payload(make_translation_survey(), language_code="zh")
    keys = {item["key"] for item in payload["items"]}

    assert payload["survey_id"] == 15
    assert payload["language_code"] == "zh"
    assert {
        "survey.title",
        "survey.description",
        "post.31.display_title",
        "post.31.fetched_description",
        "post.31.fetched_source",
        "post.31.more_info_label",
        "post_comment.41.author_name",
        "post_comment.41.text",
        "question.51.text",
        "question.51.config",
    }.issubset(keys)


def test_export_translation_csv_has_stable_headers_and_rows():
    csv_text = translation_payload_to_csv(
        build_translation_export_payload(make_translation_survey(), language_code="zh")
    )
    reader = csv.DictReader(StringIO(csv_text))
    rows = list(reader)

    assert reader.fieldnames == CSV_HEADERS
    assert rows[0]["key"] == "survey.title"
    assert any(row["key"] == "question.51.config" for row in rows)


def test_translation_export_endpoint_returns_json_template():
    db = TranslationEndpointDB(make_translation_survey())
    install_translation_endpoint_overrides(db)
    try:
        client = TestClient(app)
        response = client.get("/api/v1/surveys/15/translations/export?format=json&language=zh")
    finally:
        clear_overrides()

    assert response.status_code == 200
    body = response.json()
    assert body["language_code"] == "zh"
    assert any(item["key"] == "post.31.more_info_label" for item in body["items"])


@pytest.mark.asyncio
async def test_import_translation_json_validates_and_upserts_rows():
    survey = make_translation_survey()
    payload = {"language_code": "zh", "translations": filled_translation_entries(survey)}

    result = await import_translation_payload(
        ImportDB(), survey, payload, payload_format="json"
    )

    assert result["language_code"] == "zh"
    assert result["translation_rows"] == 3
    assert survey.translations[0].translated_fields["title"] == "zh:survey.title"
    assert survey.posts[0].translations[0].translated_fields["comments"]["41"]["text"] == (
        "zh:post_comment.41.text"
    )
    assert survey.posts[0].questions[0].translations[0].translated_fields["config"] == {
        "options": ["选项 A", "选项 B"]
    }


def test_translation_import_endpoint_accepts_json_payload():
    survey = make_translation_survey()
    db = TranslationEndpointDB(survey)
    install_translation_endpoint_overrides(db)
    payload = {"language_code": "zh", "translations": filled_translation_entries(survey)}

    try:
        client = TestClient(app)
        response = client.post("/api/v1/surveys/15/translations/import?format=json", json=payload)
    finally:
        clear_overrides()

    assert response.status_code == 200
    assert response.json()["translation_rows"] == 3
    assert len(db.added) == 3


@pytest.mark.asyncio
async def test_import_translation_csv_validates_and_upserts_rows():
    survey = make_translation_survey()
    payload = build_translation_export_payload(survey, language_code="zh")
    entries = filled_translation_entries(survey)
    for item in payload["items"]:
        item["translation"] = entries[item["key"]]
    csv_text = translation_payload_to_csv(payload)

    result = await import_translation_payload(
        ImportDB(), survey, csv_text, payload_format="csv"
    )

    assert result["translation_rows"] == 3
    assert survey.posts[0].translations[0].translated_fields["more_info_label"] == (
        "zh:post.31.more_info_label"
    )


def test_import_translation_rejects_missing_and_invalid_keys():
    survey = make_translation_survey()
    entries = filled_translation_entries(survey)
    entries.pop("post.31.display_title")

    with pytest.raises(HTTPException):
        validate_translation_import(survey, language_code="zh", entries=entries)

    entries = filled_translation_entries(survey)
    entries["post.999.display_title"] = "bad id"
    with pytest.raises(HTTPException):
        validate_translation_import(survey, language_code="zh", entries=entries)


@pytest.mark.asyncio
async def test_start_survey_returns_translated_posts_questions_and_saves_language(monkeypatch):
    monkeypatch.setattr(surveys.random, "randint", lambda _start, _end: 1)
    survey = make_translation_survey(with_translations=True)
    db = StartSurveyDB(survey)

    response = await start_survey(
        "phase5-share", StartSurveyRequest(language="zh"), db
    )

    created_response = db.added[0]
    post = response.posts[0]
    assert response.language == "zh"
    assert created_response.language == "zh"
    assert post.display_title == "显示标题"
    assert post.fetched_description == "中文描述"
    assert post.fetched_source == "示例新闻"
    assert post.more_info_label == "更多信息"
    assert post.comments[0].author_name == "研究评论"
    assert post.comments[0].text == "这是一条预览评论。"
    assert post.questions[0].text == "你认为这条帖子可信吗？"
    assert post.questions[0].config == {"options": ["可信", "不可信"]}


@pytest.mark.asyncio
async def test_start_survey_missing_translation_falls_back_safely(monkeypatch):
    monkeypatch.setattr(surveys.random, "randint", lambda _start, _end: 1)
    survey = make_translation_survey()
    survey.posts[0].translations = [
        PostTranslation(
            survey_id=15,
            post_id=31,
            language_code="zh",
            translated_fields={"display_title": "只有标题"},
        )
    ]
    db = StartSurveyDB(survey)

    response = await start_survey(
        "phase5-share", StartSurveyRequest(language="zh"), db
    )

    post = response.posts[0]
    assert post.display_title == "只有标题"
    assert post.fetched_description == "Original description"
    assert "fetched_description" in post.translation_fallbacks
