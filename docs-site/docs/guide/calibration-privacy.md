# Calibration & Privacy

Calibration supports gaze-quality analysis, but it depends on browser permission, lighting, camera stability, and participant behavior.

## Calibration Flow

1. Participant opens the survey start page.
2. Participant selects language and consents.
3. Browser requests camera permission.
4. The app checks face presence and stability.
5. Participant follows the dot sequence.
6. The app stores calibration points and a quality outcome.
7. Participant continues to the feed when the survey settings allow it.

Expected outcomes should include a numeric score or quality band such as `good`, `acceptable`, or `poor`. Poor runs should either ask for retry or be flagged for researcher review.

## Troubleshooting

| Symptom | Likely cause | Researcher/participant action |
|---|---|---|
| Camera prompt never appears | Browser permission already blocked or insecure context. | Check site permissions; use HTTPS in production or localhost during development. |
| Camera opens but no face detected | Face out of frame, covered camera, unsupported browser, dark lighting. | Center face, improve lighting, close other camera apps, refresh. |
| Dot sequence fails repeatedly | Participant looks away, moves too much, or browser performance is poor. | Ask participant to keep head still and look at each dot; retry once. |
| Calibration score is poor | Low face-detection rate or unstable gaze samples. | Mark response for review or exclude with calibration filter. |
| Mobile device behaves inconsistently | Camera/viewport constraints vary across devices. | Prefer desktop/laptop for calibrated gaze studies unless mobile has been validated. |

## Researcher Review

In analytics/export, review:

- Calibration quality band.
- Numeric score if available.
- Face detection rate.
- Stability score/rate.
- Retry count or failure reason.
- Whether poor calibration should be excluded from gaze analysis.

Poor calibration does not necessarily invalidate survey answers, but it may invalidate gaze-based conclusions.

## Data And Privacy Notes

The platform should follow these rules:

- Store anonymous participant response identifiers.
- Store calibration summaries and gaze/click samples needed for analysis.
- Do not store raw webcam video.
- Do not export raw participant tokens.
- Do not export researcher passwords or authentication secrets.
- Use HTTPS for real participants so camera permission works in a secure browser context.
- Explain camera use and tracking clearly in participant-facing consent text.
- Limit exports to researchers who own the survey.

Before final deployment, verify privacy behavior with both CSV and JSON exports. The files should contain research data needed for analysis, not raw credentials, raw video, or private browser/session data.
