"""Unit tests for tracking Pydantic schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.tracking import CreateCalibrationRequest, IrisSample


class TestCreateCalibrationRequest:
    """Tests for calibration session creation schema."""

    def test_valid_minimal(self):
        req = CreateCalibrationRequest(
            response_id=1, screen_width=1920, screen_height=1080
        )
        assert req.response_id == 1
        assert req.camera_width is None

    def test_valid_with_camera(self):
        req = CreateCalibrationRequest(
            response_id=1,
            screen_width=1920,
            screen_height=1080,
            camera_width=640,
            camera_height=480,
        )
        assert req.camera_width == 640
        assert req.camera_height == 480

    def test_missing_response_id(self):
        with pytest.raises(ValidationError):
            CreateCalibrationRequest(screen_width=1920, screen_height=1080)

    def test_missing_screen_height(self):
        with pytest.raises(ValidationError):
            CreateCalibrationRequest(response_id=1, screen_width=1920)


class TestIrisSample:
    """Tests for iris sample data schema."""

    def test_valid_sample(self):
        sample = IrisSample(
            timestamp_ms=1000,
            left_iris_x=0.45,
            left_iris_y=0.52,
            right_iris_x=0.55,
            right_iris_y=0.48,
            face_detected=True,
        )
        assert sample.face_detected is True
        assert sample.head_rotation is None

    def test_with_head_rotation(self):
        sample = IrisSample(
            timestamp_ms=1000,
            left_iris_x=0.45,
            left_iris_y=0.52,
            right_iris_x=0.55,
            right_iris_y=0.48,
            face_detected=True,
            head_rotation={"pitch": 0.1, "yaw": -0.2, "roll": 0.0},
        )
        assert sample.head_rotation["pitch"] == 0.1

    def test_face_not_detected(self):
        sample = IrisSample(
            timestamp_ms=2000,
            left_iris_x=0.0,
            left_iris_y=0.0,
            right_iris_x=0.0,
            right_iris_y=0.0,
            face_detected=False,
        )
        assert sample.face_detected is False

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            IrisSample(timestamp_ms=1000, face_detected=True)


from app.schemas.tracking import RecordCalibrationPointRequest


class TestRecordCalibrationPointRequest:
    """Tests for calibration point recording schema."""

    def test_valid_request(self):
        samples = [
            {
                "timestamp_ms": i * 100,
                "left_iris_x": 0.45,
                "left_iris_y": 0.52,
                "right_iris_x": 0.55,
                "right_iris_y": 0.48,
                "face_detected": True,
            }
            for i in range(10)
        ]
        req = RecordCalibrationPointRequest(
            point_index=0,
            target_screen_x=100,
            target_screen_y=100,
            samples=samples,
        )
        assert req.point_index == 0
        assert len(req.samples) == 10

    def test_empty_samples_list(self):
        req = RecordCalibrationPointRequest(
            point_index=0,
            target_screen_x=100,
            target_screen_y=100,
            samples=[],
        )
        assert len(req.samples) == 0

    def test_missing_point_index(self):
        with pytest.raises(ValidationError):
            RecordCalibrationPointRequest(
                target_screen_x=100, target_screen_y=100, samples=[]
            )


from app.schemas.tracking import GazeDataPoint, GazeBatchRequest, GazeBatchOut


class TestGazeDataPoint:
    """Tests for gaze data point schema."""

    def test_valid_full(self):
        point = GazeDataPoint(
            post_id=1,
            timestamp_ms=5000,
            screen_x=960.0,
            screen_y=540.0,
            left_iris_x=0.45,
            left_iris_y=0.52,
            right_iris_x=0.55,
            right_iris_y=0.48,
        )
        assert point.screen_x == 960.0
        assert point.post_id == 1

    def test_valid_minimal(self):
        point = GazeDataPoint(timestamp_ms=5000, screen_x=960.0, screen_y=540.0)
        assert point.post_id is None
        assert point.left_iris_x is None

    def test_missing_screen_coords(self):
        with pytest.raises(ValidationError):
            GazeDataPoint(timestamp_ms=5000, screen_x=960.0)


class TestGazeBatchRequest:
    """Tests for gaze batch request schema."""

    def test_valid_batch(self):
        batch = GazeBatchRequest(
            response_id=1,
            data=[
                {"timestamp_ms": 1000, "screen_x": 100.0, "screen_y": 200.0},
                {"timestamp_ms": 2000, "screen_x": 300.0, "screen_y": 400.0},
            ],
        )
        assert batch.response_id == 1
        assert len(batch.data) == 2

    def test_empty_batch(self):
        batch = GazeBatchRequest(response_id=1, data=[])
        assert len(batch.data) == 0

    def test_missing_response_id(self):
        with pytest.raises(ValidationError):
            GazeBatchRequest(data=[])


class TestGazeBatchOut:
    """Tests for gaze batch response schema."""

    def test_saved_count(self):
        out = GazeBatchOut(saved=5)
        assert out.saved == 5


from app.schemas.tracking import ClickDataPoint, ClickBatchRequest, ClickBatchOut


class TestClickDataPoint:
    """Tests for click data point schema."""

    def test_valid_with_target(self):
        point = ClickDataPoint(
            post_id=1,
            timestamp_ms=8000,
            screen_x=500.0,
            screen_y=300.0,
            target_element="headline",
        )
        assert point.target_element == "headline"

    def test_valid_without_target(self):
        point = ClickDataPoint(
            timestamp_ms=8000, screen_x=500.0, screen_y=300.0
        )
        assert point.target_element is None
        assert point.post_id is None

    def test_missing_timestamp(self):
        with pytest.raises(ValidationError):
            ClickDataPoint(screen_x=500.0, screen_y=300.0)


class TestClickBatchRequest:
    """Tests for click batch request schema."""

    def test_valid_batch(self):
        batch = ClickBatchRequest(
            response_id=1,
            data=[
                {"timestamp_ms": 1000, "screen_x": 100.0, "screen_y": 200.0},
                {
                    "timestamp_ms": 2000,
                    "screen_x": 300.0,
                    "screen_y": 400.0,
                    "target_element": "image",
                },
            ],
        )
        assert len(batch.data) == 2

    def test_empty_batch(self):
        batch = ClickBatchRequest(response_id=1, data=[])
        assert len(batch.data) == 0


class TestClickBatchOut:
    """Tests for click batch response schema."""

    def test_saved_count(self):
        out = ClickBatchOut(saved=3)
        assert out.saved == 3


from datetime import datetime

from app.schemas.tracking import (
    CalibrationSessionOut,
    CalibrationPointOut,
    CalibrationCompleteOut,
    QualityInfo,
)


class TestCalibrationSessionOut:
    """Tests for calibration session response schema."""

    def test_valid_output(self):
        out = CalibrationSessionOut(
            session_id=1,
            response_id=1,
            status="in_progress",
            expected_points=9,
            started_at=datetime(2026, 4, 1, 10, 0, 0),
        )
        assert out.status == "in_progress"
        assert out.expected_points == 9


class TestCalibrationPointOut:
    """Tests for calibration point response schema."""

    def test_valid_output(self):
        out = CalibrationPointOut(
            session_id=1,
            point_index=3,
            samples_recorded=12,
            points_completed=4,
            points_remaining=5,
        )
        assert out.points_completed == 4
        assert out.points_remaining == 5

    def test_all_points_done(self):
        out = CalibrationPointOut(
            session_id=1,
            point_index=8,
            samples_recorded=15,
            points_completed=9,
            points_remaining=0,
        )
        assert out.points_remaining == 0


class TestQualityInfo:
    """Tests for quality information schema."""

    def test_good_quality(self):
        info = QualityInfo(
            total_points=9,
            valid_points=9,
            avg_samples_per_point=12.5,
            face_detection_rate=0.95,
            overall_quality="good",
        )
        assert info.overall_quality == "good"

    def test_poor_quality(self):
        info = QualityInfo(
            total_points=9,
            valid_points=3,
            avg_samples_per_point=5.0,
            face_detection_rate=0.4,
            overall_quality="poor",
        )
        assert info.overall_quality == "poor"
