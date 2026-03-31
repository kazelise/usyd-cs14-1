"""Gaze tracking, click tracking, and calibration models. Owned by Backend C.

From the meeting:
- 'Capture the XY screen coordinates of where the user is looking,
   potentially every second or two seconds.'
- 'Mouse click metadata, including the location of clicks on the screen.'
- 'Camera calibration is essential for capturing metadata about
   where users focus their attention while viewing posts.'
"""

from datetime import datetime

from sqlalchemy import JSON, BigInteger, Float, ForeignKey, SmallInteger, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# ── Calibration ──────────────────────────────────────


class CalibrationSession(Base):
    """Webcam calibration session before a participant begins the survey.

    Uses MediaPipe Face Mesh in the browser to track iris positions
    against known screen coordinates (e.g., 9-point grid).
    """

    __tablename__ = "calibration_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    response_id: Mapped[int] = mapped_column(
        ForeignKey("survey_responses.id"), unique=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="in_progress")
    screen_width: Mapped[int] = mapped_column(nullable=False)
    screen_height: Mapped[int] = mapped_column(nullable=False)
    camera_width: Mapped[int | None] = mapped_column()
    camera_height: Mapped[int | None] = mapped_column()
    expected_points: Mapped[int] = mapped_column(SmallInteger, default=9)
    face_detection_rate: Mapped[float | None] = mapped_column(Float)
    quality: Mapped[str | None] = mapped_column(String(20))  # good / acceptable / poor
    started_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column()

    response: Mapped["SurveyResponse"] = relationship(back_populates="calibration_session")  # noqa: F821
    points: Mapped[list["CalibrationPoint"]] = relationship(
        back_populates="session", cascade="all, delete-orphan",
        order_by="CalibrationPoint.point_index",
    )


class CalibrationPoint(Base):
    """Data for one calibration point (e.g., point 3 of 9)."""

    __tablename__ = "calibration_points"
    __table_args__ = (
        UniqueConstraint("session_id", "point_index", name="uq_session_point"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("calibration_sessions.id", ondelete="CASCADE"), nullable=False
    )
    point_index: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    target_screen_x: Mapped[int] = mapped_column(nullable=False)
    target_screen_y: Mapped[int] = mapped_column(nullable=False)
    samples: Mapped[list[dict]] = mapped_column(JSON, nullable=False)
    samples_count: Mapped[int] = mapped_column(nullable=False)
    median_left_iris_x: Mapped[float | None] = mapped_column(Float)
    median_left_iris_y: Mapped[float | None] = mapped_column(Float)
    median_right_iris_x: Mapped[float | None] = mapped_column(Float)
    median_right_iris_y: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    session: Mapped["CalibrationSession"] = relationship(back_populates="points")


# ── Continuous Gaze Tracking ─────────────────────────


class GazeRecord(Base):
    """A single gaze data point captured during survey participation.

    Captured every 1-2 seconds while the participant is viewing posts.
    The XY coordinates represent where on the screen the participant
    is looking, as estimated by the gaze tracking module.
    """

    __tablename__ = "gaze_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    response_id: Mapped[int] = mapped_column(
        ForeignKey("survey_responses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    post_id: Mapped[int | None] = mapped_column(
        ForeignKey("survey_posts.id"), nullable=True
    )  # which post was on screen, null if between posts
    timestamp_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)  # client-side timestamp
    screen_x: Mapped[float] = mapped_column(Float, nullable=False)
    screen_y: Mapped[float] = mapped_column(Float, nullable=False)
    left_iris_x: Mapped[float | None] = mapped_column(Float)
    left_iris_y: Mapped[float | None] = mapped_column(Float)
    right_iris_x: Mapped[float | None] = mapped_column(Float)
    right_iris_y: Mapped[float | None] = mapped_column(Float)


# ── Mouse Click Tracking ─────────────────────────────


class ClickRecord(Base):
    """A mouse click captured during survey participation.

    From the meeting: 'Mouse click metadata will improve the
    accuracy of eye gaze tracking.'
    """

    __tablename__ = "click_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    response_id: Mapped[int] = mapped_column(
        ForeignKey("survey_responses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    post_id: Mapped[int | None] = mapped_column(
        ForeignKey("survey_posts.id"), nullable=True
    )
    timestamp_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    screen_x: Mapped[float] = mapped_column(Float, nullable=False)
    screen_y: Mapped[float] = mapped_column(Float, nullable=False)
    target_element: Mapped[str | None] = mapped_column(String(50))  # e.g. "headline", "image", "like_button"
