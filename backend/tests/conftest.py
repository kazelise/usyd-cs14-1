"""Shared fixtures for tracking module tests."""

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
        "screen_width": 1920,
        "screen_height": 1080,
        "camera_width": 640,
        "camera_height": 480,
    }
