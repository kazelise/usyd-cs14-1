"""Tests for batch data processing validation."""

from app.schemas.tracking import (
    ClickBatchRequest,
    GazeBatchRequest,
)


class TestGazeBatchProcessing:
    """Test gaze batch data processing."""

    def test_batch_preserves_order(self):
        data = [
            {"timestamp_ms": i * 1000, "screen_x": float(i * 100), "screen_y": float(i * 50)}
            for i in range(5)
        ]
        batch = GazeBatchRequest(response_id=1, data=data)
        for i, point in enumerate(batch.data):
            assert point.timestamp_ms == i * 1000

    def test_batch_with_mixed_post_ids(self):
        batch = GazeBatchRequest(
            response_id=1,
            data=[
                {"post_id": 1, "timestamp_ms": 1000, "screen_x": 100.0, "screen_y": 100.0},
                {"post_id": 2, "timestamp_ms": 2000, "screen_x": 200.0, "screen_y": 200.0},
                {"post_id": None, "timestamp_ms": 3000, "screen_x": 300.0, "screen_y": 300.0},
            ],
        )
        assert batch.data[0].post_id == 1
        assert batch.data[2].post_id is None

    def test_batch_with_50_items(self):
        data = [
            {"timestamp_ms": i * 100, "screen_x": float(i), "screen_y": float(i)} for i in range(50)
        ]
        batch = GazeBatchRequest(response_id=1, data=data)
        assert len(batch.data) == 50


class TestClickBatchProcessing:
    """Test click batch data processing."""

    def test_batch_preserves_order(self):
        data = [
            {"timestamp_ms": i * 500, "screen_x": float(i * 100), "screen_y": float(i * 50)}
            for i in range(3)
        ]
        batch = ClickBatchRequest(response_id=1, data=data)
        for i, point in enumerate(batch.data):
            assert point.timestamp_ms == i * 500

    def test_batch_various_targets(self):
        targets = ["headline", "image", "like_button", "comment", "share"]
        data = [
            {
                "timestamp_ms": i * 1000,
                "screen_x": 100.0,
                "screen_y": 100.0,
                "target_element": t,
            }
            for i, t in enumerate(targets)
        ]
        batch = ClickBatchRequest(response_id=1, data=data)
        assert [d.target_element for d in batch.data] == targets

    def test_batch_none_and_present_targets(self):
        batch = ClickBatchRequest(
            response_id=1,
            data=[
                {
                    "timestamp_ms": 1000,
                    "screen_x": 100.0,
                    "screen_y": 100.0,
                    "target_element": "image",
                },
                {"timestamp_ms": 2000, "screen_x": 200.0, "screen_y": 200.0},
            ],
        )
        assert batch.data[0].target_element == "image"
        assert batch.data[1].target_element is None
