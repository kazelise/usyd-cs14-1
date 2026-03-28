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

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_researcher
from app.database import get_db
from app.models.researcher import Researcher
from app.models.survey import PostComment, Survey, SurveyPost
from app.models.participant import ParticipantInteraction, SurveyResponse
from app.schemas.survey import (
    CommentIn,
    CommentOut,
    CreatePostRequest,
    CreateSurveyRequest,
    InteractionOut,
    InteractionRequest,
    PostOut,
    StartSurveyResponse,
    SurveyListOut,
    SurveyOut,
    UpdatePostRequest,
    UpdateSurveyRequest,
)
from app.services.og_fetcher import fetch_og_metadata

router = APIRouter(prefix="/surveys", tags=["Surveys"])


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
    await db.flush()
    await db.refresh(survey)
    return survey


@router.get("", response_model=SurveyListOut)
async def list_surveys(
    status: str | None = None,
    researcher: Researcher = Depends(get_current_researcher),
    db: AsyncSession = Depends(get_db),
):
    """List all surveys owned by the current researcher."""
    query = select(Survey).where(Survey.researcher_id == researcher.id)
    if status:
        query = query.where(Survey.status == status)
    result = await db.execute(query.order_by(Survey.created_at.desc()))
    surveys = result.scalars().all()
    count_result = await db.execute(
        select(func.count(Survey.id)).where(Survey.researcher_id == researcher.id)
    )
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
    """Update survey settings (title, groups, tracking config, etc.)."""
    result = await db.execute(
        select(Survey).where(Survey.id == survey_id, Survey.researcher_id == researcher.id)
    )
    survey = result.scalar_one_or_none()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(survey, field, value)
    survey.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(survey)
    return survey


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
    result = await db.execute(
        select(Survey).where(Survey.id == survey_id, Survey.researcher_id == researcher.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Survey not found")

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
        .options(selectinload(SurveyPost.comments))
        .where(SurveyPost.id == post.id)
    )
    post = result.scalar_one()
    return post


@router.get("/{survey_id}/posts", response_model=list[PostOut])
async def list_posts(
    survey_id: int,
    researcher: Researcher = Depends(get_current_researcher),
    db: AsyncSession = Depends(get_db),
):
    """List all posts in a survey (with their fake comments)."""
    result = await db.execute(
        select(SurveyPost)
        .options(selectinload(SurveyPost.comments))
        .where(SurveyPost.survey_id == survey_id)
        .order_by(SurveyPost.order)
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
        .options(selectinload(SurveyPost.comments))
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
    db: AsyncSession = Depends(get_db),
):
    """Start a survey as a participant.

    The participant is randomly assigned to a group (coin flip).
    Only posts visible to the assigned group are returned.
    """
    result = await db.execute(
        select(Survey)
        .options(selectinload(Survey.posts).selectinload(SurveyPost.comments))
        .where(Survey.share_code == share_code, Survey.status == "published")
    )
    survey = result.scalar_one_or_none()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found or not published")

    # Random group assignment
    assigned_group = random.randint(1, survey.num_groups)

    response = SurveyResponse(
        survey_id=survey.id,
        assigned_group=assigned_group,
    )
    db.add(response)
    await db.flush()
    await db.refresh(response)

    # Filter posts by group visibility
    visible_posts = []
    for post in survey.posts:
        if post.visible_to_groups is None or assigned_group in post.visible_to_groups:
            visible_posts.append(post)

    return StartSurveyResponse(
        response_id=response.id,
        survey_id=survey.id,
        assigned_group=assigned_group,
        calibration_required=survey.calibration_enabled,
        gaze_tracking_enabled=survey.gaze_tracking_enabled,
        gaze_interval_ms=survey.gaze_interval_ms,
        click_tracking_enabled=survey.click_tracking_enabled,
        posts=visible_posts,
    )


@router.post("/responses/{response_id}/interact", response_model=InteractionOut)
async def record_interaction(
    response_id: int,
    body: InteractionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Record a participant interaction with a post (like, comment, or click to original)."""
    result = await db.execute(
        select(SurveyResponse).where(SurveyResponse.id == response_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Response not found")

    interaction = ParticipantInteraction(
        response_id=response_id,
        post_id=body.post_id,
        action_type=body.action_type,
        comment_text=body.comment_text if body.action_type == "comment" else None,
    )
    db.add(interaction)
    await db.flush()
    await db.refresh(interaction)
    return interaction


@router.post("/responses/{response_id}/complete")
async def complete_response(
    response_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Mark a survey response as completed."""
    result = await db.execute(
        select(SurveyResponse).where(SurveyResponse.id == response_id)
    )
    response = result.scalar_one_or_none()
    if not response:
        raise HTTPException(status_code=404, detail="Response not found")
    response.status = "completed"
    response.completed_at = datetime.utcnow()
    return {"status": "completed"}
