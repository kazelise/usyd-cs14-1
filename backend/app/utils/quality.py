"""Calibration quality computation. Owned by Backend C."""

from __future__ import annotations

from statistics import mean
from typing import Any

MIN_SAMPLES_PER_POINT = 10
MIN_POINT_FACE_RATE = 0.70
MIN_POINT_STABILITY = 0.70

GOOD_FACE_RATE = 0.90
GOOD_VALID_COVERAGE = 0.78
GOOD_STABILITY = 0.80
GOOD_SCORE = 85.0

ACCEPTABLE_FACE_RATE = 0.70
ACCEPTABLE_VALID_COVERAGE = 0.56
ACCEPTABLE_STABILITY = 0.60
ACCEPTABLE_SCORE = 70.0


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(value, maximum))


def _iris_complete(sample: dict[str, Any]) -> bool:
    return all(
        sample.get(field) is not None
        for field in ("left_iris_x", "left_iris_y", "right_iris_x", "right_iris_y")
    )


def _numeric_rotation_value(rotation: dict[str, Any], key: str) -> float | None:
    value = rotation.get(key)
    if isinstance(value, int | float):
        return float(value)
    return None


def _rotation_stability(samples: list[dict[str, Any]]) -> float:
    """Return 0..1 head-pose stability from yaw/pitch, or 1.0 when not available."""
    yaw_values: list[float] = []
    pitch_values: list[float] = []

    for sample in samples:
        rotation = sample.get("head_rotation")
        if not isinstance(rotation, dict):
            continue
        yaw = _numeric_rotation_value(rotation, "yaw")
        pitch = _numeric_rotation_value(rotation, "pitch")
        if yaw is not None:
            yaw_values.append(yaw)
        if pitch is not None:
            pitch_values.append(pitch)

    if len(yaw_values) < 2 and len(pitch_values) < 2:
        return 1.0

    yaw_range = max(yaw_values) - min(yaw_values) if len(yaw_values) >= 2 else 0.0
    pitch_range = max(pitch_values) - min(pitch_values) if len(pitch_values) >= 2 else 0.0

    # Treat roughly 20 degrees of yaw or 16 degrees of pitch drift as fully unstable.
    yaw_penalty = yaw_range / 20.0
    pitch_penalty = pitch_range / 16.0
    return round(_clamp(1.0 - max(yaw_penalty, pitch_penalty)), 3)


def assess_calibration_point(point: dict[str, Any]) -> dict[str, Any]:
    """Compute per-point quality metrics from one calibration dot."""
    samples = point.get("samples") or []
    samples_count = int(point.get("samples_count") or len(samples))

    if samples_count <= 0:
        return {
            "samples_count": 0,
            "face_detection_rate": 0.0,
            "stability_score": 0.0,
            "valid": False,
        }

    detected = [
        sample
        for sample in samples
        if sample.get("face_detected") is True and _iris_complete(sample)
    ]
    face_detection_rate = round(len(detected) / samples_count, 3)
    stability_score = _rotation_stability(detected)
    valid = (
        samples_count >= MIN_SAMPLES_PER_POINT
        and face_detection_rate >= MIN_POINT_FACE_RATE
        and stability_score >= MIN_POINT_STABILITY
    )

    return {
        "samples_count": samples_count,
        "face_detection_rate": face_detection_rate,
        "stability_score": stability_score,
        "valid": valid,
    }


def _quality_reason(
    *,
    missing_points: int,
    valid_coverage: float,
    face_detection_rate: float,
    stability_score: float,
    avg_samples_per_point: float,
    passed: bool,
) -> str:
    if passed:
        return (
            f"Calibration passed with {valid_coverage:.0%} valid point coverage, "
            f"{face_detection_rate:.0%} face detection, and {stability_score:.0%} stability."
        )

    reasons: list[str] = []
    if missing_points:
        reasons.append(f"{missing_points} expected point(s) were not recorded")
    if valid_coverage < ACCEPTABLE_VALID_COVERAGE:
        reasons.append("too few points met validity thresholds")
    if face_detection_rate < ACCEPTABLE_FACE_RATE:
        reasons.append("face detection rate was too low")
    if stability_score < ACCEPTABLE_STABILITY:
        reasons.append("head pose was unstable")
    if avg_samples_per_point < MIN_SAMPLES_PER_POINT:
        reasons.append("average samples per point were too low")
    if not reasons:
        reasons.append("overall quality score was below the pass threshold")
    return "Calibration failed: " + "; ".join(reasons) + "."


def compute_calibration_quality(points: list[dict], expected_points: int) -> dict:
    """Compute research-grade calibration quality metrics.

    The scoring uses only numeric MediaPipe/iris samples. It does not require or
    store webcam images, video, frames, or biometric identity templates.
    """
    expected_points = max(int(expected_points or 0), 1)
    total_points = len(points)
    missing_points = max(expected_points - total_points, 0)

    if total_points == 0:
        return {
            "total_points": 0,
            "expected_points": expected_points,
            "valid_points": 0,
            "missing_points": expected_points,
            "avg_samples_per_point": 0.0,
            "face_detection_rate": 0.0,
            "stability_score": 0.0,
            "quality_score": 0.0,
            "passed": False,
            "overall_quality": "poor",
            "quality_reason": "Calibration failed: no calibration points were recorded.",
        }

    point_metrics = [assess_calibration_point(point) for point in points]
    valid_points = sum(1 for metric in point_metrics if metric["valid"])
    total_samples = sum(metric["samples_count"] for metric in point_metrics)
    avg_samples = round(total_samples / total_points, 1) if total_points else 0.0

    detected_samples = sum(
        1
        for point in points
        for sample in (point.get("samples") or [])
        if sample.get("face_detected") is True and _iris_complete(sample)
    )
    face_detection_rate = round(detected_samples / total_samples, 3) if total_samples else 0.0
    stability_score = round(mean(metric["stability_score"] for metric in point_metrics), 3)

    valid_coverage = min(valid_points / expected_points, 1.0)
    sample_score = _clamp(avg_samples / MIN_SAMPLES_PER_POINT)
    raw_score = 100.0 * (
        0.40 * valid_coverage
        + 0.30 * face_detection_rate
        + 0.20 * stability_score
        + 0.10 * sample_score
    )

    quality_score = raw_score
    if (
        face_detection_rate < GOOD_FACE_RATE
        or valid_coverage < GOOD_VALID_COVERAGE
        or stability_score < GOOD_STABILITY
    ):
        quality_score = min(quality_score, 84.0)
    if (
        face_detection_rate < ACCEPTABLE_FACE_RATE
        or valid_coverage < ACCEPTABLE_VALID_COVERAGE
        or stability_score < ACCEPTABLE_STABILITY
    ):
        quality_score = min(quality_score, 69.0)

    quality_score = round(max(0.0, min(100.0, quality_score)), 1)
    passed = quality_score >= ACCEPTABLE_SCORE

    if (
        passed
        and quality_score >= GOOD_SCORE
        and face_detection_rate >= GOOD_FACE_RATE
        and valid_coverage >= GOOD_VALID_COVERAGE
        and stability_score >= GOOD_STABILITY
    ):
        quality = "good"
    elif passed:
        quality = "acceptable"
    else:
        quality = "poor"

    return {
        "total_points": total_points,
        "expected_points": expected_points,
        "valid_points": valid_points,
        "missing_points": missing_points,
        "avg_samples_per_point": avg_samples,
        "face_detection_rate": face_detection_rate,
        "stability_score": stability_score,
        "quality_score": quality_score,
        "passed": passed,
        "overall_quality": quality,
        "quality_reason": _quality_reason(
            missing_points=missing_points,
            valid_coverage=valid_coverage,
            face_detection_rate=face_detection_rate,
            stability_score=stability_score,
            avg_samples_per_point=avg_samples,
            passed=passed,
        ),
    }
