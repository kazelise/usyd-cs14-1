"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useLocale } from "@/components/locale-provider";
import { t, type Locale } from "@/lib/i18n";
import { CheckCircleIcon, GlobeIcon, SurveyIcon } from "@/components/icons";

export default function StartScreen() {
  const { shareCode } = useParams();
  const router = useRouter();
  const { locale, setLocale } = useLocale();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [meta, setMeta] = useState<{ title: string; description?: string } | null>(null);

  useEffect(() => {
    const saved = typeof window !== "undefined" ? (localStorage.getItem("locale") as Locale | null) : null;
    if (saved === "en" || saved === "zh") setLocale(saved);

    (async () => {
      try {
        const survey = await api.getPublicSurvey(shareCode as string);
        setMeta(survey);
      } catch (e: any) {
        setError(e.message || t(saved === "zh" ? "zh" : "en", "surveyNotFound"));
      } finally {
        setLoading(false);
      }
    })();
  }, [setLocale, shareCode]);

  if (loading) {
    return <div className="flex min-h-screen items-center justify-center text-sm uppercase tracking-[0.24em] text-slate-400">{t(locale, "loadingStudy")}</div>;
  }

  if (error) {
    return <div className="flex min-h-screen items-center justify-center px-6 text-center text-red-500">{error}</div>;
  }

  if (!meta) return null;

  const duration = 8;

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(0,167,160,0.10),_transparent_26%),linear-gradient(180deg,#f7fafc_0%,#edf3f8_100%)] px-4 py-8 lg:px-8 lg:py-10">
      <div className="mx-auto max-w-6xl">
        <div className="mb-4 flex items-center justify-between rounded-[16px] border border-slate-200 bg-white/80 px-5 py-3 text-[13px] text-slate-500 backdrop-blur">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[#0f3146] text-white">
              <SurveyIcon className="h-4 w-4" />
            </div>
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">{t(locale, "surveyExperience")}</p>
              <p className="font-semibold text-[#163047]">{t(locale, "researchPlatform")}</p>
            </div>
          </div>
          <div className="flex items-center gap-3 rounded-full border border-slate-200 bg-slate-50 px-4 py-2">
            <GlobeIcon className="h-4 w-4 text-slate-500" />
            <select
              className="bg-transparent text-sm text-slate-500 outline-none"
              value={locale}
              onChange={(e) => {
                const next = e.target.value as Locale;
                setLocale(next);
              }}
            >
              <option value="en">English</option>
              <option value="zh">中文</option>
            </select>
          </div>
        </div>

        <div className="surface-panel overflow-hidden lg:grid lg:grid-cols-[1.15fr_0.85fr]">
          <section className="border-b border-slate-200 bg-[linear-gradient(135deg,#10324a_0%,#174867_48%,#0f3146_100%)] px-8 py-10 text-white lg:border-b-0 lg:border-r lg:px-12 lg:py-12">
            <p className="text-[12px] font-semibold uppercase tracking-[0.24em] text-[#8ddfda]">{t(locale, "participantStudy")}</p>
            <h1 className="mt-4 max-w-[14ch] text-[36px] font-semibold leading-tight tracking-[-0.06em] text-white md:text-[44px]">
              {meta.title}
            </h1>
            {meta.description && <p className="mt-5 max-w-2xl text-[15px] leading-8 text-white/74">{meta.description}</p>}

            <div className="mt-10 grid gap-4 md:grid-cols-3">
              <div className="rounded-[18px] border border-white/10 bg-white/8 px-5 py-5">
                <p className="text-[11px] uppercase tracking-[0.22em] text-white/45">{t(locale, "estTime")}</p>
                <p className="mt-3 text-[28px] font-semibold tracking-[-0.04em] text-white">
                  {duration} {t(locale, "minutes")}
                </p>
              </div>
              <div className="rounded-[18px] border border-white/10 bg-white/8 px-5 py-5">
                <p className="text-[11px] uppercase tracking-[0.22em] text-white/45">{t(locale, "format")}</p>
                <p className="mt-3 text-[15px] font-medium leading-7 text-white">{t(locale, "formatValue")}</p>
              </div>
              <div className="rounded-[18px] border border-white/10 bg-white/8 px-5 py-5">
                <p className="text-[11px] uppercase tracking-[0.22em] text-white/45">{t(locale, "tracking")}</p>
                <p className="mt-3 text-[15px] font-medium leading-7 text-white">{t(locale, "trackingValue")}</p>
              </div>
            </div>
          </section>

          <section className="bg-[#fbfdff] px-8 py-10 lg:px-10 lg:py-12">
            <div>
              <p className="section-kicker text-[#00a7a0]">{t(locale, "beforeBegin")}</p>
              <p className="section-title mt-3 md:text-[24px]">{t(locale, "participantInstructions")}</p>
              <p className="mt-3 text-[14px] leading-7 text-slate-500">{t(locale, "participantInstructionsCopy")}</p>
            </div>

            <div className="mt-8 space-y-4">
              {[t(locale, "subtitle"), t(locale, "consent"), t(locale, "desktopCamera")].map((item) => (
                <div key={item} className="rounded-[18px] border border-slate-200 bg-white px-4 py-4 shadow-[0_10px_24px_rgba(14,37,63,0.04)]">
                  <div className="grid grid-cols-[20px_minmax(0,1fr)] items-start gap-3">
                    <div className="mt-[2px] flex h-5 w-5 items-center justify-center rounded-full bg-[#e8fbfa] text-[#00a7a0]">
                      <CheckCircleIcon className="h-3 w-3" />
                    </div>
                    <p className="text-[14px] leading-7 text-slate-600">{item}</p>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-8 rounded-[18px] border border-slate-200 bg-slate-50 px-5 py-4">
              <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">{t(locale, "expectedSession")}</p>
              <p className="mt-2 text-[14px] leading-7 text-slate-600">{t(locale, "expectedSessionCopy")}</p>
            </div>

            <button
              className="primary-button mt-8 w-full py-3.5 text-[14px]"
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
