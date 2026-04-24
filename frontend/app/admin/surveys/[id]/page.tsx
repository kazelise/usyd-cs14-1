"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { useLocale } from "@/components/locale-provider";
import { buildTemplateFromSurvey, persistTemplate } from "@/lib/template-library";
import {
  ChartIcon,
  CheckCircleIcon,
  LinkIcon,
  PlusIcon,
  SearchIcon,
  SurveyIcon,
  UsersIcon,
} from "@/components/icons";

async function apiRequest(path: string, options: RequestInit = {}) {
  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!res.ok) throw new Error("Request failed");
  return res.json();
}

interface Post {
  id: number;
  order: number;
  original_url: string;
  fetched_title: string | null;
  fetched_image_url: string | null;
  fetched_source: string | null;
  display_title: string | null;
  display_image_url: string | null;
  display_likes: number;
  display_comments_count: number;
  display_shares: number;
  show_likes: boolean;
  show_comments: boolean;
  show_shares: boolean;
  visible_to_groups: number[] | null;
  comments: { id: number; order: number; author_name: string; text: string }[];
}

interface Survey {
  id: number;
  title: string;
  description?: string | null;
  status: string;
  share_code: string;
  num_groups: number;
  gaze_tracking_enabled?: boolean;
  gaze_interval_ms?: number;
  click_tracking_enabled?: boolean;
  calibration_enabled?: boolean;
  calibration_points?: number;
}

function statusClasses(status: string) {
  if (status === "published") return "status-pill status-pill-published";
  if (status === "closed") return "status-pill status-pill-closed";
  return "status-pill status-pill-draft";
}

function numberInputClass() {
  return "w-24 rounded-[16px] border border-black/10 bg-white px-3 py-2 text-sm text-black outline-none";
}

export default function SurveyEditPage() {
  const router = useRouter();
  const { locale } = useLocale();
  const params = useParams();
  const searchParams = useSearchParams();
  const surveyId = Number(params.id);
  const initialUnsavedDraft = searchParams.get("unsaved") === "1";

  const [survey, setSurvey] = useState<Survey | null>(null);
  const [posts, setPosts] = useState<Post[]>([]);
  const [newUrl, setNewUrl] = useState("");
  const [addingPost, setAddingPost] = useState(false);
  const [error, setError] = useState("");
  const [copiedShare, setCopiedShare] = useState(false);

  const [editingPost, setEditingPost] = useState<number | null>(null);
  const [editLikes, setEditLikes] = useState(0);
  const [editComments, setEditComments] = useState(0);
  const [editShares, setEditShares] = useState(0);
  const [editTitle, setEditTitle] = useState("");

  const [editingGroups, setEditingGroups] = useState<number | null>(null);
  const [groupVisibility, setGroupVisibility] = useState<number[]>([]);
  const [groupOverrides, setGroupOverrides] = useState<
    Record<string, { display_likes: number; display_comments_count: number; display_shares: number }>
  >({});

  const [commentPostId, setCommentPostId] = useState<number | null>(null);
  const [commentAuthor, setCommentAuthor] = useState("");
  const [commentText, setCommentText] = useState("");

  const [stats, setStats] = useState<
    { post_id: number; likes: number; participant_comments: number; shares: number }[] | null
  >(null);
  const [participantCommentsByPost, setParticipantCommentsByPost] = useState<
    Record<number, { id: number; post_id: number; text: string; created_at: string }[]>
  >({});
  const [isUnsavedDraft, setIsUnsavedDraft] = useState(initialUnsavedDraft);
  const [templateSaved, setTemplateSaved] = useState(false);
  const [translationLanguage, setTranslationLanguage] = useState("zh");
  const [translationFile, setTranslationFile] = useState<File | null>(null);
  const [translationBusy, setTranslationBusy] = useState(false);
  const [translationStatus, setTranslationStatus] = useState("");
  const shouldDiscardDraftRef = useRef(initialUnsavedDraft);
  const discardRequestedRef = useRef(false);
  const text =
    locale === "zh"
      ? {
          deleteConfirm: "确定删除这条帖子吗？",
          publishConfirm: "确定发布这份问卷吗？发布后参与者将可以访问。",
          templateName: "模板名称",
          templateSuffix: "模板",
          loading: "正在加载问卷",
          workspace: "问卷工作台",
          subtitle: "在把实验分享给参与者之前，先配置帖子、分组可见性和互动基线数值。",
          templateSaved: "模板已保存",
          saveAsTemplate: "保存为模板",
          linkCopied: "链接已复制",
          copyParticipantLink: "复制参与者链接",
          publishSurvey: "发布问卷",
          saveDraft: "保存草稿",
          postsConfigured: "已配置帖子",
          groupVariants: "分组版本",
          commentThreads: "评论线程",
          visibleCards: "可见卡片",
          addPost: "添加帖子",
          addPostTitle: "粘贴新闻文章链接以创建帖子卡片",
          fetching: "抓取中...",
          articleMetadata: "系统会从文章 metadata 中抓取标题、来源和图片。卡片出现后，你可以继续覆盖每组的数值和评论。",
          untitled: "未命名",
          delete: "删除",
          visibleToGroups: "对以下分组可见：",
          likes: "点赞",
          comments: "评论",
          shares: "分享",
          visibleComments: "可见评论",
          participantResponse: "参与者回应",
          noCommentContent: "该帖子显示了评论数量，但还没有配置任何评论内容。",
          overrideTitle: "覆盖标题",
          saveValues: "保存数值",
          cancel: "取消",
          editNumbers: "编辑数值",
          addComment: "添加评论",
          abGroups: "A/B 分组",
          groupVisibility: "分组可见性",
          saveGroups: "保存分组",
          commenterName: "评论者姓名",
          commentText: "评论内容",
          add: "添加",
          noPosts: "还没有帖子卡片",
          noPostsCopy: "在上方添加第一条文章链接，为这份问卷创建参与者信息流卡片。",
          studySummary: "研究摘要",
          surveyStatus: "问卷状态",
          participantLink: "参与者链接",
          linkAfterPublish: "发布后可获得链接",
          abGroupCount: "A/B 分组",
          checklist: "发布检查清单",
          checklistItems: ["至少添加一张帖子卡片", "检查显示数值和评论内容"],
          checklistSingle: "单组流程已就绪",
          checklistMulti: "确认每条帖子对各分组的可见性",
          observation: "观察",
          observationCopy: "参与者互动会叠加到你预先配置的基线数值之上，因此已发布的信息流会看起来更真实，同时仍保持实验可控。",
          translationsTitle: "翻译文件",
          translationsCopy: "导出翻译模板，填入目标语言后再导入。",
          targetLanguage: "目标语言",
          exportJson: "导出 JSON",
          exportCsv: "导出 CSV",
          chooseTranslationFile: "选择 JSON 或 CSV 文件",
          importFile: "导入文件",
          translationExported: "翻译模板已导出",
          translationImported: "翻译已导入",
          noTranslationFile: "请先选择翻译文件。",
        }
      : {
          deleteConfirm: "Delete this post?",
          publishConfirm: "Publish this survey? Participants will be able to access it.",
          templateName: "Template name",
          templateSuffix: "Template",
          loading: "Loading survey",
          workspace: "Survey Workspace",
          subtitle: "Configure the posts, group visibility, and engagement baselines before sharing the study with participants.",
          templateSaved: "Template Saved",
          saveAsTemplate: "Save as Template",
          linkCopied: "Link copied",
          copyParticipantLink: "Copy participant link",
          publishSurvey: "Publish Survey",
          saveDraft: "Save Draft",
          postsConfigured: "Posts configured",
          groupVariants: "Group variants",
          commentThreads: "Comment threads",
          visibleCards: "Visible cards",
          addPost: "Add Post",
          addPostTitle: "Paste a news article URL to create a post card",
          fetching: "Fetching...",
          articleMetadata: "The platform will fetch the headline, source, and image from the article metadata. You can override numbers and comments for each group after the card appears below.",
          untitled: "Untitled",
          delete: "Delete",
          visibleToGroups: "Visible to groups:",
          likes: "Likes",
          comments: "Comments",
          shares: "Shares",
          visibleComments: "Visible comments",
          participantResponse: "Participant response",
          noCommentContent: "Comment count is visible, but no comment content has been configured for this post.",
          overrideTitle: "Override title",
          saveValues: "Save values",
          cancel: "Cancel",
          editNumbers: "Edit numbers",
          addComment: "Add comment",
          abGroups: "A/B groups",
          groupVisibility: "Group visibility",
          saveGroups: "Save groups",
          commenterName: "Commenter name",
          commentText: "Comment text",
          add: "Add",
          noPosts: "No post cards yet",
          noPostsCopy: "Add the first article URL above to create a participant-facing feed card for this survey.",
          studySummary: "Study summary",
          surveyStatus: "Survey status",
          participantLink: "Participant link",
          linkAfterPublish: "Link available after publish",
          abGroupCount: "A/B groups",
          checklist: "Publishing checklist",
          checklistItems: ["Add at least one post card", "Review display counts and comment content"],
          checklistSingle: "Single-group flow is ready",
          checklistMulti: "Confirm group visibility for each post",
          observation: "Observation",
          observationCopy: "Participant reactions accumulate on top of your configured baseline values, so the published feed feels active while still remaining experimentally controlled.",
          translationsTitle: "Translation files",
          translationsCopy: "Export a translation template, fill the target language, then import it back.",
          targetLanguage: "Target language",
          exportJson: "Export JSON",
          exportCsv: "Export CSV",
          chooseTranslationFile: "Choose JSON or CSV file",
          importFile: "Import file",
          translationExported: "Translation template exported",
          translationImported: "Translations imported",
          noTranslationFile: "Choose a translation file first.",
        };

  const loadData = useCallback(async () => {
    try {
      const [nextSurvey, nextPosts] = await Promise.all([api.getSurvey(surveyId), api.listPosts(surveyId)]);
      setSurvey(nextSurvey);
      setPosts(nextPosts);
    } catch (err: any) {
      const message = String(err?.message || "").toLowerCase();
      if (message.includes("not found")) {
        router.push("/admin/surveys");
        return;
      }
      router.push("/auth");
    }
  }, [router, surveyId]);

  const loadStats = useCallback(async () => {
    try {
      const res = await apiRequest(`/surveys/${surveyId}/engagement-stats`);
      setStats(res.posts);
    } catch {}
  }, [surveyId]);

  const loadParticipantComments = useCallback(async () => {
    try {
      const res = await apiRequest(`/surveys/${surveyId}/participant-comments`);
      setParticipantCommentsByPost(res.comments_by_post || {});
    } catch {}
  }, [surveyId]);

  const discardUnsavedDraft = useCallback(() => {
    if (!shouldDiscardDraftRef.current || discardRequestedRef.current || !Number.isFinite(surveyId)) return;
    const token = window.localStorage.getItem("token");
    if (!token) return;
    discardRequestedRef.current = true;
    fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"}/surveys/${surveyId}`, {
      method: "DELETE",
      keepalive: true,
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }).catch(() => {
      discardRequestedRef.current = false;
    });
  }, [surveyId]);

  useEffect(() => {
    loadData();
    loadStats();
    loadParticipantComments();
  }, [loadData, loadParticipantComments, loadStats]);

  useEffect(() => {
    const nextUnsavedDraft = searchParams.get("unsaved") === "1";
    setIsUnsavedDraft(nextUnsavedDraft);
    shouldDiscardDraftRef.current = nextUnsavedDraft;
    discardRequestedRef.current = false;
  }, [searchParams]);

  useEffect(() => {
    let armed = false;
    const armTimer = window.setTimeout(() => {
      armed = true;
    }, 0);

    const handlePageHide = () => {
      if (armed) {
        discardUnsavedDraft();
      }
    };

    window.addEventListener("pagehide", handlePageHide);
    return () => {
      window.clearTimeout(armTimer);
      window.removeEventListener("pagehide", handlePageHide);
      if (armed) {
        discardUnsavedDraft();
      }
    };
  }, [discardUnsavedDraft]);

  async function addPost(e: React.FormEvent) {
    e.preventDefault();
    setAddingPost(true);
    setError("");
    try {
      await api.createPost(surveyId, { original_url: newUrl, order: posts.length + 1 });
      setNewUrl("");
      await loadData();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setAddingPost(false);
    }
  }

  async function deletePost(postId: number) {
    if (!confirm(text.deleteConfirm)) return;
    await api.deletePost(surveyId, postId);
    await loadData();
  }

  function startEdit(post: Post) {
    setEditingPost(post.id);
    setEditLikes(post.display_likes);
    setEditComments(post.display_comments_count);
    setEditShares(post.display_shares);
    setEditTitle(post.display_title || post.fetched_title || "");
  }

  async function saveEdit(postId: number) {
    await api.updatePost(surveyId, postId, {
      display_title: editTitle || null,
      display_likes: editLikes,
      display_comments_count: editComments,
      display_shares: editShares,
    });
    setEditingPost(null);
    await loadData();
  }

  async function addComment(e: React.FormEvent) {
    e.preventDefault();
    if (!commentPostId) return;
    await api.addComment(surveyId, commentPostId, { author_name: commentAuthor, text: commentText });
    setCommentPostId(null);
    setCommentAuthor("");
    setCommentText("");
    await loadData();
  }

  function startEditGroups(post: Post) {
    setEditingGroups(post.id);
    const allGroups = Array.from({ length: survey?.num_groups || 1 }, (_, index) => index + 1);
    setGroupVisibility(post.visible_to_groups || allGroups);

    const overrides: Record<
      string,
      { display_likes: number; display_comments_count: number; display_shares: number }
    > = {};

    for (const group of allGroups) {
      const existing = (post as any).group_overrides?.[String(group)];
      overrides[String(group)] = {
        display_likes: existing?.display_likes ?? post.display_likes,
        display_comments_count: existing?.display_comments_count ?? post.display_comments_count,
        display_shares: existing?.display_shares ?? post.display_shares,
      };
    }

    setGroupOverrides(overrides);
  }

  async function saveGroupSettings(postId: number) {
    const values = Object.values(groupOverrides);
    const allSame = values.every(
      (value) =>
        value.display_likes === values[0].display_likes &&
        value.display_comments_count === values[0].display_comments_count &&
        value.display_shares === values[0].display_shares,
    );

    await api.updatePost(surveyId, postId, {
      visible_to_groups: groupVisibility.length === (survey?.num_groups || 1) ? null : groupVisibility,
      group_overrides: allSame ? null : groupOverrides,
    });

    setEditingGroups(null);
    await loadData();
  }

  async function publishSurvey() {
    if (!confirm(text.publishConfirm)) return;
    await api.publishSurvey(surveyId);
    setIsUnsavedDraft(false);
    shouldDiscardDraftRef.current = false;
    router.replace(`/admin/surveys/${surveyId}`);
    await loadData();
  }

  async function saveDraft() {
    if (!survey) return;
    await api.updateSurvey(surveyId, { title: survey.title });
    setIsUnsavedDraft(false);
    shouldDiscardDraftRef.current = false;
    router.replace(`/admin/surveys/${surveyId}`);
    await loadData();
  }

  function saveAsTemplate() {
    if (!survey) return;
    const name = window.prompt(text.templateName, `${survey.title} ${text.templateSuffix}`);
    if (!name?.trim()) return;
    const template = buildTemplateFromSurvey({
      name: name.trim(),
      survey,
      posts,
    });
    persistTemplate(template);
    setTemplateSaved(true);
    window.setTimeout(() => setTemplateSaved(false), 2200);
  }

  async function copyShareUrl(url: string) {
    try {
      await navigator.clipboard.writeText(url);
      setCopiedShare(true);
      window.setTimeout(() => setCopiedShare(false), 1800);
    } catch {}
  }

  function downloadTextFile(content: string, filename: string, mimeType: string) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  async function exportTranslations(format: "json" | "csv") {
    setTranslationBusy(true);
    setTranslationStatus("");
    try {
      if (format === "json") {
        const payload = await api.exportTranslationsJson(surveyId, translationLanguage);
        downloadTextFile(
          JSON.stringify(payload, null, 2),
          `survey-${surveyId}-translations-${translationLanguage}.json`,
          "application/json",
        );
      } else {
        const csv = await api.exportTranslationsCsv(surveyId, translationLanguage);
        downloadTextFile(
          csv,
          `survey-${surveyId}-translations-${translationLanguage}.csv`,
          "text/csv;charset=utf-8",
        );
      }
      setTranslationStatus(text.translationExported);
    } catch (err: any) {
      setTranslationStatus(err.message || "Translation export failed");
    } finally {
      setTranslationBusy(false);
    }
  }

  async function importTranslations() {
    if (!translationFile) {
      setTranslationStatus(text.noTranslationFile);
      return;
    }
    setTranslationBusy(true);
    setTranslationStatus("");
    try {
      const content = await translationFile.text();
      const isCsv = translationFile.name.toLowerCase().endsWith(".csv") || translationFile.type.includes("csv");
      if (isCsv) {
        await api.importTranslationsCsv(surveyId, content, translationLanguage);
      } else {
        const payload = JSON.parse(content);
        if (!payload.language_code && !payload.language) {
          payload.language_code = translationLanguage;
        }
        await api.importTranslationsJson(surveyId, payload);
      }
      setTranslationFile(null);
      setTranslationStatus(text.translationImported);
    } catch (err: any) {
      setTranslationStatus(err.message || "Translation import failed");
    } finally {
      setTranslationBusy(false);
    }
  }

  if (!survey) {
    return <p className="pt-14 text-sm uppercase tracking-[0.24em] text-slate-400">{text.loading}</p>;
  }

  const shareUrl =
    typeof window !== "undefined" ? `${window.location.origin}/survey/${survey.share_code}/start` : "";
  const publishedPosts = posts.filter((post) => !post.visible_to_groups || post.visible_to_groups.length > 0).length;
  const totalComments = posts.reduce(
    (sum, post) =>
      sum +
      post.comments.length +
      (participantCommentsByPost[post.id]?.length || 0) +
      (stats?.find((item) => item.post_id === post.id)?.participant_comments || 0),
    0,
  );

  return (
    <div className="space-y-8">
      <section className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <p className="section-kicker">{text.workspace}</p>
          <h1 className="page-title mt-3">{survey.title}</h1>
          <p className="page-subtitle mt-3 max-w-3xl">
            {text.subtitle}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button onClick={saveAsTemplate} className="secondary-button">
            {templateSaved ? text.templateSaved : text.saveAsTemplate}
          </button>
          {survey.status === "published" && shareUrl && (
            <button
              onClick={() => copyShareUrl(shareUrl)}
              className="secondary-button h-[56px] w-[130px] justify-center gap-2 px-3"
            >
              <LinkIcon className="h-4 w-4 shrink-0" />
              <span className="text-center text-[13px] leading-4">
                {copiedShare ? text.linkCopied : text.copyParticipantLink}
              </span>
            </button>
          )}
          {survey.status === "draft" && (
            <button onClick={publishSurvey} disabled={posts.length === 0} className="primary-button">
              {text.publishSurvey}
            </button>
          )}
          {survey.status === "draft" ? (
            <button onClick={saveDraft} className="secondary-button">
              {text.saveDraft}
            </button>
          ) : (
            <span className={statusClasses(survey.status)}>{survey.status}</span>
          )}
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-4">
        <div className="metric-panel">
          <p className="section-kicker">{text.postsConfigured}</p>
          <p className="metric-value">{posts.length}</p>
        </div>
        <div className="metric-panel">
          <p className="section-kicker">{text.groupVariants}</p>
          <p className="metric-value">{survey.num_groups}</p>
        </div>
        <div className="metric-panel">
          <p className="section-kicker">{text.commentThreads}</p>
          <p className="metric-value">{totalComments}</p>
        </div>
        <div className="rounded-[18px] bg-black px-5 py-4 text-white shadow-[0_28px_60px_rgba(17,24,39,0.14)]">
          <p className="section-kicker text-white/55">{text.visibleCards}</p>
          <p className="metric-value-inverse">{publishedPosts}</p>
        </div>
      </section>

      {survey.status === "draft" && (
        <section className="surface-panel px-6 py-6 md:px-7 md:py-7">
          <div className="flex items-start justify-between gap-6">
            <div>
              <p className="section-kicker">{text.addPost}</p>
              <h2 className="section-title mt-3 md:text-[24px]">
                {text.addPostTitle}
              </h2>
            </div>
            <div className="hidden h-12 w-12 items-center justify-center rounded-[16px] bg-stone-100 text-slate-500 md:flex">
              <SearchIcon className="h-5 w-5" />
            </div>
          </div>

          <form onSubmit={addPost} className="mt-6 space-y-4">
            <div className="flex flex-col gap-3 xl:flex-row">
              <input
                type="url"
                value={newUrl}
                onChange={(e) => setNewUrl(e.target.value)}
                placeholder="https://www.bbc.com/news/article-example"
                className="field-input flex-1"
                required
              />
              <button type="submit" disabled={addingPost} className="primary-button min-w-[160px]">
                {addingPost ? text.fetching : text.addPost}
              </button>
            </div>
            {error && <p className="rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>}
            <p className="section-copy">{text.articleMetadata}</p>
          </form>
        </section>
      )}

      <section className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_300px]">
        <div className="space-y-6">
          {posts.map((post) => {
            const stat = stats?.find((item) => item.post_id === post.id);
            const totalLikes = (post.display_likes || 0) + (stat?.likes || 0);
            const totalCountComments = (post.display_comments_count || 0) + (stat?.participant_comments || 0);
            const totalShares = (post.display_shares || 0) + (stat?.shares || 0);
            const title = post.display_title || post.fetched_title || text.untitled;
            const source = post.fetched_source || new URL(post.original_url).hostname;
            const imageUrl = post.display_image_url || post.fetched_image_url;

            return (
              <div key={post.id} className="surface-panel overflow-hidden">
                <div className="grid gap-5 p-5 md:grid-cols-[200px_minmax(0,1fr)] md:p-6">
                  <div className="overflow-hidden rounded-[18px] bg-stone-100">
                    {imageUrl ? (
                      <img src={imageUrl} alt="" className="h-full min-h-[170px] w-full object-cover" />
                    ) : (
                      <div className="flex min-h-[170px] items-center justify-center bg-stone-100 text-slate-400">
                        <SurveyIcon className="h-7 w-7" />
                      </div>
                    )}
                  </div>

                  <div className="min-w-0">
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0">
                        <p className="section-kicker">{source}</p>
                        <h3 className="mt-3 text-[18px] font-semibold leading-tight tracking-[-0.05em] text-black md:text-[20px]">
                          {title}
                        </h3>
                        <a
                          href={post.original_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="mt-3 inline-flex max-w-full items-center gap-2 truncate text-[13px] text-slate-500 underline decoration-black/10 underline-offset-4"
                        >
                          <LinkIcon className="h-4 w-4 shrink-0" />
                          <span className="truncate">{post.original_url}</span>
                        </a>
                      </div>

                      {survey.status === "draft" && (
                        <button
                          onClick={() => deletePost(post.id)}
                          className="rounded-full border px-4 py-2 text-[13px] font-medium text-slate-500 transition hover:bg-black/[0.03] hover:text-black"
                        >
                          {text.delete}
                        </button>
                      )}
                    </div>

                    {post.visible_to_groups && (
                      <p className="mt-4 text-[13px] leading-6 text-slate-500">
                        {text.visibleToGroups} <span className="font-medium text-black">{post.visible_to_groups.join(", ")}</span>
                      </p>
                    )}
                  </div>
                </div>

                <div className="grid gap-4 border-y bg-stone-50 px-5 py-4 md:grid-cols-3 md:px-6">
                  {post.show_likes && (
                    <div>
                      <p className="section-kicker">{text.likes}</p>
                      <p className="mt-2 text-[26px] font-semibold tracking-[-0.04em] text-black">
                        {totalLikes.toLocaleString()}
                      </p>
                    </div>
                  )}
                  {post.show_comments && (
                    <div>
                      <p className="section-kicker">{text.comments}</p>
                      <p className="mt-2 text-[26px] font-semibold tracking-[-0.04em] text-black">{totalCountComments}</p>
                    </div>
                  )}
                  {post.show_shares && (
                    <div>
                      <p className="section-kicker">{text.shares}</p>
                      <p className="mt-2 text-[26px] font-semibold tracking-[-0.04em] text-black">{totalShares}</p>
                    </div>
                  )}
                </div>

                {(post.comments.length > 0 || (participantCommentsByPost[post.id]?.length || 0) > 0) && (
                  <div className="space-y-3 px-5 py-5 md:px-6">
                    <p className="section-kicker">{text.visibleComments}</p>

                    {post.comments.map((comment) => (
                      <div key={`r-${comment.id}`} className="rounded-[18px] border bg-stone-50 px-4 py-4">
                        <p className="text-[13px] font-semibold text-black">{comment.author_name}</p>
                        <p className="mt-1 text-[13px] leading-6 text-slate-600">{comment.text}</p>
                      </div>
                    ))}

                    {(participantCommentsByPost[post.id] || []).map((comment) => (
                      <div key={`p-${comment.id}`} className="rounded-[18px] border bg-white px-4 py-4">
                        <div className="flex items-start justify-between gap-4">
                          <div>
                            <p className="text-[13px] font-semibold text-black">{text.participantResponse}</p>
                            <p className="mt-1 text-[13px] leading-6 text-slate-600">{comment.text}</p>
                          </div>
                          <p className="text-xs text-slate-400">{new Date(comment.created_at).toLocaleString()}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {(() => {
                  const hasContent = post.comments.length > 0 || (participantCommentsByPost[post.id]?.length || 0) > 0;
                  if (totalCountComments > 0 && !hasContent) {
                    return (
                      <div className="px-5 py-5 text-[13px] leading-6 text-slate-500 md:px-6">
                        {text.noCommentContent}
                      </div>
                    );
                  }
                  return null;
                })()}

                {survey.status === "draft" && (
                  <div className="border-t px-5 py-5 md:px-6">
                    {editingPost === post.id ? (
                      <div className="space-y-4">
                        <input
                          type="text"
                          value={editTitle}
                          onChange={(e) => setEditTitle(e.target.value)}
                          placeholder={text.overrideTitle}
                          className="field-input"
                        />
                        <div className="flex flex-wrap gap-3">
                          <label className="space-y-2 text-sm text-slate-500">
                            <span className="block">{text.likes}</span>
                            <input
                              type="number"
                              value={editLikes}
                              onChange={(e) => setEditLikes(Number(e.target.value))}
                              className={numberInputClass()}
                            />
                          </label>
                          <label className="space-y-2 text-sm text-slate-500">
                            <span className="block">{text.comments}</span>
                            <input
                              type="number"
                              value={editComments}
                              onChange={(e) => setEditComments(Number(e.target.value))}
                              className={numberInputClass()}
                            />
                          </label>
                          <label className="space-y-2 text-sm text-slate-500">
                            <span className="block">{text.shares}</span>
                            <input
                              type="number"
                              value={editShares}
                              onChange={(e) => setEditShares(Number(e.target.value))}
                              className={numberInputClass()}
                            />
                          </label>
                        </div>
                        <div className="flex flex-wrap gap-3">
                          <button onClick={() => saveEdit(post.id)} className="primary-button">
                            {text.saveValues}
                          </button>
                          <button onClick={() => setEditingPost(null)} className="secondary-button">
                            {text.cancel}
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex flex-wrap gap-3">
                        <button onClick={() => startEdit(post)} className="secondary-button">
                          {text.editNumbers}
                        </button>
                        <button
                          onClick={() => {
                            setCommentPostId(post.id);
                            setCommentAuthor("");
                            setCommentText("");
                          }}
                          className="secondary-button"
                        >
                          {text.addComment}
                        </button>
                        {survey.num_groups > 1 && (
                          <button onClick={() => startEditGroups(post)} className="secondary-button">
                            {text.abGroups}
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {editingGroups === post.id && survey.num_groups > 1 && (
                  <div className="border-t bg-stone-50 px-5 py-5 md:px-6">
                    <p className="section-kicker">{text.groupVisibility}</p>
                    <div className="mt-4 flex flex-wrap gap-3">
                      {Array.from({ length: survey.num_groups }, (_, index) => index + 1).map((group) => (
                        <label key={group} className="flex items-center gap-2 rounded-full border bg-white px-4 py-2 text-[13px]">
                          <input
                            type="checkbox"
                            checked={groupVisibility.includes(group)}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setGroupVisibility((prev) => [...prev, group].sort());
                              } else {
                                setGroupVisibility((prev) => prev.filter((value) => value !== group));
                              }
                            }}
                          />
                          Group {group}
                        </label>
                      ))}
                    </div>

                    <div className="mt-5 space-y-3">
                      {Array.from({ length: survey.num_groups }, (_, index) => index + 1)
                        .filter((group) => groupVisibility.includes(group))
                        .map((group) => (
                          <div key={group} className="rounded-[18px] border bg-white p-4">
                            <p className="text-[13px] font-semibold text-black">Group {group}</p>
                            <div className="mt-4 flex flex-wrap gap-3">
                              <label className="space-y-2 text-sm text-slate-500">
                                <span className="block">{text.likes}</span>
                                <input
                                  type="number"
                                  value={groupOverrides[String(group)]?.display_likes ?? 0}
                                  onChange={(e) =>
                                    setGroupOverrides((prev) => ({
                                      ...prev,
                                      [String(group)]: {
                                        ...prev[String(group)],
                                        display_likes: Number(e.target.value),
                                      },
                                    }))
                                  }
                                  className={numberInputClass()}
                                />
                              </label>
                              <label className="space-y-2 text-sm text-slate-500">
                                <span className="block">{text.comments}</span>
                                <input
                                  type="number"
                                  value={groupOverrides[String(group)]?.display_comments_count ?? 0}
                                  onChange={(e) =>
                                    setGroupOverrides((prev) => ({
                                      ...prev,
                                      [String(group)]: {
                                        ...prev[String(group)],
                                        display_comments_count: Number(e.target.value),
                                      },
                                    }))
                                  }
                                  className={numberInputClass()}
                                />
                              </label>
                              <label className="space-y-2 text-sm text-slate-500">
                                <span className="block">{text.shares}</span>
                                <input
                                  type="number"
                                  value={groupOverrides[String(group)]?.display_shares ?? 0}
                                  onChange={(e) =>
                                    setGroupOverrides((prev) => ({
                                      ...prev,
                                      [String(group)]: {
                                        ...prev[String(group)],
                                        display_shares: Number(e.target.value),
                                      },
                                    }))
                                  }
                                  className={numberInputClass()}
                                />
                              </label>
                            </div>
                          </div>
                        ))}
                    </div>

                    <div className="mt-5 flex flex-wrap gap-3">
                      <button onClick={() => saveGroupSettings(post.id)} className="primary-button">
                        {text.saveGroups}
                      </button>
                      <button onClick={() => setEditingGroups(null)} className="secondary-button">
                        {text.cancel}
                      </button>
                    </div>
                  </div>
                )}

                {commentPostId === post.id && (
                  <form onSubmit={addComment} className="border-t bg-stone-50 px-5 py-5 md:px-6">
                    <div className="grid gap-3 md:grid-cols-[200px_minmax(0,1fr)_auto]">
                      <input
                        type="text"
                        value={commentAuthor}
                        onChange={(e) => setCommentAuthor(e.target.value)}
                        placeholder={text.commenterName}
                        className="field-input"
                        required
                      />
                      <input
                        type="text"
                        value={commentText}
                        onChange={(e) => setCommentText(e.target.value)}
                        placeholder={text.commentText}
                        className="field-input"
                        required
                      />
                      <div className="flex gap-3">
                        <button type="submit" className="primary-button">
                          {text.add}
                        </button>
                        <button type="button" onClick={() => setCommentPostId(null)} className="secondary-button">
                          {text.cancel}
                        </button>
                      </div>
                    </div>
                  </form>
                )}
              </div>
            );
          })}

          {posts.length === 0 && (
            <div className="surface-panel px-8 py-12 text-center">
              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-[22px] bg-stone-100 text-slate-500">
                <PlusIcon className="h-8 w-8" />
              </div>
              <h2 className="mt-6 text-[24px] font-semibold tracking-[-0.04em] text-black">{text.noPosts}</h2>
              <p className="mx-auto mt-3 max-w-xl text-[14px] leading-7 text-slate-500">
                {text.noPostsCopy}
              </p>
            </div>
          )}
        </div>

        <aside className="space-y-6">
          <div className="surface-panel px-6 py-6">
            <p className="section-kicker">{text.studySummary}</p>
            <div className="mt-6 space-y-5">
              <div>
                <p className="text-[13px] text-slate-500">{text.surveyStatus}</p>
                <p className="mt-1 text-[18px] font-semibold tracking-[-0.03em] text-black">{survey.status}</p>
              </div>
              <div>
                <p className="text-[13px] text-slate-500">{text.participantLink}</p>
                <p className="mt-1 break-all text-[13px] leading-6 text-black">{shareUrl || text.linkAfterPublish}</p>
              </div>
              <div>
                <p className="text-[13px] text-slate-500">{text.abGroupCount}</p>
                <p className="mt-1 text-[18px] font-semibold tracking-[-0.03em] text-black">{survey.num_groups}</p>
              </div>
            </div>
          </div>

          <div className="surface-panel-soft px-6 py-6">
            <p className="section-kicker">{text.translationsTitle}</p>
            <p className="mt-3 text-[14px] leading-7 text-slate-500">{text.translationsCopy}</p>

            <label className="mt-5 block space-y-2 text-[13px] text-slate-500">
              <span>{text.targetLanguage}</span>
              <select
                value={translationLanguage}
                onChange={(event) => setTranslationLanguage(event.target.value)}
                className="field-input h-11 text-[13px]"
              >
                <option value="zh">中文</option>
                <option value="ar">العربية</option>
                <option value="en">English</option>
              </select>
            </label>

            <div className="mt-4 grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => exportTranslations("json")}
                disabled={translationBusy}
                className="secondary-button justify-center px-3 text-[13px]"
              >
                {text.exportJson}
              </button>
              <button
                type="button"
                onClick={() => exportTranslations("csv")}
                disabled={translationBusy}
                className="secondary-button justify-center px-3 text-[13px]"
              >
                {text.exportCsv}
              </button>
            </div>

            <label className="mt-4 block rounded-[16px] border border-dashed border-slate-200 bg-white px-4 py-4 text-[13px] leading-6 text-slate-500">
              <span>{translationFile?.name || text.chooseTranslationFile}</span>
              <input
                key={translationFile ? "translation-file-selected" : "translation-file-empty"}
                type="file"
                accept=".json,.csv,application/json,text/csv"
                className="sr-only"
                onChange={(event) => setTranslationFile(event.target.files?.[0] || null)}
              />
            </label>

            <button
              type="button"
              onClick={importTranslations}
              disabled={translationBusy}
              className="primary-button mt-4 w-full justify-center"
            >
              {text.importFile}
            </button>
            {translationStatus && (
              <p className="mt-3 rounded-[14px] border border-slate-200 bg-white px-3 py-2 text-[12px] leading-5 text-slate-500">
                {translationStatus}
              </p>
            )}
          </div>

          <div className="surface-panel-soft px-6 py-6">
            <p className="section-kicker">{text.checklist}</p>
            <div className="mt-5 space-y-4">
              {[
                ...text.checklistItems,
                survey.num_groups > 1 ? text.checklistMulti : text.checklistSingle,
              ].map((item) => (
                <div key={item} className="grid grid-cols-[20px_minmax(0,1fr)] items-start gap-3">
                  <div className="mt-[2px] flex h-5 w-5 items-center justify-center rounded-full bg-slate-100 text-slate-700">
                    <CheckCircleIcon className="h-3.5 w-3.5" />
                  </div>
                  <p className="text-[14px] leading-7 text-slate-500">{item}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="surface-panel-soft px-6 py-6">
            <p className="section-kicker">{text.observation}</p>
            <div className="mt-4 flex items-start gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-[14px] bg-stone-100 text-slate-500">
                <ChartIcon className="h-4 w-4" />
              </div>
              <p className="text-[14px] leading-7 text-slate-500">{text.observationCopy}</p>
            </div>
          </div>
        </aside>
      </section>
    </div>
  );
}
