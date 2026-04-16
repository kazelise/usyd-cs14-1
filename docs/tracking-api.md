# Tracking Module API Documentation

> Last updated: 2026-04-16

**Owner:** Backend C

## Overview

The tracking module provides three groups of endpoints for capturing
participant behavior during survey sessions:

1. **Calibration** — webcam calibration using iris tracking
2. **Gaze Tracking** — continuous eye-gaze position recording
3. **Click Tracking** — mouse click event recording

All endpoints are under `/api/v1/tracking/`.

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

Calibration quality is rated as:

- **good** — face detection rate >= 90%, valid points >= 78% of expected
- **acceptable** — face detection rate >= 70%, valid points >= 56% of expected
- **poor** — below acceptable thresholds

## Request / Response Examples

### Create Calibration Session

**Request:**
```json
{
  "response_id": 42,
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

### Record Gaze Batch

**Request:**
```json
{
  "response_id": 42,
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


## Related Documents

- [Tracking Data Flow](tracking-data-flow.md) — end-to-end participant session flow
- [Design Decisions](tracking-design-decisions.md) — rationale for key design choices
