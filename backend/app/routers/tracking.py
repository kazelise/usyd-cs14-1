"""Tracking endpoints: calibration, gaze, clicks. Owned by Backend C."""

from datetime import datetime
from statistics import median

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.participant import SurveyResponse
from app.models.tracking import (
    CalibrationPoint,
    CalibrationSession,
    ClickRecord,
    GazeRecord,
)
from app.schemas.tracking import (
    CalibrationCompleteOut,
    CalibrationPointOut,
    CalibrationSessionOut,
    ClickBatchOut,
    ClickBatchRequest,
    CreateCalibrationRequest,
    GazeBatchOut,
    GazeBatchRequest,
    QualityInfo,
    RecordCalibrationPointRequest,
)

router = APIRouter(
    prefix="/tracking",
    tags=["Tracking (Backend C)"],
)


# ── Calibration ───────────────────────────────────────


@router.post(
    "/calibration/sessions",
    response_model=CalibrationSessionOut,
    status_code=201,
    summary="Create calibration session",
    responses={
        201: {"description": "Calibration session created successfully"},
        404: {"description": "Survey response not found"},
        409: {"description": "Calibration session already exists for this response"},
    },
)
async def create_calibration_session(
    body: CreateCalibrationRequest, db: AsyncSession = Depends(get_db),
):
    """Create a webcam calibration session before the participant begins the survey.

    The participant's browser captures screen and camera dimensions, then
    presents a 9-point calibration grid. Each point is recorded separately
    via the record-point endpoint.
    """
    result = await db.execute(
        select(SurveyResponse).where(SurveyResponse.id == body.response_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Survey response not found")

    existing = await db.execute(
        select(CalibrationSession).where(CalibrationSession.response_id == body.response_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Calibration session already exists")

    session = CalibrationSession(
        response_id=body.response_id,
        screen_width=body.screen_width,
        screen_height=body.screen_height,
        camera_width=body.camera_width,
        camera_height=body.camera_height,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return CalibrationSessionOut(
        session_id=session.id, response_id=session.response_id,
        status=session.status, expected_points=session.expected_points,
        started_at=session.started_at,
    )


@router.post(
    "/calibration/sessions/{session_id}/points",
    response_model=CalibrationPointOut,
    summary="Record a calibration point",
    responses={
        200: {"description": "Calibration point recorded with progress info"},
        404: {"description": "Active calibration session not found"},
    },
)
async def record_calibration_point(
    session_id: int, body: RecordCalibrationPointRequest, db: AsyncSession = Depends(get_db),
):
    """Record iris samples for one calibration point.

    The frontend displays a dot at a known screen position, collects
    MediaPipe Face Mesh iris coordinates while the participant looks at it,
    then sends all samples here. The median iris position is computed
    server-side for each point.
    """
    result = await db.execute(
        select(CalibrationSession).where(
            CalibrationSession.id == session_id, CalibrationSession.status == "in_progress",
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Active calibration session not found")

    valid = [s for s in body.samples if s.face_detected]
    point = CalibrationPoint(
        session_id=session_id, point_index=body.point_index,
        target_screen_x=body.target_screen_x, target_screen_y=body.target_screen_y,
        samples=[s.model_dump() for s in body.samples],
        samples_count=len(body.samples),
        median_left_iris_x=median([s.left_iris_x for s in valid]) if valid else None,
        median_left_iris_y=median([s.left_iris_y for s in valid]) if valid else None,
        median_right_iris_x=median([s.right_iris_x for s in valid]) if valid else None,
        median_right_iris_y=median([s.right_iris_y for s in valid]) if valid else None,
    )
    db.add(point)
    await db.flush()

    count = (await db.execute(
        select(func.count(CalibrationPoint.id)).where(CalibrationPoint.session_id == session_id)
    )).scalar() or 0

    return CalibrationPointOut(
        session_id=session_id, point_index=body.point_index,
        samples_recorded=len(body.samples), points_completed=count,
        points_remaining=session.expected_points - count,
    )


@router.post(
    "/calibration/sessions/{session_id}/complete",
    response_model=CalibrationCompleteOut,
    summary="Complete calibration session",
    responses={
        200: {"description": "Calibration completed with quality assessment"},
        404: {"description": "Active calibration session not found"},
    },
)
async def complete_calibration(session_id: int, db: AsyncSession = Depends(get_db)):
    """Finalize calibration and compute quality metrics.

    Quality is assessed based on face detection rate and number of
    valid points (>= 10 samples each):
    - **good**: face rate >= 90%, valid points >= 78% of expected
    - **acceptable**: face rate >= 70%, valid points >= 56% of expected
    - **poor**: below acceptable thresholds
    """
    result = await db.execute(
        select(CalibrationSession).options(selectinload(CalibrationSession.points))
        .where(CalibrationSession.id == session_id, CalibrationSession.status == "in_progress")
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Active calibration session not found")

    points = session.points
    total_points = len(points)
    valid_points = sum(1 for p in points if p.samples_count >= 10)
    total_samples = sum(p.samples_count for p in points)
    avg_samples = round(total_samples / total_points, 1) if total_points else 0.0

    detected = sum(1 for p in points for s in p.samples if s.get("face_detected"))
    total = sum(len(p.samples) for p in points)
    face_rate = round(detected / total, 3) if total else 0.0

    if face_rate >= 0.9 and valid_points >= session.expected_points * 0.78:
        quality = "good"
    elif face_rate >= 0.7 and valid_points >= session.expected_points * 0.56:
        quality = "acceptable"
    else:
        quality = "poor"

    session.status = "completed"
    session.completed_at = datetime.utcnow()
    session.face_detection_rate = face_rate
    session.quality = quality
    await db.flush()
    await db.refresh(session)

    return CalibrationCompleteOut(
        session_id=session.id, status="completed",
        quality=QualityInfo(
            total_points=total_points, valid_points=valid_points,
            avg_samples_per_point=avg_samples, face_detection_rate=face_rate,
            overall_quality=quality,
        ),
        completed_at=session.completed_at,
    )


# ── Gaze Tracking ─────────────────────────────────────


@router.post(
    "/gaze",
    response_model=GazeBatchOut,
    summary="Record gaze data batch",
    responses={
        200: {"description": "Gaze data saved successfully"},
    },
)
async def record_gaze_batch(body: GazeBatchRequest, db: AsyncSession = Depends(get_db)):
    """Record a batch of gaze data points.

    The frontend eye-tracking module (MediaPipe Face Mesh) estimates
    where the participant is looking on screen and sends coordinates
    every 5-10 seconds. Each data point includes screen XY position
    and raw iris coordinates for both eyes.
    """
    if not body.data:
        return GazeBatchOut(saved=0)

    result = await db.execute(
        select(SurveyResponse).where(SurveyResponse.id == body.response_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Survey response not found")

    for g in body.data:
        db.add(GazeRecord(
            response_id=body.response_id, post_id=g.post_id,
            timestamp_ms=g.timestamp_ms, screen_x=g.screen_x, screen_y=g.screen_y,
            left_iris_x=g.left_iris_x, left_iris_y=g.left_iris_y,
            right_iris_x=g.right_iris_x, right_iris_y=g.right_iris_y,
        ))
    await db.flush()
    return GazeBatchOut(saved=len(body.data))


# ── Click Tracking ────────────────────────────────────


@router.post(
    "/clicks",
    response_model=ClickBatchOut,
    summary="Record click data batch",
    responses={
        200: {"description": "Click data saved successfully"},
    },
)
async def record_click_batch(body: ClickBatchRequest, db: AsyncSession = Depends(get_db)):
    """Record a batch of mouse click events.

    The frontend captures every click during survey participation,
    buffering them and flushing every 10 seconds. Each event includes
    screen coordinates and the type of element clicked (headline,
    image, like_button, comment_button, share_count, or other).
    """
    if not body.data:
        return ClickBatchOut(saved=0)

    result = await db.execute(
        select(SurveyResponse).where(SurveyResponse.id == body.response_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Survey response not found")

    for c in body.data:
        db.add(ClickRecord(
            response_id=body.response_id, post_id=c.post_id,
            timestamp_ms=c.timestamp_ms, screen_x=c.screen_x, screen_y=c.screen_y,
            target_element=c.target_element,
        ))
    await db.flush()
    return ClickBatchOut(saved=len(body.data))
