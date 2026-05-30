"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { useLocale } from "@/components/locale-provider";

/**
 * Stable admin entry point for a researcher dry-run of any draft / published
 * survey. The URL is keyed on the survey id so it never breaks across
 * share-code rotations (issue #62), and every reopen starts fresh:
 *
 *   1. Resolve share_code (so the runner URL is correct).
 *   2. DELETE prior preview responses (server-side wipe).
 *   3. Clear preview-scoped localStorage keys (token/completion/answer cache)
 *      so the runner does NOT resume an in-flight preview from a previous
 *      open.
 *   4. Redirect to the runner with ?preview=1. The runner already skips
 *      calibration for previews, so consent isn't needed.
 */
export default function TestSessionLauncher() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();
  const { locale } = useLocale();
  const [error, setError] = useState<string>("");

  useEffect(() => {
    const surveyId = Number(params.id);
    if (!Number.isFinite(surveyId)) {
      setError("Invalid survey id");
      return;
    }

    const group = searchParams.get("group") ?? "";
    // Pin the launch locale to whatever was passed in, otherwise fall back
    // to the researcher's current locale so the preview reflects what the
    // researcher is reading right now.
    const lang = searchParams.get("lang") ?? locale;

    let cancelled = false;
    (async () => {
      try {
        const survey = await api.getSurvey(surveyId);
        if (cancelled) return;
        const shareCode: string = survey.share_code;

        // Wipe server-side preview rows so analytics + counts on the next
        // open look at a clean slate.
        try {
          await api.deletePreviewResponses(surveyId);
        } catch (e) {
          // Non-fatal: a missing endpoint or transient error shouldn't block
          // the researcher from at least seeing their draft.
          console.warn("test-session: deletePreviewResponses failed", e);
        }

        // Drop any preview-scoped local state so the runner can't resume.
        // Keys created by the runner look like:
        //   pt:{shareCode}:preview:{scope}:{locale}
        //   completed:{shareCode}:preview:{scope}:{locale}
        //   answers:{response_id}:{participant_token}
        try {
          const prefixes = [
            `pt:${shareCode}:preview:`,
            `completed:${shareCode}:preview:`,
          ];
          for (let i = localStorage.length - 1; i >= 0; i--) {
            const key = localStorage.key(i);
            if (!key) continue;
            if (prefixes.some((p) => key.startsWith(p)) || key.startsWith("answers:")) {
              localStorage.removeItem(key);
            }
          }
        } catch {
          // localStorage may be unavailable (private mode, etc.) — non-fatal.
        }

        const qs = new URLSearchParams({ preview: "1", lang });
        if (group) qs.set("group", group);
        // Use replace() so the back button skips this launcher and returns
        // the researcher to the admin detail page.
        router.replace(`/survey/${encodeURIComponent(shareCode)}?${qs.toString()}`);
      } catch (e: any) {
        if (cancelled) return;
        setError(e?.message || "Failed to start test session");
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [params.id, searchParams, locale, router]);

  return (
    <div className="flex min-h-screen items-center justify-center px-6">
      <div className="surface-panel max-w-md px-8 py-10 text-center">
        {error ? (
          <>
            <p className="text-sm font-semibold text-red-600">{error}</p>
            <button
              type="button"
              onClick={() => router.back()}
              className="secondary-button mt-6 px-4 py-2 text-xs"
            >
              {locale === "zh" ? "返回" : "Back"}
            </button>
          </>
        ) : (
          <p className="text-sm uppercase tracking-[0.18em] text-slate-400">
            {locale === "zh" ? "正在启动测试会话…" : "Launching test session…"}
          </p>
        )}
      </div>
    </div>
  );
}
