"""Translation tables for survey, post, and question localized content."""

from datetime import datetime

from sqlalchemy import JSON, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SurveyTranslation(Base):
    """Localized survey-level fields for one language."""

    __tablename__ = "survey_translations"
    __table_args__ = (
        UniqueConstraint("survey_id", "language_code", name="uq_survey_translation_language"),
        Index("ix_survey_translations_survey_language", "survey_id", "language_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    survey_id: Mapped[int] = mapped_column(
        ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False
    )
    language_code: Mapped[str] = mapped_column(String(10), nullable=False)
    translated_fields: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    survey: Mapped["Survey"] = relationship(back_populates="translations")  # noqa: F821


class PostTranslation(Base):
    """Localized post card fields for one language."""

    __tablename__ = "post_translations"
    __table_args__ = (
        UniqueConstraint("post_id", "language_code", name="uq_post_translation_language"),
        Index("ix_post_translations_survey_language", "survey_id", "language_code"),
        Index("ix_post_translations_post_language", "post_id", "language_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    survey_id: Mapped[int] = mapped_column(
        ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False
    )
    post_id: Mapped[int] = mapped_column(
        ForeignKey("survey_posts.id", ondelete="CASCADE"), nullable=False
    )
    language_code: Mapped[str] = mapped_column(String(10), nullable=False)
    translated_fields: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    survey: Mapped["Survey"] = relationship()  # noqa: F821
    post: Mapped["SurveyPost"] = relationship(back_populates="translations")  # noqa: F821


class QuestionTranslation(Base):
    """Localized question text/config fields for one language."""

    __tablename__ = "question_translations"
    __table_args__ = (
        UniqueConstraint("question_id", "language_code", name="uq_question_translation_language"),
        Index("ix_question_translations_survey_language", "survey_id", "language_code"),
        Index("ix_question_translations_question_language", "question_id", "language_code"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    survey_id: Mapped[int] = mapped_column(
        ForeignKey("surveys.id", ondelete="CASCADE"), nullable=False
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), nullable=False
    )
    language_code: Mapped[str] = mapped_column(String(10), nullable=False)
    translated_fields: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    survey: Mapped["Survey"] = relationship()  # noqa: F821
    question: Mapped["Question"] = relationship(back_populates="translations")  # noqa: F821
