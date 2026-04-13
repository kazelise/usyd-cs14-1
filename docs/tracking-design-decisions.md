# Tracking Module Design Decisions

**Owner:** Backend C

## Key Decisions

### 1. Batch Processing for Gaze & Click Data

**Decision:** Accept gaze and click data in batches rather than individual records.

**Rationale:** Sending individual gaze points every 1-2 seconds would create
excessive HTTP overhead. Batching every 5-10 seconds reduces network requests
while maintaining data granularity.

### 2. Quality Rating Thresholds

**Decision:** Three-tier quality system (good / acceptable / poor).

**Thresholds:**
- Good: face detection >= 90%, valid points >= 78% of expected
- Acceptable: face detection >= 70%, valid points >= 56% of expected
- Poor: below acceptable thresholds

**Rationale:** These thresholds were chosen based on MediaPipe Face Mesh
reliability data. A face detection rate below 70% indicates environmental
issues (lighting, camera angle) that would produce unreliable gaze data.

### 3. Median Iris Coordinates

**Decision:** Store median (not mean) of iris coordinates per calibration point.

**Rationale:** Median is more robust to outliers caused by blinks or
momentary tracking loss.

### 4. Cascade Delete

**Decision:** All tracking records cascade-delete with their parent SurveyResponse.

**Rationale:** Tracking data has no meaning without the associated survey
response. Cascade delete ensures clean removal.

### 5. Optional Post ID in Gaze/Click Records

**Decision:** `post_id` is nullable in gaze and click records.

**Rationale:** Gaze data may be captured during transitions between posts
(scrolling, loading). Click events may occur on non-post UI elements.
