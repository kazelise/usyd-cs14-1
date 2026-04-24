"""Question model for survey post questions. Owned by Backend A/B."""

from datetime import datetime

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Question(Base):
    """A question attached to a survey post.

    Supports multiple formats: free-text, Likert scale, and multiple-choice.
    Questions are ordered within a post and cascade-deleted when the post is removed.
    """

    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    post_id: Mapped[int] = mapped_column(
        ForeignKey("survey_posts.id", ondelete="CASCADE"), nullable=False
    )
    order: Mapped[int] = mapped_column(nullable=False)

    # ── Question Content ─────────────────────────────
    question_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # free_text / likert / multiple_choice
    text: Mapped[str] = mapped_column(Text, nullable=False)

    # ── Type-specific Config ─────────────────────────
    # likert: {"min": 1, "max": 5, "min_label": "Disagree", "max_label": "Agree"}
    # multiple_choice: {"options": ["Option A", "Option B", "Option C"]}
    config: Mapped[dict | None] = mapped_column(JSON)

    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    post: Mapped["SurveyPost"] = relationship(back_populates="questions")  # noqa: F821
    translations: Mapped[list["QuestionTranslation"]] = relationship(  # noqa: F821
        back_populates="question", cascade="all, delete-orphan"
    )
