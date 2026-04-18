"""Unit tests for calibration quality computation."""

import pytest

from app.utils.quality import compute_calibration_quality


def _make_point(samples_count, face_detected_count):
    """Helper to create a calibration point dict for testing."""
    samples = []
    for i in range(samples_count):
        samples.append({
            "face_detected": i < face_detected_count,
            "left_iris_x": 0.5,
            "left_iris_y": 0.5,
            "right_iris_x": 0.5,
            "right_iris_y": 0.5,
        })
    return {"samples_count": samples_count, "samples": samples}


class TestComputeCalibrationQuality:
    """Tests for the quality computation function."""

    def test_empty_points(self):
        result = compute_calibration_quality([], expected_points=9)
        assert result["total_points"] == 0
        assert result["overall_quality"] == "poor"

    def test_good_quality(self):
        points = [_make_point(12, 12) for _ in range(9)]
        result = compute_calibration_quality(points, expected_points=9)
        assert result["overall_quality"] == "good"
        assert result["valid_points"] == 9
        assert result["face_detection_rate"] == 1.0

    def test_acceptable_quality(self):
        # 7 valid points (>= 9*0.56=5.04), face rate ~0.75
        points = [_make_point(12, 9) for _ in range(7)]
        points += [_make_point(5, 3) for _ in range(2)]
        result = compute_calibration_quality(points, expected_points=9)
        assert result["overall_quality"] == "acceptable"

    def test_poor_quality_low_face_rate(self):
        points = [_make_point(12, 3) for _ in range(9)]
        result = compute_calibration_quality(points, expected_points=9)
        assert result["overall_quality"] == "poor"

    def test_poor_quality_few_valid_points(self):
        points = [_make_point(5, 5) for _ in range(9)]
        result = compute_calibration_quality(points, expected_points=9)
        assert result["overall_quality"] == "poor"
        assert result["valid_points"] == 0

    def test_avg_samples_calculation(self):
        points = [
            _make_point(10, 10),
            _make_point(14, 14),
            _make_point(12, 12),
        ]
        result = compute_calibration_quality(points, expected_points=9)
        assert result["avg_samples_per_point"] == 12.0


class TestQualityThresholdBoundaries:
    """Tests for quality threshold edge cases."""

    def test_face_rate_exactly_0_9(self):
        # 90% face detection — right at the good threshold
        points = [_make_point(10, 9) for _ in range(9)]
        result = compute_calibration_quality(points, expected_points=9)
        assert result["face_detection_rate"] == 0.9
        assert result["overall_quality"] == "good"

    def test_face_rate_just_below_0_9(self):
        # ~89% face detection with enough samples — should be acceptable
        points = [_make_point(18, 16) for _ in range(9)]
        result = compute_calibration_quality(points, expected_points=9)
        assert result["face_detection_rate"] < 0.9
        assert result["overall_quality"] == "acceptable"

    def test_face_rate_exactly_0_7(self):
        points = [_make_point(10, 7) for _ in range(9)]
        result = compute_calibration_quality(points, expected_points=9)
        assert result["face_detection_rate"] == 0.7
        assert result["overall_quality"] == "acceptable"

    def test_face_rate_just_below_0_7(self):
        # ~69% face detection — should be poor
        points = [_make_point(13, 9) for _ in range(9)]
        result = compute_calibration_quality(points, expected_points=9)
        assert result["face_detection_rate"] < 0.7
        assert result["overall_quality"] == "poor"

    def test_single_point(self):
        points = [_make_point(15, 15)]
        result = compute_calibration_quality(points, expected_points=9)
        assert result["total_points"] == 1
        assert result["face_detection_rate"] == 1.0
        # 1 valid point < 9 * 0.56 = 5.04, so poor despite high face rate
        assert result["overall_quality"] == "poor"
