"""Seed a clean, repeatable client demo dataset.

Run from the backend container or from backend/ with the app environment loaded:

    python -m scripts.seed_client_demo

The script is idempotent for the fixed share codes below: existing demo surveys
are removed and recreated so the client-facing state stays tidy.
"""

from __future__ import annotations

import asyncio
import copy
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

MAIN_SURVEY_POST_CAP = 6
GALLERY_POST_CAP = 4

_IMG_NEWS = "/demo-assets/ai-news.jpg"
_IMG_LAB = "/demo-assets/research-workspace.jpg"

# Stable demo URLs and embedded metadata avoid relying on Open Graph fetching during demos.
DEMO_POST_DEFINITIONS = [
    {
        "url": "https://www.bbc.com/news/articles/cs14-demo-ai-trust-brief",
        "source": "BBC News",
        "title": "Public trust in AI news summaries remains divided",
        "description": (
            "Participants assess how labelled sources and muted engagement cues influence "
            "first-pass credibility judgments on news-style cards."
        ),
        "image": _IMG_NEWS,
        "likes": 1840,
        "comments": 126,
        "shares": 382,
        "comments_preview": [
            ("Maya", "Seeing the masthead upfront changes how sceptical I am."),
            ("Daniel", "I still want the byline before I treat it as factual."),
            ("Chen", "The comment tone here feels more argumentative than supportive."),
        ],
        "zh": {
            "display_title": "公众对 AI 新闻摘要的信任仍存在分歧",
            "display_description": (
                "研究参与者评估来源标签与被弱化的互动数字，会如何影响第一印象中的可信度。"
            ),
            "question_text": "你觉得这条信息流卡片有多可信？",
        },
    },
    {
        "url": "https://www.nature.com/articles/cs14-demo-attention-reading",
        "source": "Nature",
        "title": "Readers skim differently when feeds emphasize reactions",
        "description": (
            "A methods-oriented write-up illustrating how denser reaction metrics can shorten "
            "dwell time on the headline tile even when body text availability is unchanged."
        ),
        "image": _IMG_LAB,
        "likes": 912,
        "comments": 48,
        "shares": 119,
        "comments_preview": [
            ("Leo", "Feels scholarly—comments are narrower and more precise."),
            ("Aisha", "The share badge makes it echo wider distribution."),
        ],
        "zh": {
            "display_title": "当信息流强调反应按钮时读者浏览方式发生改变",
            "display_description": (
                "方法向示例：即使在正文可达性不变时，反应数字更醒目也可能缩短停留在标题卡片上的时间。"
            ),
            "question_text": "这条内容看起来有多可靠？",
        },
    },
    {
        "url": "https://openai-news.example/cs14/demo/model-behaviour-bulletin",
        "source": "OpenAI Blog (demo layout)",
        "title": "Designing calmer model release notes readers can skim",
        "description": (
            "Plain-language changelog framing for responsibly summarising behavioural updates. "
            "Card copy is illustrative for platform-style previews and not a live product claim."
        ),
        "image": _IMG_NEWS,
        "likes": 2604,
        "comments": 198,
        "shares": 540,
        "comments_preview": [
            ("Taylor", "Reads like engineering notes—not a flashy promo."),
            ("Jordan", "I like that it separates facts from rollout guidance."),
            ("Priya", "Would still verify against the longer release note."),
        ],
        "zh": {
            "display_title": "更克制的模型发布说明：便于扫读的板式示例",
            "display_description": (
                "以平实文风呈现行为更新摘要的流程示例，仅用于平台样式预览，不构成真实产品陈述。"
            ),
            "question_text": "你会觉得这条发布摘要可信吗？",
        },
    },
    {
        "url": "https://hci.stanford.edu/cs14/demo/reading-metacognition-field-note",
        "source": "Stanford HCI Lab (demo vignette)",
        "title": "Field note: pacing yourself when timelines feel infinite",
        "description": (
            "Short lab blog vignette discussing metacognitive pauses—a neutral science voice "
            "contrasted with hotter news-cycle posts in the deck."
        ),
        "image": _IMG_LAB,
        "likes": 742,
        "comments": 33,
        "shares": 88,
        "comments_preview": [
            ("Robin", "Feels grounded—almost like a syllabus reminder."),
            ("Sam", "The voice is reassuring without promising certainty."),
        ],
        "zh": {
            "display_title": "田野笔记：当时间线看上去很“无限”时如何调节阅读节奏",
            "display_description": (
                "实验室博客式短文，讨论自省式停顿——在演示中与更劲爆的新闻信息流形成对照。"
            ),
            "question_text": "这条科研风格笔记在你的直觉里有多可信？",
        },
    },
    {
        "url": "https://technology-desk.example/cs14/demo/quantum-chip-primer",
        "source": "Tech Policy Desk",
        "title": "Why neutral explainers rank sources before showing metrics",
        "description": (
            "Wire-style briefing that opens with sourcing context and only afterwards surfaces "
            "like counts—a deliberately measured cadence for the study stimuli."
        ),
        "image": _IMG_NEWS,
        "likes": 438,
        "comments": 67,
        "shares": 104,
        "comments_preview": [
            ("Jamie", "Feels Reuters-adjacent: headline, then qualifiers."),
            ("Morgan", "Engagement badges feel secondary here in a helpful way."),
        ],
        "zh": {
            "display_title": "为何中性科普卡片会先列出信息来源再给互动指标",
            "display_description": (
                "简讯写法：先用来源语境打底，稍后呈现点赞等数字——在研究刺激中有意放慢节奏。"
            ),
            "question_text": "你会觉得这条简报式卡片真实吗？",
        },
    },
    {
        "url": "https://campus-wire.example/cs14/demo/undergraduate-research-panel",
        "source": "Midwest Campus News",
        "title": "Undergrad labs host live Q&A on source triage workflows",
        "description": (
            "Campus bulletin describing an interactive panel on verifying unfamiliar handles. "
            "Demonstrates collegiate tone with modest engagement relative to trending posts."
        ),
        "image": _IMG_LAB,
        "likes": 628,
        "comments": 55,
        "shares": 74,
        "comments_preview": [
            ("Ash", "Sounds like something my RA would send around."),
            ("Riley", "Comments stay practical—sharing checklists."),
        ],
        "zh": {
            "display_title": "本科生实验室在线答疑：不熟悉账号时如何核验来源",
            "display_description": (
                "校园通讯式文案，介绍核验陌生账号的流程——语气偏学院派，热度数字相对克制。"
            ),
            "question_text": "在校园通讯语境下你觉得它有多可信？",
        },
    },
]


CALIBRATION_GRID = (
    (160, 96),
    (720, 96),
    (1280, 96),
    (160, 450),
    (720, 450),
    (1280, 450),
    (160, 804),
    (720, 804),
    (1280, 804),
)


def personalize_posts_for_platform(
    definitions: list[dict], platform_ui_style: str
) -> list[dict]:
    """Tune copy hints so layouts read like their platform metaphor without spoofing branding."""

    tweaked: list[dict] = []
    for raw in definitions:
        post = copy.deepcopy(raw)
        title = post["title"]
        description = post["description"]
        if platform_ui_style == "xiaohongshu":
            post["title"] = f"摘录笔记｜{title}"
            post["description"] = (
                f"{description} · #扫读备忘 #信息可信度练习（示意文案，非官方内容）"
            )
        elif platform_ui_style == "douyin":
            post["description"] = f"⚡ 速览划重点：{description}"
            post["likes"] = int(post["likes"] * 1.35)
            post["comments_preview"] = list(post["comments_preview"]) + [
                ("路人甲", "前15秒我就把来源看了一遍👀"),
            ]
        elif platform_ui_style == "instagram":
            post["description"] = f"{description}\n• saved • review later • study stimuli"
        elif platform_ui_style == "truth_social":
            post["title"] = f"Thread starter: {title}"
            post["comments_preview"] = list(post["comments_preview"]) + [
                ("Pat", "Repost—worth reading the qualifiers."),
            ]
        elif platform_ui_style == "bluesky":
            post["description"] = f"{description}\n(alt-text implied: skyline photo placeholder)"
            post["comments_preview"] = list(post["comments_preview"]) + [
                ("SkyUser", "+1 quieter layout for long reads."),
            ]
        elif platform_ui_style == "twitter":
            post["comments_preview"] = list(post["comments_preview"]) + [
                ("Nova", "Quote-tweeting for class—need to revisit later."),
            ]

        zh = post.get("zh")
        if zh:
            if platform_ui_style == "xiaohongshu":
                zh["display_title"] = f"摘录笔记｜{zh['display_title']}"
                zh["display_description"] = (
                    f"{zh['display_description']} · #扫读草稿 #可信度小练习（示例，非官方）"
                )
            elif platform_ui_style == "douyin":
                zh["display_description"] = f"速览划重点：{zh['display_description']}"
            elif platform_ui_style == "instagram":
                zh["display_description"] = f"{zh['display_description']}\n• 之后再看 • 研究刺激用语"
            elif platform_ui_style == "truth_social":
                zh["display_title"] = f"议题帖：{zh['display_title']}"
            elif platform_ui_style == "bluesky":
                zh["display_description"] = (
                    f"{zh['display_description']}\n（示例：隐含 alt-text / 低密度时间线可读性）"
                )

        tweaked.append(post)
    return tweaked


def demo_calibration_samples(
    *,
    face_ratio: float,
    unstable: bool = False,
    count: int = 14,
) -> list[dict]:
    detected = max(1, int(count * face_ratio))
    samples: list[dict] = []
    for idx in range(count):
        yaw = (-18 if unstable and idx % 2 == 0 else 14) if unstable else 2.5
        pitch = (16 if unstable and idx % 2 == 0 else -14) if unstable else -3.5
        samples.append(
            {
                "timestamp_ms": idx * 90,
                "left_iris_x": 0.44 + idx * 0.001,
                "left_iris_y": 0.51 + (0.015 if unstable else 0),
                "right_iris_x": 0.57 - idx * 0.001,
                "right_iris_y": 0.495,
                "face_detected": idx < detected,
                "head_rotation": {"yaw": yaw, "pitch": pitch},
            }
        )
    return samples


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


async def add_demo_content(
    session,
    survey: Survey,
    post_entries: list[dict],
) -> list[Question]:
    questions: list[Question] = []

    def _sanitize_comment_rows(seq):
        cleaned = []
        for author, body in seq:
            text = body if isinstance(body, str) else str(body)
            lines = [part.strip() for part in text.splitlines() if part.strip()]
            compact = lines[0] if lines else "(empty)"
            if len(compact) > 560:
                compact = f"{compact[:557]}..."
            cleaned.append((author, compact))
        return cleaned

    for order, post_data in enumerate(post_entries, start=1):
        comments_preview = _sanitize_comment_rows(post_data["comments_preview"])
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
                    "display_likes": int(post_data["likes"] * 2.75),
                    "display_comments_count": int(post_data["comments"] * 2.1),
                    "display_shares": int(post_data["shares"] * 2.2),
                }
            },
        )
        session.add(post)
        await session.flush()

        for comment_order, (author, text) in enumerate(comments_preview, start=1):
            session.add(PostComment(post_id=post.id, order=comment_order, author_name=author, text=text))

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

        zh = post_data["zh"]
        session.add(
            PostTranslation(
                survey_id=survey.id,
                post_id=post.id,
                language_code="zh",
                translated_fields={
                    "display_title": zh["display_title"],
                    "display_description": zh["display_description"],
                    "source_label": post_data["source"],
                    "more_info_label": "打开来源说明",
                },
            )
        )
        session.add(
            QuestionTranslation(
                survey_id=survey.id,
                question_id=question.id,
                language_code="zh",
                translated_fields={
                    "text": zh["question_text"],
                    "config": {"min_label": "不太可信", "max_label": "非常可信"},
                },
            )
        )

    session.add(
        SurveyTranslation(
            survey_id=survey.id,
            language_code="zh",
            translated_fields={
                "title": "CS14 Client Demo - 社交媒体可信度研究",
                "description": (
                    "干净演示数据：多平台信息流样式、分组、校准、追踪证据、注意力置信度与导出流程。"
                ),
            },
        )
    )
    return questions


async def seed_responses(session, survey: Survey, questions: list[Question]) -> None:
    posts_sorted = sorted(survey.posts or [], key=lambda p: p.order)
    post_ids = [p.id for p in posts_sorted]
    now = datetime.utcnow()

    for index in range(12):
        group = 1 if index % 2 == 0 else 2
        language = "zh" if index in {2, 7} else "en"
        expected = 48 + index * 3
        detected = expected - (index % 5) * 4
        missing_ms = max(0, (expected - detected) * 950)
        calibration_quality = "good" if index < 7 else "acceptable" if index < 10 else "poor"
        calibration_passed = calibration_quality != "poor"
        face_ratio = 0.98 if calibration_quality == "good" else 0.86 if calibration_quality == "acceptable" else 0.52
        metrics = compute_attention_quality(
            active_ms=expected * 1000,
            expected_samples=expected,
            detected_samples=max(1, detected),
            missing_ms=missing_ms,
            no_face_periods=index % 3,
            calibration_passed=calibration_passed,
            calibration_quality=calibration_quality,
        )
        started_at = now - timedelta(minutes=46 + index * 6)
        completed_at = started_at + timedelta(minutes=4 + (index % 5))

        response = SurveyResponse(
            survey_id=survey.id,
            assigned_group=group,
            randomization_seed=f"demo-seed-{index + 1}",
            shown_post_order=post_ids.copy(),
            user_agent=f"Mozilla/5.0 CS14-DemoParticipant/{index + 1}",
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
            extra_metadata={"seeded_demo": True, "demo_wave": index // 4},
        )
        session.add(response)
        await session.flush()

        cal_session = CalibrationSession(
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
            else 0.41,
            passed=calibration_passed,
            stability_score=0.88 if calibration_quality == "good" else 0.63,
            quality_reason=(metrics["quality_reason"] or "demo calibration")[:255],
            model_type="MediaPipe Face Mesh",
            validation_error_px=22.0 + index,
            quality=calibration_quality,
            started_at=started_at,
            completed_at=started_at + timedelta(seconds=52),
        )
        session.add(cal_session)
        await session.flush()

        unstable_pts = calibration_quality == "poor"
        for point_index, (tx, ty) in enumerate(CALIBRATION_GRID, start=1):
            samples = demo_calibration_samples(
                face_ratio=face_ratio, unstable=unstable_pts, count=13 + point_index % 4
            )
            session.add(
                CalibrationPoint(
                    session_id=cal_session.id,
                    point_index=point_index,
                    target_screen_x=tx,
                    target_screen_y=ty,
                    samples=samples,
                    samples_count=len(samples),
                    face_detection_rate=face_ratio,
                    stability_score=0.83 if calibration_quality == "good" else 0.58,
                    valid=calibration_passed or point_index < 7,
                    median_left_iris_x=0.45,
                    median_left_iris_y=0.51,
                    median_right_iris_x=0.56,
                    median_right_iris_y=0.49,
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

        if not posts_sorted:
            continue

        primary_post = posts_sorted[index % len(posts_sorted)]
        secondary_post = posts_sorted[(index + 1) % len(posts_sorted)]
        tertiary_post = posts_sorted[(index + 2) % len(posts_sorted)]

        # Likes persist final state across two posts so analytics show richer distributions.
        session.add(ParticipantLike(response_id=response.id, post_id=primary_post.id))
        session.add(ParticipantLike(response_id=response.id, post_id=secondary_post.id))
        ts_base = started_at.timestamp()

        session.add(
            ParticipantInteraction(
                response_id=response.id,
                post_id=primary_post.id,
                action_type="like",
                dwell_time_ms=4200 + index * 110,
                click_x=None,
                click_y=None,
                timestamp=started_at + timedelta(seconds=120),
            )
        )
        session.add(
            ParticipantInteraction(
                response_id=response.id,
                post_id=secondary_post.id,
                action_type="comment",
                comment_text=(
                    "Noting headline vs body mismatch—checking the labelled outlet before resharing."
                ),
                dwell_time_ms=6100 + index * 130,
                click_x=None,
                click_y=None,
                timestamp=started_at + timedelta(seconds=210),
            )
        )
        session.add(
            ParticipantInteraction(
                response_id=response.id,
                post_id=tertiary_post.id,
                action_type="share",
                dwell_time_ms=2800,
                click_x=None,
                click_y=None,
                timestamp=started_at + timedelta(seconds=320),
            )
        )
        if index % 4 == 0:
            session.add(
                ParticipantInteraction(
                    response_id=response.id,
                    post_id=primary_post.id,
                    action_type="click",
                    dwell_time_ms=900,
                    click_x=512.0,
                    click_y=318.0,
                    timestamp=started_at + timedelta(seconds=400),
                )
            )

        session.add(
            ParticipantComment(
                response_id=response.id,
                post_id=secondary_post.id,
                author_name="Participant",
                text="Short jot: source feels legit but engagement feels pushed in variation B.",
            )
        )

        for target_post, offset_multiplier in zip(
            (primary_post, secondary_post, tertiary_post), (0, 1, 2)
        ):
            for sample_index in range(4):
                session.add(
                    GazeRecord(
                        response_id=response.id,
                        post_id=target_post.id,
                        timestamp_ms=int(
                            (ts_base * 1000) + offset_multiplier * 8000 + sample_index * 1100 + index * 17
                        ),
                        screen_x=520.0 + sample_index * 24 + offset_multiplier * 12 + index,
                        screen_y=260.0 + sample_index * 22 + offset_multiplier * 30,
                        left_iris_x=0.42 + sample_index * 0.01,
                        left_iris_y=0.50 + offset_multiplier * 0.008,
                        right_iris_x=0.56 + sample_index * 0.009,
                        right_iris_y=0.51,
                    )
                )
                session.add(
                    ClickRecord(
                        response_id=response.id,
                        post_id=target_post.id,
                        timestamp_ms=int((ts_base * 1000) + offset_multiplier * 5000 + sample_index * 1400),
                        screen_x=480.0 + sample_index * 32 + offset_multiplier * 10,
                        screen_y=600.0 + offset_multiplier * 18,
                        target_element="headline" if sample_index % 2 == 0 else "more_info",
                    )
                )


async def seed() -> None:
    main_posts = DEMO_POST_DEFINITIONS[:MAIN_SURVEY_POST_CAP]

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
            description=(
                "Client demo bundle with six grounded post cards, A/B cues, multilingual copy, "
                "calibrated tracking evidence, richer analytics aggregates, and export-ready rows."
            ),
        )
        questions = await add_demo_content(session, survey, main_posts)
        await session.flush()
        await session.refresh(survey, attribute_names=["posts"])
        await seed_responses(session, survey, questions)

        for share_code, platform_ui_style, name in GALLERY_SURVEYS:
            gallery_posts = personalize_posts_for_platform(
                DEMO_POST_DEFINITIONS[:GALLERY_POST_CAP], platform_ui_style
            )
            gallery = await create_survey_shell(
                session,
                researcher=researcher,
                share_code=share_code,
                title=f"CS14 Platform Preview - {name}",
                platform_ui_style=platform_ui_style,
                description=f"Visual preview deck for {name}: four representative cards seeded offline.",
                tracking_enabled=False,
                calibration_enabled=False,
            )
            await add_demo_content(session, gallery, gallery_posts)

        await session.commit()

    print(f"Seeded client demo survey: /survey/{DEMO_SHARE_CODE}?lang=en")
    print("Seeded platform gallery share codes (4 posts each):")
    for share_code, _, name in GALLERY_SURVEYS:
        print(f"  {share_code}: {name}")


if __name__ == "__main__":
    asyncio.run(seed())
