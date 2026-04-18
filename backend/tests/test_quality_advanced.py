"""Advanced quality computation tests using fixtures."""

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


class TestQualityMixedScenarios:
    """Test quality with realistic mixed calibration data."""

    def test_mixed_sample_counts(self):
        """Realistic scenario: some points have more samples than others."""
        points = []
        sample_counts = [15, 12, 8, 14, 11, 13, 9, 12, 10]
        for count in sample_counts:
            samples = [
                {
                    "face_detected": True,
                    "left_iris_x": 0.5,
                    "left_iris_y": 0.5,
                    "right_iris_x": 0.5,
                    "right_iris_y": 0.5,
                }
                for _ in range(count)
            ]
            points.append({"samples_count": count, "samples": samples})
        result = compute_calibration_quality(points, expected_points=9)
        # 7 points have >= 10 samples (valid), face rate = 1.0
        assert result["valid_points"] == 7
        # 7 < 9 * 0.78 (7.02), so not quite "good" — it's "acceptable"
        assert result["overall_quality"] == "acceptable"

    def test_intermittent_face_detection(self):
        """Some samples lose face tracking mid-calibration."""
        points = []
        for i in range(9):
            samples = []
            for j in range(12):
                # Face detection drops for every 4th sample
                samples.append(
                    {
                        "face_detected": j % 4 != 3,
                        "left_iris_x": 0.5,
                        "left_iris_y": 0.5,
                        "right_iris_x": 0.5,
                        "right_iris_y": 0.5,
                    }
                )
            points.append({"samples_count": 12, "samples": samples})
        result = compute_calibration_quality(points, expected_points=9)
        # 9 out of 12 samples per point detected = 75% face rate
        assert result["face_detection_rate"] == 0.75
        assert result["overall_quality"] == "acceptable"

    def test_all_points_few_samples(self):
        """All points recorded but with too few samples each."""
        points = [
            {
                "samples_count": 5,
                "samples": [
                    {
                        "face_detected": True,
                        "left_iris_x": 0.5,
                        "left_iris_y": 0.5,
                        "right_iris_x": 0.5,
                        "right_iris_y": 0.5,
                    }
                    for _ in range(5)
                ],
            }
            for _ in range(9)
        ]
        result = compute_calibration_quality(points, expected_points=9)
        assert result["valid_points"] == 0  # none have >= 10 samples
        assert result["face_detection_rate"] == 1.0  # all detected though
        assert result["overall_quality"] == "poor"
