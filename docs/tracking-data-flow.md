# Tracking Data Flow

**Owner:** Backend C

## Participant Session Flow

```
1. Participant opens survey link
2. Frontend creates a SurveyResponse (Backend A)
3. If calibration is enabled:
   a. Frontend requests POST /tracking/calibration/sessions
   b. Webcam activates, 9-point grid displayed
   c. For each point: POST /tracking/calibration/sessions/{id}/points
   d. After all points: POST /tracking/calibration/sessions/{id}/complete
   e. Quality check returned to frontend
4. Participant views posts:
   a. Gaze data batched every 5-10 seconds → POST /tracking/gaze
   b. Click events batched → POST /tracking/clicks
```

## Data Storage

| Table | Key Columns | Indexed On |
|-------|-------------|------------|
| calibration_sessions | response_id, status, quality | response_id (unique) |
| calibration_points | session_id, point_index, samples | (session_id, point_index) unique |
| gaze_records | response_id, post_id, screen_x/y | response_id, (response_id, timestamp_ms), (post_id, timestamp_ms) |
| click_records | response_id, post_id, screen_x/y | response_id, (response_id, timestamp_ms), (post_id, timestamp_ms) |

## Batch Processing

Gaze and click data arrive in batches to reduce HTTP overhead.
Each batch is associated with a single `response_id` and `participant_token`.
The backend accepts the batch only when the token matches an active
`survey_responses` row.
Individual records within a batch may reference different `post_id` values.
Every supplied `post_id` must belong to the same survey as the participant
response; otherwise the whole batch is rejected and no rows are persisted.


## Error Handling

| Scenario | HTTP Status | Detail |
|----------|-------------|--------|
| Survey response not found | 404 | "Survey response not found" |
| Participant token missing or invalid | 404 | "Active participant response not found" |
| Calibration session already exists | 409 | "Calibration session already exists" |
| Active calibration session not found | 404 | "Active calibration session not found" |
| Duplicate calibration point | 409 | "Calibration point {point_index} already exists for this session" |
| Completing calibration before any point is recorded | 409 | "At least one calibration point is required before completion" |
| Gaze/click `post_id` does not belong to the response survey | 422 | "post_id values do not belong to this survey: [...]" |
| Empty gaze/click batch | 200 | Returns `{"saved": 0}` |

## Testing

Run the tracking module tests:

```bash
cd backend
python -m pytest tests/ -v
```
