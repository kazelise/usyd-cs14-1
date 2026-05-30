"""Validation tests for survey config and auth request bounds.

Regression coverage for unbounded fields that could brick a survey or crash
account creation:
- calibration_points capped at 25 (matches calibration point_index le=25);
  a higher value makes calibration impossible to pass and permanently blocks
  completion.
- gaze_interval_ms kept in a sane range.
- register password bounded to bcrypt's 72-byte limit with a minimum length.
"""

import pytest
from pydantic import ValidationError

from app.schemas.auth import RegisterRequest
from app.schemas.survey import CreateSurveyRequest, UpdateSurveyRequest


class TestCalibrationPointsBounds:
    def test_default_is_accepted(self):
        assert CreateSurveyRequest(title="S").calibration_points == 9

    def test_max_allowed_boundary(self):
        assert CreateSurveyRequest(title="S", calibration_points=25).calibration_points == 25

    @pytest.mark.parametrize("value", [0, -1, 26, 1000])
    def test_out_of_range_rejected_on_create(self, value):
        with pytest.raises(ValidationError):
            CreateSurveyRequest(title="S", calibration_points=value)

    @pytest.mark.parametrize("value", [0, -1, 26])
    def test_out_of_range_rejected_on_update(self, value):
        with pytest.raises(ValidationError):
            UpdateSurveyRequest(calibration_points=value)


class TestGazeIntervalBounds:
    def test_default_is_accepted(self):
        assert CreateSurveyRequest(title="S").gaze_interval_ms == 1000

    @pytest.mark.parametrize("value", [99, 0, -1, 10001])
    def test_out_of_range_rejected(self, value):
        with pytest.raises(ValidationError):
            CreateSurveyRequest(title="S", gaze_interval_ms=value)


class TestRegisterPasswordBounds:
    def test_valid_password_accepted(self):
        req = RegisterRequest(email="a@b.com", password="strongpass", name="A")
        assert req.password == "strongpass"

    def test_too_short_rejected(self):
        with pytest.raises(ValidationError):
            RegisterRequest(email="a@b.com", password="short", name="A")

    def test_over_bcrypt_limit_rejected(self):
        with pytest.raises(ValidationError):
            RegisterRequest(email="a@b.com", password="x" * 73, name="A")

    def test_bcrypt_limit_boundary_accepted(self):
        req = RegisterRequest(email="a@b.com", password="x" * 72, name="A")
        assert len(req.password) == 72
