"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { CheckCircleIcon, SurveyIcon } from "@/components/icons";
import { CalibrationExperience } from "@/components/calibration-experience";

export default function NewSurveyPage() {
  const router = useRouter();
  const locale: string = "en";
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [numGroups, setNumGroups] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showCalibrationPreview, setShowCalibrationPreview] = useState(false);
  const text =
    locale === "zh"
      ? {
          closePreview: "关闭预览",
          createSurvey: "新建问卷",
          title: "开始新的研究实验",
          subtitle: "先定义问卷标题、添加内部说明，并选择参与者分组数量，然后再开始添加基于文章的帖子卡片。",
          surveyTitle: "问卷标题",
          surveyTitlePlaceholder: "例如：社交媒体信任实验",
          internalDescription: "内部说明",
          internalDescriptionPlaceholder: "为你的团队记录研究目标、目标受众或实验备注。",
          numGroups: "A/B 分组数量",
          oneGroup: "1 组 · 不做 A/B 测试",
          assignedRandomly: "参与者打开实验链接时会被随机分配到已配置分组。",
          sameFeed: "所有参与者都会看到相同的帖子信息流和互动数值。",
          creating: "创建中...",
          back: "返回后台",
          workspaceDefaults: "工作区默认设置",
          defaults: [
            "新建问卷默认开启眼动追踪",
            "默认记录参与者点击行为",
            "进入信息流前需要完成校准",
          ],
          afterCreation: "创建之后",
          steps: [
            "1. 粘贴文章链接，根据文章 metadata 创建帖子卡片。",
            "2. 为每条帖子调整标题覆盖、点赞、评论和分享数。",
            "3. 在发布前设置每条帖子对哪些参与者分组可见。",
          ],
          webcamTools: "摄像头工具",
          webcamCopy: "预览参与者在进入问卷信息流前会看到的校准流程。",
          previewCalibration: "预览校准",
          previewCopy: "测试 9 点虹膜追踪流程",
          irisDemo: "眼动追踪演示",
          irisDemoCopy: "实时人脸网格和注视可视化",
        }
      : {
          closePreview: "Close Preview",
          createSurvey: "Create Survey",
          title: "Start a new research study",
          subtitle: "Define the survey title, add a short internal summary, and choose how many participant groups should be available before you begin adding article-based post cards.",
          surveyTitle: "Survey title",
          surveyTitlePlaceholder: "e.g. Social Media Trust Study",
          internalDescription: "Internal description",
          internalDescriptionPlaceholder: "Describe the study objective, target audience, or research notes for your team.",
          numGroups: "Number of A/B groups",
          oneGroup: "1 group · no A/B testing",
          assignedRandomly: "Participants will be randomly assigned to a configured group when they open the study link.",
          sameFeed: "All participants will view the same post feed and engagement values.",
          creating: "Creating...",
          back: "Back to Dashboard",
          workspaceDefaults: "Workspace defaults",
          defaults: [
            "Gaze tracking is enabled for new surveys",
            "Click tracking is enabled for participant interactions",
            "Calibration is required before the feed begins",
          ],
          afterCreation: "After creation",
          steps: [
            "1. Paste article URLs to create post cards from article metadata.",
            "2. Adjust title overrides, likes, comments, and shares for each post.",
            "3. Configure which participant groups can view each post before publishing.",
          ],
          webcamTools: "Webcam Tools",
          webcamCopy: "Preview the calibration experience that participants will see before the survey feed.",
          previewCalibration: "Preview Calibration",
          previewCopy: "Test the 9-point iris tracking flow",
          irisDemo: "Iris Tracking Demo",
          irisDemoCopy: "Real-time face mesh & gaze visualization",
        };

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

  // Full-screen calibration preview
  if (showCalibrationPreview) {
    return (
      <div className="fixed inset-0 z-[320]">
        <CalibrationExperience
          responseId={0}
          onComplete={() => setShowCalibrationPreview(false)}
        />
        <button
          onClick={() => setShowCalibrationPreview(false)}
          className="fixed right-6 top-6 z-[340] rounded-full border border-white/20 bg-slate-900/80 px-4 py-2 text-sm text-white backdrop-blur hover:bg-slate-800"
        >
          ✕ {text.closePreview}
        </button>
      </div>
    );
  }

  return (
    <div className="grid min-h-[calc(100vh-118px)] items-stretch gap-5 xl:grid-cols-[minmax(0,1fr)_260px]">
      <section className="surface-panel flex h-full min-h-[calc(100vh-118px)] flex-col px-6 py-6 md:px-7 md:py-7">
        <p className="section-kicker">{text.createSurvey}</p>
        <h1 className="page-title mt-3">{text.title}</h1>
        <p className="section-copy mt-3 max-w-2xl">
          {text.subtitle}
        </p>

        <form onSubmit={handleCreate} className="mt-7 flex flex-1 flex-col">
          <div className="space-y-4">
            <div>
              <label className="mb-2 block text-[14px] font-medium text-slate-600">{text.surveyTitle}</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="field-input"
                placeholder={text.surveyTitlePlaceholder}
                required
              />
            </div>

            <div>
              <label className="mb-2 block text-[14px] font-medium text-slate-600">{text.internalDescription}</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="field-textarea min-h-[162px]"
                rows={5}
                placeholder={text.internalDescriptionPlaceholder}
              />
            </div>

            <div>
              <label className="mb-2 block text-[14px] font-medium text-slate-600">{text.numGroups}</label>
              <select
                value={numGroups}
                onChange={(e) => setNumGroups(Number(e.target.value))}
                className="field-input appearance-none"
              >
                <option value={1}>{text.oneGroup}</option>
                <option value={2}>2 groups</option>
                <option value={3}>3 groups</option>
                <option value={4}>4 groups</option>
              </select>
              <p className="mt-2 text-[13px] leading-6 text-slate-500">
                {numGroups > 1
                  ? text.assignedRandomly
                  : text.sameFeed}
              </p>
            </div>

            {error && <p className="rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>}
          </div>

          <div className="mt-auto pt-8">
            <div className="flex flex-col gap-3 sm:flex-row">
            <button type="submit" disabled={loading} className="primary-button min-w-[148px]">
              {loading ? text.creating : text.createSurvey}
            </button>
            <button type="button" onClick={() => router.push("/admin/surveys")} className="secondary-button">
              {text.back}
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
          <p className="section-title mt-4">{text.workspaceDefaults}</p>
          <div className="mt-4 space-y-4">
            {text.defaults.map((item) => (
              <div key={item} className="flex items-start gap-3">
                <CheckCircleIcon className="mt-0.5 h-4 w-4 shrink-0 text-black" />
                <p className="text-[14px] leading-7 text-slate-500">{item}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="surface-panel-soft flex h-full flex-col px-5 py-5">
          <p className="section-kicker">{text.afterCreation}</p>
          <div className="mt-4 space-y-4 text-[14px] leading-7 text-slate-500">
            {text.steps.map((step) => (
              <p key={step}>{step}</p>
            ))}
          </div>
        </div>

        <div className="surface-panel flex h-full flex-col px-5 py-5">
          <p className="section-kicker">{text.webcamTools}</p>
          <p className="mt-3 text-[13px] leading-6 text-slate-500">
            {text.webcamCopy}
          </p>
          <div className="mt-4 space-y-3">
            <button
              type="button"
              onClick={() => setShowCalibrationPreview(true)}
              className="flex w-full items-center gap-3 rounded-[14px] border border-slate-200 bg-white px-4 py-3 text-left text-sm font-medium text-slate-700 transition hover:border-cyan-300 hover:bg-cyan-50"
            >
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-cyan-100 text-cyan-700">🎯</span>
              <div>
                <p>{text.previewCalibration}</p>
                <p className="text-[11px] font-normal text-slate-400">{text.previewCopy}</p>
              </div>
            </button>
            <a
              href="/demo-tracking"
              target="_blank"
              className="flex w-full items-center gap-3 rounded-[14px] border border-slate-200 bg-white px-4 py-3 text-left text-sm font-medium text-slate-700 transition hover:border-emerald-300 hover:bg-emerald-50"
            >
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-100 text-emerald-700">👁</span>
              <div>
                <p>{text.irisDemo}</p>
                <p className="text-[11px] font-normal text-slate-400">{text.irisDemoCopy}</p>
              </div>
            </a>
          </div>
        </div>
      </aside>
    </div>
  );
}
