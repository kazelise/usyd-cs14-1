"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { t, type Locale } from "@/lib/i18n";

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
        const s = await api.getPublicSurvey(shareCode as string);
        setMeta(s);
      } catch (e: any) {
        setError(e.message || "Survey not found");
      } finally {
        setLoading(false);
      }
    })();
  }, [shareCode]);

  if (loading) return <div className="min-h-screen flex items-center justify-center text-gray-400">Loading...</div>;
  if (error) return <div className="min-h-screen flex items-center justify-center text-red-500">{error}</div>;
  if (!meta) return null;

  const duration = 8; // default estimate; could be made configurable

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="max-w-xl w-full bg-white border rounded-lg shadow p-6">
        <div className="flex items-center justify-between">
          <h1 className="text-xl font-semibold">{meta.title}</h1>
          <div className="text-sm text-gray-500 flex items-center gap-2">
            <span>{t(locale, "language")}:</span>
            <select
              className="border px-2 py-1 rounded"
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

        {meta.description && <p className="text-gray-600 mt-2">{meta.description}</p>}
        <p className="text-gray-500 mt-1">{t(locale, "subtitle")}</p>

        <div className="mt-4 bg-gray-50 rounded p-3 text-sm text-gray-600">
          <span className="font-medium">{t(locale, "estTime")}:</span> {duration} {t(locale, "minutes")}
        </div>

        <p className="text-xs text-gray-500 mt-4">{t(locale, "consent")}</p>

        <button
          className="mt-6 w-full bg-blue-600 text-white rounded-md py-2 font-medium hover:bg-blue-700"
          onClick={() => router.push(`/survey/${shareCode}?lang=${locale}`)}
        >
          {t(locale, "start")}
        </button>
      </div>
    </div>
  );
}

