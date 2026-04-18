"""Tests for schema interoperability and data flow between models."""

from datetime import datetime

from app.schemas.tracking import (
    CalibrationSessionOut,
    ClickBatchOut,
    ClickBatchRequest,
    CreateCalibrationRequest,
    GazeBatchOut,
    GazeBatchRequest,
)


class TestSchemaInteroperability:
    """Verify data flows correctly between request and response schemas."""

    def test_calibration_request_fields_map_to_output(self):
        req = CreateCalibrationRequest(response_id=42, screen_width=1920, screen_height=1080)
        out = CalibrationSessionOut(
            session_id=1,
            response_id=req.response_id,
            status="in_progress",
            expected_points=9,
            started_at=datetime.utcnow(),
        )
        assert out.response_id == req.response_id

    def test_gaze_batch_count_matches_output(self):
        batch = GazeBatchRequest(
            response_id=1,
            data=[
                {"timestamp_ms": i * 1000, "screen_x": float(i), "screen_y": float(i)}
                for i in range(7)
            ],
        )
        out = GazeBatchOut(saved=len(batch.data))
        assert out.saved == 7

    def test_click_batch_count_matches_output(self):
        batch = ClickBatchRequest(
            response_id=1,
            data=[
                {"timestamp_ms": i * 500, "screen_x": 100.0, "screen_y": 200.0} for i in range(3)
            ],
        )
        out = ClickBatchOut(saved=len(batch.data))
        assert out.saved == 3

    def test_empty_batch_produces_zero_saved(self):
        gaze_batch = GazeBatchRequest(response_id=1, data=[])
        click_batch = ClickBatchRequest(response_id=1, data=[])
        assert GazeBatchOut(saved=len(gaze_batch.data)).saved == 0
        assert ClickBatchOut(saved=len(click_batch.data)).saved == 0
