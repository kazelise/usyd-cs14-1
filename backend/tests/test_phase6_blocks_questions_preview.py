"""Phase 6 social-media blocks, question types, and preview tests."""

from datetime import datetime

import pytest

from app.models.participant import SurveyResponse
from app.models.question import Question
from app.models.question_response import QuestionResponse
from app.models.researcher import Researcher
from app.models.survey import Survey, SurveyPost
from app.routers import surveys
from app.routers.surveys import (
    create_question,
    preview_survey,
    start_survey,
    submit_question_response,
)
from app.schemas.survey import (
    CreateQuestionRequest,
    StartSurveyRequest,
    SubmitQuestionResponseRequest,
)


class ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class Phase6DB:
    def __init__(self, survey: Survey, response: SurveyResponse | None = None):
        self.survey = survey
        self.response = response
        self.added = []
        self.commits = 0

    async def execute(self, statement):
        froms = statement.get_final_froms() if hasattr(statement, "get_final_froms") else []
        if any(getattr(f, "name", None) == "question_responses" for f in froms):
            return ScalarResult(None)
        return ScalarResult(self.survey)

    async def get(self, model, item_id):
        if model is SurveyPost:
            return next((post for post in self.survey.posts if post.id == item_id), None)
        if model is SurveyResponse:
            return self.response if self.response and self.response.id == item_id else None
        if model is Question:
            for question in self.survey.questions:
                if question.id == item_id:
                    return question
            for post in self.survey.posts:
                for question in post.questions:
                    if question.id == item_id:
                        return question
        return None

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        for item in self.added:
            if isinstance(item, SurveyResponse):
                item.id = 601
                item.participant_token = "phase6-token"

    async def commit(self):
        self.commits += 1

    async def refresh(self, item):
        if isinstance(item, Question):
            item.id = item.id or 701
            item.created_at = item.created_at or datetime(2026, 4, 25, 9, 0, 0)
        if isinstance(item, QuestionResponse):
            item.id = item.id or 801
            item.created_at = item.created_at or datetime(2026, 4, 25, 9, 5, 0)


def make_researcher() -> Researcher:
    return Researcher(
        id=9,
        email="researcher@example.com",
        password_hash="hash",
        name="Researcher",
        created_at=datetime(2026, 4, 25, 8, 0, 0),
    )


def make_phase6_survey() -> Survey:
    now = datetime(2026, 4, 25, 9, 0, 0)
    survey = Survey(
        id=21,
        researcher_id=9,
        title="Phase 6 Survey",
        description="Social block completeness",
        status="published",
        share_code="phase6-share",
        num_groups=2,
        group_names={"1": "control", "2": "variant"},
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
        survey_id=21,
        order=1,
        original_url="https://example.com/story",
        fetched_title="Fetched title",
        fetched_image_url="https://example.com/image.jpg",
        fetched_description="Fetched description",
        fetched_source="Example News",
        display_title="Configured title",
        display_image_url=None,
        display_description="Configured description",
        source_label="Configured source",
        more_info_label="Read more",
        display_likes=12,
        display_comments_count=3,
        display_shares=2,
        show_likes=True,
        show_comments=True,
        show_shares=True,
        visible_to_groups=None,
        group_overrides={
            "2": {
                "display_likes": 99,
                "display_description": "Variant description",
                "source_label": "Variant source",
                "more_info_label": "Variant info",
            }
        },
        created_at=now,
    )
    post.comments = []
    post.translations = []
    post.questions = [
        Question(
            id=51,
            survey_id=21,
            post_id=31,
            order=1,
            question_type="single_choice",
            text="Pick one",
            config={"options": ["A", "B"]},
            created_at=now,
        )
    ]
    post.questions[0].translations = []
    survey.posts = [post]
    survey.translations = []
    survey.questions = [
        Question(
            id=52,
            survey_id=21,
            post_id=None,
            order=1,
            question_type="rating",
            text="Overall trust",
            config={"min": 1, "max": 5},
            created_at=now,
        )
    ]
    survey.questions[0].translations = []
    return survey


def test_phase6_schema_supports_complete_social_blocks_and_survey_questions():
    post_table = SurveyPost.__table__
    question_table = Question.__table__

    assert {"display_description", "source_label", "more_info_label"}.issubset(
        post_table.c.keys()
    )
    assert "survey_id" in question_table.c
    assert question_table.c.post_id.nullable is True


@pytest.mark.asyncio
async def test_create_post_question_supports_standard_question_types():
    survey = make_phase6_survey()
    db = Phase6DB(survey)

    question = await create_question(
        21,
        31,
        CreateQuestionRequest(
            question_type="multiple_choice",
            text="Select all that apply",
            order=2,
            config={"options": ["Fast", "Clear"]},
        ),
        db,
        make_researcher(),
    )

    assert question.survey_id == 21
    assert question.post_id == 31
    assert question.question_type == "multiple_choice"
    assert db.added[0].config == {"options": ["Fast", "Clear"]}


@pytest.mark.asyncio
async def test_preview_survey_uses_participant_serialization_without_creating_response():
    survey = make_phase6_survey()
    db = Phase6DB(survey)

    preview = await preview_survey(21, 2, "en", make_researcher(), db)

    assert preview.assigned_group == 2
    assert preview.posts[0].display_likes == 99
    assert preview.posts[0].display_description == "Variant description"
    assert preview.posts[0].source_label == "Variant source"
    assert preview.posts[0].more_info_label == "Variant info"
    assert preview.posts[0].questions[0].question_type == "single_choice"
    assert preview.questions[0].question_type == "rating"
    assert db.added == []


@pytest.mark.asyncio
async def test_start_survey_returns_social_card_questions_and_condition_values(monkeypatch):
    monkeypatch.setattr(surveys.random, "randint", lambda _start, _end: 2)
    survey = make_phase6_survey()
    db = Phase6DB(survey)

    response = await start_survey("phase6-share", StartSurveyRequest(language="en"), db)

    assert response.participant_token == "phase6-token"
    assert response.posts[0].display_likes == 99
    assert response.posts[0].display_description == "Variant description"
    assert response.posts[0].source_label == "Variant source"
    assert response.posts[0].questions[0].question_type == "single_choice"
    assert response.questions[0].question_type == "rating"


@pytest.mark.asyncio
async def test_submit_question_response_saves_answer_for_same_survey():
    survey = make_phase6_survey()
    participant_response = SurveyResponse(
        id=601,
        survey_id=21,
        participant_token="phase6-token",
        assigned_group=2,
        status="in_progress",
        started_at=datetime(2026, 4, 25, 9, 0, 0),
    )
    db = Phase6DB(survey, participant_response)

    answer = await submit_question_response(
        601,
        51,
        SubmitQuestionResponseRequest(
            question_id=51,
            participant_token="phase6-token",
            answer_text="A",
            answer_choices=["A"],
        ),
        db,
    )

    assert answer.response_id == 601
    assert answer.question_id == 51
    assert answer.answer_text == "A"
    assert answer.answer_choices == ["A"]
    assert isinstance(db.added[0], QuestionResponse)
