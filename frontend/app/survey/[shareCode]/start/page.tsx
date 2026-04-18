"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { t, type Locale } from "@/lib/i18n";
import { CheckCircleIcon, GlobeIcon, SurveyIcon } from "@/components/icons";

export default function StartScreen() {
  const { shareCode } = useParams();
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [locale, setLocale] = useState<Locale>("en");
  const [meta, setMeta] = useState<{ title: string; description?: string } | null>(null);

  useEffect(() => {
    const saved = typeof window !== "undefined" ? (localStorage.getItem("locale") as Locale | null) : null;
    if (saved === "en" || saved === "zh") setLocale(saved);

    (async () => {
      try {
        const survey = await api.getPublicSurvey(shareCode as string);
        setMeta(survey);
      } catch (e: any) {
        setError(e.message || "Survey not found");
      } finally {
        setLoading(false);
      }
    })();
  }, [shareCode]);

  if (loading) {
    return <div className="flex min-h-screen items-center justify-center text-sm uppercase tracking-[0.24em] text-slate-400">Loading study</div>;
  }

  if (error) {
    return <div className="flex min-h-screen items-center justify-center px-6 text-center text-red-500">{error}</div>;
  }

  if (!meta) return null;

  const duration = 8;

  return (
    <div className="min-h-screen px-4 py-8 lg:px-8 lg:py-10">
      <div className="mx-auto max-w-5xl">
        <div className="surface-panel overflow-hidden lg:grid lg:grid-cols-[1.05fr_0.95fr]">
          <section className="bg-black px-8 py-10 text-white lg:px-10 lg:py-12">
            <div className="flex h-12 w-12 items-center justify-center rounded-[16px] bg-white/10">
              <SurveyIcon className="h-5 w-5" />
            </div>
            <p className="mt-8 text-[12px] font-semibold uppercase tracking-[0.24em] text-white/55">Participant study</p>
            <h1 className="mt-4 text-[34px] font-semibold tracking-[-0.06em] text-white md:text-[40px]">{meta.title}</h1>
            {meta.description && <p className="mt-5 max-w-xl text-[14px] leading-7 text-white/70">{meta.description}</p>}

            <div className="mt-10 grid gap-4 md:grid-cols-2">
              <div className="rounded-[18px] border border-white/10 bg-white/5 px-5 py-5">
                <p className="text-[12px] uppercase tracking-[0.22em] text-white/45">{t(locale, "estTime")}</p>
                <p className="mt-3 text-[28px] font-semibold tracking-[-0.04em]">
                  {duration} {t(locale, "minutes")}
                </p>
              </div>
              <div className="rounded-[18px] border border-white/10 bg-white/5 px-5 py-5">
                <p className="text-[12px] uppercase tracking-[0.22em] text-white/45">Interaction</p>
                <p className="mt-3 text-[16px] font-medium leading-7 text-white">Browse, like, comment, and click naturally</p>
              </div>
            </div>
          </section>

          <section className="px-8 py-10 lg:px-10 lg:py-12">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="section-kicker">Before you begin</p>
                <p className="section-title mt-3 md:text-[24px]">Study instructions</p>
              </div>
              <div className="flex items-center gap-3 rounded-full border bg-stone-50 px-4 py-2">
                <GlobeIcon className="h-4 w-4 text-slate-500" />
                <select
                  className="bg-transparent text-sm text-slate-500 outline-none"
                  value={locale}
                  onChange={(e) => {
                    const next = e.target.value as Locale;
                    setLocale(next);
                    localStorage.setItem("locale", next);
                  }}
                >
                  <option value="en">English</option>
                  <option value="zh">中文</option>
                </select>
              </div>
            </div>

            <div className="mt-8 space-y-4">
              {[t(locale, "subtitle"), t(locale, "consent"), "Use a desktop browser and allow camera access if prompted."].map((item) => (
                <div key={item} className="flex gap-3 rounded-[18px] border bg-stone-50 px-4 py-4">
                  <CheckCircleIcon className="mt-0.5 h-4 w-4 text-black" />
                  <p className="text-[14px] leading-7 text-slate-500">{item}</p>
                </div>
              ))}
            </div>

            <button
              className="primary-button mt-8 w-full py-3"
              onClick={() => router.push(`/survey/${shareCode}?lang=${locale}`)}
            >
              {t(locale, "start")}
            </button>
          </section>
        </div>
      </div>
    </div>
  );
}