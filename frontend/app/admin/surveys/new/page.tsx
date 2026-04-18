"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { CheckCircleIcon, SurveyIcon } from "@/components/icons";

const defaults = [
  "Gaze tracking is enabled for new surveys",
  "Click tracking is enabled for participant interactions",
  "Calibration is required before the feed begins",
];

export default function NewSurveyPage() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [numGroups, setNumGroups] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const survey = await api.createSurvey({
        title,
        description: description || null,
        num_groups: numGroups,
        gaze_tracking_enabled: true,
        click_tracking_enabled: true,
        calibration_enabled: true,
      });
      router.push(`/admin/surveys/${survey.id}?unsaved=1`);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid min-h-[calc(100vh-118px)] items-stretch gap-5 xl:grid-cols-[minmax(0,1fr)_260px]">
      <section className="surface-panel flex h-full min-h-[calc(100vh-118px)] flex-col px-6 py-6 md:px-7 md:py-7">
        <p className="section-kicker">Create Survey</p>
        <h1 className="page-title mt-3">Start a new research study</h1>
        <p className="section-copy mt-3 max-w-2xl">
          Define the survey title, add a short internal summary, and choose how many participant groups should be
          available before you begin adding article-based post cards.
        </p>

        <form onSubmit={handleCreate} className="mt-7 flex flex-1 flex-col">
          <div className="space-y-4">
            <div>
              <label className="mb-2 block text-[14px] font-medium text-slate-600">Survey title</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="field-input"
                placeholder="e.g. Social Media Trust Study"
                required
              />
            </div>

            <div>
              <label className="mb-2 block text-[14px] font-medium text-slate-600">Internal description</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="field-textarea min-h-[162px]"
                rows={5}
                placeholder="Describe the study objective, target audience, or research notes for your team."
              />
            </div>

            <div>
              <label className="mb-2 block text-[14px] font-medium text-slate-600">Number of A/B groups</label>
              <select
                value={numGroups}
                onChange={(e) => setNumGroups(Number(e.target.value))}
                className="field-input appearance-none"
              >
                <option value={1}>1 group · no A/B testing</option>
                <option value={2}>2 groups</option>
                <option value={3}>3 groups</option>
                <option value={4}>4 groups</option>
              </select>
              <p className="mt-2 text-[13px] leading-6 text-slate-500">
                {numGroups > 1
                  ? "Participants will be randomly assigned to a configured group when they open the study link."
                  : "All participants will view the same post feed and engagement values."}
              </p>
            </div>

            {error && <p className="rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>}
          </div>

          <div className="mt-auto pt-8">
            <div className="flex flex-col gap-3 sm:flex-row">
            <button type="submit" disabled={loading} className="primary-button min-w-[148px]">
              {loading ? "Creating..." : "Create Survey"}
            </button>
            <button type="button" onClick={() => router.push("/admin/surveys")} className="secondary-button">
              Back to Dashboard
            </button>
            </div>
          </div>
        </form>
      </section>

      <aside className="grid h-full gap-5 xl:grid-rows-[minmax(0,1fr)_minmax(0,1fr)]">
        <div className="surface-panel flex h-full flex-col px-5 py-5">
          <div className="flex h-10 w-10 items-center justify-center rounded-[14px] bg-black text-white">
            <SurveyIcon className="h-4 w-4" />
          </div>
          <p className="section-title mt-4">Workspace defaults</p>
          <div className="mt-4 space-y-4">
            {defaults.map((item) => (
              <div key={item} className="flex items-start gap-3">
                <CheckCircleIcon className="mt-0.5 h-4 w-4 shrink-0 text-black" />
                <p className="text-[14px] leading-7 text-slate-500">{item}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="surface-panel-soft flex h-full flex-col px-5 py-5">
          <p className="section-kicker">After creation</p>
          <div className="mt-4 space-y-4 text-[14px] leading-7 text-slate-500">
            <p>1. Paste article URLs to generate post cards automatically.</p>
            <p>2. Adjust title overrides, likes, comments, and shares for each post.</p>
            <p>3. Configure which participant groups can view each post before publishing.</p>
          </div>
        </div>
      </aside>
    </div>
  );
}