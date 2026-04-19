"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { t, type Locale } from "@/lib/i18n";
import { CheckCircleIcon, GlobeIcon, LinkIcon, SurveyIcon, UsersIcon } from "@/components/icons";
import { CalibrationExperience } from "@/components/calibration-experience";
import { useGazeTracker } from "./useGazeTracker";

interface Comment {
  id: number;
  author_name: string;
  text: string;
}

interface Question {
  id: number;
  post_id: number;
  order: number;
  question_type: string; // free_text | likert | multiple_choice
  text: string;
  config: { min?: number; max?: number; min_label?: string; max_label?: string; options?: string[] } | null;
}

interface Post {
  id: number;
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
  comments: Comment[];
  questions: Question[];
}

interface SurveySession {
  response_id: number;
  survey_id: number;
  assigned_group: number;
  calibration_required: boolean;
  gaze_tracking_enabled: boolean;
  gaze_interval_ms: number;
  click_tracking_enabled: boolean;
  posts: Post[];
}

interface ParticipantComment {
  id: number;
  post_id: number;
  text: string;
}

export default function SurveyParticipantPage() {
  const params = useParams();
  const shareCode = params.shareCode as string;
  const search = useSearchParams();
  const initialLocale =
    (search.get("lang") as Locale) ||
    (typeof window !== "undefined" ? ((localStorage.getItem("locale") as Locale) || "en") : "en");

  const [locale, setLocale] = useState<Locale>(initialLocale);
  const [session, setSession] = useState<SurveySession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [completed, setCompleted] = useState(false);
  const [calibrationDone, setCalibrationDone] = useState(false);
  const [likedPosts, setLikedPosts] = useState<Set<number>>(new Set());
  const [commentInputs, setCommentInputs] = useState<Record<number, string>>({});
  const [showCommentInput, setShowCommentInput] = useState<number | null>(null);
  const [participantComments, setParticipantComments] = useState<Record<number, ParticipantComment[]>>({});
  // Question answers: { [questionId]: answer }
  const [questionAnswers, setQuestionAnswers] = useState<Record<number, { text?: string; value?: number; choices?: string[] }>>({});
  const [submittedQuestions, setSubmittedQuestions] = useState<Set<number>>(new Set());

  const clickBuffer = useRef<any[]>([]);

  // Gaze tracking — runs continuously during survey after calibration
  const { flush: flushGaze } = useGazeTracker({
    responseId: session?.response_id ?? 0,
    intervalMs: session?.gaze_interval_ms ?? 1000,
    enabled: calibrationDone && !!session?.gaze_tracking_enabled,
  });

  useEffect(() => {
    let clickListener: ((e: MouseEvent) => void) | null = null;
    let flushInterval: ReturnType<typeof setInterval> | null = null;

    async function init() {
      try {
        const result = await api.startSurvey(shareCode);
        setSession(result);

        try {
          const state = await api.getResponseState(result.response_id);
          setLikedPosts(new Set<number>(state.liked_post_ids || []));
          setParticipantComments(state.comments_by_post || {});
        } catch {}

        if (result.click_tracking_enabled) {
          clickListener = handleClick;
          document.addEventListener("click", clickListener);
          flushInterval = setInterval(() => flushClicks(result.response_id), 10000);
        }
      } catch (err: any) {
        setError(err.message || "Survey not found");
      } finally {
        setLoading(false);
      }
    }

    init();

    return () => {
      if (clickListener) document.removeEventListener("click", clickListener);
      if (flushInterval) clearInterval(flushInterval);
    };
  }, [shareCode]);

  function handleClick(e: MouseEvent) {
    const target = e.target as HTMLElement;
    let targetElement = "other";

    if (target.closest("[data-track='headline']")) targetElement = "headline";
    else if (target.closest("[data-track='image']")) targetElement = "image";
    else if (target.closest("[data-track='like']")) targetElement = "like_button";
    else if (target.closest("[data-track='comment']")) targetElement = "comment_button";
    else if (target.closest("[data-track='share']")) targetElement = "share_count";

    const postEl = target.closest("[data-post-id]");
    const postId = postEl ? Number(postEl.getAttribute("data-post-id")) : null;

    clickBuffer.current.push({
      post_id: postId,
      timestamp_ms: Date.now(),
      screen_x: e.clientX,
      screen_y: e.clientY,
      target_element: targetElement,
    });
  }

  async function flushClicks(responseId: number) {
    if (clickBuffer.current.length === 0) return;
    const batch = [...clickBuffer.current];
    clickBuffer.current = [];
    try {
      await api.recordClicks({ response_id: responseId, data: batch });
    } catch {
      clickBuffer.current = [...batch, ...clickBuffer.current];
    }
  }

  async function handleLike(postId: number) {
    if (!session) return;

    setLikedPosts((prev) => {
      const next = new Set(prev);
      if (next.has(postId)) next.delete(postId);
      else next.add(postId);
      return next;
    });

    try {
      await api.toggleLike(session.response_id, postId);
    } catch {
      setLikedPosts((prev) => {
        const next = new Set(prev);
        if (next.has(postId)) next.delete(postId);
        else next.add(postId);
        return next;
      });
    }
  }

  async function handleComment(postId: number) {
    if (!session) return;
    const text = commentInputs[postId];
    if (!text?.trim()) return;

    const created = await api.createParticipantComment(session.response_id, { post_id: postId, text });
    setParticipantComments((prev) => ({
      ...prev,
      [postId]: [...(prev[postId] || []), created],
    }));
    setCommentInputs((prev) => ({ ...prev, [postId]: "" }));
    setShowCommentInput(null);
  }

  async function handleClickPost(postId: number, url: string) {
    if (!session) return;
    await api.recordInteraction(session.response_id, { post_id: postId, action_type: "click" });
    window.open(url, "_blank");
  }

  async function handleComplete() {
    if (!session) return;
    await flushClicks(session.response_id);
    await flushGaze();
    await api.completeSurvey(session.response_id);
    setCompleted(true);
  }

  if (loading) {
    return <div className="flex min-h-screen items-center justify-center text-sm uppercase tracking-[0.24em] text-slate-400">Loading feed</div>;
  }

  if (error) {
    return <div className="flex min-h-screen items-center justify-center px-6 text-center text-red-500">{error}</div>;
  }

  if (completed) {
    return (
      <div className="flex min-h-screen items-center justify-center px-6">
        <div className="surface-panel max-w-xl px-8 py-10 text-center">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-[22px] bg-black text-white">
            <CheckCircleIcon className="h-7 w-7" />
          </div>
          <h1 className="mt-6 text-4xl font-semibold tracking-[-0.05em] text-black">{t(locale, "thankYou")}</h1>
          <p className="mt-3 text-sm leading-7 text-slate-500">{t(locale, "recorded")}</p>
        </div>
      </div>
    );
  }

  if (!session) return null;

  // Show calibration if required and not yet completed
  if (session.calibration_required && !calibrationDone) {
    return (
      <CalibrationExperience
        responseId={session.response_id}
        onComplete={(_result) => setCalibrationDone(true)}
      />
    );
  }

  const totalPosts = session.posts.length;
  const interactedPosts = likedPosts.size + Object.keys(participantComments).filter((key) => (participantComments[Number(key)] || []).length > 0).length;
  const researchNotes = [
    session.click_tracking_enabled ? "Clicks are captured in the background." : null,
    session.gaze_tracking_enabled ? "Gaze samples may be recorded during the session." : null,
    session.calibration_required ? "Calibration is required for complete tracking accuracy." : null,
  ].filter((item): item is string => Boolean(item));

  return (
    <div className="mx-auto max-w-[1560px] px-4 py-6 lg:px-6 lg:py-8">
      <div className="grid gap-6 xl:grid-cols-[250px_minmax(0,1fr)_280px]">
        <aside className="space-y-6 xl:sticky xl:top-6 xl:self-start">
          <div className="surface-panel-soft px-6 py-6">
            <div className="flex h-12 w-12 items-center justify-center rounded-[16px] bg-black text-white">
              <SurveyIcon className="h-5 w-5" />
            </div>
            <p className="section-kicker mt-6">Research Feed</p>
            <h1 className="section-title mt-3 md:text-[24px]">Participant Feed</h1>
            <p className="mt-4 text-[14px] leading-7 text-slate-500">
              Browse each post as you normally would on social media. Your interaction signals are recorded for the
              study environment.
            </p>

            {/* Tracking status indicators */}
            <div className="mt-4 space-y-2">
              {calibrationDone && session.gaze_tracking_enabled && (
                <div className="flex items-center gap-2 rounded-lg bg-emerald-50 px-3 py-2 text-xs text-emerald-700">
                  <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-500" />
                  Gaze tracking active
                </div>
              )}
              {session.click_tracking_enabled && (
                <div className="flex items-center gap-2 rounded-lg bg-blue-50 px-3 py-2 text-xs text-blue-700">
                  <span className="h-2 w-2 animate-pulse rounded-full bg-blue-500" />
                  Click tracking active
                </div>
              )}
              {calibrationDone && (
                <div className="flex items-center gap-2 rounded-lg bg-slate-100 px-3 py-2 text-xs text-slate-600">
                  <CheckCircleIcon className="h-3 w-3" />
                  Calibration completed
                </div>
              )}
            </div>
          </div>

          <div className="surface-panel-soft px-6 py-6">
            <div className="flex items-center justify-between gap-4">
              <p className="section-kicker">Language</p>
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
            <div className="mt-5 space-y-4 text-[14px] leading-7 text-slate-500">
              <p>Assigned group: <span className="font-medium text-black">{session.assigned_group}</span></p>
              <p>Click tracking: <span className="font-medium text-black">{session.click_tracking_enabled ? "On" : "Off"}</span></p>
              <p>Gaze tracking: <span className="font-medium text-black">{session.gaze_tracking_enabled ? "On" : "Off"}</span></p>
            </div>
          </div>
        </aside>

        <main className="space-y-6">
          <div className="surface-panel-soft flex flex-col gap-3 px-6 py-5 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="section-kicker">Study instructions</p>
              <p className="mt-2 text-[14px] leading-7 text-slate-500">
                Please view each post below and interact as you normally would on social media.
              </p>
            </div>
            <div className="rounded-full bg-stone-100 px-4 py-2 text-[13px] text-slate-600">
              {totalPosts} total posts
            </div>
          </div>

          <div className="space-y-6">
            {session.posts.map((post) => {
              const title = post.display_title || post.fetched_title || "Untitled";
              const imageUrl = post.display_image_url || post.fetched_image_url;
              const source = post.fetched_source || new URL(post.original_url).hostname;
              const isLiked = likedPosts.has(post.id);
              const commentCount = post.display_comments_count + post.comments.length + (participantComments[post.id]?.length || 0);

              return (
                <div key={post.id} data-post-id={post.id} className="surface-panel overflow-hidden">
                  <div className="flex items-center gap-3 px-6 pt-6">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-stone-100 text-[13px] font-semibold text-slate-500">
                      {source.charAt(0).toUpperCase()}
                    </div>
                    <div>
                      <p className="text-[13px] font-semibold text-black">{source}</p>
                      <p className="text-[11px] uppercase tracking-[0.2em] text-slate-400">Sponsored article</p>
                    </div>
                  </div>

                  <div className="mt-5 cursor-pointer" data-track="headline" onClick={() => handleClickPost(post.id, post.original_url)}>
                    {imageUrl && (
                      <div data-track="image">
                        <img src={imageUrl} alt="" className="h-72 w-full object-cover" />
                      </div>
                    )}
                    <div className="border-y bg-stone-50 px-6 py-5">
                      <p className="section-kicker">{source}</p>
                      <h2 className="mt-3 text-[22px] font-semibold leading-tight tracking-[-0.05em] text-black md:text-[24px]">{title}</h2>
                      <div className="mt-4 inline-flex items-center gap-2 text-[13px] text-slate-500">
                        <LinkIcon className="h-4 w-4" />
                        <span className="truncate">{post.original_url}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex flex-wrap items-center gap-6 px-6 py-4 text-[13px] text-slate-500">
                    {post.show_likes && <span>{(post.display_likes + (isLiked ? 1 : 0)).toLocaleString()} likes</span>}
                    {post.show_comments && <span>{commentCount} {t(locale, "comments")}</span>}
                    {post.show_shares && <span>{post.display_shares} {t(locale, "shares")}</span>}
                  </div>

                  <div className="grid border-t text-[13px] md:grid-cols-3">
                    <button
                      data-track="like"
                      onClick={() => handleLike(post.id)}
                      className={`px-4 py-4 font-medium transition hover:bg-black/[0.03] ${
                        isLiked ? "bg-black text-white hover:bg-neutral-800" : "text-slate-600"
                      }`}
                    >
                      {isLiked ? t(locale, "liked") : t(locale, "like")}
                    </button>
                    <button
                      data-track="comment"
                      onClick={() => setShowCommentInput(showCommentInput === post.id ? null : post.id)}
                      className="border-t px-4 py-4 font-medium text-slate-600 transition hover:bg-black/[0.03] md:border-l md:border-t-0"
                    >
                      {t(locale, "comment")}
                    </button>
                    <button
                      data-track="share"
                      onClick={() => {
                        api.recordInteraction(session.response_id, { post_id: post.id, action_type: "share" });
                      }}
                      className="border-t px-4 py-4 font-medium text-slate-600 transition hover:bg-black/[0.03] md:border-l md:border-t-0"
                    >
                      Share
                    </button>
                  </div>

                  {(post.comments.length > 0 || (participantComments[post.id]?.length || 0) > 0) && (
                    <div className="border-t px-6 py-6">
                      <div className="space-y-3">
                        {post.comments.map((comment) => (
                          <div key={`r-${comment.id}`} className="rounded-[18px] bg-stone-50 px-4 py-4">
                            <p className="text-[13px] font-semibold text-black">{comment.author_name}</p>
                            <p className="mt-1 text-[13px] leading-6 text-slate-600">{comment.text}</p>
                          </div>
                        ))}

                        {(participantComments[post.id] || []).map((comment) => (
                          <div key={`p-${comment.id}`} className="rounded-[18px] border bg-white px-4 py-4">
                            <div className="flex items-start justify-between gap-4">
                              <div className="flex-1">
                                <p className="text-[13px] font-semibold text-black">Your comment</p>
                                <input
                                  className="mt-2 w-full border-0 bg-transparent p-0 text-[13px] leading-6 text-slate-600 outline-none"
                                  value={comment.text}
                                  onChange={(e) => {
                                    const value = e.target.value;
                                    setParticipantComments((prev) => ({
                                      ...prev,
                                      [post.id]: (prev[post.id] || []).map((item) =>
                                        item.id === comment.id ? { ...item, text: value } : item,
                                      ),
                                    }));
                                  }}
                                  onBlur={async (e) => {
                                    const value = e.target.value;
                                    if (value.trim()) {
                                      await api.updateParticipantComment(session.response_id, comment.id, value);
                                    }
                                  }}
                                />
                              </div>
                              <button
                                className="rounded-full border px-3 py-1 text-[11px] font-medium text-slate-500 transition hover:bg-black/[0.03] hover:text-black"
                                onClick={async () => {
                                  await api.deleteParticipantComment(session.response_id, comment.id);
                                  setParticipantComments((prev) => ({
                                    ...prev,
                                    [post.id]: (prev[post.id] || []).filter((item) => item.id !== comment.id),
                                  }));
                                }}
                              >
                                Delete
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {showCommentInput === post.id && (
                    <div className="border-t bg-stone-50 px-6 py-5">
                      <div className="flex flex-col gap-3 md:flex-row">
                        <input
                          type="text"
                          value={commentInputs[post.id] || ""}
                          onChange={(e) => setCommentInputs((prev) => ({ ...prev, [post.id]: e.target.value }))}
                          placeholder={t(locale, "writeComment")}
                          className="field-input flex-1"
                          onKeyDown={(e) => e.key === "Enter" && handleComment(post.id)}
                        />
                        <button onClick={() => handleComment(post.id)} className="primary-button min-w-[96px]">
                          OK
                        </button>
                      </div>
                    </div>
                  )}

                  {/* Post Questions */}
                  {post.questions && post.questions.length > 0 && (
                    <div className="border-t px-5 py-4 space-y-4">
                      <p className="text-xs font-semibold uppercase tracking-wider text-slate-400">Questions</p>
                      {post.questions
                        .sort((a, b) => a.order - b.order)
                        .map((q) => {
                          const answered = submittedQuestions.has(q.id);
                          const answer = questionAnswers[q.id] || {};
                          return (
                            <div key={q.id} className={`rounded-xl border p-4 ${answered ? "border-emerald-200 bg-emerald-50/50" : "border-slate-200 bg-slate-50"}`}>
                              <p className="text-sm font-medium text-slate-800">{q.text}</p>

                              {/* Free text */}
                              {q.question_type === "free_text" && (
                                <textarea
                                  className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-blue-400 focus:outline-none"
                                  rows={2}
                                  placeholder="Type your answer..."
                                  disabled={answered}
                                  value={answer.text || ""}
                                  onChange={(e) => setQuestionAnswers((prev) => ({ ...prev, [q.id]: { ...prev[q.id], text: e.target.value } }))}
                                />
                              )}

                              {/* Likert scale */}
                              {q.question_type === "likert" && q.config && (
                                <div className="mt-3">
                                  <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
                                    <span>{q.config.min_label || "Strongly Disagree"}</span>
                                    <span>{q.config.max_label || "Strongly Agree"}</span>
                                  </div>
                                  <div className="flex gap-2">
                                    {Array.from({ length: (q.config.max || 5) - (q.config.min || 1) + 1 }, (_, i) => {
                                      const val = (q.config!.min || 1) + i;
                                      const selected = answer.value === val;
                                      return (
                                        <button
                                          key={val}
                                          disabled={answered}
                                          onClick={() => setQuestionAnswers((prev) => ({ ...prev, [q.id]: { value: val } }))}
                                          className={`flex-1 rounded-lg border py-2 text-sm font-medium transition ${
                                            selected ? "border-blue-500 bg-blue-500 text-white" : "border-slate-200 bg-white text-slate-600 hover:bg-slate-100"
                                          } ${answered ? "opacity-60" : ""}`}
                                        >
                                          {val}
                                        </button>
                                      );
                                    })}
                                  </div>
                                </div>
                              )}

                              {/* Multiple choice */}
                              {q.question_type === "multiple_choice" && q.config?.options && (
                                <div className="mt-2 space-y-2">
                                  {q.config.options.map((opt) => {
                                    const selected = (answer.choices || []).includes(opt);
                                    return (
                                      <button
                                        key={opt}
                                        disabled={answered}
                                        onClick={() => {
                                          setQuestionAnswers((prev) => {
                                            const current = prev[q.id]?.choices || [];
                                            const next = selected ? current.filter((c) => c !== opt) : [...current, opt];
                                            return { ...prev, [q.id]: { choices: next } };
                                          });
                                        }}
                                        className={`block w-full rounded-lg border px-3 py-2 text-left text-sm transition ${
                                          selected ? "border-blue-500 bg-blue-50 text-blue-700" : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                                        } ${answered ? "opacity-60" : ""}`}
                                      >
                                        {opt}
                                      </button>
                                    );
                                  })}
                                </div>
                              )}

                              {/* Submit button */}
                              {!answered && (answer.text || answer.value || (answer.choices && answer.choices.length > 0)) && (
                                <button
                                  className="mt-2 rounded-lg bg-black px-4 py-1.5 text-xs font-medium text-white hover:bg-slate-800"
                                  onClick={async () => {
                                    if (!session) return;
                                    await api.submitQuestionResponse(session.response_id, q.id, {
                                      question_id: q.id,
                                      answer_text: answer.text,
                                      answer_value: answer.value,
                                      answer_choices: answer.choices,
                                    });
                                    setSubmittedQuestions((prev) => new Set([...prev, q.id]));
                                  }}
                                >
                                  Submit Answer
                                </button>
                              )}
                              {answered && <p className="mt-1 text-xs text-emerald-600">Answer submitted</p>}
                            </div>
                          );
                        })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </main>

        <aside className="space-y-6 xl:sticky xl:top-6 xl:self-start">
          <div className="surface-panel-soft px-6 py-6">
            <p className="section-kicker">Progress</p>
            <p className="mt-3 text-[32px] font-semibold tracking-[-0.06em] text-black">
              {Math.min(totalPosts, Math.max(1, interactedPosts))}
            </p>
            <p className="mt-2 text-[13px] leading-6 text-slate-500">Interaction markers recorded across {totalPosts} posts</p>
          </div>

          <div className="surface-panel-soft px-6 py-6">
            <p className="section-kicker">Research notes</p>
            <div className="mt-5 space-y-4">
              {researchNotes.map((item) => (
                <div key={item} className="flex gap-3">
                  <CheckCircleIcon className="mt-0.5 h-4 w-4 text-black" />
                  <p className="text-[14px] leading-7 text-slate-500">{item}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="surface-panel px-6 py-6">
            <div className="flex items-start gap-3">
              <UsersIcon className="mt-1 h-4 w-4 text-slate-500" />
              <p className="text-[14px] leading-7 text-slate-500">
                Stay in the feed until you have reviewed all posts. You can edit or remove your own comments before
                completion.
              </p>
            </div>
            <button onClick={handleComplete} className="primary-button mt-6 w-full py-3">
              {t(locale, "complete")}
            </button>
          </div>
        </aside>
      </div>
    </div>
  );
}