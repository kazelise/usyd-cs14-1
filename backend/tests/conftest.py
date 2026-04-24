"""Shared fixtures for tracking module tests.

Provides reusable test data for calibration, gaze, and click tracking.
"""

import pytest


@pytest.fixture
def sample_iris_data():
    """Generate sample iris tracking data for tests."""
    return {
        "timestamp_ms": 1000,
        "left_iris_x": 0.45,
        "left_iris_y": 0.52,
        "right_iris_x": 0.55,
        "right_iris_y": 0.48,
        "face_detected": True,
    }


@pytest.fixture
def sample_calibration_request():
    """Generate sample calibration session request data."""
    return {
        "response_id": 1,
        "participant_token": "participant-token",
        "screen_width": 1920,
        "screen_height": 1080,
        "camera_width": 640,
        "camera_height": 480,
    }


@pytest.fixture
def sample_gaze_data():
    """Generate sample gaze tracking data point."""
    return {
        "post_id": 1,
        "timestamp_ms": 5000,
        "screen_x": 960.0,
        "screen_y": 540.0,
        "left_iris_x": 0.45,
        "left_iris_y": 0.52,
        "right_iris_x": 0.55,
        "right_iris_y": 0.48,
    }


@pytest.fixture
def sample_click_data():
    """Generate sample click tracking data point."""
    return {
        "post_id": 1,
        "timestamp_ms": 8000,
        "screen_x": 500.0,
        "screen_y": 300.0,
        "target_element": "headline",
    }


@pytest.fixture
def make_calibration_points():
    """Factory fixture to generate calibration point dicts."""

    def _make(count=9, samples_per_point=12, face_detected_ratio=1.0):
        points = []
        for _ in range(count):
            face_count = int(samples_per_point * face_detected_ratio)
            samples = [
                {
                    "face_detected": i < face_count,
                    "left_iris_x": 0.5,
                    "left_iris_y": 0.5,
                    "right_iris_x": 0.5,
                    "right_iris_y": 0.5,
                }
                for i in range(samples_per_point)
            ]
            points.append({"samples_count": samples_per_point, "samples": samples})
        return points

    return _make
