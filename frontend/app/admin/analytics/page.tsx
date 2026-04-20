"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useLocale } from "@/components/locale-provider";
import { ChartIcon, CheckCircleIcon, SearchIcon, UsersIcon } from "@/components/icons";

type SurveyListItem = {
  id: number;
  title: string;
  status: string;
  num_groups: number;
};

type GroupAnalytics = {
  group_id: number;
  participants: number;
  completed: number;
  completion_rate: number;
  clicks: number;
  likes: number;
  comments: number;
  shares: number;
};

type PostAnalytics = {
  post_id: number;
  title: string;
  source: string | null;
  visible_groups: number[] | null;
  clicks: number;
  likes: number;
  comments: number;
  shares: number;
  participant_comment_count: number;
};

type AnalyticsSummary = {
  survey_id: number;
  total_responses: number;
  completion_rate: number;
  avg_completion_minutes: number;
  calibration_success_rate: number;
  total_clicks: number;
  total_likes: number;
  total_comments: number;
  total_shares: number;
  fast_completions: number;
  low_interaction_responses: number;
  duplicate_comment_sessions: number;
  group_breakdown: GroupAnalytics[];
  posts: PostAnalytics[];
  summary: string;
};

type ParticipantComment = {
  id: number;
  post_id: number;
  text: string;
  created_at: string;
};

function formatPercent(value: number) {
  return `${Math.round(value)}%`;
}

function formatMinutes(value: number) {
  if (!value) return "0.0 min";
  return `${value.toFixed(1)} min`;
}

export default function AnalyticsPage() {
  const router = useRouter();
  const { locale } = useLocale();
  const [surveys, setSurveys] = useState<SurveyListItem[]>([]);
  const [selectedSurveyId, setSelectedSurveyId] = useState<number | null>(null);
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [selectedPostId, setSelectedPostId] = useState<number | null>(null);
  const [commentsByPost, setCommentsByPost] = useState<Record<number, ParticipantComment[]>>({});
  const [loading, setLoading] = useState(true);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [error, setError] = useState("");
  const text =
    locale === "zh"
      ? {
          failed: "加载分析失败",
          failedSummary: "加载分析摘要失败",
          loading: "正在加载分析",
          noAnalytics: "还没有问卷分析数据",
          noAnalyticsCopy: "请先创建并发布问卷。参与者开始互动后，这里会显示分析数据。",
          createSurvey: "新建问卷",
          title: "分析",
          subtitle: "查看作答质量、互动行为和分组差异。",
          export: "导出摘要",
          loadingSummary: "正在加载问卷摘要",
          totalResponses: "总作答数",
          completionRate: "完成率",
          avgCompletion: "平均完成时长",
          calibrationOk: "校准通过",
          groupComparison: "分组对比",
          participants: "名参与者",
          completed: "已完成",
          clicks: "点击",
          likes: "点赞",
          comments: "评论",
          shares: "分享",
          summary: "摘要",
          surveyOverview: "问卷概览",
          topCohort: "最活跃组别",
          noGroupData: "暂无分组数据",
          topCohortCopy: "该条件下记录了 {clicks} 次点击和 {comments} 条评论。",
          topCohortEmpty: "问卷发布后，这里会显示参与者数据。",
          engagementTotals: "互动总量",
          totalClicks: "总点击",
          totalLikes: "总点赞",
          totalComments: "总评论",
          totalShares: "总分享",
        }
      : {
          failed: "Failed to load analytics",
          failedSummary: "Failed to load analytics summary",
          loading: "Loading analytics",
          noAnalytics: "No survey analytics yet",
          noAnalyticsCopy: "Create and publish a survey first. Analytics will populate once participants begin interacting with the feed.",
          createSurvey: "Create Survey",
          title: "Analytics",
          subtitle: "Review response quality, engagement behaviour, and group-level differences.",
          export: "Export Summary",
          loadingSummary: "Loading survey summary",
          totalResponses: "Total responses",
          completionRate: "Completion rate",
          avgCompletion: "Avg completion",
          calibrationOk: "Calibration ok",
          groupComparison: "Group comparison",
          participants: "participants",
          completed: "completed",
          clicks: "clicks",
          likes: "Likes",
          comments: "Comments",
          shares: "Shares",
          summary: "Summary",
          surveyOverview: "Survey overview",
          topCohort: "Top cohort",
          noGroupData: "No group data",
          topCohortCopy: "{clicks} clicks and {comments} comments recorded in this condition.",
          topCohortEmpty: "Participant data will appear here once the survey is live.",
          engagementTotals: "Engagement totals",
          totalClicks: "Total clicks",
          totalLikes: "Total likes",
          totalComments: "Total comments",
          totalShares: "Total shares",
        };

  useEffect(() => {
    let active = true;
    api.listSurveys()
      .then((res) => {
        if (!active) return;
        const items = res.items as SurveyListItem[];
        setSurveys(items);
        if (items.length > 0) {
          setSelectedSurveyId(items[0].id);
        }
      })
      .catch((err: any) => {
        if (!active) return;
        setError(err.message || text.failed);
        router.push("/auth");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [router, text.failed]);

  useEffect(() => {
    if (!selectedSurveyId) return;
    let active = true;
    setLoadingSummary(true);
    api.getSurveyAnalytics(selectedSurveyId)
      .then((res) => {
        if (!active) return;
        const nextSummary = res as AnalyticsSummary;
        setSummary(nextSummary);
        setSelectedPostId(nextSummary.posts[0]?.post_id ?? null);
      })
      .catch((err: any) => {
        if (!active) return;
        setError(err.message || text.failedSummary);
      })
      .finally(() => {
        if (active) setLoadingSummary(false);
      });
    return () => {
      active = false;
    };
  }, [selectedSurveyId, text.failedSummary]);

  useEffect(() => {
    if (!selectedSurveyId) return;
    let active = true;
    api.getSurveyParticipantComments(selectedSurveyId)
      .then((res) => {
        if (!active) return;
        setCommentsByPost((res.comments_by_post || {}) as Record<number, ParticipantComment[]>);
      })
      .catch(() => {
        if (!active) return;
        setCommentsByPost({});
      });
    return () => {
      active = false;
    };
  }, [selectedSurveyId]);

  const selectedSurvey = useMemo(
    () => surveys.find((survey) => survey.id === selectedSurveyId) ?? null,
    [selectedSurveyId, surveys],
  );

  const topGroup = useMemo(() => {
    if (!summary?.group_breakdown?.length) return null;
    return [...summary.group_breakdown].sort((a, b) => b.clicks - a.clicks)[0];
  }, [summary]);

  const selectedPost = useMemo(() => {
    if (!summary?.posts?.length) return null;
    return summary.posts.find((post) => post.post_id === selectedPostId) ?? summary.posts[0];
  }, [selectedPostId, summary]);

  function exportSummary() {
    if (!summary || !selectedSurvey) return;
    const payload = {
      survey: selectedSurvey,
      summary,
      exported_at: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${selectedSurvey.title.replace(/\s+/g, "-").toLowerCase()}-analytics.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  if (loading) {
    return <p className="pt-14 text-sm uppercase tracking-[0.24em] text-slate-400">{text.loading}</p>;
  }

  if (!surveys.length) {
    return (
      <div className="surface-panel px-8 py-12 text-center">
        <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-[18px] bg-stone-100 text-slate-500">
          <ChartIcon className="h-5 w-5" />
        </div>
        <h1 className="mt-5 text-[24px] font-semibold tracking-[-0.04em] text-black">{text.noAnalytics}</h1>
        <p className="mx-auto mt-2 max-w-xl text-[14px] leading-7 text-slate-500">
          {text.noAnalyticsCopy}
        </p>
        <button type="button" onClick={() => router.push("/admin/surveys/new")} className="primary-button mt-6">
          {text.createSurvey}
        </button>
      </div>
    );
  }

  return (
    <div className="flex min-h-[calc(100vh-118px)] flex-col">
      <section className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <h1 className="page-title">{text.title}</h1>
          <p className="page-subtitle">{text.subtitle}</p>
        </div>

        <div className="flex w-full flex-col gap-3 md:flex-row xl:w-auto">
          <div className="relative min-w-[280px]">
            <SearchIcon className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <select
              value={selectedSurveyId ?? ""}
              onChange={(e) => setSelectedSurveyId(Number(e.target.value))}
              className="field-input appearance-none bg-white py-2 pl-11 pr-10"
            >
              {surveys.map((survey) => (
                <option key={survey.id} value={survey.id}>
                  {survey.title}
                </option>
              ))}
            </select>
          </div>
          <button type="button" onClick={exportSummary} className="secondary-button min-w-[148px]" disabled={!summary}>
            {text.export}
          </button>
        </div>
      </section>

      {error && <p className="mt-4 rounded-[16px] border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>}

      {loadingSummary || !summary ? (
        <p className="pt-14 text-sm uppercase tracking-[0.24em] text-slate-400">{text.loadingSummary}</p>
      ) : (
        <>
          <section className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <div className="metric-panel">
              <p className="section-kicker">{text.totalResponses}</p>
              <p className="metric-value">{summary.total_responses}</p>
            </div>
            <div className="metric-panel">
              <p className="section-kicker">{text.completionRate}</p>
              <p className="metric-value">{formatPercent(summary.completion_rate)}</p>
            </div>
            <div className="metric-panel">
              <p className="section-kicker">{text.avgCompletion}</p>
              <p className="metric-value">{formatMinutes(summary.avg_completion_minutes)}</p>
            </div>
            <div className="rounded-[18px] bg-black px-5 py-4 text-white shadow-[0_28px_60px_rgba(17,24,39,0.14)]">
              <p className="section-kicker text-white/55">{text.calibrationOk}</p>
              <p className="metric-value-inverse">{formatPercent(summary.calibration_success_rate)}</p>
            </div>
          </section>

          <section className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
            <div className="surface-panel px-6 py-6">
              <p className="section-kicker">{text.groupComparison}</p>
              <div className="mt-5 space-y-4">
                {summary.group_breakdown.map((group) => (
                  <div key={group.group_id} className="rounded-[18px] border bg-stone-50 px-4 py-4">
                    <div className="flex items-center justify-between gap-4">
                      <div>
                        <p className="text-[16px] font-semibold tracking-[-0.03em] text-black">Group {group.group_id}</p>
                        <p className="mt-1 text-[13px] leading-6 text-slate-500">
                          {group.participants} {text.participants} · {formatPercent(group.completion_rate)} {text.completed}
                        </p>
                      </div>
                      <div className="rounded-full bg-white px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                        {group.clicks} {text.clicks}
                      </div>
                    </div>
                    <div className="mt-4 grid gap-3 sm:grid-cols-4">
                      <div>
                        <p className="section-kicker">{text.likes}</p>
                        <p className="mt-2 text-[22px] font-semibold tracking-[-0.04em] text-black">{group.likes}</p>
                      </div>
                      <div>
                        <p className="section-kicker">{text.comments}</p>
                        <p className="mt-2 text-[22px] font-semibold tracking-[-0.04em] text-black">{group.comments}</p>
                      </div>
                      <div>
                        <p className="section-kicker">{text.shares}</p>
                        <p className="mt-2 text-[22px] font-semibold tracking-[-0.04em] text-black">{group.shares}</p>
                      </div>
                      <div>
                        <p className="section-kicker">{text.completed}</p>
                        <p className="mt-2 text-[22px] font-semibold tracking-[-0.04em] text-black">{group.completed}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="surface-panel px-6 py-6">
              <p className="section-kicker">{text.summary}</p>
              <h2 className="mt-3 text-[22px] font-semibold tracking-[-0.04em] text-black">
                {selectedSurvey?.title ?? text.surveyOverview}
              </h2>
              <p className="mt-3 text-[14px] leading-7 text-slate-500">{summary.summary}</p>

              <div className="mt-6 grid gap-3 md:grid-cols-2">
                <div className="rounded-[18px] border bg-stone-50 px-4 py-4">
                  <p className="section-kicker">{text.topCohort}</p>
                  <p className="mt-2 text-[18px] font-semibold tracking-[-0.03em] text-black">
                    {topGroup ? `Group ${topGroup.group_id}` : text.noGroupData}
                  </p>
                  <p className="mt-2 text-[13px] leading-6 text-slate-500">
                    {topGroup
                      ? text.topCohortCopy.replace("{clicks}", String(topGroup.clicks)).replace("{comments}", String(topGroup.comments))
                      : text.topCohortEmpty}
                  </p>
                </div>
                <div className="rounded-[18px] border bg-stone-50 px-4 py-4">
                  <p className="section-kicker">{text.engagementTotals}</p>
                  <div className="mt-3 space-y-2 text-[13px] leading-6 text-slate-500">
                    <p>{text.totalClicks}: <span className="font-medium text-black">{summary.total_clicks}</span></p>
                    <p>{text.totalLikes}: <span className="font-medium text-black">{summary.total_likes}</span></p>
                    <p>{text.totalComments}: <span className="font-medium text-black">{summary.total_comments}</span></p>
                    <p>{text.totalShares}: <span className="font-medium text-black">{summary.total_shares}</span></p>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1.25fr)_320px]">
            <div className="surface-panel overflow-hidden">
              <div className="flex flex-col gap-3 border-b px-6 py-5 md:flex-row md:items-center md:justify-between">
                <div>
                  <p className="section-kicker">Post performance</p>
                  <p className="mt-2 text-[14px] leading-7 text-slate-500">
                    Compare engagement totals across each configured post card in the current survey.
                  </p>
                </div>
                <div className="rounded-full bg-stone-100 px-4 py-2 text-[13px] text-slate-600">
                  {summary.posts.length} configured posts
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="min-w-full text-left">
                  <thead className="bg-stone-50">
                    <tr className="text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-500">
                      <th className="px-6 py-4">Post</th>
                      <th className="px-4 py-4">Clicks</th>
                      <th className="px-4 py-4">Likes</th>
                      <th className="px-4 py-4">Comments</th>
                      <th className="px-4 py-4">Shares</th>
                      <th className="px-4 py-4">Groups</th>
                    </tr>
                  </thead>
                  <tbody>
                    {summary.posts.map((post) => {
                      const active = selectedPost?.post_id === post.post_id;
                      return (
                        <tr
                          key={post.post_id}
                          className={`cursor-pointer border-t text-[13px] text-slate-600 transition hover:bg-stone-50 ${
                            active ? "bg-stone-50" : ""
                          }`}
                          onClick={() => setSelectedPostId(post.post_id)}
                        >
                          <td className="px-6 py-4">
                            <div>
                              <p className="font-semibold text-black">{post.title}</p>
                              <p className="mt-1 text-[12px] uppercase tracking-[0.16em] text-slate-400">
                                {post.source || "Unknown source"}
                              </p>
                            </div>
                          </td>
                          <td className="px-4 py-4">{post.clicks}</td>
                          <td className="px-4 py-4">{post.likes}</td>
                          <td className="px-4 py-4">{post.comments}</td>
                          <td className="px-4 py-4">{post.shares}</td>
                          <td className="px-4 py-4">
                            {post.visible_groups?.length ? post.visible_groups.join(", ") : "All"}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            <aside className="surface-panel px-6 py-6">
              <p className="section-kicker">Post drill-down</p>
              {selectedPost ? (
                <>
                  <h2 className="mt-3 text-[20px] font-semibold tracking-[-0.04em] text-black">{selectedPost.title}</h2>
                  <p className="mt-2 text-[12px] uppercase tracking-[0.16em] text-slate-400">
                    {selectedPost.source || "Unknown source"}
                  </p>

                  <div className="mt-5 grid gap-3 sm:grid-cols-2">
                    <div className="rounded-[16px] border bg-stone-50 px-4 py-3">
                      <p className="section-kicker">Clicks</p>
                      <p className="mt-2 text-[24px] font-semibold tracking-[-0.04em] text-black">{selectedPost.clicks}</p>
                    </div>
                    <div className="rounded-[16px] border bg-stone-50 px-4 py-3">
                      <p className="section-kicker">Likes</p>
                      <p className="mt-2 text-[24px] font-semibold tracking-[-0.04em] text-black">{selectedPost.likes}</p>
                    </div>
                    <div className="rounded-[16px] border bg-stone-50 px-4 py-3">
                      <p className="section-kicker">Comments</p>
                      <p className="mt-2 text-[24px] font-semibold tracking-[-0.04em] text-black">{selectedPost.comments}</p>
                    </div>
                    <div className="rounded-[16px] border bg-stone-50 px-4 py-3">
                      <p className="section-kicker">Shares</p>
                      <p className="mt-2 text-[24px] font-semibold tracking-[-0.04em] text-black">{selectedPost.shares}</p>
                    </div>
                  </div>

                  <div className="mt-5 rounded-[18px] border bg-stone-50 px-4 py-4">
                    <p className="section-kicker">Visibility</p>
                    <p className="mt-2 text-[14px] leading-7 text-slate-600">
                      {selectedPost.visible_groups?.length
                        ? `Visible to groups ${selectedPost.visible_groups.join(", ")}`
                        : "Visible to all participant groups"}
                    </p>
                  </div>

                  <div className="mt-5">
                    <p className="section-kicker">Participant comments</p>
                    <div className="mt-3 space-y-3">
                      {(commentsByPost[selectedPost.post_id] || []).slice(0, 3).map((comment) => (
                        <div key={comment.id} className="rounded-[18px] border bg-white px-4 py-4">
                          <p className="text-[13px] font-semibold text-black">Participant response</p>
                          <p className="mt-1 text-[13px] leading-6 text-slate-600">{comment.text}</p>
                        </div>
                      ))}
                      {!(commentsByPost[selectedPost.post_id] || []).length && (
                        <div className="rounded-[18px] border bg-stone-50 px-4 py-4 text-[13px] leading-6 text-slate-500">
                          No participant comments captured for this post yet.
                        </div>
                      )}
                    </div>
                  </div>
                </>
              ) : (
                <p className="mt-3 text-[14px] leading-7 text-slate-500">
                  Select a post row to inspect its engagement mix and comment sample.
                </p>
              )}
            </aside>
          </section>

          <section className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
            <div className="surface-panel px-6 py-6">
              <p className="section-kicker">Response quality</p>
              <div className="mt-5 grid gap-3 sm:grid-cols-2">
                <div className="rounded-[18px] border bg-stone-50 px-4 py-4">
                  <p className="section-kicker">Fast completions</p>
                  <p className="mt-2 text-[24px] font-semibold tracking-[-0.04em] text-black">{summary.fast_completions}</p>
                </div>
                <div className="rounded-[18px] border bg-stone-50 px-4 py-4">
                  <p className="section-kicker">Low interaction</p>
                  <p className="mt-2 text-[24px] font-semibold tracking-[-0.04em] text-black">{summary.low_interaction_responses}</p>
                </div>
                <div className="rounded-[18px] border bg-stone-50 px-4 py-4">
                  <p className="section-kicker">Duplicate comments</p>
                  <p className="mt-2 text-[24px] font-semibold tracking-[-0.04em] text-black">{summary.duplicate_comment_sessions}</p>
                </div>
                <div className="rounded-[18px] border bg-stone-50 px-4 py-4">
                  <p className="section-kicker">Calibration pass</p>
                  <p className="mt-2 text-[24px] font-semibold tracking-[-0.04em] text-black">{formatPercent(summary.calibration_success_rate)}</p>
                </div>
              </div>
            </div>

            <div className="surface-panel-soft px-6 py-6">
              <p className="section-kicker">Recommended next checks</p>
              <div className="mt-5 space-y-4">
                {[
                  "Open the highest-click post and compare visible groups before publishing the next draft.",
                  "Review low-interaction sessions to confirm your post order and question cadence are working.",
                  "Export this summary when you need a lightweight dataset handoff for reporting or analysis.",
                ].map((item) => (
                  <div key={item} className="flex items-start gap-3">
                    <CheckCircleIcon className="mt-0.5 h-4 w-4 text-black" />
                    <p className="text-[14px] leading-7 text-slate-500">{item}</p>
                  </div>
                ))}
              </div>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
