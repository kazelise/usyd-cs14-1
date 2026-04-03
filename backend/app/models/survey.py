"""Survey, SurveyPost, PostComment models. Owned by Backend A/B.

Design notes (from client meeting):
- Researchers create surveys with social media post questions ONLY.
- Researcher pastes a URL → platform auto-fetches OG metadata → creates post card.
- Researcher can override: title, image, likes, comments, shares.
- Researcher manually writes fake comment content.
- Surveys support A/B testing: participants randomly assigned to groups,
  different groups can see different posts or different display settings.
"""

import secrets
from datetime import datetime

from sqlalchemy import JSON, Boolean, ForeignKey, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Survey(Base):
    """A survey created by a researcher. Contains social media post questions."""

    __tablename__ = "surveys"

    id: Mapped[int] = mapped_column(primary_key=True)
    researcher_id: Mapped[int] = mapped_column(ForeignKey("researchers.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft / published / closed
    share_code: Mapped[str] = mapped_column(
        String(20), unique=True, default=lambda: secrets.token_urlsafe(12)
    )

    # ── A/B Testing Configuration ────────────────────
    num_groups: Mapped[int] = mapped_column(SmallInteger, default=1)  # 1 = no A/B testing
    group_names: Mapped[dict | None] = mapped_column(
        JSON
    )  # e.g. {"1": "with_likes", "2": "no_likes"}

    # ── Gaze & Click Tracking ────────────────────────
    gaze_tracking_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    gaze_interval_ms: Mapped[int] = mapped_column(default=1000)  # capture every N ms
    click_tracking_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    calibration_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    calibration_points: Mapped[int] = mapped_column(SmallInteger, default=9)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    researcher: Mapped["Researcher"] = relationship(back_populates="surveys")  # noqa: F821
    posts: Mapped[list["SurveyPost"]] = relationship(
        back_populates="survey", cascade="all, delete-orphan", order_by="SurveyPost.order"
    )
    responses: Mapped[list["SurveyResponse"]] = relationship(back_populates="survey")  # noqa: F821


class SurveyPost(Base):
    """A social media post question within a survey.

    Created by pasting a URL. The platform fetches Open Graph metadata
    (title, image, source) and the researcher can then override any field
    and set fake engagement numbers.
    """

    __tablename__ = "survey_posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    survey_id: Mapped[int] = mapped_column(
        ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False
    )
    order: Mapped[int] = mapped_column(nullable=False)

    # ── Original URL & Auto-Fetched Metadata ─────────
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    fetched_title: Mapped[str | None] = mapped_column(Text)
    fetched_image_url: Mapped[str | None] = mapped_column(Text)
    fetched_description: Mapped[str | None] = mapped_column(Text)
    fetched_source: Mapped[str | None] = mapped_column(String(255))  # e.g. "bbc.com"

    # ── Researcher Overrides (null = use fetched value) ─
    display_title: Mapped[str | None] = mapped_column(Text)
    display_image_url: Mapped[str | None] = mapped_column(Text)

    # ── Fake Engagement Numbers (set by researcher) ──
    display_likes: Mapped[int] = mapped_column(default=0)
    display_comments_count: Mapped[int] = mapped_column(default=0)
    display_shares: Mapped[int] = mapped_column(default=0)
    show_likes: Mapped[bool] = mapped_column(Boolean, default=True)
    show_comments: Mapped[bool] = mapped_column(Boolean, default=True)
    show_shares: Mapped[bool] = mapped_column(Boolean, default=True)

    # ── A/B Group Conditions ─────────────────────────
    # Which groups can see this post. null = visible to all groups.
    visible_to_groups: Mapped[list | None] = mapped_column(JSON)  # e.g. [1, 2]
    # Per-group display overrides. e.g. {"1": {"display_likes": 1000}, "2": {"display_likes": 0}}
    group_overrides: Mapped[dict | None] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    survey: Mapped["Survey"] = relationship(back_populates="posts")
    comments: Mapped[list["PostComment"]] = relationship(
        back_populates="post", cascade="all, delete-orphan", order_by="PostComment.order"
    )


class PostComment(Base):
    """A fake comment added by the researcher to a social media post.

    From the meeting: 'If researchers want to display comments,
    they must manually add the comment content themselves.'
    """

    __tablename__ = "post_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(
        ForeignKey("survey_posts.id", ondelete="CASCADE"), nullable=False
    )
    order: Mapped[int] = mapped_column(nullable=False)
    author_name: Mapped[str] = mapped_column(String(100), nullable=False)
    author_avatar_url: Mapped[str | None] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    post: Mapped["SurveyPost"] = relationship(back_populates="comments")
