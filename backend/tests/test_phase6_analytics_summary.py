"""Analytics summary contract tests."""

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
                comments=1,
                shares=1,
                participant_comment_count=1,
            )
        ],
        summary="Tracking evidence is ready for export.",
    )

    assert summary.model_dump()["total_gaze_samples"] == 24
