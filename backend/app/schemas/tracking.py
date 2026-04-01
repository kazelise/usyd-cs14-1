"""Tracking schemas: calibration, gaze, clicks. Owned by Backend C."""

from datetime import datetime

from pydantic import BaseModel, Field

# ── Calibration ───────────────────────────────────────


class CreateCalibrationRequest(BaseModel):
    """Start a webcam calibration session before the participant begins the survey."""

    response_id: int = Field(..., description="Survey response ID from /surveys/{share_code}/start", examples=[1])
    screen_width: int = Field(..., description="Participant screen width in pixels", examples=[1920])
    screen_height: int = Field(..., description="Participant screen height in pixels", examples=[1080])
    camera_width: int | None = Field(None, description="Webcam resolution width", examples=[640])
    camera_height: int | None = Field(None, description="Webcam resolution height", examples=[480])


class CalibrationSessionOut(BaseModel):
    """Response after creating a calibration session."""

    session_id: int = Field(..., description="Unique calibration session ID", examples=[1])
    response_id: int = Field(..., description="Linked survey response ID", examples=[1])
    status: str = Field(..., description="Session status: in_progress or completed", examples=["in_progress"])
    expected_points: int = Field(..., description="Number of calibration points (default 9)", examples=[9])
    started_at: datetime = Field(..., description="Session start timestamp")
    model_config = {"from_attributes": True}


class IrisSample(BaseModel):
    """A single iris position sample captured by MediaPipe Face Mesh."""

    timestamp_ms: int = Field(..., description="Client-side timestamp in milliseconds", examples=[1711800000000])
    left_iris_x: float = Field(..., description="Left iris X coordinate (normalized 0-1)", examples=[0.45])
    left_iris_y: float = Field(..., description="Left iris Y coordinate (normalized 0-1)", examples=[0.52])
    right_iris_x: float = Field(..., description="Right iris X coordinate (normalized 0-1)", examples=[0.55])
    right_iris_y: float = Field(..., description="Right iris Y coordinate (normalized 0-1)", examples=[0.51])
    face_detected: bool = Field(..., description="Whether a face was detected in this frame", examples=[True])
    head_rotation: dict | None = Field(None, description="Optional head rotation angles {pitch, yaw, roll}")


class RecordCalibrationPointRequest(BaseModel):
    """Record iris samples for one calibration point (e.g., point 3 of 9)."""

    point_index: int = Field(..., description="Calibration point index (0-8 for 9-point grid)", examples=[0])
    target_screen_x: int = Field(..., description="Target dot X position on screen in pixels", examples=[960])
    target_screen_y: int = Field(..., description="Target dot Y position on screen in pixels", examples=[540])
    samples: list[IrisSample] = Field(..., description="Iris samples collected while participant looked at this point")


class CalibrationPointOut(BaseModel):
    """Response after recording a calibration point."""

    session_id: int = Field(..., description="Calibration session ID", examples=[1])
    point_index: int = Field(..., description="Completed point index", examples=[0])
    samples_recorded: int = Field(..., description="Number of iris samples recorded for this point", examples=[30])
    points_completed: int = Field(..., description="Total points completed so far", examples=[1])
    points_remaining: int = Field(..., description="Points remaining before calibration can be completed", examples=[8])


class QualityInfo(BaseModel):
    """Calibration quality assessment metrics."""

    total_points: int = Field(..., description="Total calibration points recorded", examples=[9])
    valid_points: int = Field(..., description="Points with >= 10 samples", examples=[8])
    avg_samples_per_point: float = Field(..., description="Average samples collected per point", examples=[28.5])
    face_detection_rate: float = Field(..., description="Ratio of frames with face detected (0-1)", examples=[0.95])
    overall_quality: str = Field(..., description="Quality rating: good, acceptable, or poor", examples=["good"])


class CalibrationCompleteOut(BaseModel):
    """Response after completing calibration with quality metrics."""

    session_id: int = Field(..., description="Calibration session ID", examples=[1])
    status: str = Field(..., description="Always 'completed'", examples=["completed"])
    quality: QualityInfo = Field(..., description="Calibration quality assessment")
    completed_at: datetime = Field(..., description="Completion timestamp")


# ── Gaze Tracking ─────────────────────────────────────


class GazeDataPoint(BaseModel):
    """A single gaze data point captured by the browser eye-tracking module."""

    post_id: int | None = Field(None, description="ID of the post currently on screen, null if between posts", examples=[1])
    timestamp_ms: int = Field(..., description="Client-side timestamp in milliseconds", examples=[1711800000000])
    screen_x: float = Field(..., description="Estimated gaze X position on screen in pixels", examples=[512.5])
    screen_y: float = Field(..., description="Estimated gaze Y position on screen in pixels", examples=[384.0])
    left_iris_x: float | None = Field(None, description="Left iris X coordinate (normalized 0-1)", examples=[0.45])
    left_iris_y: float | None = Field(None, description="Left iris Y coordinate (normalized 0-1)", examples=[0.52])
    right_iris_x: float | None = Field(None, description="Right iris X coordinate (normalized 0-1)", examples=[0.55])
    right_iris_y: float | None = Field(None, description="Right iris Y coordinate (normalized 0-1)", examples=[0.51])


class GazeBatchRequest(BaseModel):
    """Batch of gaze data points. Frontend sends these every 5-10 seconds during survey participation."""

    response_id: int = Field(..., description="Survey response ID from /surveys/{share_code}/start", examples=[1])
    data: list[GazeDataPoint] = Field(..., description="Array of gaze data points to record")


class GazeBatchOut(BaseModel):
    """Response after successfully saving gaze data."""

    saved: int = Field(..., description="Number of gaze records saved", examples=[15])


# ── Click Tracking ────────────────────────────────────


class ClickDataPoint(BaseModel):
    """A single mouse click event captured during survey participation."""

    post_id: int | None = Field(None, description="ID of the post that was clicked, null if outside a post", examples=[1])
    timestamp_ms: int = Field(..., description="Client-side timestamp in milliseconds", examples=[1711800000000])
    screen_x: float = Field(..., description="Click X position on screen in pixels", examples=[450.0])
    screen_y: float = Field(..., description="Click Y position on screen in pixels", examples=[320.0])
    target_element: str | None = Field(None, description="Clicked element type: headline, image, like_button, comment_button, share_count, or other", examples=["like_button"])


class ClickBatchRequest(BaseModel):
    """Batch of click events. Frontend flushes the click buffer every 10 seconds."""

    response_id: int = Field(..., description="Survey response ID from /surveys/{share_code}/start", examples=[1])
    data: list[ClickDataPoint] = Field(..., description="Array of click events to record")


class ClickBatchOut(BaseModel):
    """Response after successfully saving click data."""

    saved: int = Field(..., description="Number of click records saved", examples=[5])
