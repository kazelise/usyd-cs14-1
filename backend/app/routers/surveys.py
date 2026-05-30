"""Survey, post, and participant endpoints. Owned by Backend A/B.

Core flow:
1. Researcher creates survey → configures A/B groups
2. Researcher adds posts by pasting URLs → OG metadata auto-fetched
3. Researcher overrides display fields and sets fake engagement numbers
4. Researcher adds fake comments to posts
5. Researcher publishes survey → gets share link
6. Participant opens share link → randomly assigned to group → sees filtered posts
7. Participant interacts with posts (like/comment/click) → data captured
"""

import random
import secrets
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from jose import JWTError
from jose import jwt as jose_jwt
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import ALGORITHM, get_current_researcher
from app.config import settings
from app.database import get_db
from app.models.participant import (
    ParticipantComment,
    ParticipantInteraction,
    ParticipantLike,
    SurveyResponse,
)
from app.models.question import Question
from app.models.question_response import QuestionResponse
from app.models.researcher import Researcher
from app.models.survey import PostComment, Survey, SurveyPost
from app.models.tracking import CalibrationSession, ClickRecord, GazeRecord
from app.schemas.survey import (
    AttentionSummaryIn,
    CommentIn,
    CommentOut,
    CreatePostRequest,
    CreateQuestionRequest,
    CreateSurveyRequest,
    GroupAnalyticsOut,
    InteractionOut,
    InteractionRequest,
    ParticipantCommentOut,
    PostAnalyticsRowOut,
    PostEngagementStat,
    PostOut,
    PublicSurveyOut,
    QuestionOut,
    QuestionResponseOut,
    ResponseStateOut,
    StartSurveyRequest,
    StartSurveyResponse,
    SubmitQuestionResponseRequest,
    SurveyAnalyticsOut,
    SurveyEngagementStats,
    SurveyListOut,
    SurveyOut,
    SurveyParticipantCommentsOut,
    SurveyPreviewResponse,
    UpdatePostRequest,
    UpdateQuestionRequest,
    UpdateSurveyRequest,
)
from app.services.export_service import (
    ExportFilters,
    export_payload_to_csv,
    load_survey_export,
)
from app.services.og_fetcher import fetch_og_metadata
from app.services.translation_service import (
    apply_translations_to_post,
    apply_translations_to_public_survey,
    apply_translations_to_question,
    build_translation_export_payload,
    import_translation_payload,
    load_owned_survey_for_translations,
    normalize_optional_language,
    translation_payload_to_csv,
)
from app.utils.attention import compute_attention_quality

router = APIRouter(prefix="/surveys", tags=["Surveys"])

PARTICIPANT_POST_OVERRIDE_FIELDS = {
    "display_title",
    "display_image_url",
    "display_description",
    "source_label",
    "more_info_label",
    "display_likes",
    "display_comments_count",
    "display_shares",
    "show_likes",
    "show_comments",
    "show_shares",
}

# Fields that, when changed on a published survey, would corrupt existing responses.
_STRUCTURAL_SURVEY_FIELDS = frozenset(
    {
        "platform_style",
        "platform_ui_style",
        "num_groups",
        "group_names",
        "gaze_tracking_enabled",
        "gaze_interval_ms",
        "click_tracking_enabled",
        "calibration_enabled",
        "calibration_points",
        "default_language",
        "supported_languages",
    }
)


def _require_researcher_jwt(authorization: str | None) -> int:
    """Validate the Authorization header. Return the researcher id from `sub`.

    Raises 403 if the header is missing/malformed or the JWT is invalid/expired.
    Ownership of the target survey is NOT checked here — the caller is
    responsible for confirming the returned id matches the survey owner before
    granting researcher-only behaviors (such as previewing a draft).
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=403, detail="Preview sessions require researcher authentication"
        )
    token = authorization.split(" ", 1)[1]
    try:
        payload = jose_jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except (JWTError, Exception):
        raise HTTPException(status_code=403, detail="Invalid or expired researcher token")
    try:
        return int(payload.get("sub", 0))
    except (TypeError, ValueError):
        raise HTTPException(status_code=403, detail="Invalid researcher token payload")


def validate_scale_config(question_type: str | None, config: dict | None) -> None:
    """Reject likert/rating questions whose scale bounds are unusable.

    A scale needs integer ``min``/``max`` with ``0 <= min < max``. When the
    config omits these, the participant side falls back to the defaults
    (min 1, max 5), so we only reject values that are explicitly present and
    violate the contract.
    """
    if question_type not in ("likert", "rating"):
        return
    config = config or {}

    def _as_int(value, default):
        if value is None:
            return default
        if isinstance(value, bool) or not isinstance(value, int):
            raise HTTPException(status_code=422, detail="rating/likert requires integer min < max")
        return value

    minimum = _as_int(config.get("min"), 1)
    maximum = _as_int(config.get("max"), 5)
    if minimum < 0 or minimum >= maximum:
        raise HTTPException(status_code=422, detail="rating/likert requires integer min < max")


def _validate_question_answer(question: Question, body: SubmitQuestionResponseRequest) -> None:
    """Validate submitted answer content against the question type and config."""
    qtype = question.question_type
    config = question.config or {}

    if qtype in ("text", "free_text"):
        if not body.answer_text or not body.answer_text.strip():
            raise HTTPException(
                status_code=422, detail="answer_text is required and must not be empty"
            )

    elif qtype in ("rating", "likert"):
        if body.answer_value is None:
            raise HTTPException(
                status_code=422, detail="answer_value is required for rating/likert questions"
            )
        min_val = int(config.get("min", 1))
        max_val = int(config.get("max", 5))
        if not (min_val <= body.answer_value <= max_val):
            raise HTTPException(
                status_code=422, detail=f"answer_value must be between {min_val} and {max_val}"
            )

    elif qtype == "single_choice":
        options = config.get("options", [])
        if not isinstance(options, list) or not options:
            raise HTTPException(
                status_code=422, detail="single_choice questions must define config.options"
            )
        if not body.answer_choices or len(body.answer_choices) != 1:
            raise HTTPException(
                status_code=422, detail="single_choice requires exactly one selected option"
            )
        if body.answer_choices[0] not in options:
            raise HTTPException(status_code=422, detail="Selected choice is not a valid option")

    elif qtype == "multiple_choice":
        options = config.get("options", [])
        if not isinstance(options, list) or not options:
            raise HTTPException(
                status_code=422, detail="multiple_choice questions must define config.options"
            )
        if not body.answer_choices:
            raise HTTPException(
                status_code=422, detail="multiple_choice requires at least one selected option"
            )
        invalid = [c for c in body.answer_choices if c not in options]
        if invalid:
            raise HTTPException(status_code=422, detail=f"Invalid choices: {invalid}")


async def _count_survey_responses(survey_id: int, db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count(SurveyResponse.id)).where(SurveyResponse.survey_id == survey_id)
    )
    return result.scalar() or 0


async def _count_real_survey_responses(survey_id: int, db: AsyncSession) -> int:
    """Count NON-preview responses only. Preview rows are researcher dry-runs
    that should not block edits (issue #62)."""
    result = await db.execute(
        select(func.count(SurveyResponse.id)).where(
            SurveyResponse.survey_id == survey_id,
            SurveyResponse.is_preview.is_(False),
        )
    )
    return result.scalar() or 0


async def _ensure_no_survey_responses(survey_id: int, db: AsyncSession, detail: str) -> None:
    if await _count_real_survey_responses(survey_id, db) > 0:
        raise HTTPException(status_code=409, detail=detail)


# ── Internal Helper Functions ──────────────────────────────────────────


async def get_survey_or_404(survey_id: int, researcher_id: int, db: AsyncSession) -> Survey:
    """
    Enforces referential integrity and permission checks for researcher data[cite: 10, 208].
    """
    result = await db.execute(
        select(Survey).where(Survey.id == survey_id, Survey.researcher_id == researcher_id)
    )
    survey = result.scalar_one_or_none()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    return survey


def get_platform_style(survey: Survey) -> str:
    return getattr(survey, "platform_style", None) or "x"


def build_participant_post(post: SurveyPost, assigned_group: int) -> PostOut:
    """Build participant-visible post data without mutating the ORM model."""
    post_out = PostOut.model_validate(post)
    post_out.display_description = post_out.display_description or post_out.fetched_description
    post_out.source_label = post_out.source_label or post_out.fetched_source
    post_out.more_info_label = post_out.more_info_label or "More Information"
    overrides = (post.group_overrides or {}).get(str(assigned_group), {})
    for field, value in overrides.items():
        if field in PARTICIPANT_POST_OVERRIDE_FIELDS:
            setattr(post_out, field, value)
    return post_out


def build_participant_posts(
    survey: Survey, assigned_group: int, language_code: str | None
) -> list[PostOut]:
    """Build participant-visible post blocks for a group without creating analytics data."""
    visible_posts = []
    for post in survey.posts:
        if post.visible_to_groups is None or assigned_group in post.visible_to_groups:
            post_out = build_participant_post(post, assigned_group)
            visible_posts.append(apply_translations_to_post(post_out, post, language_code))
    return visible_posts


def build_participant_questions(survey: Survey, language_code: str | None) -> list[QuestionOut]:
    """Build survey-level questions that are not attached to a post block."""
    questions = [
        question
        for question in getattr(survey, "questions", []) or []
        if getattr(question, "post_id", None) is None
    ]
    return [
        apply_translations_to_question(
            QuestionOut.model_validate(question), question, language_code
        )
        for question in sorted(questions, key=lambda item: item.order)
    ]


def supported_languages_for_survey(survey: Survey) -> list[str]:
    languages = list(getattr(survey, "supported_languages", None) or ["en", "ar", "zh"])
    if "en" not in languages:
        languages.insert(0, "en")
    if "ar" not in languages:
        languages.append("ar")
    return languages


def default_language_for_survey(survey: Survey) -> str:
    default_language = getattr(survey, "default_language", None) or "en"
    if default_language in supported_languages_for_survey(survey):
        return default_language
    return "en"


def normalize_survey_language(survey: Survey, language: str | None) -> str:
    if not language:
        return default_language_for_survey(survey)
    language_code = normalize_optional_language(language)
    if language_code in supported_languages_for_survey(survey):
        return language_code
    return default_language_for_survey(survey)


def response_scope(survey_id: int, include_preview: bool = False):
    conditions = [SurveyResponse.survey_id == survey_id]
    if not include_preview:
        conditions.append(SurveyResponse.is_preview.is_(False))
    return conditions


def analytics_response_scope(
    survey_id: int,
    *,
    include_preview: bool = False,
    assigned_group: int | None = None,
    language: str | None = None,
    response_status: str | None = None,
    calibration_passed: bool | None = None,
):
    """Like response_scope but also applies the export-style filters.

    Filters here intentionally mirror the GET /surveys/{id}/export filters so
    the visible analytics summary and the CSV/JSON downloads stay coherent.
    """
    conditions = response_scope(survey_id, include_preview)
    if assigned_group is not None:
        conditions.append(SurveyResponse.assigned_group == assigned_group)
    if language:
        conditions.append(SurveyResponse.language == language)
    if response_status:
        conditions.append(SurveyResponse.status == response_status)
    if calibration_passed is not None:
        conditions.append(
            SurveyResponse.id.in_(
                select(CalibrationSession.response_id).where(
                    CalibrationSession.passed.is_(calibration_passed)
                )
            )
        )
    return conditions


async def get_response_or_404(response_id: int, db: AsyncSession) -> SurveyResponse:
    result = await db.execute(select(SurveyResponse).where(SurveyResponse.id == response_id))
    response = result.scalar_one_or_none()
    if not response:
        raise HTTPException(status_code=404, detail="Response not found")
    return response


async def get_participant_response_or_404(
    response_id: int,
    participant_token: str,
    db: AsyncSession,
    *,
    require_active: bool = True,
) -> SurveyResponse:
    """Return a participant response only when the anonymous token matches.

    Mirrors `routers.tracking.get_active_response_or_404` so every public
    participant endpoint validates the session token, not just the response id.
    """
    result = await db.execute(select(SurveyResponse).where(SurveyResponse.id == response_id))
    response = result.scalar_one_or_none()
    if not response or response.participant_token != participant_token:
        raise HTTPException(status_code=404, detail="Response not found")
    if require_active and response.status != "in_progress":
        raise HTTPException(status_code=409, detail="Response is not active")
    return response


async def ensure_post_belongs_to_survey(post_id: int, survey_id: int, db: AsyncSession) -> None:
    result = await db.execute(
        select(SurveyPost.id).where(
            SurveyPost.id == post_id,
            SurveyPost.survey_id == survey_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=422, detail="Post does not belong to this response survey")


# ══════════════════════════════════════════════════════
#  RESEARCHER ENDPOINTS (require auth)
# ══════════════════════════════════════════════════════


@router.post("", response_model=SurveyOut, status_code=201)
async def create_survey(
    body: CreateSurveyRequest,
    researcher: Researcher = Depends(get_current_researcher),
    db: AsyncSession = Depends(get_db),
):
    """Create a new survey with optional A/B group configuration."""
    survey = Survey(researcher_id=researcher.id, **body.model_dump())
    db.add(survey)
    await db.commit()
    await db.refresh(survey)
    return survey


@router.get("", response_model=SurveyListOut)
async def list_surveys(
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
    researcher: Researcher = Depends(get_current_researcher),
    db: AsyncSession = Depends(get_db),
):
    """List all surveys owned by the current researcher."""
    query = select(Survey).where(Survey.researcher_id == researcher.id)
    if status:
        query = query.where(Survey.status == status)
    count_query = select(func.count(Survey.id)).where(Survey.researcher_id == researcher.id)
    if status:
        count_query = count_query.where(Survey.status == status)
    count_result = await db.execute(count_query)

    result = await db.execute(query.order_by(Survey.created_at.desc()).limit(limit).offset(offset))
    surveys = result.scalars().all()
    return SurveyListOut(items=surveys, total=count_result.scalar() or 0)


@router.get("/{survey_id}", response_model=SurveyOut)
async def get_survey(
    survey_id: int,
    researcher: Researcher = Depends(get_current_researcher),
    db: AsyncSession = Depends(get_db),
):
    """Get a single survey by ID."""
    result = await db.execute(
        select(Survey).where(Survey.id == survey_id, Survey.researcher_id == researcher.id)
    )
    survey = result.scalar_one_or_none()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    return survey


@router.patch("/{survey_id}", response_model=SurveyOut)
async def update_survey(
    survey_id: int,
    body: UpdateSurveyRequest,
    researcher: Researcher = Depends(get_current_researcher),
    db: AsyncSession = Depends(get_db),
):
    """Updates survey parameters while maintaining temporal audit trails."""
    survey = await get_survey_or_404(survey_id, researcher.id, db)
    updates = body.model_dump(exclude_unset=True)
    if survey.status == "published":
        blocked = _STRUCTURAL_SURVEY_FIELDS & updates.keys()
        if blocked:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot change structural configuration on a published survey: {sorted(blocked)}",
            )
    for field, value in updates.items():
        setattr(survey, field, value)
    survey.updated_at = datetime.utcnow()
    await db.commit()
    return survey


@router.delete("/{survey_id}", status_code=204)
async def delete_survey(
    survey_id: int,
    researcher: Researcher = Depends(get_current_researcher),
    db: AsyncSession = Depends(get_db),
):
    """Delete a draft survey owned by the current researcher."""
    result = await db.execute(
        select(Survey).where(Survey.id == survey_id, Survey.researcher_id == researcher.id)
    )
    survey = result.scalar_one_or_none()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    if survey.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft surveys can be deleted")
    await db.delete(survey)
    await db.flush()


@router.post("/{survey_id}/publish", response_model=SurveyOut)
async def publish_survey(
    survey_id: int,
    researcher: Researcher = Depends(get_current_researcher),
    db: AsyncSession = Depends(get_db),
):
    """Publish a draft survey, making it available via share link."""
    result = await db.execute(
        select(Survey).where(Survey.id == survey_id, Survey.researcher_id == researcher.id)
    )
    survey = result.scalar_one_or_none()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    if survey.status != "draft":
        raise HTTPException(status_code=409, detail="Only draft surveys can be published")
    posts_count_q = await db.execute(
        select(func.count(SurveyPost.id)).where(SurveyPost.survey_id == survey_id)
    )
    if (posts_count_q.scalar() or 0) == 0:
        raise HTTPException(
            status_code=422, detail="Survey must have at least one post before publishing"
        )
    survey.status = "published"
    if survey.published_at is None:
        survey.published_at = datetime.utcnow()
    survey.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(survey)
    return survey


@router.post("/{survey_id}/close", response_model=SurveyOut)
async def close_survey(
    survey_id: int,
    researcher: Researcher = Depends(get_current_researcher),
    db: AsyncSession = Depends(get_db),
):
    """Close a published survey, blocking new participant sessions.

    Past responses and exports are preserved. In-flight participant sessions
    that already hold a valid participant_token continue to work (the resume
    branch in start_survey does not re-check status) — this is intentional so
    researchers don't kick out live participants when retiring a study.
    """
    result = await db.execute(
        select(Survey).where(Survey.id == survey_id, Survey.researcher_id == researcher.id)
    )
    survey = result.scalar_one_or_none()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    if survey.status != "published":
        raise HTTPException(status_code=409, detail="Only published surveys can be closed")
    survey.status = "closed"
    survey.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(survey)
    return survey


@router.post("/{survey_id}/reopen", response_model=SurveyOut)
async def reopen_survey(
    survey_id: int,
    researcher: Researcher = Depends(get_current_researcher),
    db: AsyncSession = Depends(get_db),
):
    """Reopen a previously closed survey so it accepts new participants again."""
    result = await db.execute(
        select(Survey).where(Survey.id == survey_id, Survey.researcher_id == researcher.id)
    )
    survey = result.scalar_one_or_none()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    if survey.status != "closed":
        raise HTTPException(status_code=409, detail="Only closed surveys can be reopened")
    survey.status = "published"
    survey.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(survey)
    return survey


@router.delete("/{survey_id}/preview-responses", status_code=204)
async def delete_preview_responses(
    survey_id: int,
    researcher: Researcher = Depends(get_current_researcher),
    db: AsyncSession = Depends(get_db),
):
    """Wipe all preview (researcher dry-run) responses for a survey (issue #62).

    Called by the admin test-session route on entry so each reopen of the
    test session starts from a clean slate. Only the survey owner can call
    this; real participant responses (`is_preview=False`) are NOT touched.
    """
    survey_result = await db.execute(
        select(Survey).where(Survey.id == survey_id, Survey.researcher_id == researcher.id)
    )
    survey = survey_result.scalar_one_or_none()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")

    preview_q = await db.execute(
        select(SurveyResponse).where(
            SurveyResponse.survey_id == survey_id,
            SurveyResponse.is_preview.is_(True),
        )
    )
    for response in preview_q.scalars().all():
        # SA cascade handles interactions + calibration_session; DB-level
        # ondelete CASCADE handles likes, comments, gaze, clicks, q-responses.
        await db.delete(response)
    await db.flush()
    return None


@router.get("/{survey_id}/export")
async def export_survey_data(
    survey_id: int,
    export_format: Literal["csv", "json"] = Query("csv", alias="format"),
    condition: int | None = None,
    assigned_group: int | None = None,
    language: str | None = None,
    response_status: str | None = None,
    calibration_passed: bool | None = None,
    include_preview: bool = False,
    researcher: Researcher = Depends(get_current_researcher),
    db: AsyncSession = Depends(get_db),
):
    """Export research data for one owned survey as CSV or JSON."""
    payload = await load_survey_export(
        db,
        survey_id=survey_id,
        researcher_id=researcher.id,
        filters=ExportFilters(
            assigned_group=assigned_group,
            condition=condition,
            language=language,
            response_status=response_status,
            calibration_passed=calibration_passed,
            include_preview=include_preview,
        ),
    )
    if export_format == "json":
        return payload

    filename = f"survey_{survey_id}_export.csv"
    return StreamingResponse(
        iter([export_payload_to_csv(payload)]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{survey_id}/translations/export")
async def export_survey_translations(
    survey_id: int,
    export_format: Literal["csv", "json"] = Query("json", alias="format"),
    language: str = "zh",
    researcher: Researcher = Depends(get_current_researcher),
    db: AsyncSession = Depends(get_db),
):
    """Export a translation template and any existing localized values."""
    survey = await load_owned_survey_for_translations(
        db, survey_id=survey_id, researcher_id=researcher.id
    )
    payload = build_translation_export_payload(survey, language_code=language)
    if export_format == "json":
        return payload

    filename = f"survey_{survey_id}_translations_{payload['language_code']}.csv"
    return StreamingResponse(
        iter([translation_payload_to_csv(payload)]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{survey_id}/translations/import")
async def import_survey_translations(
    survey_id: int,
    request: Request,
    import_format: Literal["csv", "json"] = Query("json", alias="format"),
    language: str | None = None,
    researcher: Researcher = Depends(get_current_researcher),
    db: AsyncSession = Depends(get_db),
):
    """Import translated survey/post/comment/question fields for one language."""
    survey = await load_owned_survey_for_translations(
        db, survey_id=survey_id, researcher_id=researcher.id
    )
    content_type = request.headers.get("content-type", "")
    payload_format: Literal["csv", "json"] = (
        "csv" if import_format == "csv" or "text/csv" in content_type else "json"
    )
    if payload_format == "csv":
        raw_payload = (await request.body()).decode("utf-8")
    else:
        raw_payload = await request.json()

    return await import_translation_payload(
        db,
        survey,
        raw_payload,
        payload_format=payload_format,
        language_override=language,
    )


@router.get("/{survey_id}/preview", response_model=SurveyPreviewResponse)
async def preview_survey(
    survey_id: int,
    assigned_group: int = Query(1, ge=1),
    language: str | None = None,
    researcher: Researcher = Depends(get_current_researcher),
    db: AsyncSession = Depends(get_db),
):
    """Preview participant-visible blocks without creating a participant response."""
    result = await db.execute(
        select(Survey)
        .options(
            selectinload(Survey.translations),
            selectinload(Survey.questions).selectinload(Question.translations),
            selectinload(Survey.posts).selectinload(SurveyPost.translations),
            selectinload(Survey.posts).selectinload(SurveyPost.comments),
            selectinload(Survey.posts)
            .selectinload(SurveyPost.questions)
            .selectinload(Question.translations),
        )
        .where(Survey.id == survey_id, Survey.researcher_id == researcher.id)
    )
    survey = result.scalar_one_or_none()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    if assigned_group > survey.num_groups:
        raise HTTPException(status_code=400, detail="assigned_group exceeds survey group count")

    language_code = normalize_survey_language(survey, language)
    return SurveyPreviewResponse(
        survey_id=survey.id,
        assigned_group=assigned_group,
        platform_style=get_platform_style(survey),
        platform_ui_style=survey.platform_ui_style or "twitter",
        calibration_required=survey.calibration_enabled,
        calibration_points=survey.calibration_points,
        gaze_tracking_enabled=survey.gaze_tracking_enabled,
        gaze_interval_ms=survey.gaze_interval_ms,
        click_tracking_enabled=survey.click_tracking_enabled,
        language=language_code,
        default_language=default_language_for_survey(survey),
        supported_languages=supported_languages_for_survey(survey),
        posts=build_participant_posts(survey, assigned_group, language_code),
        questions=build_participant_questions(survey, language_code),
    )


# ── Post CRUD ─────────────────────────────────────────


@router.post("/{survey_id}/posts", response_model=PostOut, status_code=201)
async def create_post(
    survey_id: int,
    body: CreatePostRequest,
    researcher: Researcher = Depends(get_current_researcher),
    db: AsyncSession = Depends(get_db),
):
    """Create a social media post by providing a URL.

    The backend automatically fetches Open Graph metadata (title, image,
    description, source) from the URL — same as how Facebook/Twitter
    generates link previews.
    """
    await get_survey_or_404(survey_id, researcher.id, db)
    await _ensure_no_survey_responses(
        survey_id,
        db,
        "Cannot add posts after participant responses exist",
    )

    # Fetch OG metadata from the URL
    og = await fetch_og_metadata(body.original_url)

    post = SurveyPost(
        survey_id=survey_id,
        order=body.order,
        original_url=body.original_url,
        fetched_title=og.title,
        fetched_image_url=og.image_url,
        fetched_description=og.description,
        fetched_source=og.source,
    )
    db.add(post)
    await db.flush()

    # Reload with comments relationship to avoid async lazy-load error
    result = await db.execute(
        select(SurveyPost)
        .options(selectinload(SurveyPost.comments), selectinload(SurveyPost.questions))
        .where(SurveyPost.id == post.id)
    )
    post = result.scalar_one()
    return post


@router.get("/{survey_id}/posts", response_model=list[PostOut])
async def list_posts(
    survey_id: int,
    limit: int = 50,
    offset: int = 0,
    researcher: Researcher = Depends(get_current_researcher),
    db: AsyncSession = Depends(get_db),
):
    """List all posts in a survey (with their fake comments)."""
    # Verify ownership
    survey_result = await db.execute(
        select(Survey).where(Survey.id == survey_id, Survey.researcher_id == researcher.id)
    )
    if not survey_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Survey not found")

    result = await db.execute(
        select(SurveyPost)
        .options(selectinload(SurveyPost.comments), selectinload(SurveyPost.questions))
        .where(SurveyPost.survey_id == survey_id)
        .order_by(SurveyPost.order)
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


@router.patch("/{survey_id}/posts/{post_id}", response_model=PostOut)
async def update_post(
    survey_id: int,
    post_id: int,
    body: UpdatePostRequest,
    researcher: Researcher = Depends(get_current_researcher),
    db: AsyncSession = Depends(get_db),
):
    """Update post display settings: override title/image, set fake numbers, configure A/B visibility."""
    await get_survey_or_404(survey_id, researcher.id, db)
    result = await db.execute(
        select(SurveyPost)
        .options(selectinload(SurveyPost.comments), selectinload(SurveyPost.questions))
        .where(SurveyPost.id == post_id, SurveyPost.survey_id == survey_id)
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    await _ensure_no_survey_responses(
        survey_id,
        db,
        "Cannot change post configuration after participant responses exist",
    )
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(post, field, value)
    await db.flush()
    await db.refresh(post)
    return post


@router.delete("/{survey_id}/posts/{post_id}", status_code=204)
async def delete_post(
    survey_id: int,
    post_id: int,
    researcher: Researcher = Depends(get_current_researcher),
    db: AsyncSession = Depends(get_db),
):
    """Delete a post from a survey."""
    await get_survey_or_404(survey_id, researcher.id, db)
    result = await db.execute(
        select(SurveyPost).where(SurveyPost.id == post_id, SurveyPost.survey_id == survey_id)
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    await _ensure_no_survey_responses(
        survey_id,
        db,
        "Cannot delete posts after participant responses exist",
    )
    await db.delete(post)


# ── Post Comments (fake, by researcher) ───────────────


@router.post("/{survey_id}/posts/{post_id}/comments", response_model=CommentOut, status_code=201)
async def add_comment(
    survey_id: int,
    post_id: int,
    body: CommentIn,
    researcher: Researcher = Depends(get_current_researcher),
    db: AsyncSession = Depends(get_db),
):
    """Add a fake comment to a post. Researchers manually write comment content."""
    await get_survey_or_404(survey_id, researcher.id, db)
    result = await db.execute(
        select(SurveyPost).where(SurveyPost.id == post_id, SurveyPost.survey_id == survey_id)
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Get next order number
    count_result = await db.execute(
        select(func.count(PostComment.id)).where(PostComment.post_id == post_id)
    )
    next_order = (count_result.scalar() or 0) + 1

    comment = PostComment(post_id=post_id, order=next_order, **body.model_dump())
    db.add(comment)
    await db.flush()
    await db.refresh(comment)
    return comment


# ══════════════════════════════════════════════════════
#  PARTICIPANT ENDPOINTS (no auth required)
# ══════════════════════════════════════════════════════


@router.post("/{share_code}/start", response_model=StartSurveyResponse)
async def start_survey(
    share_code: str,
    body: StartSurveyRequest | None = None,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Start a survey as a participant.

    The participant is randomly assigned to a group (coin flip).
    Only posts visible to the assigned group are returned.
    """
    result = await db.execute(
        select(Survey)
        .options(
            selectinload(Survey.translations),
            selectinload(Survey.questions).selectinload(Question.translations),
            selectinload(Survey.posts).selectinload(SurveyPost.translations),
            selectinload(Survey.posts).selectinload(SurveyPost.comments),
            selectinload(Survey.posts)
            .selectinload(SurveyPost.questions)
            .selectinload(Question.translations),
        )
        .where(Survey.share_code == share_code)
    )
    survey = result.scalar_one_or_none()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found or inactive")
    if survey.share_code_expires_at and survey.share_code_expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Survey link has expired")

    # Status gating + preview auth, in one place so the two paths can't drift.
    # - Anonymous participants: survey must be published.
    # - Preview (issue #62): allow draft AND published, but only when the
    #   caller carries a valid researcher JWT AND owns the survey. Closed
    #   surveys remain unpreviewable (researchers retire studies via /close).
    is_preview = bool(body and (body.is_preview or body.preview_assigned_group is not None))
    if is_preview:
        researcher_id = _require_researcher_jwt(authorization)
        if survey.researcher_id != researcher_id:
            raise HTTPException(status_code=403, detail="Not authorized to preview this survey")
        if survey.status not in {"draft", "published"}:
            raise HTTPException(status_code=404, detail="Survey not found or inactive")
    else:
        if survey.status != "published":
            raise HTTPException(status_code=404, detail="Survey not found or inactive")

    language_code = normalize_survey_language(survey, body.language if body else None)

    # Resume path: when the client supplies a token from a prior start_survey
    # call and it matches an in_progress response for THIS survey, reuse that
    # response instead of creating a new one. Preserves assigned_group
    # (randomization integrity) and keeps the existing calibration session,
    # likes, and comments attached after a tab close.
    response = None
    if body and body.participant_token:
        existing_q = await db.execute(
            select(SurveyResponse).where(
                SurveyResponse.participant_token == body.participant_token,
                SurveyResponse.survey_id == survey.id,
                SurveyResponse.status == "in_progress",
            )
        )
        response = existing_q.scalar_one_or_none()

    calibration_completed = False
    if response is None:
        randomization_seed = secrets.token_hex(16)
        # Guard against legacy/out-of-band rows where num_groups < 1, which would
        # otherwise make random.randint(1, num_groups) raise and 500 the start call.
        group_count = survey.num_groups if survey.num_groups and survey.num_groups >= 1 else 1
        if body and body.is_preview and body.preview_assigned_group is not None:
            if body.preview_assigned_group > group_count:
                raise HTTPException(
                    status_code=400, detail="preview_assigned_group exceeds survey group count"
                )
            assigned_group = body.preview_assigned_group
        else:
            assigned_group = random.randint(1, group_count)
        shown_posts = build_participant_posts(survey, assigned_group, language_code)
        response = SurveyResponse(
            survey_id=survey.id,
            assigned_group=assigned_group,
            randomization_seed=randomization_seed,
            shown_post_order=[post.id for post in shown_posts],
            language=language_code,
            screen_width=body.screen_width if body else None,
            screen_height=body.screen_height if body else None,
            user_agent=body.user_agent if body else None,
            is_preview=body.is_preview if body else False,
            status="in_progress",
            started_at=datetime.utcnow(),
        )
        db.add(response)
        await db.flush()
        await db.refresh(response)
    else:
        assigned_group = response.assigned_group
        language_code = response.language
        if response.is_preview is None:
            response.is_preview = False
        shown_posts = build_participant_posts(survey, assigned_group, language_code)
        if response.shown_post_order is None:
            response.shown_post_order = [post.id for post in shown_posts]
        # On resume, look at any prior CalibrationSession attached to this
        # response. Only skip the calibration UI when it was a genuine passing
        # calibration (completed, not poor, not explicitly failed). If it was
        # abandoned mid-way (in_progress) or completed-but-poor/failed, drop it
        # (cascading its points) so the frontend can re-create cleanly without
        # hitting the "session already exists" 409 from create_calibration_session.
        existing_calib_q = await db.execute(
            select(CalibrationSession)
            .options(selectinload(CalibrationSession.points))
            .where(CalibrationSession.response_id == response.id)
        )
        existing_calib = existing_calib_q.scalar_one_or_none()
        if existing_calib is not None:
            if (
                existing_calib.status == "completed"
                and existing_calib.quality != "poor"
                and existing_calib.passed is not False
            ):
                calibration_completed = True
            else:
                for point in existing_calib.points:
                    await db.delete(point)
                await db.delete(existing_calib)
                await db.flush()
    if "shown_posts" not in locals():
        shown_posts = build_participant_posts(survey, assigned_group, language_code)

    return StartSurveyResponse(
        response_id=response.id,
        participant_token=response.participant_token,
        survey_id=survey.id,
        assigned_group=assigned_group,
        randomization_seed=response.randomization_seed,
        shown_post_order=response.shown_post_order or [post.id for post in shown_posts],
        is_preview=response.is_preview,
        platform_style=get_platform_style(survey),
        platform_ui_style=survey.platform_ui_style or "twitter",
        calibration_required=survey.calibration_enabled,
        calibration_points=survey.calibration_points,
        calibration_completed=calibration_completed,
        gaze_tracking_enabled=survey.gaze_tracking_enabled,
        gaze_interval_ms=survey.gaze_interval_ms,
        click_tracking_enabled=survey.click_tracking_enabled,
        language=response.language,
        default_language=default_language_for_survey(survey),
        supported_languages=supported_languages_for_survey(survey),
        posts=shown_posts,
        questions=build_participant_questions(survey, language_code),
    )


@router.get("/public/{share_code}", response_model=PublicSurveyOut)
async def get_public_survey(
    share_code: str,
    language: str | None = None,
    preview: bool = False,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: AsyncSession = Depends(get_db),
):
    """Public metadata for start screen before starting a session.

    Drafts are gated to authenticated researchers via `?preview=1` + a valid
    `Authorization` header that resolves to the survey's owner — same contract
    as `start_survey`. Closed surveys remain unpreviewable.
    """
    result = await db.execute(
        select(Survey)
        .options(selectinload(Survey.translations))
        .where(Survey.share_code == share_code)
    )
    survey = result.scalar_one_or_none()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found or not published")
    if survey.share_code_expires_at and survey.share_code_expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Survey link has expired")
    if preview:
        researcher_id = _require_researcher_jwt(authorization)
        if survey.researcher_id != researcher_id:
            raise HTTPException(status_code=403, detail="Not authorized to preview this survey")
        if survey.status not in {"draft", "published"}:
            raise HTTPException(status_code=404, detail="Survey not found or not published")
    elif survey.status != "published":
        raise HTTPException(status_code=404, detail="Survey not found or not published")
    public_survey = apply_translations_to_public_survey(
        survey, normalize_survey_language(survey, language)
    )
    public_survey.default_language = default_language_for_survey(survey)
    public_survey.supported_languages = supported_languages_for_survey(survey)
    return public_survey


@router.post("/responses/{response_id}/interact", response_model=InteractionOut)
async def record_interaction(
    response_id: int,
    body: InteractionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Record a participant interaction with a post (like, comment, or click to original)."""
    response = await get_participant_response_or_404(response_id, body.participant_token, db)
    await ensure_post_belongs_to_survey(body.post_id, response.survey_id, db)

    interaction = ParticipantInteraction(
        response_id=response_id,
        post_id=body.post_id,
        action_type=body.action_type,
        comment_text=body.comment_text if body.action_type == "comment" else None,
        # Capturing Qualtrics-grade behavioral metrics for analysis
        dwell_time_ms=getattr(body, "dwell_time_ms", None),
        click_x=getattr(body, "click_x", None),
        click_y=getattr(body, "click_y", None),
    )
    db.add(interaction)
    await db.flush()
    await db.refresh(interaction)
    return interaction


class ToggleLikeRequest(BaseModel):
    post_id: int
    participant_token: str = Field(min_length=1, max_length=128)


@router.post("/responses/{response_id}/likes/toggle")
async def toggle_like(
    response_id: int,
    body: ToggleLikeRequest,
    db: AsyncSession = Depends(get_db),
):
    response = await get_participant_response_or_404(response_id, body.participant_token, db)
    await ensure_post_belongs_to_survey(body.post_id, response.survey_id, db)

    existing_q = await db.execute(
        select(ParticipantLike).where(
            ParticipantLike.response_id == response_id,
            ParticipantLike.post_id == body.post_id,
        )
    )
    existing = existing_q.scalar_one_or_none()
    if existing:
        await db.delete(existing)
        db.add(
            ParticipantInteraction(
                response_id=response_id,
                post_id=body.post_id,
                action_type="unlike",
            )
        )
        await db.flush()
        return {"liked": False}
    else:
        db.add(ParticipantLike(response_id=response_id, post_id=body.post_id))
        db.add(
            ParticipantInteraction(
                response_id=response_id,
                post_id=body.post_id,
                action_type="like",
            )
        )
        await db.flush()
        return {"liked": True}


@router.get("/responses/{response_id}/state", response_model=ResponseStateOut)
async def get_response_state(
    response_id: int,
    x_participant_token: Annotated[
        str, Header(alias="X-Participant-Token", min_length=1, max_length=128)
    ],
    db: AsyncSession = Depends(get_db),
):
    # State may legitimately be fetched after completion (e.g. resume after
    # tab close), so we only enforce token ownership, not in_progress status.
    await get_participant_response_or_404(
        response_id, x_participant_token, db, require_active=False
    )

    likes_result = await db.execute(
        select(ParticipantLike.post_id).where(ParticipantLike.response_id == response_id)
    )
    liked_post_ids = list(likes_result.scalars().all())

    comments_result = await db.execute(
        select(ParticipantComment)
        .where(ParticipantComment.response_id == response_id)
        .order_by(ParticipantComment.created_at)
    )
    comments = comments_result.scalars().all()
    comments_by_post: dict[int, list[ParticipantCommentOut]] = {}
    for c in comments:
        comments_by_post.setdefault(c.post_id, []).append(ParticipantCommentOut.model_validate(c))

    interacted_result = await db.execute(
        select(ParticipantInteraction.post_id)
        .where(ParticipantInteraction.response_id == response_id)
        .distinct()
    )
    answered_result = await db.execute(
        select(QuestionResponse.question_id)
        .where(QuestionResponse.response_id == response_id)
        .distinct()
    )
    return ResponseStateOut(
        liked_post_ids=liked_post_ids,
        comments_by_post=comments_by_post,
        interacted_post_ids=list(interacted_result.scalars().all()),
        answered_question_ids=list(answered_result.scalars().all()),
    )


async def _apply_attention_summary(
    response: SurveyResponse,
    summary: AttentionSummaryIn,
    db: AsyncSession,
) -> dict[str, object]:
    """Compute and persist the response-level attention/confidence metadata."""
    calibration_q = await db.execute(
        select(CalibrationSession).where(CalibrationSession.response_id == response.id)
    )
    calibration = calibration_q.scalar_one_or_none()
    metrics = compute_attention_quality(
        active_ms=summary.active_ms,
        expected_samples=summary.expected_samples,
        detected_samples=summary.detected_samples,
        missing_ms=summary.missing_ms,
        no_face_periods=summary.no_face_periods,
        calibration_passed=calibration.passed if calibration else None,
        calibration_quality=calibration.quality if calibration else None,
    )
    response.attention_active_ms = metrics["active_ms"]
    response.attention_expected_samples = metrics["expected_samples"]
    response.attention_detected_samples = metrics["detected_samples"]
    response.attention_missing_ms = metrics["missing_ms"]
    response.attention_no_face_periods = metrics["no_face_periods"]
    response.attention_coverage = metrics["coverage"]
    response.attention_confidence = metrics["confidence"]
    response.attention_quality = metrics["quality"]
    response.attention_quality_reason = metrics["quality_reason"]
    return metrics


class AttentionSummaryRequest(BaseModel):
    participant_token: str = Field(min_length=1, max_length=128)
    summary: AttentionSummaryIn


@router.post("/responses/{response_id}/attention-summary")
async def submit_attention_summary(
    response_id: int,
    body: AttentionSummaryRequest,
    db: AsyncSession = Depends(get_db),
):
    """Record survey-time attention/confidence metadata for a response.

    The participant client posts this just before /complete so a response that
    fails to complete (network drop, tab close) still keeps the partial
    quality signal for analysis. The server recomputes the confidence score
    from raw counts so the client cannot inflate it.
    """
    response = await get_participant_response_or_404(response_id, body.participant_token, db)
    metrics = await _apply_attention_summary(response, body.summary, db)
    await db.commit()
    return {
        "coverage": metrics["coverage"],
        "confidence": metrics["confidence"],
        "quality": metrics["quality"],
        "quality_reason": metrics["quality_reason"],
    }


class CompleteResponseRequest(BaseModel):
    participant_token: str = Field(min_length=1, max_length=128)
    attention_summary: AttentionSummaryIn | None = Field(
        default=None,
        description=(
            "Optional survey-time tracking summary. When provided, the server "
            "computes the response-level attention confidence/quality bucket "
            "from these counts (raw video is never sent)."
        ),
    )


async def _validate_completion_requirements(response: SurveyResponse, db: AsyncSession) -> None:
    """Reject real participant completions that would produce unusable research rows."""
    if response.is_preview:
        return

    survey_result = await db.execute(select(Survey).where(Survey.id == response.survey_id))
    survey = survey_result.scalar_one_or_none()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")

    if survey.calibration_enabled:
        calibration_result = await db.execute(
            select(CalibrationSession).where(CalibrationSession.response_id == response.id)
        )
        calibration = calibration_result.scalar_one_or_none()
        calibration_ok = (
            calibration is not None
            and calibration.status == "completed"
            and calibration.passed is not False
            and calibration.quality != "poor"
        )
        if not calibration_ok:
            raise HTTPException(
                status_code=422,
                detail="Webcam calibration must be completed before submitting this survey",
            )

    shown_post_ids = list(response.shown_post_order or [])
    question_scope = [Question.survey_id == response.survey_id]
    if shown_post_ids:
        question_scope.append(or_(Question.post_id.is_(None), Question.post_id.in_(shown_post_ids)))
    else:
        question_scope.append(Question.post_id.is_(None))

    question_result = await db.execute(select(Question.id).where(*question_scope))
    required_question_ids = list(question_result.scalars().all())
    if required_question_ids:
        answer_result = await db.execute(
            select(QuestionResponse.question_id).where(
                QuestionResponse.response_id == response.id,
                QuestionResponse.question_id.in_(required_question_ids),
            )
        )
        answered_question_ids = set(answer_result.scalars().all())
        missing_question_ids = [
            question_id
            for question_id in required_question_ids
            if question_id not in answered_question_ids
        ]
        if missing_question_ids:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "missing_required_answers",
                    "missing_question_ids": missing_question_ids,
                },
            )
        return

    if not shown_post_ids:
        return

    interaction_result = await db.execute(
        select(ParticipantInteraction.id)
        .where(ParticipantInteraction.response_id == response.id)
        .limit(1)
    )
    if interaction_result.scalar_one_or_none() is not None:
        return

    like_result = await db.execute(
        select(ParticipantLike.id).where(ParticipantLike.response_id == response.id).limit(1)
    )
    if like_result.scalar_one_or_none() is not None:
        return

    comment_result = await db.execute(
        select(ParticipantComment.id).where(ParticipantComment.response_id == response.id).limit(1)
    )
    if comment_result.scalar_one_or_none() is not None:
        return

    raise HTTPException(
        status_code=422,
        detail="At least one post interaction or required answer is needed before completion",
    )


@router.post("/responses/{response_id}/complete")
async def complete_response(
    response_id: int,
    body: CompleteResponseRequest,
    db: AsyncSession = Depends(get_db),
):
    """Mark a survey response as completed."""
    response = await get_participant_response_or_404(response_id, body.participant_token, db)

    if body.attention_summary is not None:
        await _apply_attention_summary(response, body.attention_summary, db)

    await _validate_completion_requirements(response, db)

    # Enforcing server-side timestamps to prevent client-side manipulation
    now = datetime.utcnow()
    duration = (now - response.started_at).total_seconds()

    # Implementation of automated speed filtering to protect research integrity
    # Responses under 30 seconds are flagged as potential low-effort samples
    if duration < 30:
        response.status = "flagged"
        response.is_speed_test_failed = True
    else:
        response.status = "completed"

    response.completed_at = now
    await db.commit()
    return {
        "status": response.status,
        "duration_seconds": duration,
        "attention_confidence": response.attention_confidence,
        "attention_quality": response.attention_quality,
    }


class ParticipantCommentIn(BaseModel):
    post_id: int
    text: str
    author_name: str | None = None
    participant_token: str = Field(min_length=1, max_length=128)


class ParticipantCommentPatch(BaseModel):
    text: str
    participant_token: str = Field(min_length=1, max_length=128)


@router.post(
    "/responses/{response_id}/comments", response_model=ParticipantCommentOut, status_code=201
)
async def create_participant_comment(
    response_id: int,
    body: ParticipantCommentIn,
    db: AsyncSession = Depends(get_db),
):
    response = await get_participant_response_or_404(response_id, body.participant_token, db)
    await ensure_post_belongs_to_survey(body.post_id, response.survey_id, db)

    comment = ParticipantComment(
        response_id=response.id, post_id=body.post_id, text=body.text, author_name=body.author_name
    )
    db.add(comment)
    db.add(
        ParticipantInteraction(
            response_id=response_id,
            post_id=body.post_id,
            action_type="comment",
            comment_text=body.text,
        )
    )
    await db.flush()
    await db.refresh(comment)
    return comment


@router.patch(
    "/responses/{response_id}/comments/{comment_id}", response_model=ParticipantCommentOut
)
async def update_participant_comment(
    response_id: int,
    comment_id: int,
    body: ParticipantCommentPatch,
    db: AsyncSession = Depends(get_db),
):
    await get_participant_response_or_404(response_id, body.participant_token, db)
    result = await db.execute(
        select(ParticipantComment).where(
            ParticipantComment.id == comment_id, ParticipantComment.response_id == response_id
        )
    )
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    comment.text = body.text
    comment.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(comment)
    return comment


@router.delete("/responses/{response_id}/comments/{comment_id}", status_code=204)
async def delete_participant_comment(
    response_id: int,
    comment_id: int,
    x_participant_token: Annotated[
        str, Header(alias="X-Participant-Token", min_length=1, max_length=128)
    ],
    db: AsyncSession = Depends(get_db),
):
    await get_participant_response_or_404(response_id, x_participant_token, db)
    result = await db.execute(
        select(ParticipantComment).where(
            ParticipantComment.id == comment_id, ParticipantComment.response_id == response_id
        )
    )
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    await db.delete(comment)


# ── Researcher analytics: engagement stats ───────────


@router.get("/{survey_id}/engagement-stats", response_model=SurveyEngagementStats)
async def get_engagement_stats(
    survey_id: int,
    include_preview: bool = False,
    researcher: Researcher = Depends(get_current_researcher),
    db: AsyncSession = Depends(get_db),
):
    # verify ownership
    survey_result = await db.execute(
        select(Survey).where(Survey.id == survey_id, Survey.researcher_id == researcher.id)
    )
    survey = survey_result.scalar_one_or_none()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")

    # collect post ids
    posts_result = await db.execute(select(SurveyPost.id).where(SurveyPost.survey_id == survey_id))
    post_ids = list(posts_result.scalars().all())
    if not post_ids:
        return SurveyEngagementStats(survey_id=survey_id, posts=[])

    # likes counted from ParticipantLike limited to this survey's responses
    likes_counts_result = await db.execute(
        select(ParticipantLike.post_id, func.count(ParticipantLike.id))
        .join(SurveyResponse, ParticipantLike.response_id == SurveyResponse.id)
        .where(*response_scope(survey_id, include_preview))
        .group_by(ParticipantLike.post_id)
    )
    likes_map = {pid: cnt for pid, cnt in likes_counts_result.all()}

    # comments counted from ParticipantComment limited to this survey's responses
    # Participant comments (new table) counts + keys for de-dup
    pc_rows_result = await db.execute(
        select(ParticipantComment)
        .join(SurveyResponse, ParticipantComment.response_id == SurveyResponse.id)
        .where(*response_scope(survey_id, include_preview))
    )
    pc_rows = pc_rows_result.scalars().all()
    comments_map: dict[int, int] = {}
    pc_keys: set[tuple[int, int, str]] = set()
    for c in pc_rows:
        comments_map[c.post_id] = comments_map.get(c.post_id, 0) + 1
        pc_keys.add((c.response_id, c.post_id, (c.text or "").strip()))

    # ── Fallbacks for data created before new tables ─────────────────────
    # If there are no rows in ParticipantLike/ParticipantComment yet (old UI),
    # infer likes from latest like/unlike interaction per (response, post),
    # and infer comments from comment interactions.
    # Latest like status subquery
    latest_like_ts = (
        select(
            ParticipantInteraction.response_id,
            ParticipantInteraction.post_id,
            func.max(ParticipantInteraction.timestamp).label("max_ts"),
        )
        .join(SurveyResponse, ParticipantInteraction.response_id == SurveyResponse.id)
        .where(
            *response_scope(survey_id, include_preview),
            ParticipantInteraction.action_type.in_(["like", "unlike"]),
        )
        .group_by(ParticipantInteraction.response_id, ParticipantInteraction.post_id)
        .subquery()
    )
    inferred_likes_result = await db.execute(
        select(ParticipantInteraction.post_id, func.count())
        .join(
            latest_like_ts,
            (ParticipantInteraction.response_id == latest_like_ts.c.response_id)
            & (ParticipantInteraction.post_id == latest_like_ts.c.post_id)
            & (ParticipantInteraction.timestamp == latest_like_ts.c.max_ts),
        )
        .where(ParticipantInteraction.action_type == "like")
        .group_by(ParticipantInteraction.post_id)
    )
    inferred_likes_map = {pid: cnt for pid, cnt in inferred_likes_result.all()}
    # Merge only where explicit likes are missing
    for pid, cnt in inferred_likes_map.items():
        likes_map.setdefault(pid, cnt)

    # Legacy interactions fallback, but skip those already present in new table (de-dup)
    pi_rows_result = await db.execute(
        select(ParticipantInteraction)
        .join(SurveyResponse, ParticipantInteraction.response_id == SurveyResponse.id)
        .where(
            *response_scope(survey_id, include_preview),
            ParticipantInteraction.action_type == "comment",
            ParticipantInteraction.comment_text.is_not(None),
        )
    )
    seen_keys: set[tuple[int, int, str]] = set()
    for i in pi_rows_result.scalars().all():
        key = (i.response_id, i.post_id, (i.comment_text or "").strip())
        if key in pc_keys or key in seen_keys:
            continue
        comments_map[i.post_id] = comments_map.get(i.post_id, 0) + 1
        seen_keys.add(key)

    # shares counted from interactions (share is not toggle)
    shares_counts_result = await db.execute(
        select(ParticipantInteraction.post_id, func.count(ParticipantInteraction.id))
        .join(SurveyResponse, ParticipantInteraction.response_id == SurveyResponse.id)
        .where(
            *response_scope(survey_id, include_preview),
            ParticipantInteraction.action_type == "share",
        )
        .group_by(ParticipantInteraction.post_id)
    )
    shares_map = {pid: cnt for pid, cnt in shares_counts_result.all()}

    stats = [
        PostEngagementStat(
            post_id=pid,
            likes=likes_map.get(pid, 0),
            participant_comments=comments_map.get(pid, 0),
            shares=shares_map.get(pid, 0),
        )
        for pid in post_ids
    ]
    return SurveyEngagementStats(survey_id=survey_id, posts=stats)


@router.get("/{survey_id}/participant-comments", response_model=SurveyParticipantCommentsOut)
async def get_participant_comments(
    survey_id: int,
    include_preview: bool = False,
    researcher: Researcher = Depends(get_current_researcher),
    db: AsyncSession = Depends(get_db),
):
    # verify ownership
    survey_result = await db.execute(
        select(Survey).where(Survey.id == survey_id, Survey.researcher_id == researcher.id)
    )
    if not survey_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Survey not found")

    # Comments from new table
    pc_result = await db.execute(
        select(ParticipantComment)
        .join(SurveyResponse, ParticipantComment.response_id == SurveyResponse.id)
        .where(*response_scope(survey_id, include_preview))
    )
    by_post: dict[int, list[ParticipantCommentOut]] = {}
    pc_keys: set[tuple[int, int, str]] = set()
    for c in pc_result.scalars().all():
        by_post.setdefault(c.post_id, []).append(ParticipantCommentOut.model_validate(c))
        pc_keys.add((c.response_id, c.post_id, (c.text or "").strip()))

    # Comments from legacy interactions (fallback) — de-duplicate with new table
    pi_result = await db.execute(
        select(ParticipantInteraction)
        .join(SurveyResponse, ParticipantInteraction.response_id == SurveyResponse.id)
        .where(
            *response_scope(survey_id, include_preview),
            ParticipantInteraction.action_type == "comment",
            ParticipantInteraction.comment_text.is_not(None),
        )
    )
    seen_keys: set[tuple[int, int, str]] = set()
    for i in pi_result.scalars().all():
        key = (i.response_id, i.post_id, (i.comment_text or "").strip())
        if key in pc_keys or key in seen_keys:
            continue
        by_post.setdefault(i.post_id, []).append(
            ParticipantCommentOut(
                id=i.id,
                post_id=i.post_id,
                text=i.comment_text or "",
                created_at=i.timestamp,
                updated_at=None,
            )
        )
        seen_keys.add(key)

    # Sort each post's comments by created_at
    for pid in list(by_post.keys()):
        by_post[pid].sort(key=lambda x: x.created_at)
    return SurveyParticipantCommentsOut(comments_by_post=by_post)


@router.get("/{survey_id}/analytics-summary", response_model=SurveyAnalyticsOut)
async def get_analytics_summary(
    survey_id: int,
    include_preview: bool = False,
    assigned_group: int | None = None,
    condition: int | None = None,
    language: str | None = None,
    response_status: str | None = None,
    calibration_passed: bool | None = None,
    researcher: Researcher = Depends(get_current_researcher),
    db: AsyncSession = Depends(get_db),
):
    survey_result = await db.execute(
        select(Survey).where(Survey.id == survey_id, Survey.researcher_id == researcher.id)
    )
    survey = survey_result.scalar_one_or_none()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")

    # Mirror the export filter contract: `assigned_group` takes precedence,
    # falling back to `condition` so both query params behave identically.
    effective_group = assigned_group if assigned_group is not None else condition

    scope = analytics_response_scope(
        survey_id,
        include_preview=include_preview,
        assigned_group=effective_group,
        language=language,
        response_status=response_status,
        calibration_passed=calibration_passed,
    )

    responses_result = await db.execute(select(SurveyResponse).where(*scope))
    responses = responses_result.scalars().all()
    total_responses = len(responses)
    completed_responses = [r for r in responses if r.status == "completed" and r.completed_at]
    completion_rate = (len(completed_responses) / total_responses * 100) if total_responses else 0

    completion_minutes = [
        max((r.completed_at - r.started_at).total_seconds() / 60, 0)
        for r in completed_responses
        if r.started_at and r.completed_at
    ]
    avg_completion_minutes = (
        sum(completion_minutes) / len(completion_minutes) if completion_minutes else 0
    )
    # Include "flagged" (speed-test-failed) responses in fast_completions — they are by definition
    # the fastest completions and must not vanish from the data quality dashboard.
    fast_completions = sum(
        1
        for r in responses
        if r.status in ("completed", "flagged")
        and r.started_at
        and r.completed_at
        and (r.completed_at - r.started_at).total_seconds() / 60 < 2
    )

    calibration_result = await db.execute(
        select(CalibrationSession)
        .join(SurveyResponse, CalibrationSession.response_id == SurveyResponse.id)
        .where(*scope)
    )
    calibration_sessions = calibration_result.scalars().all()
    successful_calibrations = [
        session
        for session in calibration_sessions
        if session.status == "completed" and session.quality != "poor"
    ]
    calibration_success_rate = (
        len(successful_calibrations) / len(calibration_sessions) * 100
        if calibration_sessions
        else 0
    )

    click_rows_result = await db.execute(
        select(ClickRecord.response_id, ClickRecord.post_id, func.count(ClickRecord.id))
        .join(SurveyResponse, ClickRecord.response_id == SurveyResponse.id)
        .where(*scope)
        .group_by(ClickRecord.response_id, ClickRecord.post_id)
    )
    click_rows = click_rows_result.all()
    response_click_totals: dict[int, int] = {}
    post_clicks_map: dict[int, int] = {}
    group_clicks_map: dict[int, int] = {}
    response_to_group = {response.id: response.assigned_group for response in responses}
    for response_id, post_id, count in click_rows:
        response_click_totals[response_id] = response_click_totals.get(response_id, 0) + count
        if post_id is not None:
            post_clicks_map[post_id] = post_clicks_map.get(post_id, 0) + count
        group_id = response_to_group.get(response_id, 1)
        group_clicks_map[group_id] = group_clicks_map.get(group_id, 0) + count
    total_clicks = sum(response_click_totals.values())

    gaze_samples_result = await db.execute(
        select(func.count(GazeRecord.id))
        .join(SurveyResponse, GazeRecord.response_id == SurveyResponse.id)
        .where(*scope)
    )
    total_gaze_samples = gaze_samples_result.scalar_one() or 0

    likes_result = await db.execute(
        select(ParticipantLike.response_id, ParticipantLike.post_id)
        .join(SurveyResponse, ParticipantLike.response_id == SurveyResponse.id)
        .where(*scope)
    )
    like_rows = likes_result.all()
    response_like_totals: dict[int, int] = {}
    post_likes_map: dict[int, int] = {}
    group_likes_map: dict[int, int] = {}
    for response_id, post_id in like_rows:
        response_like_totals[response_id] = response_like_totals.get(response_id, 0) + 1
        post_likes_map[post_id] = post_likes_map.get(post_id, 0) + 1
        group_id = response_to_group.get(response_id, 1)
        group_likes_map[group_id] = group_likes_map.get(group_id, 0) + 1
    total_likes = len(like_rows)

    comments_result = await db.execute(
        select(ParticipantComment)
        .join(SurveyResponse, ParticipantComment.response_id == SurveyResponse.id)
        .where(*scope)
    )
    participant_comments = comments_result.scalars().all()
    response_comment_totals: dict[int, int] = {}
    post_comment_map: dict[int, int] = {}
    group_comment_map: dict[int, int] = {}
    comment_texts_by_response: dict[int, list[str]] = {}
    for comment in participant_comments:
        response_comment_totals[comment.response_id] = (
            response_comment_totals.get(comment.response_id, 0) + 1
        )
        post_comment_map[comment.post_id] = post_comment_map.get(comment.post_id, 0) + 1
        group_id = response_to_group.get(comment.response_id, 1)
        group_comment_map[group_id] = group_comment_map.get(group_id, 0) + 1
        comment_texts_by_response.setdefault(comment.response_id, []).append(
            (comment.text or "").strip().lower()
        )
    total_comments = len(participant_comments)

    shares_result = await db.execute(
        select(ParticipantInteraction.response_id, ParticipantInteraction.post_id)
        .join(SurveyResponse, ParticipantInteraction.response_id == SurveyResponse.id)
        .where(
            *scope,
            ParticipantInteraction.action_type == "share",
        )
    )
    share_rows = shares_result.all()
    response_share_totals: dict[int, int] = {}
    post_shares_map: dict[int, int] = {}
    group_shares_map: dict[int, int] = {}
    for response_id, post_id in share_rows:
        response_share_totals[response_id] = response_share_totals.get(response_id, 0) + 1
        post_shares_map[post_id] = post_shares_map.get(post_id, 0) + 1
        group_id = response_to_group.get(response_id, 1)
        group_shares_map[group_id] = group_shares_map.get(group_id, 0) + 1
    total_shares = len(share_rows)

    low_interaction_responses = 0
    duplicate_comment_sessions = 0
    for response in responses:
        response_id = response.id
        interaction_total = (
            response_click_totals.get(response_id, 0)
            + response_like_totals.get(response_id, 0)
            + response_comment_totals.get(response_id, 0)
            + response_share_totals.get(response_id, 0)
        )
        if interaction_total == 0:
            low_interaction_responses += 1
        comment_texts = [text for text in comment_texts_by_response.get(response_id, []) if text]
        if len(comment_texts) > len(set(comment_texts)):
            duplicate_comment_sessions += 1

    group_breakdown: list[GroupAnalyticsOut] = []
    for group_id in range(1, survey.num_groups + 1):
        group_responses = [
            response for response in responses if response.assigned_group == group_id
        ]
        group_completed = [
            response for response in group_responses if response.status == "completed"
        ]
        group_breakdown.append(
            GroupAnalyticsOut(
                group_id=group_id,
                participants=len(group_responses),
                completed=len(group_completed),
                completion_rate=(len(group_completed) / len(group_responses) * 100)
                if group_responses
                else 0,
                clicks=group_clicks_map.get(group_id, 0),
                likes=group_likes_map.get(group_id, 0),
                comments=group_comment_map.get(group_id, 0),
                shares=group_shares_map.get(group_id, 0),
            )
        )

    researcher_comments_result = await db.execute(
        select(PostComment.post_id, func.count(PostComment.id))
        .join(SurveyPost, PostComment.post_id == SurveyPost.id)
        .where(SurveyPost.survey_id == survey_id)
        .group_by(PostComment.post_id)
    )
    researcher_comment_map = {post_id: count for post_id, count in researcher_comments_result.all()}

    posts_result = await db.execute(
        select(SurveyPost).where(SurveyPost.survey_id == survey_id).order_by(SurveyPost.order)
    )
    posts = posts_result.scalars().all()
    post_rows = [
        PostAnalyticsRowOut(
            post_id=post.id,
            title=post.display_title or post.fetched_title or "Untitled",
            source=post.fetched_source,
            visible_groups=post.visible_to_groups,
            clicks=post_clicks_map.get(post.id, 0),
            likes=post_likes_map.get(post.id, 0),
            comments=researcher_comment_map.get(post.id, 0),
            shares=post_shares_map.get(post.id, 0),
            participant_comment_count=post_comment_map.get(post.id, 0),
        )
        for post in posts
    ]

    top_post = max(post_rows, key=lambda post: post.clicks, default=None)
    top_group = max(group_breakdown, key=lambda group: group.clicks, default=None)
    summary_parts = []
    if top_post and top_post.clicks > 0:
        summary_parts.append(
            f'"{top_post.title}" is driving the strongest engagement with {top_post.clicks} recorded clicks.'
        )
    if top_group and top_group.participants > 0:
        summary_parts.append(
            f"Group {top_group.group_id} is currently the most active cohort with {top_group.clicks} clicks and a {top_group.completion_rate:.0f}% completion rate."
        )
    if calibration_sessions:
        summary_parts.append(
            f"Calibration quality is holding at {calibration_success_rate:.0f}% acceptable-or-better sessions."
        )
    if total_gaze_samples or total_clicks:
        summary_parts.append(
            f"The exportable dataset currently includes {total_gaze_samples} gaze samples and {total_clicks} click records."
        )
    summary = (
        " ".join(summary_parts)
        or "Collect participant responses to unlock engagement and response-quality insights."
    )

    return SurveyAnalyticsOut(
        survey_id=survey_id,
        total_responses=total_responses,
        completion_rate=completion_rate,
        avg_completion_minutes=avg_completion_minutes,
        calibration_success_rate=calibration_success_rate,
        total_gaze_samples=total_gaze_samples,
        total_clicks=total_clicks,
        total_likes=total_likes,
        total_comments=total_comments,
        total_shares=total_shares,
        fast_completions=fast_completions,
        low_interaction_responses=low_interaction_responses,
        duplicate_comment_sessions=duplicate_comment_sessions,
        group_breakdown=group_breakdown,
        posts=post_rows,
        summary=summary,
    )


# ── Question Endpoints ────────────────────────────────────────────────────────


@router.post("/{survey_id}/posts/{post_id}/questions", response_model=QuestionOut, status_code=201)
@router.post(
    "/surveys/{survey_id}/posts/{post_id}/questions",
    response_model=QuestionOut,
    status_code=201,
    include_in_schema=False,
)
async def create_question(
    survey_id: int,
    post_id: int,
    body: CreateQuestionRequest,
    db: AsyncSession = Depends(get_db),
    researcher: Researcher = Depends(get_current_researcher),
):
    await get_survey_or_404(survey_id, researcher.id, db)
    await _ensure_no_survey_responses(
        survey_id,
        db,
        "Cannot add questions after participant responses exist",
    )
    post = await db.get(SurveyPost, post_id)
    if not post or post.survey_id != survey_id:
        raise HTTPException(404, "Post not found")
    validate_scale_config(body.question_type, body.config)
    q = Question(survey_id=survey_id, post_id=post_id, **body.model_dump())
    db.add(q)
    await db.commit()
    await db.refresh(q)
    return q


@router.get("/{survey_id}/posts/{post_id}/questions", response_model=list[QuestionOut])
@router.get(
    "/surveys/{survey_id}/posts/{post_id}/questions",
    response_model=list[QuestionOut],
    include_in_schema=False,
)
async def list_questions(
    survey_id: int,
    post_id: int,
    db: AsyncSession = Depends(get_db),
    researcher: Researcher = Depends(get_current_researcher),
):
    await get_survey_or_404(survey_id, researcher.id, db)
    post = await db.get(SurveyPost, post_id)
    if not post or post.survey_id != survey_id:
        raise HTTPException(404, "Post not found")
    result = await db.execute(
        select(Question).where(Question.post_id == post_id).order_by(Question.order)
    )
    return result.scalars().all()


@router.patch("/{survey_id}/posts/{post_id}/questions/{question_id}", response_model=QuestionOut)
@router.patch(
    "/surveys/{survey_id}/posts/{post_id}/questions/{question_id}",
    response_model=QuestionOut,
    include_in_schema=False,
)
async def update_question(
    survey_id: int,
    post_id: int,
    question_id: int,
    body: UpdateQuestionRequest,
    db: AsyncSession = Depends(get_db),
    researcher: Researcher = Depends(get_current_researcher),
):
    await get_survey_or_404(survey_id, researcher.id, db)
    q = await db.get(Question, question_id)
    if not q or q.post_id != post_id or q.survey_id != survey_id:
        raise HTTPException(404, "Question not found")
    await _ensure_no_survey_responses(
        survey_id,
        db,
        "Cannot change questions after participant responses exist",
    )
    updates = body.model_dump(exclude_unset=True)
    new_type = updates.get("question_type", q.question_type)
    new_config = updates.get("config", q.config)
    validate_scale_config(new_type, new_config)
    for k, v in updates.items():
        setattr(q, k, v)
    await db.commit()
    await db.refresh(q)
    return q


@router.delete("/{survey_id}/posts/{post_id}/questions/{question_id}", status_code=204)
@router.delete(
    "/surveys/{survey_id}/posts/{post_id}/questions/{question_id}",
    status_code=204,
    include_in_schema=False,
)
async def delete_question(
    survey_id: int,
    post_id: int,
    question_id: int,
    db: AsyncSession = Depends(get_db),
    researcher: Researcher = Depends(get_current_researcher),
):
    await get_survey_or_404(survey_id, researcher.id, db)
    q = await db.get(Question, question_id)
    if not q or q.post_id != post_id or q.survey_id != survey_id:
        raise HTTPException(404, "Question not found")
    await _ensure_no_survey_responses(
        survey_id,
        db,
        "Cannot delete questions after participant responses exist",
    )
    await db.delete(q)
    await db.commit()


@router.post("/{survey_id}/questions", response_model=QuestionOut, status_code=201)
async def create_survey_question(
    survey_id: int,
    body: CreateQuestionRequest,
    db: AsyncSession = Depends(get_db),
    researcher: Researcher = Depends(get_current_researcher),
):
    await get_survey_or_404(survey_id, researcher.id, db)
    await _ensure_no_survey_responses(
        survey_id,
        db,
        "Cannot add questions after participant responses exist",
    )
    validate_scale_config(body.question_type, body.config)
    q = Question(survey_id=survey_id, post_id=None, **body.model_dump())
    db.add(q)
    await db.commit()
    await db.refresh(q)
    return q


@router.get("/{survey_id}/questions", response_model=list[QuestionOut])
async def list_survey_questions(
    survey_id: int,
    db: AsyncSession = Depends(get_db),
    researcher: Researcher = Depends(get_current_researcher),
):
    await get_survey_or_404(survey_id, researcher.id, db)
    result = await db.execute(
        select(Question)
        .where(Question.survey_id == survey_id, Question.post_id.is_(None))
        .order_by(Question.order)
    )
    return result.scalars().all()


@router.patch("/{survey_id}/questions/{question_id}", response_model=QuestionOut)
async def update_survey_question(
    survey_id: int,
    question_id: int,
    body: UpdateQuestionRequest,
    db: AsyncSession = Depends(get_db),
    researcher: Researcher = Depends(get_current_researcher),
):
    await get_survey_or_404(survey_id, researcher.id, db)
    q = await db.get(Question, question_id)
    if not q or q.survey_id != survey_id or q.post_id is not None:
        raise HTTPException(404, "Question not found")
    await _ensure_no_survey_responses(
        survey_id,
        db,
        "Cannot change questions after participant responses exist",
    )
    updates = body.model_dump(exclude_unset=True)
    new_type = updates.get("question_type", q.question_type)
    new_config = updates.get("config", q.config)
    validate_scale_config(new_type, new_config)
    for k, v in updates.items():
        setattr(q, k, v)
    await db.commit()
    await db.refresh(q)
    return q


@router.delete("/{survey_id}/questions/{question_id}", status_code=204)
async def delete_survey_question(
    survey_id: int,
    question_id: int,
    db: AsyncSession = Depends(get_db),
    researcher: Researcher = Depends(get_current_researcher),
):
    await get_survey_or_404(survey_id, researcher.id, db)
    q = await db.get(Question, question_id)
    if not q or q.survey_id != survey_id or q.post_id is not None:
        raise HTTPException(404, "Question not found")
    await _ensure_no_survey_responses(
        survey_id,
        db,
        "Cannot delete questions after participant responses exist",
    )
    await db.delete(q)
    await db.commit()


# ── Question Response Endpoints ───────────────────────────────────────────────


@router.post(
    "/responses/{response_id}/questions/{question_id}/answer",
    response_model=QuestionResponseOut,
    status_code=201,
)
async def submit_question_response(
    response_id: int,
    question_id: int,
    body: SubmitQuestionResponseRequest,
    db: AsyncSession = Depends(get_db),
):
    from app.models.question_response import QuestionResponse

    survey_response = await db.get(SurveyResponse, response_id)
    if not survey_response or survey_response.participant_token != body.participant_token:
        raise HTTPException(404, "Response not found")
    if survey_response.status != "in_progress":
        raise HTTPException(409, "Response is not active")
    if body.question_id != question_id:
        raise HTTPException(400, "Question ID mismatch")
    question = await db.get(Question, question_id)
    if not question:
        raise HTTPException(404, "Question not found")
    if question.survey_id != survey_response.survey_id:
        raise HTTPException(404, "Question not found")
    _validate_question_answer(question, body)
    existing_answer = await db.execute(
        select(QuestionResponse).where(
            QuestionResponse.response_id == response_id,
            QuestionResponse.question_id == question_id,
        )
    )
    if existing_answer.scalar_one_or_none():
        raise HTTPException(409, "Answer already submitted for this question")
    answer = QuestionResponse(
        response_id=response_id,
        question_id=question_id,
        answer_text=body.answer_text,
        answer_value=body.answer_value,
        answer_choices=body.answer_choices,
    )
    db.add(answer)
    await db.commit()
    await db.refresh(answer)
    return answer


@router.get(
    "/responses/{response_id}/answers",
    response_model=list[QuestionResponseOut],
)
async def list_question_responses(
    response_id: int,
    db: AsyncSession = Depends(get_db),
    researcher: Researcher = Depends(get_current_researcher),
):
    from sqlalchemy import select

    from app.models.question_response import QuestionResponse

    # Enforce that the calling researcher owns the survey this response belongs to
    ownership_q = await db.execute(
        select(SurveyResponse.id)
        .join(Survey, Survey.id == SurveyResponse.survey_id)
        .where(SurveyResponse.id == response_id, Survey.researcher_id == researcher.id)
    )
    if not ownership_q.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Response not found")

    result = await db.execute(
        select(QuestionResponse).where(QuestionResponse.response_id == response_id)
    )
    return result.scalars().all()
