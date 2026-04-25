"""Tracking endpoints: calibration, gaze, clicks. Owned by Backend C.

Refactored for clarity and maintainability.
"""

from datetime import datetime
from statistics import median

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.participant import SurveyResponse
from app.models.survey import Survey, SurveyPost
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
    CompleteCalibrationRequest,
    CreateCalibrationRequest,
    GazeBatchOut,
    GazeBatchRequest,
    QualityInfo,
    RecordCalibrationPointRequest,
)
from app.utils.quality import assess_calibration_point, compute_calibration_quality

router = APIRouter(prefix="/tracking", tags=["Tracking"])


async def get_active_response_or_404(
    response_id: int, participant_token: str, db: AsyncSession
) -> SurveyResponse:
    """Return an active participant response only when the anonymous token matches."""
    result = await db.execute(select(SurveyResponse).where(SurveyResponse.id == response_id))
    response = result.scalar_one_or_none()
    if not response or response.participant_token != participant_token:
        raise HTTPException(status_code=404, detail="Survey response not found")
    if response.status != "in_progress":
        raise HTTPException(status_code=409, detail="Survey response is not active")
    return response


async def validate_post_ids_for_response(
    response: SurveyResponse,
    post_ids: set[int],
    db: AsyncSession,
) -> None:
    """Ensure tracking data references only posts in the response's survey."""
    if not post_ids:
        return

    result = await db.execute(
        select(SurveyPost.id).where(
            SurveyPost.survey_id == response.survey_id,
            SurveyPost.id.in_(post_ids),
        )
    )
    valid_post_ids = set(result.scalars().all())
    invalid_post_ids = sorted(post_ids - valid_post_ids)
    if invalid_post_ids:
        raise HTTPException(
            status_code=422,
            detail=f"post_id values do not belong to this survey: {invalid_post_ids}",
        )


# ── Calibration ───────────────────────────────────────


@router.post("/calibration/sessions", response_model=CalibrationSessionOut, status_code=201)
async def create_calibration_session(
    body: CreateCalibrationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a calibration session when participant begins webcam calibration."""
    response = await get_active_response_or_404(
        body.response_id, body.participant_token, db
    )

    existing = await db.execute(
        select(CalibrationSession).where(CalibrationSession.response_id == body.response_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Calibration session already exists")

    survey = await db.get(Survey, response.survey_id)
    expected_points = survey.calibration_points if survey else 9

    session = CalibrationSession(
        response_id=response.id,
        screen_width=body.screen_width,
        screen_height=body.screen_height,
        camera_width=body.camera_width,
        camera_height=body.camera_height,
        expected_points=expected_points,
        model_type="mediapipe_face_mesh",
        model_params={"expected_points": expected_points},
    )
    db.add(session)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409, detail="Calibration session already exists"
        ) from exc
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
    await get_active_response_or_404(session.response_id, body.participant_token, db)
    if body.point_index > session.expected_points:
        raise HTTPException(
            status_code=422,
            detail=f"point_index must be between 1 and {session.expected_points}",
        )

    sample_dicts = [s.model_dump() for s in body.samples]
    point_metrics = assess_calibration_point(
        {"samples_count": len(body.samples), "samples": sample_dicts}
    )
    valid = [
        s
        for s in body.samples
        if s.face_detected
        and s.left_iris_x is not None
        and s.left_iris_y is not None
        and s.right_iris_x is not None
        and s.right_iris_y is not None
    ]
    point = CalibrationPoint(
        session_id=session_id,
        point_index=body.point_index,
        target_screen_x=body.target_screen_x,
        target_screen_y=body.target_screen_y,
        samples=sample_dicts,
        samples_count=len(body.samples),
        face_detection_rate=point_metrics["face_detection_rate"],
        stability_score=point_metrics["stability_score"],
        valid=point_metrics["valid"],
        median_left_iris_x=median([s.left_iris_x for s in valid]) if valid else None,
        median_left_iris_y=median([s.left_iris_y for s in valid]) if valid else None,
        median_right_iris_x=median([s.right_iris_x for s in valid]) if valid else None,
        median_right_iris_y=median([s.right_iris_y for s in valid]) if valid else None,
    )
    db.add(point)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Calibration point {body.point_index} already exists for this session",
        ) from exc

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
async def complete_calibration(
    session_id: int,
    body: CompleteCalibrationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Complete calibration and compute quality metrics."""
    result = await db.execute(
        select(CalibrationSession)
        .options(selectinload(CalibrationSession.points))
        .where(CalibrationSession.id == session_id, CalibrationSession.status == "in_progress")
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Active calibration session not found")
    await get_active_response_or_404(session.response_id, body.participant_token, db)

    points = session.points
    if not points:
        raise HTTPException(
            status_code=409,
            detail="At least one calibration point is required before completion",
        )
    point_dicts = [{"samples_count": p.samples_count, "samples": p.samples} for p in points]
    metrics = compute_calibration_quality(point_dicts, session.expected_points)

    session.status = "completed"
    session.completed_at = datetime.utcnow()
    session.face_detection_rate = metrics["face_detection_rate"]
    session.stability_score = metrics["stability_score"]
    session.quality_score = metrics["quality_score"]
    session.passed = metrics["passed"]
    session.quality_reason = metrics["quality_reason"]
    session.quality = metrics["overall_quality"]
    await db.flush()
    await db.refresh(session)

    return CalibrationCompleteOut(
        session_id=session.id,
        status="completed",
        quality=QualityInfo(
            total_points=metrics["total_points"],
            expected_points=metrics["expected_points"],
            valid_points=metrics["valid_points"],
            missing_points=metrics["missing_points"],
            avg_samples_per_point=metrics["avg_samples_per_point"],
            face_detection_rate=metrics["face_detection_rate"],
            stability_score=metrics["stability_score"],
            quality_score=metrics["quality_score"],
            passed=metrics["passed"],
            overall_quality=metrics["overall_quality"],
            quality_reason=metrics["quality_reason"],
        ),
        completed_at=session.completed_at,
    )


# ── Gaze Tracking ─────────────────────────────────────


@router.post("/gaze", response_model=GazeBatchOut)
async def record_gaze_batch(body: GazeBatchRequest, db: AsyncSession = Depends(get_db)):
    """Record a batch of gaze data points. Frontend sends these every 5-10 seconds."""
    response = await get_active_response_or_404(
        body.response_id, body.participant_token, db
    )
    await validate_post_ids_for_response(
        response, {g.post_id for g in body.data if g.post_id is not None}, db
    )
    for g in body.data:
        db.add(
            GazeRecord(
                response_id=response.id,
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
    response = await get_active_response_or_404(
        body.response_id, body.participant_token, db
    )
    await validate_post_ids_for_response(
        response, {c.post_id for c in body.data if c.post_id is not None}, db
    )
    for c in body.data:
        db.add(
            ClickRecord(
                response_id=response.id,
                post_id=c.post_id,
                timestamp_ms=c.timestamp_ms,
                screen_x=c.screen_x,
                screen_y=c.screen_y,
                target_element=c.target_element,
            )
        )
    await db.flush()
    return ClickBatchOut(saved=len(body.data))
