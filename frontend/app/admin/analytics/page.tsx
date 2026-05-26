"use client";

import type { ReactNode } from "react";
import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { ChartIcon, ChevronDownIcon } from "@/components/icons";
import { useLocale } from "@/components/locale-provider";

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
  total_gaze_samples: number;
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

type ChartScope = "posts" | "groups";
type ChartStyle = "bars" | "columns" | "donut";
type ChartRow = {
  id: string;
  label: string;
  detail?: string;
  value: number;
  displayValue: string;
};
type MetricOption<T> = {
  id: string;
  label: string;
  suffix?: string;
  getValue: (item: T) => number;
};

function formatPercent(value: number) {
  return `${Math.round(value)}%`;
}

function formatMinutes(value: number) {
  if (!value) return "0.0 min";
  return `${value.toFixed(1)} min`;
}

const DOCS_EXPORT_URL = "https://cs14-docs.kazelis.top/guide/data-export.html";

function HorizontalRatioBars({
  bars,
  valueSuffix = "",
}: {
  bars: { label: string; value: number; displayValue?: string }[];
  valueSuffix?: string;
}) {
  const max = Math.max(1e-6, ...bars.map((b) => b.value));
  return (
    <div className="space-y-3 pt-1">
      {bars.map((b) => (
        <div key={b.label}>
          <div className="flex items-baseline justify-between gap-2 text-[12px]">
            <span className="min-w-0 truncate font-medium text-black">{b.label}</span>
            <span className="shrink-0 tabular-nums text-slate-500">
              {b.displayValue ?? `${Math.round(b.value)}${valueSuffix}`}
            </span>
          </div>
          <div className="mt-1 h-2.5 overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-[#0f3146]"
              style={{ width: `${Math.min(100, (b.value / max) * 100)}%` }}
              role="presentation"
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function ChartStyleButton({
  active,
  children,
  onClick,
}: {
  active: boolean;
  children: ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-full px-3 py-1.5 text-[12px] font-semibold transition ${
        active
          ? "bg-[#e4f7f4] text-[#0f3146]"
          : "bg-white text-slate-500 hover:bg-slate-50 hover:text-slate-700"
      }`}
    >
      {children}
    </button>
  );
}

function DataChart({
  rows,
  style,
  emptyText,
}: {
  rows: ChartRow[];
  style: ChartStyle;
  emptyText: string;
}) {
  const palette = ["#0f3146", "#33b9b2", "#8fd8d4", "#f0b67f", "#7f9fc0", "#d2e9e7", "#c8a2c8", "#9fb7a5"];
  const max = Math.max(1e-6, ...rows.map((row) => row.value));
  const total = rows.reduce((sum, row) => sum + row.value, 0);

  if (!rows.length) {
    return <p className="mt-5 text-[13px] text-slate-500">{emptyText}</p>;
  }

  if (style === "donut") {
    let cursor = 0;
    const gradient =
      total > 0
        ? rows
            .map((row, index) => {
              const start = cursor;
              const end = cursor + (row.value / total) * 100;
              cursor = end;
              return `${palette[index % palette.length]} ${start}% ${end}%`;
            })
            .join(", ")
        : "#e5e7eb 0% 100%";

    return (
      <div className="mt-5 grid gap-5 md:grid-cols-[220px_minmax(0,1fr)] md:items-center">
        <div className="relative mx-auto h-[210px] w-[210px] rounded-full" style={{ background: `conic-gradient(${gradient})` }}>
          <div className="absolute inset-[34px] flex flex-col items-center justify-center rounded-full bg-white text-center shadow-[inset_0_0_0_1px_rgba(15,49,70,0.08)]">
            <span className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">Total</span>
            <span className="mt-1 text-[30px] font-semibold tracking-[-0.05em] text-black">{Math.round(total)}</span>
          </div>
        </div>
        <div className="space-y-2">
          {rows.slice(0, 8).map((row, index) => (
            <div key={row.id} className="flex items-center justify-between gap-3 rounded-[14px] bg-stone-50 px-3 py-2">
              <span className="flex min-w-0 items-center gap-2">
                <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: palette[index % palette.length] }} />
                <span className="min-w-0 truncate text-[13px] font-medium text-slate-700">{row.label}</span>
              </span>
              <span className="shrink-0 text-[13px] font-semibold tabular-nums text-black">{row.displayValue}</span>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (style === "columns") {
    return (
      <div className="mt-5 flex h-[300px] items-end gap-3 overflow-x-auto rounded-[22px] bg-gradient-to-b from-white to-stone-50 px-4 pb-4 pt-6">
        {rows.slice(0, 12).map((row, index) => (
          <div key={row.id} className="flex min-w-[82px] flex-1 flex-col items-center gap-2">
            <span className="text-[12px] font-semibold tabular-nums text-black">{row.displayValue}</span>
            <div
              className="w-full rounded-t-[18px] bg-gradient-to-t from-[#0f3146] to-[#72d2cc] shadow-[0_16px_28px_rgba(15,49,70,0.16)]"
              style={{ height: `${Math.max(8, (row.value / max) * 210)}px`, opacity: 1 - Math.min(index * 0.035, 0.28) }}
              role="presentation"
            />
            <span className="line-clamp-2 min-h-[32px] text-center text-[11px] leading-4 text-slate-500">{row.label}</span>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="mt-5 space-y-3">
      {rows.slice(0, 12).map((row, index) => (
        <div key={row.id} className="rounded-[18px] border border-slate-100 bg-white px-4 py-3 shadow-[0_14px_30px_rgba(15,49,70,0.04)]">
          <div className="flex items-baseline justify-between gap-3">
            <div className="min-w-0">
              <p className="truncate text-[13px] font-semibold text-black">{row.label}</p>
              {row.detail && <p className="mt-0.5 truncate text-[11px] uppercase tracking-[0.12em] text-slate-400">{row.detail}</p>}
            </div>
            <span className="shrink-0 text-[14px] font-semibold tabular-nums text-[#0f3146]">{row.displayValue}</span>
          </div>
          <div className="mt-2 h-2.5 overflow-hidden rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-gradient-to-r from-[#0f3146] to-[#62c9c4]"
              style={{ width: `${Math.max(2, Math.min(100, (row.value / max) * 100))}%` }}
              role="presentation"
            />
          </div>
          <p className="mt-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-300">
            Rank {index + 1}
          </p>
        </div>
      ))}
    </div>
  );
}

export default function AnalyticsPage() {
  const router = useRouter();
  const { locale } = useLocale();
  const [surveys, setSurveys] = useState<SurveyListItem[]>([]);
  const [selectedSurveyId, setSelectedSurveyId] = useState<number | null>(null);
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [chartScope, setChartScope] = useState<ChartScope>("posts");
  const [chartMetric, setChartMetric] = useState("clicks");
  const [chartStyle, setChartStyle] = useState<ChartStyle>("bars");
  const [loading, setLoading] = useState(true);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [error, setError] = useState("");
  const [exportGroup, setExportGroup] = useState("");
  const [exportLanguage, setExportLanguage] = useState("");
  const [exportStatus, setExportStatus] = useState("");
  const [exportCalibration, setExportCalibration] = useState("");
  const [includePreview, setIncludePreview] = useState(false);
  const [exportMenuOpen, setExportMenuOpen] = useState(false);
  const [filtersExpanded, setFiltersExpanded] = useState(false);
  const exportMenuRef = useRef<HTMLDivElement | null>(null);
  const text = useMemo(
    () =>
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
          exportCsv: "导出CSV",
          exportJson: "导出JSON",
          exportLabel: "导出",
          exportMenuHeading: "下载内容",
          exportSummaryDesc: "面板快照（JSON）",
          exportCsvDesc: "完整研究数据（CSV）",
          exportJsonDesc: "完整研究数据（JSON）",
          filters: "数据过滤",
          filtersShow: "显示过滤器",
          filtersHide: "收起过滤器",
          filtersActive: "项已应用",
          filtersClear: "清除",
          surveyLabel: "问卷",
          filterGroupLabel: "分组",
          filterLanguageLabel: "语言",
          filterStatusLabel: "作答状态",
          filterCalibrationLabel: "校准结果",
          allGroups: "全部分组",
          allLanguages: "全部语言",
          anyStatus: "全部状态",
          anyCalibration: "全部校准结果",
          completedOnly: "仅已完成",
          inProgressOnly: "仅进行中",
          flaggedOnly: "仅已标记",
          calibrationPassed: "校准通过",
          calibrationFailed: "校准未通过",
          previewResponses: "包含预览作答",
          excludePreview: "默认排除预览/测试作答",
          failedExport: "导出研究数据失败",
          loadingSummary: "正在加载问卷摘要",
          totalResponses: "总作答数",
          completionRate: "完成率",
          avgCompletion: "平均完成时长",
          calibrationOk: "校准通过",
          gazeSamples: "眼动样本",
          calibrationOkChip: "通过",
          groupComparison: "分组对比",
          participants: "名参与者",
          completed: "已完成",
          clicks: "点击",
          likes: "点赞",
          comments: "评论",
          configuredComments: "预设评论",
          participantComments: "参与者评论",
          shares: "分享",
          summary: "摘要",
          insights: "洞察",
          surveyOverview: "问卷概览",
          topCohort: "最活跃组别",
          noGroupData: "暂无分组数据",
          topCohortCopy: "{clicks} 次点击 · {comments} 条评论",
          topCohortEmpty: "问卷发布后，这里会显示参与者数据。",
          engagementTotals: "互动总量",
          engagementTotalsLine: "{clicks} 点击 · {likes} 点赞 · {comments} 评论 · {shares} 分享 · {gaze} 眼动",
          exportReadiness: "导出就绪度",
          exportReadinessCopy: "校准 {calibration}% · 已完成 {completed} 份可导出",
          fullSummaryToggle: "查看完整文字摘要",
          tableHeadGroup: "分组",
          tableHeadParticipants: "参与者",
          tableHeadCompletion: "完成率",
          tableHeadClicks: "点击",
          tableHeadLikes: "点赞",
          tableHeadComments: "评论",
          tableHeadShares: "分享",
          chartCompletionByGroup: "各组完成率",
          chartClicksByGroup: "各组点击次数",
          chartPostClicks: "帖子点击（相对对比）",
          exportFieldsHint:
            "导出包含校准摘要、注意力信心指标、眼动/点击计数、互动（含屏幕点击坐标）及作答。完整字段说明见文档：",
          exportFieldsHintLink: "数据导出指南",
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
          exportCsv: "Export CSV",
          exportJson: "Export JSON",
          exportLabel: "Export",
          exportMenuHeading: "Download",
          exportSummaryDesc: "Dashboard snapshot (JSON)",
          exportCsvDesc: "Full research data (CSV)",
          exportJsonDesc: "Full research data (JSON)",
          filters: "Filters",
          filtersShow: "Show filters",
          filtersHide: "Hide filters",
          filtersActive: "applied",
          filtersClear: "Clear",
          surveyLabel: "Survey",
          filterGroupLabel: "Group",
          filterLanguageLabel: "Language",
          filterStatusLabel: "Response status",
          filterCalibrationLabel: "Calibration",
          allGroups: "All groups",
          allLanguages: "All languages",
          anyStatus: "Any status",
          anyCalibration: "Any calibration",
          completedOnly: "Completed only",
          inProgressOnly: "In progress only",
          flaggedOnly: "Flagged only",
          calibrationPassed: "Calibration passed",
          calibrationFailed: "Calibration failed",
          previewResponses: "Include preview responses",
          excludePreview: "Preview/test responses are excluded by default",
          failedExport: "Failed to export research data",
          loadingSummary: "Loading survey summary",
          totalResponses: "Total responses",
          completionRate: "Completion rate",
          avgCompletion: "Avg completion",
          calibrationOk: "Calibration ok",
          gazeSamples: "Gaze samples",
          calibrationOkChip: "OK",
          groupComparison: "Group comparison",
          participants: "participants",
          completed: "completed",
          clicks: "clicks",
          likes: "Likes",
          comments: "Comments",
          configuredComments: "Configured comments",
          participantComments: "Participant comments",
          shares: "Shares",
          summary: "Summary",
          insights: "Insights",
          surveyOverview: "Survey overview",
          topCohort: "Top cohort",
          noGroupData: "No group data yet",
          topCohortCopy: "{clicks} clicks · {comments} comments",
          topCohortEmpty: "Participant data will appear here once the survey is live.",
          engagementTotals: "Engagement totals",
          engagementTotalsLine: "{clicks} clicks · {likes} likes · {comments} comments · {shares} shares · {gaze} gaze",
          exportReadiness: "Export readiness",
          exportReadinessCopy: "Calibration {calibration}% · {completed} completed responses ready to download",
          fullSummaryToggle: "View full text summary",
          tableHeadGroup: "Group",
          tableHeadParticipants: "Participants",
          tableHeadCompletion: "Completion",
          tableHeadClicks: "Clicks",
          tableHeadLikes: "Likes",
          tableHeadComments: "Comments",
          tableHeadShares: "Shares",
          chartCompletionByGroup: "Completion by group",
          chartClicksByGroup: "Clicks by group",
          chartPostClicks: "Post clicks (relative)",
          exportFieldsHint:
            "Downloads include calibration summaries, attention-confidence metrics, gaze/click counts, interactions (with screen click coordinates), and answers. Column reference:",
          exportFieldsHintLink: "Data export guide",
        },
    [locale],
  );

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

  const exportFilters = useMemo(
    () => ({
      assigned_group: exportGroup ? Number(exportGroup) : undefined,
      language: exportLanguage || undefined,
      response_status: exportStatus || undefined,
      calibration_passed:
        exportCalibration === "passed"
          ? true
          : exportCalibration === "failed"
            ? false
            : undefined,
      include_preview: includePreview ? true : undefined,
    }),
    [exportCalibration, exportGroup, exportLanguage, exportStatus, includePreview],
  );

  useEffect(() => {
    if (!selectedSurveyId) return;
    let active = true;
    setLoadingSummary(true);
    setSummary(null);
    setError("");
    api.getSurveyAnalytics(selectedSurveyId, exportFilters)
      .then((res) => {
        if (!active) return;
        setSummary(res as AnalyticsSummary);
      })
      .catch((err: any) => {
        if (!active) return;
        setSummary(null);
        setError(err.message || text.failedSummary);
      })
      .finally(() => {
        if (active) setLoadingSummary(false);
      });
    return () => {
      active = false;
    };
  }, [selectedSurveyId, exportFilters, text.failedSummary]);

  useEffect(() => {
    if (!exportMenuOpen) return;
    function onDocClick(event: MouseEvent) {
      if (!exportMenuRef.current) return;
      if (!exportMenuRef.current.contains(event.target as Node)) {
        setExportMenuOpen(false);
      }
    }
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setExportMenuOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDocClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [exportMenuOpen]);

  const selectedSurvey = useMemo(
    () => surveys.find((survey) => survey.id === selectedSurveyId) ?? null,
    [selectedSurveyId, surveys],
  );

  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (exportGroup) count += 1;
    if (exportLanguage) count += 1;
    if (exportStatus) count += 1;
    if (exportCalibration) count += 1;
    if (includePreview) count += 1;
    return count;
  }, [exportCalibration, exportGroup, exportLanguage, exportStatus, includePreview]);

  function clearAllFilters() {
    setExportGroup("");
    setExportLanguage("");
    setExportStatus("");
    setExportCalibration("");
    setIncludePreview(false);
  }

  const exportFilenameSuffix = useMemo(() => {
    const parts = [
      exportGroup ? `group-${exportGroup}` : null,
      exportLanguage || null,
      exportStatus || null,
      exportCalibration || null,
      includePreview ? "with-preview" : null,
    ].filter(Boolean);
    return parts.length ? `-${parts.join("-")}` : "";
  }, [exportCalibration, exportGroup, exportLanguage, exportStatus, includePreview]);

  const topGroup = useMemo(() => {
    if (!summary?.group_breakdown?.length) return null;
    return [...summary.group_breakdown].sort((a, b) => b.clicks - a.clicks)[0];
  }, [summary]);

  const postMetricOptions: MetricOption<PostAnalytics>[] = useMemo(
    () => [
      { id: "clicks", label: text.clicks, getValue: (post) => post.clicks },
      { id: "likes", label: text.likes, getValue: (post) => post.likes },
      { id: "comments", label: text.configuredComments, getValue: (post) => post.comments },
      {
        id: "participant_comment_count",
        label: text.participantComments,
        getValue: (post) => post.participant_comment_count,
      },
      { id: "shares", label: text.shares, getValue: (post) => post.shares },
    ],
    [text],
  );

  const groupMetricOptions: MetricOption<GroupAnalytics>[] = useMemo(
    () => [
      { id: "participants", label: "Participants", getValue: (group) => group.participants },
      { id: "completed", label: "Completed", getValue: (group) => group.completed },
      { id: "completion_rate", label: "Completion rate", suffix: "%", getValue: (group) => group.completion_rate },
      { id: "clicks", label: "Clicks", getValue: (group) => group.clicks },
      { id: "likes", label: "Likes", getValue: (group) => group.likes },
      { id: "comments", label: "Comments", getValue: (group) => group.comments },
      { id: "shares", label: "Shares", getValue: (group) => group.shares },
    ],
    [],
  );

  const activePostMetric = postMetricOptions.find((option) => option.id === chartMetric) ?? postMetricOptions[0];
  const activeGroupMetric = groupMetricOptions.find((option) => option.id === chartMetric) ?? groupMetricOptions[0];
  const metricOptions = chartScope === "posts" ? postMetricOptions : groupMetricOptions;
  const activeMetric = chartScope === "posts" ? activePostMetric : activeGroupMetric;

  const chartRows = useMemo<ChartRow[]>(() => {
    if (!summary || !activeMetric) return [];
    if (chartScope === "posts") {
      return [...summary.posts]
        .map((post) => {
          const value = activePostMetric.getValue(post);
          return {
            id: `post-${post.post_id}`,
            label: post.title.length > 68 ? `${post.title.slice(0, 67)}…` : post.title,
            detail: post.source || "Unknown source",
            value,
            displayValue: `${Math.round(value)}${activePostMetric.suffix ?? ""}`,
          };
        })
        .sort((a, b) => b.value - a.value);
    }
    return [...summary.group_breakdown]
      .map((group) => {
        const value = activeGroupMetric.getValue(group);
        return {
          id: `group-${group.group_id}`,
          label: `Group ${group.group_id}`,
          detail: `${group.participants} participants`,
          value,
          displayValue: activeGroupMetric.suffix === "%" ? formatPercent(value) : `${Math.round(value)}`,
        };
      })
      .sort((a, b) => b.value - a.value);
  }, [activeGroupMetric, activeMetric, activePostMetric, chartScope, summary]);

  const engagementRows = useMemo<ChartRow[]>(() => {
    if (!summary) return [];
    return [
      { id: "clicks", label: "Clicks", value: summary.total_clicks, displayValue: String(summary.total_clicks) },
      { id: "likes", label: "Likes", value: summary.total_likes, displayValue: String(summary.total_likes) },
      { id: "comments", label: "Comments", value: summary.total_comments, displayValue: String(summary.total_comments) },
      { id: "shares", label: "Shares", value: summary.total_shares, displayValue: String(summary.total_shares) },
    ];
  }, [summary]);

  const qualityBars = useMemo(() => {
    if (!summary) return [];
    return [
      { label: "Completion rate", value: summary.completion_rate, displayValue: formatPercent(summary.completion_rate) },
      { label: "Calibration success", value: summary.calibration_success_rate, displayValue: formatPercent(summary.calibration_success_rate) },
      { label: "Fast completions", value: summary.fast_completions },
      { label: "Low interaction", value: summary.low_interaction_responses },
      { label: "Duplicate comments", value: summary.duplicate_comment_sessions },
    ];
  }, [summary]);

  function exportSummary() {
    if (!summary || !selectedSurvey || loadingSummary || error) return;
    const payload = {
      survey: selectedSurvey,
      summary,
      exported_at: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${selectedSurvey.title.replace(/\s+/g, "-").replace(/[^\w.-]+/g, "-").toLowerCase()}-analytics.json`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  function downloadTextFile(filename: string, content: string, type: string) {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  async function exportResearchData(format: "csv" | "json") {
    if (!selectedSurvey || !summary || loadingSummary || error) return;
    const filenameBase = selectedSurvey.title.replace(/\s+/g, "-").replace(/[^\w.-]+/g, "-").toLowerCase();
    try {
      if (format === "csv") {
        const csv = await api.exportSurveyDataCsv(selectedSurvey.id, exportFilters);
        downloadTextFile(`${filenameBase}-research-data${exportFilenameSuffix}.csv`, csv, "text/csv;charset=utf-8");
        return;
      }
      const payload = await api.exportSurveyDataJson(selectedSurvey.id, exportFilters);
      downloadTextFile(
        `${filenameBase}-research-data${exportFilenameSuffix}.json`,
        JSON.stringify(payload, null, 2),
        "application/json",
      );
    } catch (err: any) {
      setError(err.message || text.failedExport);
    }
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

  const calibrationPercent = summary ? Math.round(summary.calibration_success_rate) : 0;
  const completedResponses = summary
    ? Math.round((summary.completion_rate / 100) * summary.total_responses)
    : 0;
  const calibrationPass = summary ? summary.calibration_success_rate >= 80 : false;
  const exportReadinessLine = text.exportReadinessCopy
    .replace("{calibration}", String(calibrationPercent))
    .replace("{completed}", String(completedResponses));
  const engagementLine = summary
    ? text.engagementTotalsLine
        .replace("{clicks}", String(summary.total_clicks))
        .replace("{likes}", String(summary.total_likes))
        .replace("{comments}", String(summary.total_comments))
        .replace("{shares}", String(summary.total_shares))
        .replace("{gaze}", String(summary.total_gaze_samples))
    : "";

  return (
    <div className="flex min-h-[calc(100vh-118px)] flex-col">
      <section className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-5">
          <h1 className="page-title">{text.title}</h1>
          <div className="relative inline-flex">
            <label htmlFor="analytics-survey-select" className="sr-only">
              {text.surveyLabel}
            </label>
            <select
              id="analytics-survey-select"
              value={selectedSurveyId ?? ""}
              onChange={(e) => setSelectedSurveyId(Number(e.target.value))}
              className="appearance-none rounded-full border border-slate-200 bg-white py-2 pl-4 pr-9 text-[13px] font-medium text-slate-700 outline-none transition hover:border-slate-300 focus:border-[rgba(0,167,160,0.42)] focus:shadow-[0_0_0_4px_rgba(0,167,160,0.12)]"
            >
              {surveys.map((survey) => (
                <option key={survey.id} value={survey.id}>
                  {survey.title}
                </option>
              ))}
            </select>
            <ChevronDownIcon className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          </div>
        </div>

        <div ref={exportMenuRef} className="relative inline-flex self-start lg:self-auto">
          <button
            type="button"
            onClick={() => setExportMenuOpen((open) => !open)}
            className="primary-button min-w-[148px] gap-1.5"
            disabled={!summary || loadingSummary || !!error}
            aria-haspopup="menu"
            aria-expanded={exportMenuOpen}
          >
            <span>{text.exportLabel}</span>
            <span className="text-[11px] font-medium opacity-70">CSV · JSON</span>
            <ChevronDownIcon className={`h-3.5 w-3.5 transition ${exportMenuOpen ? "rotate-180" : ""}`} />
          </button>
          {exportMenuOpen && (
            <div
              role="menu"
              className="absolute right-0 top-full z-30 mt-2 w-[300px] overflow-hidden rounded-[14px] border border-slate-200 bg-white shadow-[0_22px_44px_rgba(15,49,70,0.12)]"
            >
              <p className="px-4 pb-1 pt-3 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
                {text.exportMenuHeading}
              </p>
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setExportMenuOpen(false);
                  exportSummary();
                }}
                className="flex w-full items-start gap-3 px-4 py-3 text-left text-[13px] transition hover:bg-stone-50"
              >
                <span className="mt-0.5 inline-flex h-6 min-w-[44px] items-center justify-center rounded-full bg-stone-100 px-2 text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-600">
                  JSON
                </span>
                <span className="flex flex-col">
                  <span className="font-semibold text-black">{text.export}</span>
                  <span className="text-[12px] leading-5 text-slate-500">{text.exportSummaryDesc}</span>
                </span>
              </button>
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setExportMenuOpen(false);
                  exportResearchData("csv");
                }}
                className="flex w-full items-start gap-3 border-t border-slate-100 px-4 py-3 text-left text-[13px] transition hover:bg-stone-50"
              >
                <span className="mt-0.5 inline-flex h-6 min-w-[44px] items-center justify-center rounded-full bg-stone-100 px-2 text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-600">
                  CSV
                </span>
                <span className="flex flex-col">
                  <span className="font-semibold text-black">{text.exportCsv}</span>
                  <span className="text-[12px] leading-5 text-slate-500">{text.exportCsvDesc}</span>
                </span>
              </button>
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setExportMenuOpen(false);
                  exportResearchData("json");
                }}
                className="flex w-full items-start gap-3 border-t border-slate-100 px-4 py-3 text-left text-[13px] transition hover:bg-stone-50"
              >
                <span className="mt-0.5 inline-flex h-6 min-w-[44px] items-center justify-center rounded-full bg-stone-100 px-2 text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-600">
                  JSON
                </span>
                <span className="flex flex-col">
                  <span className="font-semibold text-black">{text.exportJson}</span>
                  <span className="text-[12px] leading-5 text-slate-500">{text.exportJsonDesc}</span>
                </span>
              </button>
            </div>
          )}
        </div>
      </section>

      {summary && (
        <section className="mt-4 rounded-[14px] border border-slate-200 bg-white px-3 py-2">
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => setFiltersExpanded((open) => !open)}
              className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-[12px] font-medium text-slate-600 transition hover:border-slate-300"
              aria-expanded={filtersExpanded}
            >
              <span>{text.filters}</span>
              {activeFilterCount > 0 && (
                <span className="inline-flex h-4 min-w-[18px] items-center justify-center rounded-full bg-black px-1 text-[10px] font-semibold text-white">
                  {activeFilterCount}
                </span>
              )}
              <ChevronDownIcon className={`h-3.5 w-3.5 transition ${filtersExpanded ? "rotate-180" : ""}`} />
            </button>

            {!filtersExpanded && activeFilterCount === 0 && (
              <span className="text-[12px] text-slate-400">{text.filtersShow}</span>
            )}

            {!filtersExpanded && activeFilterCount > 0 && (
              <>
                {exportGroup && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-stone-100 px-2.5 py-1 text-[11px] font-medium text-slate-600">
                    Group {exportGroup}
                  </span>
                )}
                {exportLanguage && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-stone-100 px-2.5 py-1 text-[11px] font-medium text-slate-600">
                    {exportLanguage.toUpperCase()}
                  </span>
                )}
                {exportStatus && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-stone-100 px-2.5 py-1 text-[11px] font-medium text-slate-600">
                    {exportStatus === "completed"
                      ? text.completedOnly
                      : exportStatus === "in_progress"
                        ? text.inProgressOnly
                        : text.flaggedOnly}
                  </span>
                )}
                {exportCalibration && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-stone-100 px-2.5 py-1 text-[11px] font-medium text-slate-600">
                    {exportCalibration === "passed" ? text.calibrationPassed : text.calibrationFailed}
                  </span>
                )}
                {includePreview && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-stone-100 px-2.5 py-1 text-[11px] font-medium text-slate-600">
                    {text.previewResponses}
                  </span>
                )}
                <button
                  type="button"
                  onClick={clearAllFilters}
                  className="ml-auto text-[11px] font-medium text-slate-500 underline-offset-2 hover:underline"
                >
                  {text.filtersClear}
                </button>
              </>
            )}
          </div>

          {filtersExpanded && (
            <div className="mt-3 flex flex-col gap-2 border-t border-slate-100 pt-3 lg:flex-row lg:flex-wrap lg:items-center">
              <label htmlFor="analytics-filter-group" className="sr-only">
                {text.filterGroupLabel}
              </label>
              <select
                id="analytics-filter-group"
                aria-label={text.filterGroupLabel}
                value={exportGroup}
                onChange={(event) => setExportGroup(event.target.value)}
                className="h-9 min-w-[130px] flex-1 rounded-full border border-slate-200 bg-white px-3 text-[12px] outline-none transition hover:border-slate-300 lg:flex-none"
              >
                <option value="">{text.allGroups}</option>
                {summary.group_breakdown.map((group) => (
                  <option key={group.group_id} value={group.group_id}>
                    Group {group.group_id}
                  </option>
                ))}
              </select>
              <label htmlFor="analytics-filter-language" className="sr-only">
                {text.filterLanguageLabel}
              </label>
              <select
                id="analytics-filter-language"
                aria-label={text.filterLanguageLabel}
                value={exportLanguage}
                onChange={(event) => setExportLanguage(event.target.value)}
                className="h-9 min-w-[130px] flex-1 rounded-full border border-slate-200 bg-white px-3 text-[12px] outline-none transition hover:border-slate-300 lg:flex-none"
              >
                <option value="">{text.allLanguages}</option>
                <option value="en">English</option>
                <option value="zh">中文</option>
                <option value="ar">العربية</option>
              </select>
              <label htmlFor="analytics-filter-status" className="sr-only">
                {text.filterStatusLabel}
              </label>
              <select
                id="analytics-filter-status"
                aria-label={text.filterStatusLabel}
                value={exportStatus}
                onChange={(event) => setExportStatus(event.target.value)}
                className="h-9 min-w-[140px] flex-1 rounded-full border border-slate-200 bg-white px-3 text-[12px] outline-none transition hover:border-slate-300 lg:flex-none"
              >
                <option value="">{text.anyStatus}</option>
                <option value="completed">{text.completedOnly}</option>
                <option value="in_progress">{text.inProgressOnly}</option>
                <option value="flagged">{text.flaggedOnly}</option>
              </select>
              <label htmlFor="analytics-filter-calibration" className="sr-only">
                {text.filterCalibrationLabel}
              </label>
              <select
                id="analytics-filter-calibration"
                aria-label={text.filterCalibrationLabel}
                value={exportCalibration}
                onChange={(event) => setExportCalibration(event.target.value)}
                className="h-9 min-w-[150px] flex-1 rounded-full border border-slate-200 bg-white px-3 text-[12px] outline-none transition hover:border-slate-300 lg:flex-none"
              >
                <option value="">{text.anyCalibration}</option>
                <option value="passed">{text.calibrationPassed}</option>
                <option value="failed">{text.calibrationFailed}</option>
              </select>
              <label className="inline-flex h-9 items-center gap-2 rounded-full border border-slate-200 bg-white px-3 text-[12px] text-slate-600">
                <input
                  type="checkbox"
                  className="h-3.5 w-3.5 accent-[#00a7a0]"
                  checked={includePreview}
                  onChange={(event) => setIncludePreview(event.target.checked)}
                />
                <span>{text.previewResponses}</span>
              </label>
              {activeFilterCount > 0 && (
                <button
                  type="button"
                  onClick={clearAllFilters}
                  className="ml-auto text-[12px] font-medium text-slate-500 underline-offset-2 hover:underline"
                >
                  {text.filtersClear}
                </button>
              )}
            </div>
          )}
        </section>
      )}

      {summary && (
        <p className="mt-2 text-[12px] leading-5 text-slate-500">
          {text.exportFieldsHint}{" "}
          <a href={DOCS_EXPORT_URL} target="_blank" rel="noreferrer" className="font-medium text-[#0f3146] underline decoration-black/15 underline-offset-2">
            {text.exportFieldsHintLink}
          </a>
        </p>
      )}

      {error && <p className="mt-4 rounded-[14px] border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>}

      {error ? null : loadingSummary || !summary ? (
        <p className="pt-14 text-sm uppercase tracking-[0.14em] text-slate-400">{text.loadingSummary}</p>
      ) : (
        <>
          <section className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
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
            <div className="metric-panel">
              <div className="flex items-center gap-2">
                <p className="section-kicker">{text.calibrationOk}</p>
                {calibrationPass && (
                  <span className="inline-flex items-center rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.1em] text-emerald-700">
                    {text.calibrationOkChip}
                  </span>
                )}
              </div>
              <p className="metric-value">{formatPercent(summary.calibration_success_rate)}</p>
            </div>
          </section>

          <section className="mt-4 grid gap-3 xl:grid-cols-[minmax(0,1fr)_340px]">
            <div className="surface-panel px-5 py-5">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <p className="section-kicker">Explore data</p>
                  <h2 className="mt-2 text-[22px] font-semibold tracking-[-0.04em] text-black">
                    Choose the data and chart you need
                  </h2>
                  <p className="mt-1 max-w-2xl text-[13px] leading-6 text-slate-500">
                    Switch between posts and groups, then select a metric and chart style for a cleaner read of the same analytics data.
                  </p>
                </div>
                <div className="flex shrink-0 rounded-full border border-slate-100 bg-stone-50 p-1">
                  <ChartStyleButton
                    active={chartScope === "posts"}
                    onClick={() => {
                      setChartScope("posts");
                      setChartMetric("clicks");
                    }}
                  >
                    Posts
                  </ChartStyleButton>
                  <ChartStyleButton
                    active={chartScope === "groups"}
                    onClick={() => {
                      setChartScope("groups");
                      setChartMetric("participants");
                    }}
                  >
                    Groups
                  </ChartStyleButton>
                </div>
              </div>

              <div className="mt-5 flex flex-col gap-3 border-y border-slate-100 py-3 md:flex-row md:items-center md:justify-between">
                <label className="flex flex-col gap-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-400 md:min-w-[220px]">
                  Metric
                  <select
                    value={activeMetric.id}
                    onChange={(event) => setChartMetric(event.target.value)}
                    className="h-10 rounded-full border border-slate-200 bg-white px-3 text-[13px] font-medium normal-case tracking-normal text-slate-700 outline-none transition hover:border-slate-300 focus:border-[rgba(0,167,160,0.42)] focus:shadow-[0_0_0_4px_rgba(0,167,160,0.12)]"
                  >
                    {metricOptions.map((option) => (
                      <option key={option.id} value={option.id}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>

                <div className="flex rounded-full border border-slate-100 bg-stone-50 p-1">
                  <ChartStyleButton active={chartStyle === "bars"} onClick={() => setChartStyle("bars")}>
                    Bars
                  </ChartStyleButton>
                  <ChartStyleButton active={chartStyle === "columns"} onClick={() => setChartStyle("columns")}>
                    Columns
                  </ChartStyleButton>
                  <ChartStyleButton active={chartStyle === "donut"} onClick={() => setChartStyle("donut")}>
                    Donut
                  </ChartStyleButton>
                </div>
              </div>

              <DataChart
                rows={chartRows}
                style={chartStyle}
                emptyText={chartScope === "posts" ? "No post engagement recorded yet." : text.noGroupData}
              />
            </div>

            <aside className="surface-panel px-5 py-5">
              <p className="section-kicker">Response quality</p>
              <h2 className="mt-2 text-[20px] font-semibold tracking-[-0.04em] text-black">
                Signal check
              </h2>
              <p className="mt-1 text-[13px] leading-6 text-slate-500">
                Key completion and calibration signals are grouped here so quality checks stay visible without opening a post drill-down.
              </p>

              <div className="mt-4 grid grid-cols-2 gap-2">
                <div className="rounded-[16px] bg-stone-50 px-3 py-3">
                  <p className="section-kicker">Fast</p>
                  <p className="mt-1 text-[24px] font-semibold tracking-[-0.05em] text-black">{summary.fast_completions}</p>
                </div>
                <div className="rounded-[16px] bg-stone-50 px-3 py-3">
                  <p className="section-kicker">Low interaction</p>
                  <p className="mt-1 text-[24px] font-semibold tracking-[-0.05em] text-black">{summary.low_interaction_responses}</p>
                </div>
                <div className="rounded-[16px] bg-stone-50 px-3 py-3">
                  <p className="section-kicker">Duplicates</p>
                  <p className="mt-1 text-[24px] font-semibold tracking-[-0.05em] text-black">{summary.duplicate_comment_sessions}</p>
                </div>
                <div className="rounded-[16px] bg-stone-50 px-3 py-3">
                  <p className="section-kicker">Gaze</p>
                  <p className="mt-1 text-[24px] font-semibold tracking-[-0.05em] text-black">{summary.total_gaze_samples}</p>
                </div>
              </div>

              <div className="mt-4 rounded-[18px] bg-white">
                <HorizontalRatioBars bars={qualityBars} />
              </div>
            </aside>
          </section>

          <section className="mt-3 grid gap-3 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
            <div className="surface-panel px-5 py-5">
              <p className="section-kicker">Engagement mix</p>
              <DataChart rows={engagementRows} style="donut" emptyText="No engagement recorded yet." />
            </div>

            <div className="surface-panel px-5 py-5">
              <p className="section-kicker">{text.insights}</p>
              <div className="mt-3 grid gap-3 md:grid-cols-3">
                <div className="rounded-[18px] bg-stone-50 px-4 py-4">
                  <span className="section-kicker">{text.topCohort}</span>
                  <p className="mt-2 text-[17px] font-semibold tracking-[-0.03em] text-black">
                    {topGroup ? `Group ${topGroup.group_id}` : text.noGroupData}
                  </p>
                  <p className="mt-1 text-[12px] leading-5 text-slate-500">
                    {topGroup
                      ? text.topCohortCopy.replace("{clicks}", String(topGroup.clicks)).replace("{comments}", String(topGroup.comments))
                      : text.topCohortEmpty}
                  </p>
                </div>
                <div className="rounded-[18px] bg-stone-50 px-4 py-4">
                  <span className="section-kicker">{text.engagementTotals}</span>
                  <p className="mt-2 text-[13px] leading-6 text-slate-700">{engagementLine}</p>
                </div>
                <div className="rounded-[18px] bg-stone-50 px-4 py-4">
                  <span className="section-kicker">{text.exportReadiness}</span>
                  <p className="mt-2 text-[13px] leading-6 text-slate-700">{exportReadinessLine}</p>
                </div>
              </div>

              {summary.summary && (
                <details className="mt-4 group">
                  <summary className="cursor-pointer list-none text-[12px] font-medium text-slate-500 hover:text-slate-700">
                    <span className="inline-flex items-center gap-1">
                      <ChevronDownIcon className="h-3.5 w-3.5 transition group-open:rotate-180" />
                      {text.fullSummaryToggle}
                    </span>
                  </summary>
                  <p className="mt-3 text-[13px] leading-6 text-slate-500">{summary.summary}</p>
                </details>
              )}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
