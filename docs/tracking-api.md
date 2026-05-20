# Tracking Module API Documentation

> Last updated: 2026-04-25

**Owner:** Backend C

## Overview

The tracking module provides three groups of endpoints for capturing
participant behavior during survey sessions:

1. **Calibration** — webcam calibration using iris tracking
2. **Gaze Tracking** — continuous eye-gaze position recording
3. **Click Tracking** — mouse click event recording

All endpoints are under `/api/v1/tracking/`.

Participant-side write endpoints require both `response_id` and
`participant_token`. The backend only accepts writes when the response exists,
the token matches, and the participant response is still `in_progress`.

## Endpoints

### Calibration

| Method | Path | Description |
|--------|------|-------------|
| POST | `/calibration/sessions` | Create a new calibration session |
| POST | `/calibration/sessions/{id}/points` | Record one calibration point |
| POST | `/calibration/sessions/{id}/complete` | Complete session & get quality |

### Gaze Tracking

| Method | Path | Description |
|--------|------|-------------|
| POST | `/gaze` | Submit a batch of gaze data points |

### Click Tracking

| Method | Path | Description |
|--------|------|-------------|
| POST | `/clicks` | Submit a batch of click events |

## Quality Metrics

Calibration completion returns a research-grade quality object and stores the
same outcome on `calibration_sessions`:

- `total_points`
- `expected_points`
- `valid_points`
- `missing_points`
- `avg_samples_per_point`
- `face_detection_rate`
- `stability_score`
- `quality_score` from 0 to 100
- `passed`
- `overall_quality`: `good`, `acceptable`, or `poor`
- `quality_reason`

A valid point requires enough samples, sufficient face detection, and stable
head pose when `head_rotation.yaw` / `head_rotation.pitch` are supplied.
Quality is rated as:

- **good** — score >= 85 with strong face detection, point coverage, and stability
- **acceptable** — score >= 70 and above minimum face/coverage/stability thresholds
- **poor** — failed pass threshold or missing/unstable/low-detection data

Only numeric calibration and gaze values are stored. Webcam images, videos,
frames, and raw media blobs must not be sent or persisted.

## Validation Limits

- `screen_width`, `screen_height`, `camera_width`, and `camera_height` must be positive.
- `point_index` is 1-based and must be within the session's expected point range.
- Calibration point samples must include 1 to 60 samples.
- Gaze and click batches may include at most 500 records.
- `post_id`, when supplied on gaze or click records, must belong to the same survey as the participant response.
- `target_element`, when supplied on click records, must be a non-empty string.
- Normalized iris coordinates must be between 0 and 1 when present.
- If `face_detected` is true, all four iris coordinates are required. The frontend fallback is to send normalized numeric estimates rather than raw webcam media.

## Request / Response Examples

### Create Calibration Session

**Request:**
```json
{
  "response_id": 42,
  "participant_token": "anonymous-session-token",
  "screen_width": 1920,
  "screen_height": 1080,
  "camera_width": 640,
  "camera_height": 480
}
```

**Response (201):**
```json
{
  "session_id": 1,
  "response_id": 42,
  "status": "in_progress",
  "expected_points": 9,
  "started_at": "2026-04-01T10:00:00"
}
```

Creating a second calibration session for the same response returns `409`.

### Record Calibration Point

**Request:**
```json
{
  "participant_token": "anonymous-session-token",
  "point_index": 1,
  "target_screen_x": 960,
  "target_screen_y": 540,
  "samples": [
    {
      "timestamp_ms": 1714000000000,
      "left_iris_x": 0.45,
      "left_iris_y": 0.52,
      "right_iris_x": 0.55,
      "right_iris_y": 0.48,
      "face_detected": true,
      "head_rotation": {
        "yaw": 1.2,
        "pitch": -0.4,
        "roll": 0.0
      }
    }
  ]
}
```

**Response (200):**
```json
{
  "session_id": 1,
  "point_index": 1,
  "samples_recorded": 1,
  "points_completed": 1,
  "points_remaining": 8
}
```

Submitting the same `point_index` twice for a session returns `409`.

### Complete Calibration

**Request:**
```json
{
  "participant_token": "anonymous-session-token"
}
```

**Response (200):**
```json
{
  "session_id": 1,
  "status": "completed",
  "quality": {
    "total_points": 9,
    "expected_points": 9,
    "valid_points": 9,
    "missing_points": 0,
    "avg_samples_per_point": 12.0,
    "face_detection_rate": 0.98,
    "stability_score": 0.96,
    "quality_score": 96.8,
    "passed": true,
    "overall_quality": "good",
    "quality_reason": "Calibration passed with 100% valid point coverage, 98% face detection, and 96% stability."
  },
  "completed_at": "2026-04-25T10:05:00"
}
```

Completing a calibration session before at least one point has been recorded
returns `409`.

### Record Gaze Batch

**Request:**
```json
{
  "response_id": 42,
  "participant_token": "anonymous-session-token",
  "data": [
    {
      "post_id": 1,
      "timestamp_ms": 5000,
      "screen_x": 960.0,
      "screen_y": 540.0,
      "left_iris_x": 0.45,
      "left_iris_y": 0.52
    }
  ]
}
```

**Response (200):**
```json
{
  "saved": 1
}
```

If a batch references a `post_id` outside the response's survey, the request
returns `422` and no records from that batch are saved.

### Record Click Batch

**Request:**
```json
{
  "response_id": 42,
  "participant_token": "anonymous-session-token",
  "data": [
    {
      "post_id": 1,
      "timestamp_ms": 8000,
      "screen_x": 500.0,
      "screen_y": 300.0,
      "target_element": "headline"
    }
  ]
}
```

**Response (200):**
```json
{
  "saved": 1
}
```

If a batch references a `post_id` outside the response's survey, the request
returns `422` and no records from that batch are saved.


## Related Documents

- [Tracking Data Flow](tracking-data-flow.md) — end-to-end participant session flow
- [Design Decisions](tracking-design-decisions.md) — rationale for key design choices
