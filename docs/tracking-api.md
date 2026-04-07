# Tracking Module API Documentation

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
