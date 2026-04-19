"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
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
  const shouldDiscardDraftRef = useRef(initialUnsavedDraft);
  const discardRequestedRef = useRef(false);

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
    if (!confirm("Delete this post?")) return;
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
    if (!confirm("Publish this survey? Participants will be able to access it.")) return;
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
    const name = window.prompt("Template name", `${survey.title} Template`);
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

  if (!survey) {
    return <p className="pt-14 text-sm uppercase tracking-[0.24em] text-slate-400">Loading survey</p>;
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
          <p className="section-kicker">Survey Workspace</p>
          <h1 className="page-title mt-3">{survey.title}</h1>
          <p className="page-subtitle mt-3 max-w-3xl">
            Configure the posts, group visibility, and engagement baselines before sharing the study with participants.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button onClick={saveAsTemplate} className="secondary-button">
            {templateSaved ? "Template Saved" : "Save as Template"}
          </button>
          {survey.status === "published" && shareUrl && (
            <button
              onClick={() => copyShareUrl(shareUrl)}
              className="secondary-button h-[56px] w-[130px] justify-center gap-2 px-3"
            >
              <LinkIcon className="h-4 w-4 shrink-0" />
              <span className="text-center text-[13px] leading-4">
                {copiedShare ? "Link copied" : "Copy participant link"}
              </span>
            </button>
          )}
          {survey.status === "draft" && (
            <button onClick={publishSurvey} disabled={posts.length === 0} className="primary-button">
              Publish Survey
            </button>
          )}
          {survey.status === "draft" ? (
            <button onClick={saveDraft} className="secondary-button">
              Save Draft
            </button>
          ) : (
            <span className={statusClasses(survey.status)}>{survey.status}</span>
          )}
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-4">
        <div className="metric-panel">
          <p className="section-kicker">Posts configured</p>
          <p className="metric-value">{posts.length}</p>
        </div>
        <div className="metric-panel">
          <p className="section-kicker">Group variants</p>
          <p className="metric-value">{survey.num_groups}</p>
        </div>
        <div className="metric-panel">
          <p className="section-kicker">Comment threads</p>
          <p className="metric-value">{totalComments}</p>
        </div>
        <div className="rounded-[18px] bg-black px-5 py-4 text-white shadow-[0_28px_60px_rgba(17,24,39,0.14)]">
          <p className="section-kicker text-white/55">Visible cards</p>
          <p className="metric-value-inverse">{publishedPosts}</p>
        </div>
      </section>

      {survey.status === "draft" && (
        <section className="surface-panel px-6 py-6 md:px-7 md:py-7">
          <div className="flex items-start justify-between gap-6">
            <div>
              <p className="section-kicker">Add Post</p>
              <h2 className="section-title mt-3 md:text-[24px]">
                Paste a news article URL to generate a post card
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
                {addingPost ? "Fetching..." : "Add Post"}
              </button>
            </div>
            {error && <p className="rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>}
            <p className="section-copy">
              The platform will fetch the headline, source, and image automatically. You can override numbers and
              comments for each group after the card appears below.
            </p>
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
            const title = post.display_title || post.fetched_title || "Untitled";
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
                          Delete
                        </button>
                      )}
                    </div>

                    {post.visible_to_groups && (
                      <p className="mt-4 text-[13px] leading-6 text-slate-500">
                        Visible to groups: <span className="font-medium text-black">{post.visible_to_groups.join(", ")}</span>
                      </p>
                    )}
                  </div>
                </div>

                <div className="grid gap-4 border-y bg-stone-50 px-5 py-4 md:grid-cols-3 md:px-6">
                  {post.show_likes && (
                    <div>
                      <p className="section-kicker">Likes</p>
                      <p className="mt-2 text-[26px] font-semibold tracking-[-0.04em] text-black">
                        {totalLikes.toLocaleString()}
                      </p>
                    </div>
                  )}
                  {post.show_comments && (
                    <div>
                      <p className="section-kicker">Comments</p>
                      <p className="mt-2 text-[26px] font-semibold tracking-[-0.04em] text-black">{totalCountComments}</p>
                    </div>
                  )}
                  {post.show_shares && (
                    <div>
                      <p className="section-kicker">Shares</p>
                      <p className="mt-2 text-[26px] font-semibold tracking-[-0.04em] text-black">{totalShares}</p>
                    </div>
                  )}
                </div>

                {(post.comments.length > 0 || (participantCommentsByPost[post.id]?.length || 0) > 0) && (
                  <div className="space-y-3 px-5 py-5 md:px-6">
                    <p className="section-kicker">Visible comments</p>

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
                            <p className="text-[13px] font-semibold text-black">Participant response</p>
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
                        Comment count is visible, but no comment content has been configured for this post.
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
                          placeholder="Override title"
                          className="field-input"
                        />
                        <div className="flex flex-wrap gap-3">
                          <label className="space-y-2 text-sm text-slate-500">
                            <span className="block">Likes</span>
                            <input
                              type="number"
                              value={editLikes}
                              onChange={(e) => setEditLikes(Number(e.target.value))}
                              className={numberInputClass()}
                            />
                          </label>
                          <label className="space-y-2 text-sm text-slate-500">
                            <span className="block">Comments</span>
                            <input
                              type="number"
                              value={editComments}
                              onChange={(e) => setEditComments(Number(e.target.value))}
                              className={numberInputClass()}
                            />
                          </label>
                          <label className="space-y-2 text-sm text-slate-500">
                            <span className="block">Shares</span>
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
                            Save values
                          </button>
                          <button onClick={() => setEditingPost(null)} className="secondary-button">
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex flex-wrap gap-3">
                        <button onClick={() => startEdit(post)} className="secondary-button">
                          Edit numbers
                        </button>
                        <button
                          onClick={() => {
                            setCommentPostId(post.id);
                            setCommentAuthor("");
                            setCommentText("");
                          }}
                          className="secondary-button"
                        >
                          Add comment
                        </button>
                        {survey.num_groups > 1 && (
                          <button onClick={() => startEditGroups(post)} className="secondary-button">
                            A/B groups
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {editingGroups === post.id && survey.num_groups > 1 && (
                  <div className="border-t bg-stone-50 px-5 py-5 md:px-6">
                    <p className="section-kicker">Group visibility</p>
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
                                <span className="block">Likes</span>
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
                                <span className="block">Comments</span>
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
                                <span className="block">Shares</span>
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
                        Save groups
                      </button>
                      <button onClick={() => setEditingGroups(null)} className="secondary-button">
                        Cancel
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
                        placeholder="Commenter name"
                        className="field-input"
                        required
                      />
                      <input
                        type="text"
                        value={commentText}
                        onChange={(e) => setCommentText(e.target.value)}
                        placeholder="Comment text"
                        className="field-input"
                        required
                      />
                      <div className="flex gap-3">
                        <button type="submit" className="primary-button">
                          Add
                        </button>
                        <button type="button" onClick={() => setCommentPostId(null)} className="secondary-button">
                          Cancel
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
              <h2 className="mt-6 text-[24px] font-semibold tracking-[-0.04em] text-black">No post cards yet</h2>
              <p className="mx-auto mt-3 max-w-xl text-[14px] leading-7 text-slate-500">
                Add the first article URL above to generate a participant-facing feed card for this survey.
              </p>
            </div>
          )}
        </div>

        <aside className="space-y-6">
          <div className="surface-panel px-6 py-6">
            <p className="section-kicker">Study summary</p>
            <div className="mt-6 space-y-5">
              <div>
                <p className="text-[13px] text-slate-500">Survey status</p>
                <p className="mt-1 text-[18px] font-semibold tracking-[-0.03em] text-black">{survey.status}</p>
              </div>
              <div>
                <p className="text-[13px] text-slate-500">Participant link</p>
                <p className="mt-1 break-all text-[13px] leading-6 text-black">{shareUrl || "Link available after publish"}</p>
              </div>
              <div>
                <p className="text-[13px] text-slate-500">A/B groups</p>
                <p className="mt-1 text-[18px] font-semibold tracking-[-0.03em] text-black">{survey.num_groups}</p>
              </div>
            </div>
          </div>

          <div className="surface-panel-soft px-6 py-6">
            <p className="section-kicker">Publishing checklist</p>
            <div className="mt-5 space-y-4">
              {[
                "Add at least one article-derived post card",
                "Review display counts and comment content",
                survey.num_groups > 1 ? "Confirm group visibility for each post" : "Single-group flow is ready",
              ].map((item) => (
                <div key={item} className="flex gap-3">
                  <CheckCircleIcon className="mt-0.5 h-4 w-4 text-black" />
                  <p className="text-[14px] leading-7 text-slate-500">{item}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="surface-panel-soft px-6 py-6">
            <p className="section-kicker">Observation</p>
            <div className="mt-4 flex items-start gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-[14px] bg-stone-100 text-slate-500">
                <ChartIcon className="h-4 w-4" />
              </div>
              <p className="text-[14px] leading-7 text-slate-500">
                Participant reactions accumulate on top of your configured baseline values, so the published feed feels
                active while still remaining experimentally controlled.
              </p>
            </div>
          </div>
        </aside>
      </section>
    </div>
  );
}