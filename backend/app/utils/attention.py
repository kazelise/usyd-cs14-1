"""Survey-time attention quality scoring.

The participant client periodically samples the webcam during the survey. We
do not store the raw video, only counts of detected vs. missed face/iris
samples plus an "active tracking" duration. From those, the server derives a
0..1 confidence score and a coarse quality bucket so that downstream exports
and analytics can downgrade responses where the participant repeatedly
covered the camera or looked away.

The scorer is deliberately tolerant: a calibration that already passed is
worth a soft floor, and a survey where the participant did most of the work
with face visible still gets a respectable score even when a few coverage
gaps occurred. Calibration that explicitly failed pulls the score down so a
response cannot exaggerate quality past what the camera ever supported.
"""

from __future__ import annotations

from typing import Any

GOOD_COVERAGE = 0.85
GOOD_MISSING_RATIO = 0.10

ACCEPTABLE_COVERAGE = 0.60
ACCEPTABLE_MISSING_RATIO = 0.30

MIN_EXPECTED_SAMPLES = 5


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(value, maximum))


def _safe_ratio(numerator: float | int | None, denominator: float | int | None) -> float:
    if not denominator:
        return 0.0
    return float(numerator or 0) / float(denominator)


def compute_attention_quality(
    *,
    active_ms: int | None,
    expected_samples: int | None,
    detected_samples: int | None,
    missing_ms: int | None,
    no_face_periods: int | None = None,
    calibration_passed: bool | None = None,
    calibration_quality: str | None = None,
) -> dict[str, Any]:
    """Return coverage, confidence, quality bucket and a short reason string.

    The shape is dict[str, Any] so the caller can spread it onto a SQLAlchemy
    response or include it in an export payload without re-deriving anything.
    """

    active_ms_int = max(int(active_ms or 0), 0)
    expected_int = max(int(expected_samples or 0), 0)
    detected_int = max(int(detected_samples or 0), 0)
    missing_ms_int = max(int(missing_ms or 0), 0)
    periods_int = max(int(no_face_periods or 0), 0)

    # Cap detected at expected so a misbehaving client can't fake >100% coverage.
    detected_capped = min(detected_int, expected_int) if expected_int else detected_int

    coverage = _safe_ratio(detected_capped, expected_int)
    missing_ratio = _safe_ratio(missing_ms_int, active_ms_int)

    # Base confidence from sample coverage.
    confidence = coverage

    # Penalize when face is missing for long stretches even if a few samples landed.
    if missing_ratio > 0:
        confidence = min(confidence, max(0.0, 1.0 - missing_ratio))

    # Tiny sessions (e.g. participant raced through in <5 sample windows)
    # cannot reasonably support a high confidence score.
    if expected_int and expected_int < MIN_EXPECTED_SAMPLES:
        confidence = min(confidence, 0.5)

    # Survey-time tracking was disabled or never started.
    if expected_int == 0 and active_ms_int == 0:
        confidence = 0.0

    # Calibration that explicitly failed caps the survey-time confidence.
    if calibration_passed is False:
        confidence = min(confidence, 0.5)
    elif calibration_quality == "poor":
        confidence = min(confidence, 0.6)

    confidence = round(_clamp(confidence), 3)
    coverage_rounded = round(_clamp(coverage), 3)

    too_few_windows = bool(expected_int) and expected_int < MIN_EXPECTED_SAMPLES

    if expected_int == 0 and active_ms_int == 0:
        bucket = "unknown"
        reason = (
            "No survey-time tracking data was reported; cannot estimate attention quality."
        )
    elif (
        coverage_rounded >= GOOD_COVERAGE
        and missing_ratio <= GOOD_MISSING_RATIO
        and calibration_passed is not False
        and not too_few_windows
    ):
        bucket = "high"
        reason = (
            f"Face/eye samples covered {coverage_rounded:.0%} of expected windows "
            f"with {missing_ratio:.0%} missing-face time."
        )
    elif (
        coverage_rounded >= ACCEPTABLE_COVERAGE
        and missing_ratio <= ACCEPTABLE_MISSING_RATIO
    ):
        bucket = "medium"
        if too_few_windows:
            reason = (
                f"Limited tracking window: only {expected_int} sample(s) collected; "
                "treating confidence as partial."
            )
        else:
            reason = (
                f"Partial attention coverage: {coverage_rounded:.0%} samples captured, "
                f"{missing_ratio:.0%} missing-face time, {periods_int} dropout(s)."
            )
    else:
        bucket = "low"
        gaps: list[str] = []
        if coverage_rounded < ACCEPTABLE_COVERAGE:
            gaps.append(f"only {coverage_rounded:.0%} sample coverage")
        if missing_ratio > ACCEPTABLE_MISSING_RATIO:
            gaps.append(f"{missing_ratio:.0%} missing-face time")
        if periods_int >= 3:
            gaps.append(f"{periods_int} tracking dropouts")
        if calibration_passed is False:
            gaps.append("calibration did not pass")
        reason = (
            "Low attention confidence: " + ", ".join(gaps) + "."
            if gaps
            else "Low attention confidence."
        )

    return {
        "active_ms": active_ms_int,
        "expected_samples": expected_int,
        "detected_samples": detected_int,
        "missing_ms": missing_ms_int,
        "no_face_periods": periods_int,
        "coverage": coverage_rounded,
        "confidence": confidence,
        "quality": bucket,
        "quality_reason": reason,
    }
