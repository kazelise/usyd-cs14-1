# Attention Confidence

The platform has two camera-related stages:

1. **Calibration before the survey feed.** Participants follow a dot sequence. The system stores calibration quality, pass/fail, face detection rate, and numeric iris samples for calibration points.
2. **Survey-time tracking during the feed.** After calibration, the participant runner samples face/eye detection and gaze estimates while the participant views posts.

## What Is Captured During Survey Completion

The browser uses MediaPipe Face Mesh locally. It periodically records numeric data:

- visible post id
- timestamp
- estimated screen x/y
- left and right iris positions
- expected sample count
- detected sample count
- missing-face time
- number of no-face dropout periods

Raw webcam video, frames, audio, or biometric identity templates are not uploaded or stored.

## What Happens If the Participant Leaves Frame

If the face or eyes are not detected:

- the floating tracking widget changes from "Face & eyes detected" to weak/lost states;
- expected samples continue increasing, but detected samples do not;
- missing-face milliseconds increase;
- repeated misses become dropout periods;
- the final response receives lower `attention_confidence` and `attention_quality`.

The server recomputes the quality from counts, so the client cannot inflate the score.

## Current Scoring Rules

| Signal | Meaning |
| --- | --- |
| `attention_coverage` | detected samples divided by expected samples. |
| `attention_confidence` | 0 to 1 score capped by coverage, missing-face ratio, short sessions, and calibration quality. |
| `attention_quality` | `high`, `medium`, `low`, or `unknown`. |
| `attention_quality_reason` | Human-readable reason included in CSV/JSON export. |

Typical interpretation:

- **High**: at least 85% sample coverage, at most 10% missing-face time, calibration did not fail.
- **Medium**: at least 60% sample coverage and at most 30% missing-face time.
- **Low**: poor coverage, long missing-face time, repeated dropouts, or failed calibration.
- **Unknown**: no survey-time tracking data was reported.

## Demo Wording

Use this wording with the client:

> During the survey we collect numeric gaze/attention samples and a response-level confidence score. If the participant leaves the frame or covers their eyes, the final response is still saved but is marked lower confidence for analysis and export.
