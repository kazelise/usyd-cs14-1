"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { PlusIcon, SearchIcon, SurveyIcon, UsersIcon } from "@/components/icons";
import { useLocale } from "@/components/locale-provider";
import type { Locale } from "@/lib/i18n";

interface Survey {
  id: number;
  title: string;
  status: string;
  share_code: string;
  num_groups: number;
  created_at: string;
}

function statusClasses(status: string) {
  if (status === "published") return "status-pill status-pill-published";
  if (status === "closed") return "status-pill status-pill-closed";
  return "status-pill status-pill-draft";
}

function dateLocaleTag(locale: Locale) {
  if (locale === "zh") return "zh-CN";
  if (locale === "ar") return "ar";
  return "en";
}

function formatDate(date: string, locale: Locale) {
  return new Date(date).toLocaleDateString(dateLocaleTag(locale), {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function normaliseStatusFilter(value: string | null) {
  return value === "draft" || value === "published" || value === "closed" ? value : "";
}

function statusLabel(status: string, text: { draft: string; published: string; closed: string }) {
  if (status === "published") return text.published;
  if (status === "closed") return text.closed;
  return text.draft;
}

function SurveysPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { locale } = useLocale();
  const [surveys, setSurveys] = useState<Survey[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const text =
    locale === "zh"
      ? {
          loading: "正在加载问卷",
          title: "问卷工作台",
          subtitle: "创建、发布并检查面向 client 演示的研究问卷。",
          statusFilter: "状态",
          allStatuses: "全部状态",
          draft: "草稿",
          closed: "已关闭",
          titleOrCode: "标题或分享码",
          searchPlaceholder: "按标题或分享码搜索",
          showing: (shown: number, total: number) => `显示 ${shown}/${total} 份问卷`,
          clearFilters: "清除筛选",
          total: "问卷总数",
          published: "已发布",
          drafts: "草稿",
          variants: "分组版本",
          configuredGroups: "个已配置分组",
          singleGroup: "单组实验",
          created: "创建于",
          newSurvey: "新建问卷",
          newSurveyCopy: "从空白草稿开始，配置平台样式、帖子、指标和分组变化。",
          noMatching: "没有匹配的问卷",
          noSurveys: "还没有问卷",
          adjustFilters: "调整搜索词或切换筛选条件以查看更多实验。",
          emptyCopy: "创建你的第一份问卷，开始搭建面向参与者的帖子信息流并记录互动。",
          createSurvey: "新建问卷",
        }
      : {
          loading: "Loading surveys",
          title: "Survey Workspace",
          subtitle: "Create, publish, and review client-ready research studies.",
          statusFilter: "Status",
          allStatuses: "All statuses",
          draft: "Draft",
          closed: "Closed",
          titleOrCode: "Title or share code",
          searchPlaceholder: "Search by title or share code",
          showing: (shown: number, total: number) => `Showing ${shown} of ${total} surveys`,
          clearFilters: "Clear filters",
          total: "Total surveys",
          published: "Published",
          drafts: "Drafts",
          variants: "Group variants",
          configuredGroups: "configured groups",
          singleGroup: "Single-group study",
          created: "Created",
          newSurvey: "New Survey",
          newSurveyCopy: "Start from a blank draft and configure platform style, posts, metrics, and group variations.",
          noMatching: "No matching surveys",
          noSurveys: "No surveys yet",
          adjustFilters: "Adjust your search or switch filters to view more studies.",
          emptyCopy: "Create your first survey to start building participant-facing post feeds and tracking engagement.",
          createSurvey: "Create Survey",
        };

  useEffect(() => {
    api.listSurveys()
      .then((res) => setSurveys(res.items))
      .catch(() => router.push("/auth"))
      .finally(() => setLoading(false));
  }, [router]);

  const statusFilter = normaliseStatusFilter(searchParams.get("filter"));
  const searchTerm = search.trim().toLowerCase();
  const hasActiveFilters = Boolean(statusFilter || searchTerm);

  function updateStatusFilter(value: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (value) {
      params.set("filter", value);
    } else {
      params.delete("filter");
    }

    const query = params.toString();
    router.replace(query ? `/admin/surveys?${query}` : "/admin/surveys", { scroll: false });
  }

  function clearFilters() {
    setSearch("");
    router.replace("/admin/surveys", { scroll: false });
  }

  const filteredSurveys = useMemo(() => {
    return surveys.filter((survey) => {
      if (statusFilter && survey.status !== statusFilter) return false;
      if (!searchTerm) return true;
      return (
        survey.title.toLowerCase().includes(searchTerm) ||
        survey.share_code.toLowerCase().includes(searchTerm)
      );
    });
  }, [searchTerm, statusFilter, surveys]);

  const metrics = useMemo(() => {
    const published = surveys.filter((survey) => survey.status === "published").length;
    const drafts = surveys.filter((survey) => survey.status === "draft").length;
    const groupVariants = surveys.reduce((sum, survey) => sum + survey.num_groups, 0);

    return {
      total: surveys.length,
      published,
      drafts,
      groupVariants,
    };
  }, [surveys]);

  if (loading) {
    return <p className="pt-14 text-sm uppercase tracking-[0.24em] text-slate-400">{text.loading}</p>;
  }

  return (
    <div className="flex min-h-[calc(100vh-118px)] min-w-0 flex-col">
      <section className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div className="min-w-0">
          <h1 className="page-title">{text.title}</h1>
          <p className="page-subtitle">{text.subtitle}</p>
        </div>

        <div className="grid w-full gap-3 sm:grid-cols-[180px_minmax(0,1fr)] xl:max-w-[620px]">
          <label className="min-w-0">
            <span className="mb-2 block text-[12px] font-semibold uppercase tracking-[0.18em] text-slate-400">
              {text.statusFilter}
            </span>
            <select
              value={statusFilter}
              onChange={(e) => updateStatusFilter(e.target.value)}
              className="field-input rounded-[18px] bg-white py-2.5"
            >
              <option value="">{text.allStatuses}</option>
              <option value="published">{text.published}</option>
              <option value="draft">{text.draft}</option>
              <option value="closed">{text.closed}</option>
            </select>
          </label>
          <label className="min-w-0">
            <span className="mb-2 block text-[12px] font-semibold uppercase tracking-[0.18em] text-slate-400">
              {text.titleOrCode}
            </span>
            <span className="relative block">
              <SearchIcon className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder={text.searchPlaceholder}
                className="field-input rounded-[18px] bg-white py-2.5 pl-11 pr-4"
              />
            </span>
          </label>
        </div>
      </section>

      <section className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div className="metric-panel">
          <p className="section-kicker">{text.total}</p>
          <p className="metric-value">{metrics.total}</p>
        </div>
        <div className="metric-panel">
          <p className="section-kicker">{text.published}</p>
          <p className="metric-value">{metrics.published}</p>
        </div>
        <div className="metric-panel">
          <p className="section-kicker">{text.drafts}</p>
          <p className="metric-value">{metrics.drafts}</p>
        </div>
        <div className="rounded-[18px] bg-[linear-gradient(135deg,#0f3146_0%,#1f5876_56%,#00a7a0_100%)] px-5 py-4 text-white shadow-[0_24px_48px_rgba(15,49,70,0.2)]">
          <p className="section-kicker text-white/60">{text.variants}</p>
          <p className="metric-value-inverse">{metrics.groupVariants}</p>
        </div>
      </section>

      {hasActiveFilters && filteredSurveys.length > 0 && (
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 rounded-[18px] border border-slate-200 bg-white px-4 py-3">
          <p className="text-[13px] font-medium text-slate-500">{text.showing(filteredSurveys.length, surveys.length)}</p>
          <button
            type="button"
            onClick={clearFilters}
            className="rounded-full border border-slate-200 px-3 py-1.5 text-[13px] font-medium text-[#0f3146] transition hover:border-[#9ddfd8] hover:bg-[#effcfb]"
          >
            {text.clearFilters}
          </button>
        </div>
      )}

      {filteredSurveys.length > 0 && (
        <section className="mt-4 grid flex-1 content-start gap-4">
          <div className="grid auto-rows-fr gap-4 md:grid-cols-2 xl:grid-cols-3">
            {filteredSurveys.map((survey) => (
              <Link
                key={survey.id}
                href={`/admin/surveys/${survey.id}`}
                className="surface-panel flex h-full min-h-[238px] min-w-0 flex-col justify-between p-5 transition hover:-translate-y-1 hover:shadow-[0_30px_60px_rgba(14,37,63,0.10)]"
              >
                <div className="min-w-0">
                  <span className={statusClasses(survey.status)}>{statusLabel(survey.status, text)}</span>
                  <h2 className="mt-6 break-words text-[18px] font-semibold leading-tight tracking-[-0.02em] text-black">
                    {survey.title}
                  </h2>
                  <p className="mt-2 text-[13px] leading-6 text-slate-500">
                    {survey.num_groups > 1 ? `${survey.num_groups} ${text.configuredGroups}` : text.singleGroup}
                  </p>
                </div>

                <div className="flex items-end justify-between gap-4 text-[13px] text-slate-500">
                  <div className="space-y-2">
                    <div className="flex items-center gap-2">
                      <UsersIcon className="h-4 w-4" />
                      <span>{survey.num_groups}</span>
                    </div>
                    {survey.status === "published" && (
                      <div className="break-all rounded-full bg-stone-100 px-3 py-1 font-mono text-xs text-slate-600">
                        /{survey.share_code}
                      </div>
                    )}
                  </div>
                  <span className="text-right">{text.created} {formatDate(survey.created_at, locale)}</span>
                </div>
              </Link>
            ))}

            <Link
              href="/admin/surveys/new"
              className="flex h-full min-h-[238px] flex-col items-center justify-center rounded-[20px] border border-dashed border-[#9ddfd8] bg-[#f7fffe] p-5 text-center transition hover:bg-white hover:shadow-[0_24px_48px_rgba(14,37,63,0.07)]"
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-[16px] bg-[#e8fbfa] text-[#00a7a0]">
                <PlusIcon className="h-5 w-5" />
              </div>
              <p className="mt-4 text-[17px] font-semibold tracking-[-0.04em] text-black">{text.newSurvey}</p>
              <p className="mt-2 max-w-[18rem] text-[13px] leading-6 text-slate-500">
                {text.newSurveyCopy}
              </p>
            </Link>
          </div>
        </section>
      )}

      {filteredSurveys.length === 0 && (
        <section className="surface-panel mt-4 px-8 py-12 text-center">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-[22px] bg-[#e8fbfa] text-[#00a7a0]">
            <SurveyIcon className="h-7 w-7" />
          </div>
          <h2 className="mt-6 text-3xl font-semibold tracking-[-0.04em] text-black">
            {hasActiveFilters ? text.noMatching : text.noSurveys}
          </h2>
          <p className="mx-auto mt-3 max-w-lg text-sm leading-7 text-slate-500">
            {hasActiveFilters
              ? text.adjustFilters
              : text.emptyCopy}
          </p>
          {hasActiveFilters ? (
            <button type="button" onClick={clearFilters} className="secondary-button mt-6 justify-center">
              {text.clearFilters}
            </button>
          ) : (
            <Link href="/admin/surveys/new" className="primary-button mt-6 gap-2">
              <PlusIcon className="h-4 w-4" />
              {text.createSurvey}
            </Link>
          )}
        </section>
      )}
    </div>
  );
}

export default function SurveysPage() {
  return (
    <Suspense fallback={<p className="pt-14 text-sm uppercase tracking-[0.24em] text-slate-400">Loading surveys</p>}>
      <SurveysPageContent />
    </Suspense>
  );
}
