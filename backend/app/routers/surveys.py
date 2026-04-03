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
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_researcher
from app.database import get_db
from app.models.researcher import Researcher
from app.models.survey import PostComment, Survey, SurveyPost
from app.models.participant import (
    ParticipantInteraction,
    ParticipantLike,
    ParticipantComment,
    SurveyResponse,
)
from app.schemas.survey import (
    CommentIn,
    CommentOut,
    CreatePostRequest,
    CreateSurveyRequest,
    InteractionOut,
    InteractionRequest,
    ParticipantCommentOut,
    PublicSurveyOut,
    ResponseStateOut,
    PostEngagementStat,
    SurveyEngagementStats,
    SurveyParticipantCommentsOut,
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
    # Verify ownership
    survey_result = await db.execute(
        select(Survey).where(Survey.id == survey_id, Survey.researcher_id == researcher.id)
    )
    if not survey_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Survey not found")

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

    # Filter posts by group visibility and apply group overrides
    visible_posts = []
    for post in survey.posts:
        if post.visible_to_groups is None or assigned_group in post.visible_to_groups:
            # Apply per-group display overrides if configured
            if post.group_overrides and str(assigned_group) in post.group_overrides:
                overrides = post.group_overrides[str(assigned_group)]
                for field, value in overrides.items():
                    if hasattr(post, field):
                        setattr(post, field, value)
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


@router.get("/public/{share_code}", response_model=PublicSurveyOut)
async def get_public_survey(
    share_code: str,
    db: AsyncSession = Depends(get_db),
):
    """Public metadata for start screen before starting a session."""
    result = await db.execute(
        select(Survey).where(Survey.share_code == share_code, Survey.status == "published")
    )
    survey = result.scalar_one_or_none()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found or not published")
    return survey


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
        select(ParticipantComment).where(ParticipantComment.response_id == response_id).order_by(ParticipantComment.created_at)
    )
    comments = comments_result.scalars().all()
    comments_by_post: dict[int, list[ParticipantCommentOut]] = {}
    for c in comments:
        comments_by_post.setdefault(c.post_id, []).append(
            ParticipantCommentOut.model_validate(c)
        )
    return ResponseStateOut(liked_post_ids=liked_post_ids, comments_by_post=comments_by_post)


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
    await db.flush()
    return {"status": "completed"}


class ParticipantCommentIn(BaseModel):
    post_id: int
    text: str
    author_name: str | None = None


class ParticipantCommentPatch(BaseModel):
    text: str


@router.post("/responses/{response_id}/comments", response_model=ParticipantCommentOut, status_code=201)
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


@router.patch("/responses/{response_id}/comments/{comment_id}", response_model=ParticipantCommentOut)
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
    posts_result = await db.execute(
        select(SurveyPost.id).where(SurveyPost.survey_id == survey_id)
    )
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
