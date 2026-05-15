"""Survey-time attention/confidence scoring tests."""

from app.utils.attention import compute_attention_quality


def test_attention_quality_no_samples_returns_unknown():
    metrics = compute_attention_quality(
        active_ms=0,
        expected_samples=0,
        detected_samples=0,
        missing_ms=0,
    )

    assert metrics["coverage"] == 0.0
    assert metrics["confidence"] == 0.0
    assert metrics["quality"] == "unknown"


def test_high_coverage_clean_session_is_high_confidence():
    metrics = compute_attention_quality(
        active_ms=60_000,
        expected_samples=60,
        detected_samples=58,
        missing_ms=2_000,
        no_face_periods=1,
        calibration_passed=True,
        calibration_quality="good",
    )

    assert metrics["quality"] == "high"
    assert metrics["confidence"] >= 0.9
    assert metrics["coverage"] >= 0.95


def test_partial_face_coverage_is_medium_confidence():
    metrics = compute_attention_quality(
        active_ms=60_000,
        expected_samples=60,
        detected_samples=42,
        missing_ms=12_000,
        no_face_periods=3,
        calibration_passed=True,
        calibration_quality="acceptable",
    )

    assert metrics["quality"] == "medium"
    assert 0.6 <= metrics["confidence"] <= 0.9


def test_mostly_missing_face_is_low_confidence():
    metrics = compute_attention_quality(
        active_ms=60_000,
        expected_samples=60,
        detected_samples=12,
        missing_ms=42_000,
        no_face_periods=8,
        calibration_passed=True,
        calibration_quality="acceptable",
    )

    assert metrics["quality"] == "low"
    assert metrics["confidence"] < 0.6


def test_clean_face_but_failed_calibration_is_capped_below_high():
    metrics = compute_attention_quality(
        active_ms=60_000,
        expected_samples=60,
        detected_samples=60,
        missing_ms=0,
        no_face_periods=0,
        calibration_passed=False,
        calibration_quality="poor",
    )

    # Survey-time tracking looks perfect, but calibration failure caps the
    # final confidence so analytics doesn't over-trust the response.
    assert metrics["confidence"] <= 0.5
    assert metrics["quality"] != "high"


def test_client_cannot_inflate_coverage_above_expected():
    # Misbehaving client claims 200 detected samples for a 50-sample window.
    metrics = compute_attention_quality(
        active_ms=50_000,
        expected_samples=50,
        detected_samples=200,
        missing_ms=0,
        calibration_passed=True,
    )

    assert metrics["coverage"] == 1.0
    assert metrics["confidence"] <= 1.0


def test_tiny_session_cannot_be_high_confidence():
    metrics = compute_attention_quality(
        active_ms=2_000,
        expected_samples=2,
        detected_samples=2,
        missing_ms=0,
        calibration_passed=True,
        calibration_quality="good",
    )

    assert metrics["confidence"] <= 0.5
    assert metrics["quality"] != "high"
