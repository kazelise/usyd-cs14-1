"""Tests for calibration workflow data consistency."""

from datetime import datetime

from app.schemas.tracking import (
    CalibrationCompleteOut,
    CalibrationPointOut,
    CalibrationSessionOut,
    CreateCalibrationRequest,
    IrisSample,
    QualityInfo,
    RecordCalibrationPointRequest,
)


class TestCalibrationWorkflowSchemas:
    """Test the full calibration workflow through schemas."""

    def test_session_creation_to_output(self, sample_calibration_request):
        req = CreateCalibrationRequest(**sample_calibration_request)
        out = CalibrationSessionOut(
            session_id=1,
            response_id=req.response_id,
            status="in_progress",
            expected_points=9,
            started_at=datetime.utcnow(),
        )
        assert out.response_id == req.response_id
        assert out.status == "in_progress"

    def test_point_recording_flow(self, sample_iris_data):
        samples = [IrisSample(**sample_iris_data) for _ in range(12)]
        req = RecordCalibrationPointRequest(
            participant_token="participant-token",
            point_index=0,
            target_screen_x=100,
            target_screen_y=100,
            samples=samples,
        )
        out = CalibrationPointOut(
            session_id=1,
            point_index=req.point_index,
            samples_recorded=len(req.samples),
            points_completed=1,
            points_remaining=8,
        )
        assert out.samples_recorded == 12
        assert out.points_remaining == 8

    def test_completion_flow(self):
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
            completed_at=datetime.utcnow(),
        )
        assert out.status == "completed"
        assert out.quality.overall_quality == "good"

    def test_nine_point_sequence(self, sample_iris_data):
        """Simulate recording all 9 calibration points."""
        grid_positions = [
            (0, 0),
            (960, 0),
            (1920, 0),
            (0, 540),
            (960, 540),
            (1920, 540),
            (0, 1080),
            (960, 1080),
            (1920, 1080),
        ]
        for idx, (x, y) in enumerate(grid_positions):
            samples = [IrisSample(**sample_iris_data) for _ in range(12)]
            req = RecordCalibrationPointRequest(
                participant_token="participant-token",
                point_index=idx,
                target_screen_x=x,
                target_screen_y=y,
                samples=samples,
            )
            assert req.point_index == idx
            assert len(req.samples) == 12
