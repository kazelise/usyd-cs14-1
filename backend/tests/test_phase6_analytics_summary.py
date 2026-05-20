"""Analytics summary contract tests."""

from app.models.participant import SurveyResponse
from app.models.tracking import CalibrationSession
from app.routers.surveys import analytics_response_scope
from app.schemas.survey import GroupAnalyticsOut, PostAnalyticsRowOut, SurveyAnalyticsOut


def test_analytics_summary_exposes_tracking_evidence_totals():
    summary = SurveyAnalyticsOut(
        survey_id=7,
        total_responses=2,
        completion_rate=50.0,
        avg_completion_minutes=4.5,
        calibration_success_rate=100.0,
        total_gaze_samples=24,
        total_clicks=6,
        total_likes=3,
        total_comments=1,
        total_shares=1,
        fast_completions=0,
        low_interaction_responses=0,
        duplicate_comment_sessions=0,
        group_breakdown=[
            GroupAnalyticsOut(
                group_id=1,
                participants=2,
                completed=1,
                completion_rate=50.0,
                clicks=6,
                likes=3,
                comments=1,
                shares=1,
            )
        ],
        posts=[
            PostAnalyticsRowOut(
                post_id=11,
                title="Treatment post",
                source="example.com",
                visible_groups=[1],
                clicks=6,
                likes=3,
                comments=2,
                shares=1,
                participant_comment_count=1,
            )
        ],
        summary="Tracking evidence is ready for export.",
    )

    assert summary.model_dump()["total_gaze_samples"] == 24
    assert summary.posts[0].comments != summary.posts[0].participant_comment_count


def test_analytics_response_scope_default_excludes_preview_only():
    conditions = analytics_response_scope(7)

    rendered = [str(condition) for condition in conditions]
    assert any("survey_responses.survey_id" in text for text in rendered)
    assert any("survey_responses.is_preview" in text for text in rendered)
    # No optional filter conditions when nothing is requested.
    assert len(conditions) == 2


def test_analytics_response_scope_applies_export_style_filters():
    conditions = analytics_response_scope(
        7,
        include_preview=True,
        assigned_group=2,
        language="zh",
        response_status="completed",
        calibration_passed=True,
    )

    rendered = [str(condition) for condition in conditions]
    # include_preview=True drops the is_preview gate, so only the survey scope
    # plus four explicit filters remain.
    assert len(conditions) == 5
    assert all("is_preview" not in text for text in rendered)
    assert any("assigned_group" in text for text in rendered)
    assert any("language" in text for text in rendered)
    assert any("status" in text for text in rendered)
    # calibration_passed becomes a subquery against CalibrationSession.passed.
    assert any("calibration_sessions" in text and "passed" in text for text in rendered)


def test_analytics_response_scope_filters_match_export_filter_columns():
    """The visible analytics summary must read from the same columns the
    /export endpoint filters on, so a researcher cannot see one number on
    screen and a different row count in the downloaded CSV.
    """
    summary_conditions = analytics_response_scope(
        7,
        assigned_group=1,
        language="en",
        response_status="completed",
        calibration_passed=False,
    )
    rendered = " ".join(str(condition) for condition in summary_conditions)

    assert SurveyResponse.assigned_group.key in rendered
    assert SurveyResponse.language.key in rendered
    assert SurveyResponse.status.key in rendered
    assert CalibrationSession.passed.key in rendered
