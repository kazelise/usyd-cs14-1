"""Tracking schemas: calibration, gaze, clicks. Owned by Backend C."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

# ── Calibration ───────────────────────────────────────


class CreateCalibrationRequest(BaseModel):
    response_id: int = Field(
        gt=0, description="ID of the survey response this calibration belongs to"
    )
    participant_token: str = Field(
        min_length=1, max_length=128, description="Anonymous participant token for this response"
    )
    screen_width: int = Field(gt=0, description="Participant screen width in pixels")
    screen_height: int = Field(gt=0, description="Participant screen height in pixels")
    camera_width: int | None = Field(default=None, gt=0, description="Webcam resolution width")
    camera_height: int | None = Field(default=None, gt=0, description="Webcam resolution height")


class CalibrationSessionOut(BaseModel):
    session_id: int
    response_id: int
    status: str
    expected_points: int
    started_at: datetime
    model_config = {"from_attributes": True}


class HeadRotation(BaseModel):
    yaw: float | None = None
    pitch: float | None = None
    roll: float | None = None


class IrisSample(BaseModel):
    timestamp_ms: int = Field(ge=0, description="Client-side timestamp in milliseconds")
    left_iris_x: float | None = Field(
        default=None, ge=0, le=1, description="Left iris X coordinate (normalized)"
    )
    left_iris_y: float | None = Field(
        default=None, ge=0, le=1, description="Left iris Y coordinate (normalized)"
    )
    right_iris_x: float | None = Field(
        default=None, ge=0, le=1, description="Right iris X coordinate (normalized)"
    )
    right_iris_y: float | None = Field(
        default=None, ge=0, le=1, description="Right iris Y coordinate (normalized)"
    )
    face_detected: bool = Field(description="Whether face was detected in this sample")
    head_rotation: HeadRotation | None = Field(
        default=None, description="Head rotation angles if available"
    )

    @model_validator(mode="after")
    def require_iris_when_face_detected(self):
        if self.face_detected and any(
            value is None
            for value in (
                self.left_iris_x,
                self.left_iris_y,
                self.right_iris_x,
                self.right_iris_y,
            )
        ):
            raise ValueError(
                "iris coordinates are required when face_detected is true; "
                "frontend fallback should send normalized numeric estimates"
            )
        return self


class RecordCalibrationPointRequest(BaseModel):
    participant_token: str = Field(min_length=1, max_length=128)
    point_index: int = Field(ge=1, le=25)
    target_screen_x: int = Field(ge=0)
    target_screen_y: int = Field(ge=0)
    samples: list[IrisSample] = Field(min_length=1, max_length=60)


class CalibrationPointOut(BaseModel):
    session_id: int
    point_index: int
    samples_recorded: int
    points_completed: int
    points_remaining: int


class QualityInfo(BaseModel):
    total_points: int
    expected_points: int
    valid_points: int
    missing_points: int
    avg_samples_per_point: float
    face_detection_rate: float
    stability_score: float
    quality_score: float
    passed: bool
    overall_quality: Literal["good", "acceptable", "poor"]
    quality_reason: str


class CalibrationCompleteOut(BaseModel):
    session_id: int
    status: str
    quality: QualityInfo
    completed_at: datetime


class CompleteCalibrationRequest(BaseModel):
    participant_token: str


# ── Gaze Tracking ─────────────────────────────────────


class GazeDataPoint(BaseModel):
    """A single gaze data point from the frontend."""

    post_id: int | None = Field(default=None, gt=0)
    timestamp_ms: int = Field(ge=0)
    screen_x: float
    screen_y: float
    left_iris_x: float | None = Field(default=None, ge=0, le=1)
    left_iris_y: float | None = Field(default=None, ge=0, le=1)
    right_iris_x: float | None = Field(default=None, ge=0, le=1)
    right_iris_y: float | None = Field(default=None, ge=0, le=1)


class GazeBatchRequest(BaseModel):
    """Frontend sends gaze data in batches (e.g., every 5-10 seconds)."""

    response_id: int = Field(gt=0)
    participant_token: str = Field(min_length=1, max_length=128)
    data: list[GazeDataPoint] = Field(max_length=500)


class GazeBatchOut(BaseModel):
    saved: int


# ── Click Tracking ────────────────────────────────────


class ClickDataPoint(BaseModel):
    post_id: int | None = Field(default=None, gt=0)
    timestamp_ms: int = Field(ge=0)
    screen_x: float
    screen_y: float
    target_element: str | None = Field(default=None, max_length=80)


class ClickBatchRequest(BaseModel):
    response_id: int = Field(gt=0)
    participant_token: str = Field(min_length=1, max_length=128)
    data: list[ClickDataPoint] = Field(max_length=500)


class ClickBatchOut(BaseModel):
    saved: int
