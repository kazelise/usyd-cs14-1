"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";
import { ChartIcon, PlusIcon, SearchIcon, SurveyIcon, UsersIcon } from "@/components/icons";

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

function formatDate(date: string) {
  return new Date(date).toLocaleDateString("en-AU", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function SurveysPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [surveys, setSurveys] = useState<Survey[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listSurveys()
      .then((res) => setSurveys(res.items))
      .catch(() => router.push("/auth"))
      .finally(() => setLoading(false));
  }, [router]);

  const filter = searchParams.get("filter");

  const filteredSurveys = useMemo(() => {
    return surveys.filter((survey) => {
      if (filter && survey.status !== filter) return false;
      const needle = search.trim().toLowerCase();
      if (!needle) return true;
      return (
        survey.title.toLowerCase().includes(needle) ||
        survey.share_code.toLowerCase().includes(needle)
      );
    });
  }, [filter, search, surveys]);

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
    return <p className="pt-14 text-sm uppercase tracking-[0.24em] text-slate-400">Loading surveys</p>;
  }

  return (
    <div className="flex min-h-[calc(100vh-118px)] flex-col">
      <section className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <h1 className="page-title">My Surveys</h1>
          <p className="page-subtitle">Manage and track your active research projects.</p>
        </div>

        <div className="relative w-full max-w-[380px]">
          <SearchIcon className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search projects..."
            className="field-input rounded-[18px] bg-white py-2 pl-11 pr-4"
          />
        </div>
      </section>

      <section className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <div className="metric-panel">
          <p className="section-kicker">Total surveys</p>
          <p className="metric-value">{metrics.total}</p>
        </div>
        <div className="metric-panel">
          <p className="section-kicker">Published</p>
          <p className="metric-value">{metrics.published}</p>
        </div>
        <div className="metric-panel">
          <p className="section-kicker">Drafts</p>
          <p className="metric-value">{metrics.drafts}</p>
        </div>
        <div className="rounded-[18px] bg-[linear-gradient(135deg,#0f3146_0%,#1f5876_56%,#00a7a0_100%)] px-5 py-4 text-white shadow-[0_24px_48px_rgba(15,49,70,0.2)]">
          <p className="section-kicker text-white/60">Group variants</p>
          <p className="metric-value-inverse">{metrics.groupVariants}</p>
        </div>
      </section>

      <section className="mt-4 grid flex-1 content-start gap-4">
        <div className="grid auto-rows-fr gap-4 xl:grid-cols-3">
          {filteredSurveys.map((survey) => (
            <Link
              key={survey.id}
              href={`/admin/surveys/${survey.id}`}
              className="surface-panel flex h-full min-h-[238px] flex-col justify-between p-5 transition hover:-translate-y-1 hover:shadow-[0_30px_60px_rgba(14,37,63,0.10)]"
            >
              <div>
                <span className={statusClasses(survey.status)}>{survey.status}</span>
                <h2 className="mt-6 max-w-[16ch] text-[18px] font-semibold leading-tight tracking-[-0.05em] text-black">
                  {survey.title}
                </h2>
                <p className="mt-2 text-[13px] leading-6 text-slate-500">
                  {survey.num_groups > 1 ? `${survey.num_groups} configured groups` : "Single-group study"}
                </p>
              </div>

              <div className="flex items-end justify-between gap-4 text-[13px] text-slate-500">
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <UsersIcon className="h-4 w-4" />
                    <span>{survey.num_groups}</span>
                  </div>
                  {survey.status === "published" && (
                    <div className="rounded-full bg-stone-100 px-3 py-1 font-mono text-xs text-slate-600">
                      /{survey.share_code}
                    </div>
                  )}
                </div>
                <span>Created {formatDate(survey.created_at)}</span>
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
            <p className="mt-4 text-[17px] font-semibold tracking-[-0.04em] text-black">New Survey</p>
            <p className="mt-2 max-w-[18rem] text-[13px] leading-6 text-slate-500">
              Start from a blank draft and configure posts, metrics, and group variations.
            </p>
          </Link>
        </div>
      </section>

      {filteredSurveys.length === 0 && (
        <section className="surface-panel mt-4 px-8 py-12 text-center">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-[22px] bg-[#e8fbfa] text-[#00a7a0]">
            <SurveyIcon className="h-7 w-7" />
          </div>
          <h2 className="mt-6 text-3xl font-semibold tracking-[-0.04em] text-black">
            {search || filter ? "No matching surveys" : "No surveys yet"}
          </h2>
          <p className="mx-auto mt-3 max-w-lg text-sm leading-7 text-slate-500">
            {search || filter
              ? "Adjust your search or switch filters to view more studies."
              : "Create your first survey to start building participant-facing post feeds and tracking engagement."}
          </p>
          {!search && !filter && (
            <Link href="/admin/surveys/new" className="primary-button mt-6 gap-2">
              <PlusIcon className="h-4 w-4" />
              Create Survey
            </Link>
          )}
        </section>
      )}

      <section className="surface-panel mt-4 flex flex-col gap-4 px-5 py-5 xl:flex-row xl:items-center xl:justify-between">
        <div className="flex items-start gap-4">
          <div className="flex h-11 w-11 items-center justify-center rounded-[14px] bg-[#e8fbfa] text-[#00a7a0]">
            <ChartIcon className="h-4 w-4" />
          </div>
          <div>
            <p className="section-title">AI Assistant Analysis</p>
            <p className="mt-2 max-w-3xl text-[13px] leading-6 text-slate-500">
              Your most active published study is trending above the workspace average. Use the survey detail view to
              review comment activity, group visibility, and engagement totals before publishing the next draft.
            </p>
          </div>
        </div>
        <Link href="/admin/surveys" className="secondary-button min-w-[160px]">
          View Trends
        </Link>
      </section>
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
