"""Seed a clean, repeatable client demo dataset.

Run from the backend container or from backend/ with the app environment loaded:

    python -m scripts.seed_client_demo

The script is idempotent for the fixed share codes below: existing demo surveys
are removed and recreated so the client-facing state stays tidy.
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime, timedelta

from sqlalchemy import delete, select

from app.auth import hash_password
from app.database import async_session
from app.models import (
    CalibrationPoint,
    CalibrationSession,
    ClickRecord,
    GazeRecord,
    ParticipantComment,
    ParticipantInteraction,
    ParticipantLike,
    PostComment,
    PostTranslation,
    Question,
    QuestionResponse,
    QuestionTranslation,
    Researcher,
    Survey,
    SurveyPost,
    SurveyResponse,
    SurveyTranslation,
)
from app.utils.attention import compute_attention_quality

DEMO_SHARE_CODE = "CS14DEMO2026"
GALLERY_SURVEYS = [
    ("CS14X2026", "twitter", "X Timeline"),
    ("CS14IG2026", "instagram", "Instagram Visual Feed"),
    ("CS14RED2026", "xiaohongshu", "Xiaohongshu Notes"),
    ("CS14TRUTH26", "truth_social", "Truth Social Feed"),
    ("CS14BSKY2026", "bluesky", "Bluesky Feed"),
    ("CS14DOUYIN26", "douyin", "Douyin / TikTok Vertical Feed"),
]

DEMO_POSTS = [
    {
        "url": "https://www.bbc.com/news/articles/cy4d8k7v2j1o",
        "source": "BBC News",
        "title": "Public trust in AI news summaries remains divided",
        "description": "Headline article on AI and news credibility, shown with controlled engagement cues for the study stimuli.",
        "image": "/demo-assets/ai-news.jpg",
        "likes": 1840,
        "comments": 126,
        "shares": 382,
        "comments_preview": [
            ("Maya", "The source label changes how much I trust this at first glance."),
            ("Daniel", "I would still open the article before sharing it."),
        ],
    },
    {
        "url": "https://www.nature.com/articles/d41586-024-00000-0",
        "source": "Nature",
        "title": "Researchers compare how platform design changes reading attention",
        "description": "Research-focused card comparing how interface design shapes reading attention, with stable engagement baselines.",
        "image": "/demo-assets/research-workspace.jpg",
        "likes": 912,
        "comments": 48,
        "shares": 119,
        "comments_preview": [
            ("Aisha", "This looks more credible when the comments are specific."),
            ("Leo", "The share count makes it feel more mainstream."),
        ],
    },
]


async def get_or_create_demo_researcher(session) -> Researcher:
    email = os.getenv("DEMO_RESEARCHER_EMAIL", "cs14.demo@example.com")
    result = await session.execute(select(Researcher).where(Researcher.email == email))
    researcher = result.scalar_one_or_none()
    if researcher:
        return researcher

    password = os.getenv("DEMO_RESEARCHER_PASSWORD", "change-me-client-demo")
    researcher = Researcher(
        email=email,
        name=os.getenv("DEMO_RESEARCHER_NAME", "CS14 Demo Researcher"),
        password_hash=hash_password(password),
    )
    session.add(researcher)
    await session.flush()
    return researcher


async def delete_existing_demo(session, share_code: str) -> None:
    result = await session.execute(select(Survey).where(Survey.share_code == share_code))
    survey = result.scalar_one_or_none()
    if not survey:
        return

    post_ids = list(
        (
            await session.execute(select(SurveyPost.id).where(SurveyPost.survey_id == survey.id))
        ).scalars()
    )
    response_ids = list(
        (
            await session.execute(
                select(SurveyResponse.id).where(SurveyResponse.survey_id == survey.id)
            )
        ).scalars()
    )
    question_ids = list(
        (
            await session.execute(select(Question.id).where(Question.survey_id == survey.id))
        ).scalars()
    )
    calibration_ids = []
    if response_ids:
        calibration_ids = list(
            (
                await session.execute(
                    select(CalibrationSession.id).where(
                        CalibrationSession.response_id.in_(response_ids)
                    )
                )
            ).scalars()
        )

    if question_ids:
        await session.execute(
            delete(QuestionResponse).where(QuestionResponse.question_id.in_(question_ids))
        )
        await session.execute(
            delete(QuestionTranslation).where(QuestionTranslation.question_id.in_(question_ids))
        )
    if response_ids:
        await session.execute(delete(GazeRecord).where(GazeRecord.response_id.in_(response_ids)))
        await session.execute(delete(ClickRecord).where(ClickRecord.response_id.in_(response_ids)))
        await session.execute(
            delete(ParticipantLike).where(ParticipantLike.response_id.in_(response_ids))
        )
        await session.execute(
            delete(ParticipantComment).where(ParticipantComment.response_id.in_(response_ids))
        )
        await session.execute(
            delete(ParticipantInteraction).where(
                ParticipantInteraction.response_id.in_(response_ids)
            )
        )
    if calibration_ids:
        await session.execute(
            delete(CalibrationPoint).where(CalibrationPoint.session_id.in_(calibration_ids))
        )
        await session.execute(
            delete(CalibrationSession).where(CalibrationSession.id.in_(calibration_ids))
        )
    if response_ids:
        await session.execute(delete(SurveyResponse).where(SurveyResponse.id.in_(response_ids)))
    if post_ids:
        await session.execute(delete(PostComment).where(PostComment.post_id.in_(post_ids)))
        await session.execute(delete(PostTranslation).where(PostTranslation.post_id.in_(post_ids)))
        await session.execute(delete(SurveyPost).where(SurveyPost.id.in_(post_ids)))
    if question_ids:
        await session.execute(delete(Question).where(Question.id.in_(question_ids)))
    await session.execute(delete(SurveyTranslation).where(SurveyTranslation.survey_id == survey.id))
    await session.execute(delete(Survey).where(Survey.id == survey.id))
    await session.flush()


async def create_survey_shell(
    session,
    *,
    researcher: Researcher,
    share_code: str,
    title: str,
    platform_ui_style: str,
    description: str,
    tracking_enabled: bool = True,
    calibration_enabled: bool = True,
) -> Survey:
    platform_style = (
        platform_ui_style if platform_ui_style in {"facebook", "instagram", "xiaohongshu"} else "x"
    )
    survey = Survey(
        researcher_id=researcher.id,
        title=title,
        description=description,
        status="published",
        share_code=share_code,
        platform_style=platform_style,
        platform_ui_style=platform_ui_style,
        default_language="en",
        supported_languages=["en", "zh", "ar"],
        num_groups=2,
        group_names={"1": "Control", "2": "High engagement cues"},
        gaze_tracking_enabled=tracking_enabled,
        gaze_interval_ms=1000,
        click_tracking_enabled=True,
        calibration_enabled=calibration_enabled,
        calibration_points=9,
        published_at=datetime.utcnow(),
    )
    session.add(survey)
    await session.flush()
    return survey


async def add_demo_content(session, survey: Survey, *, compact: bool = False) -> list[Question]:
    questions: list[Question] = []
    posts = DEMO_POSTS[:1] if compact else DEMO_POSTS
    for order, post_data in enumerate(posts, start=1):
        post = SurveyPost(
            survey_id=survey.id,
            order=order,
            original_url=post_data["url"],
            fetched_title=post_data["title"],
            fetched_image_url=post_data["image"],
            fetched_description=post_data["description"],
            fetched_source=post_data["source"],
            display_title=post_data["title"],
            display_image_url=post_data["image"],
            display_description=post_data["description"],
            source_label=post_data["source"],
            more_info_label="Open source article",
            display_likes=post_data["likes"],
            display_comments_count=post_data["comments"],
            display_shares=post_data["shares"],
            show_likes=True,
            show_comments=True,
            show_shares=True,
            visible_to_groups=None,
            group_overrides={
                "2": {
                    "display_likes": post_data["likes"] * 3,
                    "display_comments_count": post_data["comments"] * 2,
                    "display_shares": post_data["shares"] * 2,
                }
            },
        )
        session.add(post)
        await session.flush()

        for comment_order, (author, text) in enumerate(post_data["comments_preview"], start=1):
            session.add(
                PostComment(post_id=post.id, order=comment_order, author_name=author, text=text)
            )

        question = Question(
            survey_id=survey.id,
            post_id=post.id,
            order=1,
            question_type="likert",
            text="How credible does this post feel?",
            config={"min": 1, "max": 5, "min_label": "Not credible", "max_label": "Very credible"},
        )
        session.add(question)
        await session.flush()
        questions.append(question)

        session.add(
            PostTranslation(
                survey_id=survey.id,
                post_id=post.id,
                language_code="zh",
                translated_fields={
                    "display_title": "公众对 AI 新闻摘要的信任仍存在分歧"
                    if order == 1
                    else "研究人员比较平台设计如何改变阅读注意力",
                    "display_description": "关于人工智能与新闻可信度的头条内容，在受控互动线索下作为研究刺激呈现。",
                    "source_label": post_data["source"],
                    "more_info_label": "打开来源文章",
                },
            )
        )
        session.add(
            QuestionTranslation(
                survey_id=survey.id,
                question_id=question.id,
                language_code="zh",
                translated_fields={
                    "text": "你觉得这条帖子有多可信？",
                    "config": {"min_label": "不可信", "max_label": "非常可信"},
                },
            )
        )

    session.add(
        SurveyTranslation(
            survey_id=survey.id,
            language_code="zh",
            translated_fields={
                "title": "CS14 Client Demo - 社交媒体可信度研究",
                "description": "干净演示数据：平台样式、分组、校准、实时注意力质量和导出流程。",
            },
        )
    )
    return questions


async def seed_responses(session, survey: Survey, questions: list[Question]) -> None:
    now = datetime.utcnow()
    for index in range(12):
        group = 1 if index % 2 == 0 else 2
        language = "zh" if index in {2, 7} else "en"
        expected = 42 + index
        detected = expected - (index % 4) * 3
        missing_ms = (expected - detected) * 1000
        calibration_quality = "good" if index < 7 else "acceptable" if index < 10 else "poor"
        calibration_passed = calibration_quality != "poor"
        metrics = compute_attention_quality(
            active_ms=expected * 1000,
            expected_samples=expected,
            detected_samples=detected,
            missing_ms=missing_ms,
            no_face_periods=index % 3,
            calibration_passed=calibration_passed,
            calibration_quality=calibration_quality,
        )
        started_at = now - timedelta(minutes=20 + index)
        completed_at = started_at + timedelta(minutes=3 + (index % 4))
        response = SurveyResponse(
            survey_id=survey.id,
            assigned_group=group,
            randomization_seed=f"demo-seed-{index + 1}",
            shown_post_order=[],
            user_agent="CS14 demo seed",
            screen_width=1440,
            screen_height=900,
            language=language,
            participant_fingerprint=f"demo-fingerprint-{index + 1}",
            status="completed" if index != 11 else "flagged",
            is_preview=False,
            is_speed_test_failed=index == 11,
            started_at=started_at,
            completed_at=completed_at,
            attention_active_ms=metrics["active_ms"],
            attention_expected_samples=metrics["expected_samples"],
            attention_detected_samples=metrics["detected_samples"],
            attention_missing_ms=metrics["missing_ms"],
            attention_no_face_periods=metrics["no_face_periods"],
            attention_coverage=metrics["coverage"],
            attention_confidence=metrics["confidence"],
            attention_quality=metrics["quality"],
            attention_quality_reason=metrics["quality_reason"],
            extra_metadata={"seeded_demo": True},
        )
        session.add(response)
        await session.flush()

        session.add(
            CalibrationSession(
                response_id=response.id,
                status="completed",
                screen_width=1440,
                screen_height=900,
                camera_width=640,
                camera_height=480,
                expected_points=9,
                face_detection_rate=metrics["coverage"],
                quality_score=0.92
                if calibration_quality == "good"
                else 0.72
                if calibration_quality == "acceptable"
                else 0.44,
                passed=calibration_passed,
                stability_score=0.88 if calibration_quality == "good" else 0.64,
                quality_reason=metrics["quality_reason"],
                model_type="MediaPipe Face Mesh",
                validation_error_px=28.0 + index,
                quality=calibration_quality,
                started_at=started_at,
                completed_at=started_at + timedelta(seconds=45),
            )
        )

        for q_index, question in enumerate(questions):
            value = 3 + ((index + q_index) % 3)
            session.add(
                QuestionResponse(
                    response_id=response.id,
                    question_id=question.id,
                    answer_text=str(value),
                    answer_value=value,
                    answer_choices=None,
                )
            )

        first_post_id = survey.posts[0].id if survey.posts else None
        if first_post_id is not None:
            session.add(ParticipantLike(response_id=response.id, post_id=first_post_id))
            session.add(
                ParticipantInteraction(
                    response_id=response.id,
                    post_id=first_post_id,
                    action_type="like",
                )
            )
            if index % 3 == 0:
                session.add(
                    ParticipantInteraction(
                        response_id=response.id,
                        post_id=first_post_id,
                        action_type="comment",
                        comment_text="This source looks more trustworthy with context.",
                    )
                )
            for sample_index in range(4):
                session.add(
                    GazeRecord(
                        response_id=response.id,
                        post_id=first_post_id,
                        timestamp_ms=int((started_at.timestamp() * 1000) + sample_index * 1000),
                        screen_x=520.0 + sample_index * 18 + index,
                        screen_y=280.0 + sample_index * 24,
                        left_iris_x=0.42 + sample_index * 0.01,
                        left_iris_y=0.50,
                        right_iris_x=0.56 + sample_index * 0.01,
                        right_iris_y=0.51,
                    )
                )
                session.add(
                    ClickRecord(
                        response_id=response.id,
                        post_id=first_post_id,
                        timestamp_ms=int((started_at.timestamp() * 1000) + sample_index * 1500),
                        screen_x=480.0 + sample_index * 30,
                        screen_y=610.0,
                        target_element="headline" if sample_index % 2 == 0 else "more_info",
                    )
                )


async def seed() -> None:
    async with async_session() as session:
        researcher = await get_or_create_demo_researcher(session)
        for share_code in [DEMO_SHARE_CODE, *[item[0] for item in GALLERY_SURVEYS]]:
            await delete_existing_demo(session, share_code)

        survey = await create_survey_shell(
            session,
            researcher=researcher,
            share_code=DEMO_SHARE_CODE,
            title="CS14 Client Demo - Social Media Credibility Study",
            platform_ui_style="twitter",
            description="Clean client demo with social post cards, groups, multilingual content, calibration, attention confidence, analytics, and export data.",
        )
        questions = await add_demo_content(session, survey)
        await session.flush()
        await session.refresh(survey, attribute_names=["posts"])
        await seed_responses(session, survey, questions)

        for share_code, platform_ui_style, name in GALLERY_SURVEYS:
            gallery = await create_survey_shell(
                session,
                researcher=researcher,
                share_code=share_code,
                title=f"CS14 Platform Preview - {name}",
                platform_ui_style=platform_ui_style,
                description=f"Visual preview survey for the {name} participant feed style.",
                tracking_enabled=False,
                calibration_enabled=False,
            )
            await add_demo_content(session, gallery, compact=True)

        await session.commit()

    print(f"Seeded client demo survey: /survey/{DEMO_SHARE_CODE}?lang=en")
    print("Seeded platform gallery share codes:")
    for share_code, _, name in GALLERY_SURVEYS:
        print(f"  {share_code}: {name}")


if __name__ == "__main__":
    asyncio.run(seed())
