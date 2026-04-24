"""Research data export service for CSV and JSON outputs."""

from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.participant import ParticipantInteraction, SurveyResponse
from app.models.question import Question
from app.models.question_response import QuestionResponse
from app.models.survey import Survey, SurveyPost
from app.models.tracking import CalibrationSession, ClickRecord, GazeRecord

POST_OVERRIDE_FIELDS = {
    "display_title",
    "display_image_url",
    "display_likes",
    "display_comments_count",
    "display_shares",
    "show_likes",
    "show_comments",
    "show_shares",
}

CSV_HEADERS = [
    "survey_id",
    "response_id",
    "participant_id",
    "assigned_group",
    "language",
    "response_status",
    "started_at",
    "completed_at",
    "calibration_status",
    "calibration_quality",
    "calibration_quality_score",
    "calibration_passed",
    "gaze_count",
    "click_count",
    "participant_interactions",
    "question_responses",
    "displayed_posts",
]


@dataclass(frozen=True)
class ExportFilters:
    assigned_group: int | None = None
    condition: int | None = None
    language: str | None = None
    response_status: str | None = None
    calibration_passed: bool | None = None

    @property
    def group_value(self) -> int | None:
        return self.assigned_group if self.assigned_group is not None else self.condition

    def as_dict(self) -> dict[str, Any]:
        return {
            "assigned_group": self.assigned_group,
            "condition": self.condition,
            "language": self.language,
            "response_status": self.response_status,
            "calibration_passed": self.calibration_passed,
        }


def isoformat(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def anonymous_participant_id(participant_token: str | None, response_id: int) -> str:
    token = participant_token or f"missing-token:{response_id}"
    digest = hashlib.sha256(f"{settings.SECRET_KEY}:{token}".encode()).hexdigest()
    return f"anon_{digest[:16]}"


def response_matches_filters(response: SurveyResponse, filters: ExportFilters) -> bool:
    group_value = filters.group_value
    if group_value is not None and response.assigned_group != group_value:
        return False
    if filters.language is not None and response.language != filters.language:
        return False
    if filters.response_status is not None and response.status != filters.response_status:
        return False
    if filters.calibration_passed is not None:
        calibration = response.calibration_session
        if calibration is None or calibration.passed is not filters.calibration_passed:
            return False
    return True


def displayed_post_for_group(post: SurveyPost, assigned_group: int) -> dict[str, Any]:
    values = {
        "post_id": post.id,
        "order": post.order,
        "original_url": post.original_url,
        "source": post.fetched_source,
        "display_title": post.display_title or post.fetched_title,
        "display_image_url": post.display_image_url or post.fetched_image_url,
        "display_likes": post.display_likes,
        "display_comments_count": post.display_comments_count,
        "display_shares": post.display_shares,
        "show_likes": post.show_likes,
        "show_comments": post.show_comments,
        "show_shares": post.show_shares,
        "visible_to_groups": post.visible_to_groups,
    }
    overrides = (post.group_overrides or {}).get(str(assigned_group), {})
    for field, value in overrides.items():
        if field in POST_OVERRIDE_FIELDS:
            values[field] = value
    return values


def visible_displayed_posts(survey: Survey, assigned_group: int) -> list[dict[str, Any]]:
    posts = []
    for post in survey.posts:
        if post.visible_to_groups is None or assigned_group in post.visible_to_groups:
            posts.append(displayed_post_for_group(post, assigned_group))
    return posts


def serialize_interaction(interaction: ParticipantInteraction) -> dict[str, Any]:
    return {
        "id": interaction.id,
        "post_id": interaction.post_id,
        "action_type": interaction.action_type,
        "comment_text": interaction.comment_text,
        "dwell_time_ms": interaction.dwell_time_ms,
        "click_x": interaction.click_x,
        "click_y": interaction.click_y,
        "timestamp": isoformat(interaction.timestamp),
    }


def serialize_question_response(
    answer: QuestionResponse, question: Question | None
) -> dict[str, Any]:
    return {
        "id": answer.id,
        "question_id": answer.question_id,
        "post_id": question.post_id if question else None,
        "question_type": question.question_type if question else None,
        "question_text": question.text if question else None,
        "answer_text": answer.answer_text,
        "answer_value": answer.answer_value,
        "answer_choices": answer.answer_choices,
        "created_at": isoformat(answer.created_at),
    }


def serialize_calibration(session: CalibrationSession | None) -> dict[str, Any]:
    if session is None:
        return {
            "status": None,
            "quality": None,
            "quality_score": None,
            "passed": None,
            "face_detection_rate": None,
            "stability_score": None,
            "quality_reason": None,
            "completed_at": None,
        }
    return {
        "status": session.status,
        "quality": session.quality,
        "quality_score": session.quality_score,
        "passed": session.passed,
        "face_detection_rate": session.face_detection_rate,
        "stability_score": session.stability_score,
        "quality_reason": session.quality_reason,
        "completed_at": isoformat(session.completed_at),
    }


def build_export_payload(
    survey: Survey,
    responses: list[SurveyResponse],
    *,
    filters: ExportFilters,
    gaze_counts: dict[int, int],
    click_counts: dict[int, int],
    question_responses_by_response: dict[int, list[dict[str, Any]]],
) -> dict[str, Any]:
    rows = []
    for response in responses:
        calibration = serialize_calibration(response.calibration_session)
        interactions = [
            serialize_interaction(interaction)
            for interaction in sorted(
                response.interactions,
                key=lambda interaction: interaction.timestamp or datetime.min,
            )
        ]
        rows.append(
            {
                "survey_id": survey.id,
                "response_id": response.id,
                "participant_id": anonymous_participant_id(
                    response.participant_token, response.id
                ),
                "assigned_group": response.assigned_group,
                "language": response.language,
                "response_status": response.status,
                "started_at": isoformat(response.started_at),
                "completed_at": isoformat(response.completed_at),
                "calibration": calibration,
                "gaze_count": gaze_counts.get(response.id, 0),
                "click_count": click_counts.get(response.id, 0),
                "participant_interactions": interactions,
                "question_responses": question_responses_by_response.get(response.id, []),
                "displayed_posts": visible_displayed_posts(survey, response.assigned_group),
            }
        )

    return {
        "survey_id": survey.id,
        "exported_at": datetime.utcnow().isoformat(),
        "filters": filters.as_dict(),
        "responses": rows,
    }


async def load_survey_export(
    db: AsyncSession,
    *,
    survey_id: int,
    researcher_id: int,
    filters: ExportFilters,
) -> dict[str, Any]:
    survey_result = await db.execute(
        select(Survey)
        .options(
            selectinload(Survey.posts).selectinload(SurveyPost.questions),
        )
        .where(Survey.id == survey_id, Survey.researcher_id == researcher_id)
    )
    survey = survey_result.scalar_one_or_none()
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")

    responses_result = await db.execute(
        select(SurveyResponse)
        .options(
            selectinload(SurveyResponse.interactions),
            selectinload(SurveyResponse.calibration_session),
        )
        .where(SurveyResponse.survey_id == survey_id)
        .order_by(SurveyResponse.started_at, SurveyResponse.id)
    )
    responses = [
        response
        for response in responses_result.scalars().all()
        if response_matches_filters(response, filters)
    ]
    response_ids = [response.id for response in responses]

    gaze_counts = await count_tracking_rows(db, GazeRecord, response_ids)
    click_counts = await count_tracking_rows(db, ClickRecord, response_ids)
    question_responses = await load_question_responses(db, response_ids)

    return build_export_payload(
        survey,
        responses,
        filters=filters,
        gaze_counts=gaze_counts,
        click_counts=click_counts,
        question_responses_by_response=question_responses,
    )


async def count_tracking_rows(
    db: AsyncSession, model: type[GazeRecord] | type[ClickRecord], response_ids: list[int]
) -> dict[int, int]:
    if not response_ids:
        return {}
    result = await db.execute(
        select(model.response_id, func.count(model.id))
        .where(model.response_id.in_(response_ids))
        .group_by(model.response_id)
    )
    return {response_id: count for response_id, count in result.all()}


async def load_question_responses(
    db: AsyncSession, response_ids: list[int]
) -> dict[int, list[dict[str, Any]]]:
    if not response_ids:
        return {}

    result = await db.execute(
        select(QuestionResponse, Question)
        .join(Question, QuestionResponse.question_id == Question.id, isouter=True)
        .where(QuestionResponse.response_id.in_(response_ids))
        .order_by(QuestionResponse.response_id, QuestionResponse.created_at)
    )
    by_response: dict[int, list[dict[str, Any]]] = {}
    for answer, question in result.all():
        by_response.setdefault(answer.response_id, []).append(
            serialize_question_response(answer, question)
        )
    return by_response


def export_payload_to_csv(payload: dict[str, Any]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_HEADERS)
    writer.writeheader()
    for response in payload["responses"]:
        calibration = response["calibration"]
        writer.writerow(
            {
                "survey_id": response["survey_id"],
                "response_id": response["response_id"],
                "participant_id": response["participant_id"],
                "assigned_group": response["assigned_group"],
                "language": response["language"],
                "response_status": response["response_status"],
                "started_at": response["started_at"],
                "completed_at": response["completed_at"],
                "calibration_status": calibration["status"],
                "calibration_quality": calibration["quality"],
                "calibration_quality_score": calibration["quality_score"],
                "calibration_passed": calibration["passed"],
                "gaze_count": response["gaze_count"],
                "click_count": response["click_count"],
                "participant_interactions": json.dumps(
                    response["participant_interactions"], ensure_ascii=False
                ),
                "question_responses": json.dumps(
                    response["question_responses"], ensure_ascii=False
                ),
                "displayed_posts": json.dumps(response["displayed_posts"], ensure_ascii=False),
            }
        )
    return output.getvalue()
