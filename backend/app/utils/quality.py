"""Calibration quality computation. Owned by Backend C."""


def compute_calibration_quality(points: list[dict], expected_points: int) -> dict:
    """Compute calibration quality metrics from recorded points.

    Args:
        points: list of dicts, each with 'samples_count' and 'samples' keys.
        expected_points: number of calibration points expected (e.g. 9).

    Returns:
        dict with total_points, valid_points, avg_samples_per_point,
        face_detection_rate, and overall_quality.
    """
    total_points = len(points)
    if total_points == 0:
        return {
            "total_points": 0,
            "valid_points": 0,
            "avg_samples_per_point": 0.0,
            "face_detection_rate": 0.0,
            "overall_quality": "poor",
        }

    valid_points = sum(1 for p in points if p["samples_count"] >= 10)
    total_samples = sum(p["samples_count"] for p in points)
    avg_samples = round(total_samples / total_points, 1)

    detected = sum(1 for p in points for s in p["samples"] if s.get("face_detected"))
    total = sum(len(p["samples"]) for p in points)
    face_rate = round(detected / total, 3) if total else 0.0

    if face_rate >= 0.9 and valid_points >= expected_points * 0.78:
        quality = "good"
    elif face_rate >= 0.7 and valid_points >= expected_points * 0.56:
        quality = "acceptable"
    else:
        quality = "poor"

    return {
        "total_points": total_points,
        "valid_points": valid_points,
        "avg_samples_per_point": avg_samples,
        "face_detection_rate": face_rate,
        "overall_quality": quality,
    }
