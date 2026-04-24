"""Survey and post schemas. Owned by Backend A/B."""

from datetime import datetime

from pydantic import BaseModel, Field

# ── Survey ────────────────────────────────────────────


class CreateSurveyRequest(BaseModel):
    title: str
    description: str | None = None
    num_groups: int = 1
    group_names: dict | None = None  # {"1": "with_likes", "2": "no_likes"}
    gaze_tracking_enabled: bool = True
    gaze_interval_ms: int = 1000
    click_tracking_enabled: bool = True
    calibration_enabled: bool = True
    calibration_points: int = 9


class UpdateSurveyRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    num_groups: int | None = None
    group_names: dict | None = None
    gaze_tracking_enabled: bool | None = None
    gaze_interval_ms: int | None = None
    click_tracking_enabled: bool | None = None
    calibration_enabled: bool | None = None
    calibration_points: int | None = None


class SurveyOut(BaseModel):
    id: int
    title: str
    description: str | None
    status: str
    share_code: str
    num_groups: int
    group_names: dict | None
    gaze_tracking_enabled: bool
    gaze_interval_ms: int
    click_tracking_enabled: bool
    calibration_enabled: bool
    calibration_points: int
    share_code_expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class SurveyListOut(BaseModel):
    items: list[SurveyOut]
    total: int


# ── Public (participant pre-start) ───────────────────


class PublicSurveyOut(BaseModel):
    title: str
    description: str | None = None
    status: str
    language: str | None = None
    fallback_language: str = "en"
    translation_fallbacks: list[str] = Field(default_factory=list)
    model_config = {"from_attributes": True}


# ── Question ─────────────────────────────────────────


class CreateQuestionRequest(BaseModel):
    """Create a question attached to a survey post."""

    question_type: str  # free_text / likert / multiple_choice
    text: str
    order: int
    config: dict | None = None  # e.g. {"min": 1, "max": 5} for likert


class UpdateQuestionRequest(BaseModel):
    question_type: str | None = None
    text: str | None = None
    order: int | None = None
    config: dict | None = None


class QuestionOut(BaseModel):
    id: int
    post_id: int
    order: int
    question_type: str
    text: str
    config: dict | None
    created_at: datetime
    language: str | None = None
    fallback_language: str = "en"
    translation_fallbacks: list[str] = Field(default_factory=list)
    model_config = {"from_attributes": True}


# ── Post Comment (fake, added by researcher) ─────────


class CommentIn(BaseModel):
    author_name: str
    author_avatar_url: str | None = None
    text: str


class CommentOut(BaseModel):
    id: int
    order: int
    author_name: str
    author_avatar_url: str | None
    text: str
    language: str | None = None
    fallback_language: str = "en"
    translation_fallbacks: list[str] = Field(default_factory=list)
    model_config = {"from_attributes": True}


# ── Survey Post ───────────────────────────────────────


class CreatePostRequest(BaseModel):
    """Researcher provides a URL. Backend fetches OG metadata automatically."""

    original_url: str
    order: int


class UpdatePostRequest(BaseModel):
    """Researcher overrides fetched metadata and sets fake engagement numbers."""

    display_title: str | None = None
    display_image_url: str | None = None
    display_likes: int | None = None
    display_comments_count: int | None = None
    display_shares: int | None = None
    show_likes: bool | None = None
    show_comments: bool | None = None
    show_shares: bool | None = None
    visible_to_groups: list[int] | None = None
    group_overrides: dict | None = None
    order: int | None = None


class PostOut(BaseModel):
    id: int
    survey_id: int
    order: int
    original_url: str
    fetched_title: str | None
    fetched_image_url: str | None
    fetched_description: str | None
    fetched_source: str | None
    display_title: str | None
    display_image_url: str | None
    display_likes: int
    display_comments_count: int
    display_shares: int
    show_likes: bool
    show_comments: bool
    show_shares: bool
    visible_to_groups: list | None
    group_overrides: dict | None
    more_info_label: str = "More Information"
    language: str | None = None
    fallback_language: str = "en"
    translation_fallbacks: list[str] = Field(default_factory=list)
    comments: list[CommentOut] = Field(default_factory=list)
    questions: list[QuestionOut] = Field(default_factory=list)
    created_at: datetime
    model_config = {"from_attributes": True}


# ── Participant-Side ──────────────────────────────────


class StartSurveyRequest(BaseModel):
    language: str | None = None
    screen_width: int | None = None
    screen_height: int | None = None
    user_agent: str | None = None


class StartSurveyResponse(BaseModel):
    response_id: int
    participant_token: str
    survey_id: int
    assigned_group: int
    calibration_required: bool
    calibration_points: int
    gaze_tracking_enabled: bool
    gaze_interval_ms: int
    click_tracking_enabled: bool
    language: str | None = None
    fallback_language: str = "en"
    posts: list[PostOut]


class InteractionRequest(BaseModel):
    post_id: int
    action_type: str  # like / comment / click
    comment_text: str | None = None


class InteractionOut(BaseModel):
    id: int
    post_id: int
    action_type: str
    comment_text: str | None
    timestamp: datetime
    model_config = {"from_attributes": True}


# ── Participant state & comments ─────────────────────


class ParticipantCommentOut(BaseModel):
    id: int
    post_id: int
    text: str
    created_at: datetime
    updated_at: datetime | None = None
    model_config = {"from_attributes": True}


class ResponseStateOut(BaseModel):
    liked_post_ids: list[int]
    comments_by_post: dict[int, list[ParticipantCommentOut]]


# ── Researcher analytics ─────────────────────────────


class PostEngagementStat(BaseModel):
    post_id: int
    likes: int
    participant_comments: int
    shares: int


class SurveyEngagementStats(BaseModel):
    survey_id: int
    posts: list[PostEngagementStat]


class SurveyParticipantCommentsOut(BaseModel):
    comments_by_post: dict[int, list[ParticipantCommentOut]]


class GroupAnalyticsOut(BaseModel):
    group_id: int
    participants: int
    completed: int
    completion_rate: float
    clicks: int
    likes: int
    comments: int
    shares: int


class PostAnalyticsRowOut(BaseModel):
    post_id: int
    title: str
    source: str | None = None
    visible_groups: list[int] | None = None
    clicks: int
    likes: int
    comments: int
    shares: int
    participant_comment_count: int


class SurveyAnalyticsOut(BaseModel):
    survey_id: int
    total_responses: int
    completion_rate: float
    avg_completion_minutes: float
    calibration_success_rate: float
    total_clicks: int
    total_likes: int
    total_comments: int
    total_shares: int
    fast_completions: int
    low_interaction_responses: int
    duplicate_comment_sessions: int
    group_breakdown: list[GroupAnalyticsOut]
    posts: list[PostAnalyticsRowOut]
    summary: str


# ── Question Response ─────────────────────────────────


class SubmitQuestionResponseRequest(BaseModel):
    question_id: int
    answer_text: str | None = None
    answer_value: int | None = None
    answer_choices: list | None = None


class QuestionResponseOut(BaseModel):
    id: int
    response_id: int
    question_id: int
    answer_text: str | None
    answer_value: int | None
    answer_choices: list | None
    created_at: datetime
    model_config = {"from_attributes": True}
