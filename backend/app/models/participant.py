"""Participant response and interaction models. Owned by Backend A/B.

Captures: which group the participant was assigned to,
and their interactions (likes, comments) with posts.
"""

import secrets
from datetime import datetime

from sqlalchemy import ForeignKey, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SurveyResponse(Base):
    """One participant's session for a survey."""

    __tablename__ = "survey_responses"

    id: Mapped[int] = mapped_column(primary_key=True)
    survey_id: Mapped[int] = mapped_column(ForeignKey("surveys.id"), nullable=False)
    participant_token: Mapped[str] = mapped_column(
        String(64), unique=True, default=lambda: secrets.token_urlsafe(32)
    )

    # ── A/B Group Assignment ─────────────────────────
    assigned_group: Mapped[int] = mapped_column(SmallInteger, default=1)

    # ── Participant Metadata ─────────────────────────
    user_agent: Mapped[str | None] = mapped_column(Text)
    screen_width: Mapped[int | None] = mapped_column()
    screen_height: Mapped[int | None] = mapped_column()
    language: Mapped[str | None] = mapped_column(String(10))

    status: Mapped[str] = mapped_column(String(20), default="in_progress")
    started_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column()

    survey: Mapped["Survey"] = relationship(back_populates="responses")  # noqa: F821
    interactions: Mapped[list["ParticipantInteraction"]] = relationship(
        back_populates="response", cascade="all, delete-orphan"
    )
    calibration_session: Mapped["CalibrationSession | None"] = relationship(  # noqa: F821
        back_populates="response"
    )


class ParticipantInteraction(Base):
    """A participant's interaction with a survey post (like, comment, click).

    From the meeting: 'As a user, I might comment on it, I might like it...
    this is extra data that needs to be saved.'
    These are separate from the fake numbers set by the researcher.
    """

    __tablename__ = "participant_interactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    response_id: Mapped[int] = mapped_column(
        ForeignKey("survey_responses.id", ondelete="CASCADE"), nullable=False
    )
    post_id: Mapped[int] = mapped_column(
        ForeignKey("survey_posts.id"), nullable=False
    )
    action_type: Mapped[str] = mapped_column(String(20), nullable=False)  # like / comment / click
    comment_text: Mapped[str | None] = mapped_column(Text)  # only if action_type == "comment"
    timestamp: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    response: Mapped["SurveyResponse"] = relationship(back_populates="interactions")


class ParticipantLike(Base):
    """Current like state per (response, post).

    Keeps the latest like status to support toggle (like/unlike) in UI,
    while `ParticipantInteraction` records the event stream for analytics.
    """

    __tablename__ = "participant_likes"
    __table_args__ = (
        UniqueConstraint("response_id", "post_id", name="uq_participant_like_response_post"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    response_id: Mapped[int] = mapped_column(
        ForeignKey("survey_responses.id", ondelete="CASCADE"), nullable=False
    )
    post_id: Mapped[int] = mapped_column(
        ForeignKey("survey_posts.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    response: Mapped["SurveyResponse"] = relationship()


class ParticipantComment(Base):
    """A comment written by a participant during a survey session.

    Separate from `PostComment` (researcher-authored fake comments).
    """

    __tablename__ = "participant_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    response_id: Mapped[int] = mapped_column(
        ForeignKey("survey_responses.id", ondelete="CASCADE"), nullable=False
    )
    post_id: Mapped[int] = mapped_column(
        ForeignKey("survey_posts.id", ondelete="CASCADE"), nullable=False
    )
    author_name: Mapped[str | None] = mapped_column(String(100))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column()

    response: Mapped["SurveyResponse"] = relationship()
