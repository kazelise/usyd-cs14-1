"""Advanced quality computation tests using fixtures."""

import pytest

from app.utils.quality import compute_calibration_quality


class TestQualityWithFixtures:
    """Test quality computation using conftest fixtures."""

    def test_good_quality_with_factory(self, make_calibration_points):
        points = make_calibration_points(count=9, samples_per_point=12, face_detected_ratio=1.0)
        result = compute_calibration_quality(points, expected_points=9)
        assert result["overall_quality"] == "good"

    def test_acceptable_quality_with_factory(self, make_calibration_points):
        points = make_calibration_points(count=9, samples_per_point=12, face_detected_ratio=0.75)
        result = compute_calibration_quality(points, expected_points=9)
        assert result["overall_quality"] == "acceptable"

    def test_poor_quality_with_factory(self, make_calibration_points):
        points = make_calibration_points(count=9, samples_per_point=5, face_detected_ratio=0.3)
        result = compute_calibration_quality(points, expected_points=9)
        assert result["overall_quality"] == "poor"

    def test_fewer_points_than_expected(self, make_calibration_points):
        points = make_calibration_points(count=4, samples_per_point=15, face_detected_ratio=1.0)
        result = compute_calibration_quality(points, expected_points=9)
        assert result["total_points"] == 4
        # 4 valid points < 9 * 0.56 = 5.04
        assert result["overall_quality"] == "poor"

    def test_more_points_than_expected(self, make_calibration_points):
        points = make_calibration_points(count=12, samples_per_point=12, face_detected_ratio=0.95)
        result = compute_calibration_quality(points, expected_points=9)
        assert result["total_points"] == 12
        assert result["overall_quality"] == "good"
