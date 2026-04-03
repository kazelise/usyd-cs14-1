"""Tracking schemas: calibration, gaze, clicks. Owned by Backend C."""

from datetime import datetime

from pydantic import BaseModel

# ── Calibration ───────────────────────────────────────


class CreateCalibrationRequest(BaseModel):
    response_id: int
    screen_width: int
    screen_height: int
    camera_width: int | None = None
    camera_height: int | None = None


class CalibrationSessionOut(BaseModel):
    session_id: int
    response_id: int
    status: str
    expected_points: int
    started_at: datetime
    model_config = {"from_attributes": True}


class IrisSample(BaseModel):
    timestamp_ms: int
    left_iris_x: float
    left_iris_y: float
    right_iris_x: float
    right_iris_y: float
    face_detected: bool
    head_rotation: dict | None = None


class RecordCalibrationPointRequest(BaseModel):
    point_index: int
    target_screen_x: int
    target_screen_y: int
    samples: list[IrisSample]


class CalibrationPointOut(BaseModel):
    session_id: int
    point_index: int
    samples_recorded: int
    points_completed: int
    points_remaining: int


class QualityInfo(BaseModel):
    total_points: int
    valid_points: int
    avg_samples_per_point: float
    face_detection_rate: float
    overall_quality: str


class CalibrationCompleteOut(BaseModel):
    session_id: int
    status: str
    quality: QualityInfo
    completed_at: datetime


# ── Gaze Tracking ─────────────────────────────────────


class GazeDataPoint(BaseModel):
    """A single gaze data point from the frontend."""

    post_id: int | None = None
    timestamp_ms: int
    screen_x: float
    screen_y: float
    left_iris_x: float | None = None
    left_iris_y: float | None = None
    right_iris_x: float | None = None
    right_iris_y: float | None = None


class GazeBatchRequest(BaseModel):
    """Frontend sends gaze data in batches (e.g., every 5-10 seconds)."""

    response_id: int
    data: list[GazeDataPoint]


class GazeBatchOut(BaseModel):
    saved: int


# ── Click Tracking ────────────────────────────────────


class ClickDataPoint(BaseModel):
    post_id: int | None = None
    timestamp_ms: int
    screen_x: float
    screen_y: float
    target_element: str | None = None  # "headline", "image", "like_button", etc.


class ClickBatchRequest(BaseModel):
    response_id: int
    data: list[ClickDataPoint]


class ClickBatchOut(BaseModel):
    saved: int
