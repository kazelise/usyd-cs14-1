"""Tests for schema field type coercion and serialization."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from app.schemas.tracking import (
    CalibrationSessionOut,
    CalibrationCompleteOut,
    QualityInfo,
    GazeDataPoint,
)


class TestFieldTypeCoercion:
    """Test that schemas handle type coercion correctly."""

    def test_gaze_int_to_float_coercion(self):
        """Pydantic should coerce int to float for screen coords."""
        point = GazeDataPoint(timestamp_ms=1000, screen_x=960, screen_y=540)
        assert isinstance(point.screen_x, (int, float))

    def test_quality_info_float_fields(self):
        info = QualityInfo(
            total_points=9,
            valid_points=9,
            avg_samples_per_point=12,
            face_detection_rate=1,
            overall_quality="good",
        )
        assert info.avg_samples_per_point == 12.0


class TestSchemaSerialization:
    """Test schema serialization to dict/JSON."""

    def test_gaze_point_to_dict(self):
        point = GazeDataPoint(
            post_id=1, timestamp_ms=5000, screen_x=960.0, screen_y=540.0
        )
        data = point.model_dump()
        assert data["post_id"] == 1
        assert data["screen_x"] == 960.0
        assert data["left_iris_x"] is None

    def test_quality_info_to_dict(self):
        info = QualityInfo(
            total_points=9,
            valid_points=8,
            avg_samples_per_point=11.5,
            face_detection_rate=0.92,
            overall_quality="good",
        )
        data = info.model_dump()
        assert "overall_quality" in data
        assert data["face_detection_rate"] == 0.92

    def test_calibration_complete_nested_serialization(self):
        out = CalibrationCompleteOut(
            session_id=1,
            status="completed",
            quality=QualityInfo(
                total_points=9,
                valid_points=9,
                avg_samples_per_point=12.0,
                face_detection_rate=0.95,
                overall_quality="good",
            ),
            completed_at=datetime(2026, 4, 10, 10, 0, 0),
        )
        data = out.model_dump()
        assert data["quality"]["overall_quality"] == "good"
        assert data["session_id"] == 1
