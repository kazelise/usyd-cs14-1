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
| gaze_records | response_id, post_id, screen_x/y | response_id |
| click_records | response_id, post_id, screen_x/y | response_id |

## Batch Processing

Gaze and click data arrive in batches to reduce HTTP overhead.
Each batch is associated with a single `response_id`.
Individual records within a batch may reference different `post_id` values.


## Error Handling

| Scenario | HTTP Status | Detail |
|----------|-------------|--------|
| Survey response not found | 404 | "Survey response not found" |
| Calibration session already exists | 409 | "Calibration session already exists" |
| Active calibration session not found | 404 | "Active calibration session not found" |
| Empty gaze/click batch | 200 | Returns `{"saved": 0}` |

## Testing

Run the tracking module tests:

```bash
cd backend
python -m pytest tests/ -v
```
