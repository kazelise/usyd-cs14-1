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
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_researcher
from app.database import get_db
from app.models.participant import (
    ParticipantComment,
    ParticipantInteraction,
    ParticipantLike,
    SurveyResponse,
)
from app.models.question import Question
from app.models.researcher import Researcher
from app.models.survey import PostComment, Survey, SurveyPost
from app.models.tracking import CalibrationSession, ClickRecord
from app.schemas.survey import (
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
        apply_translations_to_question(QuestionOut.model_validate(question), question, language_code)
        for question in sorted(questions, key=lambda item: item.order)
    ]


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
    for field, value in body.model_dump(exclude_unset=True).items():
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
    survey.status = "published"
    survey.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(survey)
    return survey


@router.get("/{survey_id}/export")
async def export_survey_data(
    survey_id: int,
    export_format: Literal["csv", "json"] = Query("csv", alias="format"),
    condition: int | None = None,
    assigned_group: int | None = None,
    language: str | None = None,
    response_status: str | None = None,
    calibration_passed: bool | None = None,
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

    language_code = normalize_optional_language(language)
    return SurveyPreviewResponse(
        survey_id=survey.id,
        assigned_group=assigned_group,
        calibration_required=survey.calibration_enabled,
        calibration_points=survey.calibration_points,
        gaze_tracking_enabled=survey.gaze_tracking_enabled,
        gaze_interval_ms=survey.gaze_interval_ms,
        click_tracking_enabled=survey.click_tracking_enabled,
        language=language_code,
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
    result = await db.execute(
        select(SurveyPost)
        .options(selectinload(SurveyPost.comments), selectinload(SurveyPost.questions))
        .where(SurveyPost.id == post_id, SurveyPost.survey_id == survey_id)
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
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
    result = await db.execute(
        select(SurveyPost).where(SurveyPost.id == post_id, SurveyPost.survey_id == survey_id)
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
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
        .where(Survey.share_code == share_code, Survey.status == "published")
    )
    survey = result.scalar_one_or_none()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found or inactive")
    if survey.share_code_expires_at and survey.share_code_expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Survey link has expired")
        
    language_code = normalize_optional_language(body.language) if body and body.language else None

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
        assigned_group = random.randint(1, survey.num_groups)
        response = SurveyResponse(
            survey_id=survey.id,
            assigned_group=assigned_group,
            language=language_code,
            screen_width=body.screen_width if body else None,
            screen_height=body.screen_height if body else None,
            user_agent=body.user_agent if body else None,
            status="in_progress",
            started_at=datetime.utcnow(),
        )
        db.add(response)
        await db.flush()
        await db.refresh(response)
    else:
        assigned_group = response.assigned_group
        language_code = response.language
        # On resume, look at any prior CalibrationSession attached to this
        # response. If it was completed, signal the frontend to skip the
        # calibration UI. If it was abandoned mid-way (in_progress), drop it
        # so the frontend can re-create cleanly without hitting the
        # "session already exists" 409 from create_calibration_session.
        existing_calib_q = await db.execute(
            select(CalibrationSession).where(
                CalibrationSession.response_id == response.id
            )
        )
        existing_calib = existing_calib_q.scalar_one_or_none()
        if existing_calib is not None:
            if existing_calib.status == "completed":
                calibration_completed = True
            else:
                await db.delete(existing_calib)
                await db.flush()

    return StartSurveyResponse(
        response_id=response.id,
        participant_token=response.participant_token,
        survey_id=survey.id,
        assigned_group=assigned_group,
        calibration_required=survey.calibration_enabled,
        calibration_points=survey.calibration_points,
        calibration_completed=calibration_completed,
        gaze_tracking_enabled=survey.gaze_tracking_enabled,
        gaze_interval_ms=survey.gaze_interval_ms,
        click_tracking_enabled=survey.click_tracking_enabled,
        language=response.language,
        posts=build_participant_posts(survey, assigned_group, language_code),
        questions=build_participant_questions(survey, language_code),
    )


@router.get("/public/{share_code}", response_model=PublicSurveyOut)
async def get_public_survey(
    share_code: str,
    language: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Public metadata for start screen before starting a session."""
    result = await db.execute(
        select(Survey)
        .options(selectinload(Survey.translations))
        .where(Survey.share_code == share_code, Survey.status == "published")
    )
    survey = result.scalar_one_or_none()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found or not published")
    if survey.share_code_expires_at and survey.share_code_expires_at < datetime.utcnow():
        raise HTTPException(status_code=410, detail="Survey link has expired")
    return apply_translations_to_public_survey(survey, language)


@router.post("/responses/{response_id}/interact", response_model=InteractionOut)
async def record_interaction(
    response_id: int,
    body: InteractionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Record a participant interaction with a post (like, comment, or click to original)."""
    result = await db.execute(select(SurveyResponse).where(SurveyResponse.id == response_id))
    response = result.scalar_one_or_none()
    if not response:
        raise HTTPException(status_code=404, detail="Response not found")
    post_result = await db.execute(
        select(SurveyPost.id).where(
            SurveyPost.id == body.post_id,
            SurveyPost.survey_id == response.survey_id,
        )
    )
    if not post_result.scalar_one_or_none():
        raise HTTPException(status_code=422, detail="Post does not belong to this response survey")

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


@router.post("/responses/{response_id}/likes/toggle")
async def toggle_like(
    response_id: int,
    body: ToggleLikeRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SurveyResponse).where(SurveyResponse.id == response_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Response not found")

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
    db: AsyncSession = Depends(get_db),
):
    # ensure response exists
    result = await db.execute(select(SurveyResponse).where(SurveyResponse.id == response_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Response not found")

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
    return ResponseStateOut(liked_post_ids=liked_post_ids, comments_by_post=comments_by_post)


@router.post("/responses/{response_id}/complete")
async def complete_response(
    response_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Mark a survey response as completed."""
    result = await db.execute(select(SurveyResponse).where(SurveyResponse.id == response_id))
    response = result.scalar_one_or_none()
    if not response:
        raise HTTPException(status_code=404, detail="Response not found")

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
    return {"status": response.status, "duration_seconds": duration}


class ParticipantCommentIn(BaseModel):
    post_id: int
    text: str
    author_name: str | None = None


class ParticipantCommentPatch(BaseModel):
    text: str


@router.post(
    "/responses/{response_id}/comments", response_model=ParticipantCommentOut, status_code=201
)
async def create_participant_comment(
    response_id: int,
    body: ParticipantCommentIn,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SurveyResponse).where(SurveyResponse.id == response_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Response not found")

    comment = ParticipantComment(
        response_id=response_id, post_id=body.post_id, text=body.text, author_name=body.author_name
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
    db: AsyncSession = Depends(get_db),
):
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
        .where(SurveyResponse.survey_id == survey_id)
        .group_by(ParticipantLike.post_id)
    )
    likes_map = {pid: cnt for pid, cnt in likes_counts_result.all()}

    # comments counted from ParticipantComment limited to this survey's responses
    # Participant comments (new table) counts + keys for de-dup
    pc_rows_result = await db.execute(
        select(ParticipantComment)
        .join(SurveyResponse, ParticipantComment.response_id == SurveyResponse.id)
        .where(SurveyResponse.survey_id == survey_id)
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
            SurveyResponse.survey_id == survey_id,
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
            SurveyResponse.survey_id == survey_id,
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
            SurveyResponse.survey_id == survey_id,
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
        .where(SurveyResponse.survey_id == survey_id)
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
            SurveyResponse.survey_id == survey_id,
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
    researcher: Researcher = Depends(get_current_researcher),
    db: AsyncSession = Depends(get_db),
):
    survey_result = await db.execute(
        select(Survey).where(Survey.id == survey_id, Survey.researcher_id == researcher.id)
    )
    survey = survey_result.scalar_one_or_none()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")

    responses_result = await db.execute(
        select(SurveyResponse).where(SurveyResponse.survey_id == survey_id)
    )
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
    fast_completions = sum(1 for minutes in completion_minutes if minutes < 2)

    calibration_result = await db.execute(
        select(CalibrationSession)
        .join(SurveyResponse, CalibrationSession.response_id == SurveyResponse.id)
        .where(SurveyResponse.survey_id == survey_id)
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
        .where(SurveyResponse.survey_id == survey_id)
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

    likes_result = await db.execute(
        select(ParticipantLike.response_id, ParticipantLike.post_id)
        .join(SurveyResponse, ParticipantLike.response_id == SurveyResponse.id)
        .where(SurveyResponse.survey_id == survey_id)
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
        .where(SurveyResponse.survey_id == survey_id)
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
            SurveyResponse.survey_id == survey_id,
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
            comments=post_comment_map.get(post.id, 0),
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
    post = await db.get(SurveyPost, post_id)
    if not post or post.survey_id != survey_id:
        raise HTTPException(404, "Post not found")
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
    for k, v in body.model_dump(exclude_unset=True).items():
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
    for k, v in body.model_dump(exclude_unset=True).items():
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
    if not survey_response:
        raise HTTPException(404, "Response not found")
    if body.participant_token and survey_response.participant_token != body.participant_token:
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

    result = await db.execute(
        select(QuestionResponse).where(QuestionResponse.response_id == response_id)
    )
    return result.scalars().all()
