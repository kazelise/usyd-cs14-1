"""Tracking endpoints: calibration, gaze, clicks. Owned by Backend C.

Refactored for clarity and maintainability.
"""

from datetime import datetime
from statistics import median

from app.utils.quality import compute_calibration_quality

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

router = APIRouter(prefix="/tracking", tags=["Tracking"])


# ── Calibration ───────────────────────────────────────


@router.post("/calibration/sessions", response_model=CalibrationSessionOut, status_code=201)
async def create_calibration_session(
    body: CreateCalibrationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a calibration session when participant begins webcam calibration."""
    result = await db.execute(select(SurveyResponse).where(SurveyResponse.id == body.response_id))
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
        session_id=session.id,
        response_id=session.response_id,
        status=session.status,
        expected_points=session.expected_points,
        started_at=session.started_at,
    )


@router.post("/calibration/sessions/{session_id}/points", response_model=CalibrationPointOut)
async def record_calibration_point(
    session_id: int,
    body: RecordCalibrationPointRequest,
    db: AsyncSession = Depends(get_db),
):
    """Record data for one calibration point."""
    result = await db.execute(
        select(CalibrationSession).where(
            CalibrationSession.id == session_id,
            CalibrationSession.status == "in_progress",
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Active calibration session not found")

    valid = [s for s in body.samples if s.face_detected]
    point = CalibrationPoint(
        session_id=session_id,
        point_index=body.point_index,
        target_screen_x=body.target_screen_x,
        target_screen_y=body.target_screen_y,
        samples=[s.model_dump() for s in body.samples],
        samples_count=len(body.samples),
        median_left_iris_x=median([s.left_iris_x for s in valid]) if valid else None,
        median_left_iris_y=median([s.left_iris_y for s in valid]) if valid else None,
        median_right_iris_x=median([s.right_iris_x for s in valid]) if valid else None,
        median_right_iris_y=median([s.right_iris_y for s in valid]) if valid else None,
    )
    db.add(point)
    await db.flush()

    count = (
        await db.execute(
            select(func.count(CalibrationPoint.id)).where(CalibrationPoint.session_id == session_id)
        )
    ).scalar() or 0

    return CalibrationPointOut(
        session_id=session_id,
        point_index=body.point_index,
        samples_recorded=len(body.samples),
        points_completed=count,
        points_remaining=session.expected_points - count,
    )


@router.post("/calibration/sessions/{session_id}/complete", response_model=CalibrationCompleteOut)
async def complete_calibration(session_id: int, db: AsyncSession = Depends(get_db)):
    """Complete calibration and compute quality metrics."""
    result = await db.execute(
        select(CalibrationSession)
        .options(selectinload(CalibrationSession.points))
        .where(CalibrationSession.id == session_id, CalibrationSession.status == "in_progress")
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Active calibration session not found")

    points = session.points
    point_dicts = [
        {"samples_count": p.samples_count, "samples": p.samples} for p in points
    ]
    metrics = compute_calibration_quality(point_dicts, session.expected_points)

    session.status = "completed"
    session.completed_at = datetime.utcnow()
    session.face_detection_rate = metrics["face_detection_rate"]
    session.quality = metrics["overall_quality"]
    await db.flush()
    await db.refresh(session)

    return CalibrationCompleteOut(
        session_id=session.id,
        status="completed",
        quality=QualityInfo(
            total_points=metrics["total_points"],
            valid_points=metrics["valid_points"],
            avg_samples_per_point=metrics["avg_samples_per_point"],
            face_detection_rate=metrics["face_detection_rate"],
            overall_quality=metrics["overall_quality"],
        ),
        completed_at=session.completed_at,
    )


# ── Gaze Tracking ─────────────────────────────────────


@router.post("/gaze", response_model=GazeBatchOut)
async def record_gaze_batch(body: GazeBatchRequest, db: AsyncSession = Depends(get_db)):
    """Record a batch of gaze data points. Frontend sends these every 5-10 seconds."""
    for g in body.data:
        db.add(
            GazeRecord(
                response_id=body.response_id,
                post_id=g.post_id,
                timestamp_ms=g.timestamp_ms,
                screen_x=g.screen_x,
                screen_y=g.screen_y,
                left_iris_x=g.left_iris_x,
                left_iris_y=g.left_iris_y,
                right_iris_x=g.right_iris_x,
                right_iris_y=g.right_iris_y,
            )
        )
    await db.flush()
    return GazeBatchOut(saved=len(body.data))


# ── Click Tracking ────────────────────────────────────


@router.post("/clicks", response_model=ClickBatchOut)
async def record_click_batch(body: ClickBatchRequest, db: AsyncSession = Depends(get_db)):
    """Record a batch of mouse click events."""
    for c in body.data:
        db.add(
            ClickRecord(
                response_id=body.response_id,
                post_id=c.post_id,
                timestamp_ms=c.timestamp_ms,
                screen_x=c.screen_x,
                screen_y=c.screen_y,
                target_element=c.target_element,
            )
        )
    await db.flush()
    return ClickBatchOut(saved=len(body.data))
