"""Tests using conftest fixtures for gaze and click tracking."""

import pytest
from app.schemas.tracking import (
    GazeDataPoint,
    GazeBatchRequest,
    ClickDataPoint,
    ClickBatchRequest,
)


class TestGazeWithFixtures:
    """Test gaze schemas using fixtures."""

    def test_create_from_fixture(self, sample_gaze_data):
        point = GazeDataPoint(**sample_gaze_data)
        assert point.screen_x == 960.0
        assert point.screen_y == 540.0

    def test_batch_from_fixture(self, sample_gaze_data):
        batch = GazeBatchRequest(
            response_id=1,
            data=[sample_gaze_data, sample_gaze_data],
        )
        assert len(batch.data) == 2
        assert all(d.post_id == 1 for d in batch.data)

    def test_fixture_iris_data_present(self, sample_gaze_data):
        point = GazeDataPoint(**sample_gaze_data)
        assert point.left_iris_x is not None
        assert point.right_iris_x is not None


class TestClickWithFixtures:
    """Test click schemas using fixtures."""

    def test_create_from_fixture(self, sample_click_data):
        point = ClickDataPoint(**sample_click_data)
        assert point.target_element == "headline"

    def test_batch_from_fixture(self, sample_click_data):
        batch = ClickBatchRequest(
            response_id=1,
            data=[sample_click_data],
        )
        assert len(batch.data) == 1
        assert batch.data[0].target_element == "headline"

    def test_multiple_clicks_on_same_post(self, sample_click_data):
        batch = ClickBatchRequest(
            response_id=1,
            data=[sample_click_data for _ in range(5)],
        )
        assert len(batch.data) == 5
        assert all(d.post_id == 1 for d in batch.data)
