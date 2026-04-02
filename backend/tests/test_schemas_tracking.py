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
