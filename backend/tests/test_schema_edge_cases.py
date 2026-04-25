"""Edge case tests for tracking schema validation."""

import pytest
from pydantic import ValidationError

from app.schemas.tracking import (
    ClickBatchRequest,
    ClickDataPoint,
    CreateCalibrationRequest,
    GazeBatchRequest,
    GazeDataPoint,
    IrisSample,
)


class TestCalibrationRequestEdgeCases:
    """Edge cases for calibration request validation."""

    def test_zero_screen_dimensions(self):
        with pytest.raises(ValidationError):
            CreateCalibrationRequest(
                response_id=1,
                participant_token="participant-token",
                screen_width=0,
                screen_height=0,
            )

    def test_large_screen_dimensions(self):
        req = CreateCalibrationRequest(
            response_id=1,
            participant_token="participant-token",
            screen_width=7680,
            screen_height=4320,
        )
        assert req.screen_width == 7680

    def test_negative_response_id(self):
        with pytest.raises(ValidationError):
            CreateCalibrationRequest(
                response_id=-1,
                participant_token="participant-token",
                screen_width=1920,
                screen_height=1080,
            )

    def test_string_response_id_rejected(self):
        with pytest.raises(ValidationError):
            CreateCalibrationRequest(
                response_id="abc",
                participant_token="participant-token",
                screen_width=1920,
                screen_height=1080,
            )


class TestGazeDataPointEdgeCases:
    """Edge cases for gaze data point validation."""

    def test_zero_coordinates(self):
        point = GazeDataPoint(timestamp_ms=0, screen_x=0.0, screen_y=0.0)
        assert point.screen_x == 0.0

    def test_negative_coordinates(self):
        point = GazeDataPoint(timestamp_ms=1000, screen_x=-100.0, screen_y=-50.0)
        assert point.screen_x == -100.0

    def test_very_large_coordinates(self):
        point = GazeDataPoint(timestamp_ms=1000, screen_x=99999.0, screen_y=99999.0)
        assert point.screen_x == 99999.0


class TestClickDataPointEdgeCases:
    """Edge cases for click data point validation."""

    def test_empty_target_element(self):
        with pytest.raises(ValidationError):
            ClickDataPoint(timestamp_ms=1000, screen_x=100.0, screen_y=100.0, target_element="")

    def test_long_target_element(self):
        point = ClickDataPoint(
            timestamp_ms=1000,
            screen_x=100.0,
            screen_y=100.0,
            target_element="very_long_element_name_here",
        )
        assert len(point.target_element) > 0


class TestIrisSampleEdgeCases:
    """Edge cases for iris sample data."""

    def test_extreme_iris_coordinates(self):
        sample = IrisSample(
            timestamp_ms=1000,
            left_iris_x=1.0,
            left_iris_y=1.0,
            right_iris_x=0.0,
            right_iris_y=0.0,
            face_detected=True,
        )
        assert sample.left_iris_x == 1.0

    def test_negative_iris_coordinates(self):
        with pytest.raises(ValidationError):
            IrisSample(
                timestamp_ms=1000,
                left_iris_x=-0.1,
                left_iris_y=-0.1,
                right_iris_x=-0.1,
                right_iris_y=-0.1,
                face_detected=False,
            )

    def test_empty_head_rotation(self):
        sample = IrisSample(
            timestamp_ms=1000,
            left_iris_x=0.5,
            left_iris_y=0.5,
            right_iris_x=0.5,
            right_iris_y=0.5,
            face_detected=True,
            head_rotation={},
        )
        assert sample.head_rotation.yaw is None


class TestBatchRequestEdgeCases:
    """Edge cases for batch request schemas."""

    def test_gaze_batch_single_item(self):
        batch = GazeBatchRequest(
            response_id=1,
            participant_token="participant-token",
            data=[{"timestamp_ms": 1000, "screen_x": 100.0, "screen_y": 200.0}],
        )
        assert len(batch.data) == 1

    def test_gaze_batch_large(self):
        data = [
            {"timestamp_ms": i * 1000, "screen_x": float(i), "screen_y": float(i)}
            for i in range(100)
        ]
        batch = GazeBatchRequest(response_id=1, participant_token="participant-token", data=data)
        assert len(batch.data) == 100

    def test_gaze_batch_too_large_rejected(self):
        data = [
            {"timestamp_ms": i * 1000, "screen_x": float(i), "screen_y": float(i)}
            for i in range(501)
        ]
        with pytest.raises(ValidationError):
            GazeBatchRequest(response_id=1, participant_token="participant-token", data=data)

    def test_click_batch_single_item(self):
        batch = ClickBatchRequest(
            response_id=1,
            participant_token="participant-token",
            data=[{"timestamp_ms": 1000, "screen_x": 100.0, "screen_y": 200.0}],
        )
        assert len(batch.data) == 1

    def test_click_batch_all_with_targets(self):
        data = [
            {
                "timestamp_ms": 1000,
                "screen_x": 100.0,
                "screen_y": 200.0,
                "target_element": elem,
            }
            for elem in ["headline", "image", "like_button", "comment"]
        ]
        batch = ClickBatchRequest(response_id=1, participant_token="participant-token", data=data)
        assert all(d.target_element is not None for d in batch.data)

    def test_mixed_gaze_data_types(self):
        """Test batch with mix of full and minimal gaze points."""
        batch = GazeBatchRequest(
            response_id=1,
            participant_token="participant-token",
            data=[
                {
                    "post_id": 1,
                    "timestamp_ms": 1000,
                    "screen_x": 100.0,
                    "screen_y": 200.0,
                    "left_iris_x": 0.5,
                    "left_iris_y": 0.5,
                    "right_iris_x": 0.5,
                    "right_iris_y": 0.5,
                },
                {"timestamp_ms": 2000, "screen_x": 300.0, "screen_y": 400.0},
            ],
        )
        assert batch.data[0].left_iris_x == 0.5
        assert batch.data[1].left_iris_x is None
