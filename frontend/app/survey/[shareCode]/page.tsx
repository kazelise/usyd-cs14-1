"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { CalibrationExperience } from "@/components/calibration-experience";

interface Comment {
  id: number;
  author_name: string;
  text: string;
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

export default function SurveyParticipantPage() {
  const params = useParams();
  const shareCode = params.shareCode as string;

  const [session, setSession] = useState<SurveySession | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [completed, setCompleted] = useState(false);
  const [calibrationDone, setCalibrationDone] = useState(false);

  const [likedPosts, setLikedPosts] = useState<Set<number>>(new Set());
  const [commentInputs, setCommentInputs] = useState<Record<number, string>>({});
  const [showCommentInput, setShowCommentInput] = useState<number | null>(null);

  const clickBuffer = useRef<
    Array<{
      post_id: number | null;
      timestamp_ms: number;
      screen_x: number;
      screen_y: number;
      target_element: string;
    }>
  >([]);

  useEffect(() => {
    let flushInterval: ReturnType<typeof setInterval> | null = null;
    let clickListener: ((e: MouseEvent) => void) | null = null;

    async function init() {
      try {
        const res = await api.startSurvey(shareCode);
        setSession(res);
        setCalibrationDone(!res.calibration_required);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Survey not found");
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

  useEffect(() => {
    if (!session || !calibrationDone || !session.click_tracking_enabled) return;

    const clickListener = (event: MouseEvent) => handleClick(event);
    const flushInterval = window.setInterval(() => flushClicks(session.response_id), 10000);
    document.addEventListener("click", clickListener);

    return () => {
      document.removeEventListener("click", clickListener);
      window.clearInterval(flushInterval);
    };
  }, [calibrationDone, session]);

  function handleClick(event: MouseEvent) {
    const target = event.target as HTMLElement;
    let targetElement = "other";
    if (target.closest("[data-track='headline']")) targetElement = "headline";
    else if (target.closest("[data-track='image']")) targetElement = "image";
    else if (target.closest("[data-track='like']")) targetElement = "like_button";
    else if (target.closest("[data-track='comment']")) targetElement = "comment_button";
    else if (target.closest("[data-track='share']")) targetElement = "share_count";

    const postElement = target.closest("[data-post-id]");
    const postId = postElement ? Number(postElement.getAttribute("data-post-id")) : null;

    clickBuffer.current.push({
      post_id: postId,
      timestamp_ms: Date.now(),
      screen_x: event.clientX,
      screen_y: event.clientY,
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
    if (!session || likedPosts.has(postId)) return;
    setLikedPosts((previous) => new Set(previous).add(postId));
    await api.recordInteraction(session.response_id, {
      post_id: postId,
      action_type: "like",
    });
  }

  async function handleComment(postId: number) {
    if (!session) return;
    const text = commentInputs[postId];
    if (!text?.trim()) return;

    await api.recordInteraction(session.response_id, {
      post_id: postId,
      action_type: "comment",
      comment_text: text,
    });
    setCommentInputs((previous) => ({ ...previous, [postId]: "" }));
    setShowCommentInput(null);
  }

  async function handleClickPost(postId: number, url: string) {
    if (!session) return;
    await api.recordInteraction(session.response_id, {
      post_id: postId,
      action_type: "click",
    });
    window.open(url, "_blank", "noopener,noreferrer");
  }

  async function handleComplete() {
    if (!session) return;
    await flushClicks(session.response_id);
    await api.completeSurvey(session.response_id);
    setCompleted(true);
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-300">
        Loading survey session...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 p-6">
        <div className="rounded-3xl border border-rose-400/20 bg-rose-400/10 px-6 py-5 text-rose-100">
          {error}
        </div>
      </div>
    );
  }

  if (completed) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top,#022c22_0%,#052e16_40%,#020617_100%)] px-6 text-white">
        <div className="max-w-lg rounded-[32px] border border-white/10 bg-white/6 p-10 text-center shadow-2xl backdrop-blur">
          <p className="text-xs uppercase tracking-[0.28em] text-emerald-200">Session Completed</p>
          <h1 className="mt-4 text-4xl font-semibold tracking-tight">Thank you.</h1>
          <p className="mt-3 text-sm leading-7 text-emerald-50/80">
            Your interactions, click data, and calibration session have been recorded.
          </p>
        </div>
      </div>
    );
  }

  if (!session) return null;

  if (!calibrationDone) {
    return (
      <CalibrationExperience
        responseId={session.response_id}
        onComplete={() => {
          setCalibrationDone(true);
        }}
      />
    );
  }

  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,#f8fafc_0%,#eff6ff_28%,#eef2ff_100%)]">
      <div className="mx-auto max-w-6xl px-4 py-10 lg:px-8">
        <div className="mb-10 flex flex-col gap-6 rounded-[32px] border border-slate-200 bg-white/85 p-8 shadow-[0_20px_60px_rgba(15,23,42,0.08)] backdrop-blur lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-sky-600">Participant Feed</p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-900">Social Media Survey</h1>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-500">
              Browse the posts below and interact naturally. Your click behavior is now being tracked for the active
              response session.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
              <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Group</p>
              <p className="mt-1 text-xl font-semibold text-slate-900">{session.assigned_group}</p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
              <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Calibration</p>
              <p className="mt-1 text-xl font-semibold text-emerald-600">Done</p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3">
              <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Posts</p>
              <p className="mt-1 text-xl font-semibold text-slate-900">{session.posts.length}</p>
            </div>
          </div>
        </div>

        <div className="space-y-8">
          {session.posts.map((post) => {
            const title = post.display_title || post.fetched_title || "Untitled";
            const imageUrl = post.display_image_url || post.fetched_image_url;
            const source = post.fetched_source || new URL(post.original_url).hostname;
            const isLiked = likedPosts.has(post.id);

            return (
              <article
                key={post.id}
                data-post-id={post.id}
                className="overflow-hidden rounded-[30px] border border-slate-200 bg-white shadow-[0_14px_40px_rgba(15,23,42,0.06)]"
              >
                <div className="flex items-center gap-3 px-6 pt-6">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-900 text-sm font-semibold text-white">
                    {source.charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <p className="font-medium text-slate-900">{source}</p>
                    <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Sponsored content</p>
                  </div>
                </div>

                <div className="mt-5 cursor-pointer" data-track="headline" onClick={() => handleClickPost(post.id, post.original_url)}>
                  {imageUrl && (
                    <div data-track="image" className="overflow-hidden">
                      <img src={imageUrl} alt="" className="h-80 w-full object-cover" />
                    </div>
                  )}
                  <div className="border-y border-slate-100 bg-slate-50/80 px-6 py-5">
                    <p className="text-xs uppercase tracking-[0.24em] text-slate-400">{source}</p>
                    <h2 className="mt-2 text-2xl font-semibold tracking-tight text-slate-900">{title}</h2>
                  </div>
                </div>

                <div className="flex flex-wrap items-center justify-between gap-3 px-6 py-4 text-sm text-slate-500">
                  <span>
                    {post.show_likes && <>👍 {(post.display_likes + (isLiked ? 1 : 0)).toLocaleString()}</>}
                  </span>
                  <span className="flex gap-4">
                    {post.show_comments && <span>{post.display_comments_count + post.comments.length} comments</span>}
                    {post.show_shares && <span>{post.display_shares} shares</span>}
                  </span>
                </div>

                <div className="grid border-t border-slate-100 sm:grid-cols-3">
                  <button
                    data-track="like"
                    onClick={() => handleLike(post.id)}
                    className={`px-4 py-4 text-sm font-medium transition hover:bg-slate-50 ${
                      isLiked ? "text-sky-600" : "text-slate-500"
                    }`}
                  >
                    {isLiked ? "Liked" : "Like"}
                  </button>
                  <button
                    data-track="comment"
                    onClick={() => setShowCommentInput(showCommentInput === post.id ? null : post.id)}
                    className="border-t border-slate-100 px-4 py-4 text-sm font-medium text-slate-500 transition hover:bg-slate-50 sm:border-l sm:border-t-0"
                  >
                    Comment
                  </button>
                  <button
                    data-track="share"
                    onClick={() => {
                      void api.recordInteraction(session.response_id, {
                        post_id: post.id,
                        action_type: "share",
                      });
                    }}
                    className="border-t border-slate-100 px-4 py-4 text-sm font-medium text-slate-500 transition hover:bg-slate-50 sm:border-l sm:border-t-0"
                  >
                    Share
                  </button>
                </div>

                {post.comments.length > 0 && (
                  <div className="space-y-3 border-t border-slate-100 px-6 py-5">
                    {post.comments.map((comment) => (
                      <div key={comment.id} className="flex gap-3">
                        <div className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-slate-200 text-xs font-semibold text-slate-600">
                          {comment.author_name.charAt(0)}
                        </div>
                        <div className="rounded-3xl bg-slate-100 px-4 py-3 text-sm text-slate-700">
                          <span className="font-semibold text-slate-900">{comment.author_name}</span>{" "}
                          {comment.text}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {showCommentInput === post.id && (
                  <div className="flex gap-3 border-t border-slate-100 px-6 py-5">
                    <input
                      type="text"
                      value={commentInputs[post.id] || ""}
                      onChange={(event) =>
                        setCommentInputs((previous) => ({ ...previous, [post.id]: event.target.value }))
                      }
                      onKeyDown={(event) => {
                        if (event.key === "Enter") {
                          void handleComment(post.id);
                        }
                      }}
                      placeholder="Write a comment..."
                      className="flex-1 rounded-full border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-sky-400"
                    />
                    <button
                      onClick={() => handleComment(post.id)}
                      className="rounded-full bg-slate-900 px-5 py-3 text-sm font-medium text-white transition hover:bg-slate-700"
                    >
                      Post
                    </button>
                  </div>
                )}
              </article>
            );
          })}
        </div>

        <div className="mt-12 text-center">
          <button
            onClick={handleComplete}
            className="rounded-full bg-emerald-500 px-8 py-4 text-sm font-semibold text-white shadow-lg shadow-emerald-500/20 transition hover:bg-emerald-600"
          >
            Complete Survey
          </button>
        </div>
      </div>
    </div>
  );
}
