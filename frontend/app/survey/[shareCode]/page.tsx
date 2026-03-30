"use client";
import { useEffect, useState, useRef } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";

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

  // Track likes per post
  const [likedPosts, setLikedPosts] = useState<Set<number>>(new Set());
  // Track comment inputs
  const [commentInputs, setCommentInputs] = useState<Record<number, string>>({});
  const [showCommentInput, setShowCommentInput] = useState<number | null>(null);

  // Click tracking buffer
  const clickBuffer = useRef<any[]>([]);

  useEffect(() => {
    let clickListener: ((e: MouseEvent) => void) | null = null;
    let flushInterval: ReturnType<typeof setInterval> | null = null;

    async function init() {
      try {
        const res = await api.startSurvey(shareCode);
        setSession(res);

        // Start click tracking
        if (res.click_tracking_enabled) {
          clickListener = handleClick;
          document.addEventListener("click", clickListener);
          flushInterval = setInterval(() => flushClicks(res.response_id), 10000);
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
    // Determine what element was clicked
    const target = e.target as HTMLElement;
    let targetElement = "other";
    if (target.closest("[data-track='headline']")) targetElement = "headline";
    else if (target.closest("[data-track='image']")) targetElement = "image";
    else if (target.closest("[data-track='like']")) targetElement = "like_button";
    else if (target.closest("[data-track='comment']")) targetElement = "comment_button";
    else if (target.closest("[data-track='share']")) targetElement = "share_count";

    // Find which post this click belongs to
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
      // Re-add to buffer on failure
      clickBuffer.current = [...batch, ...clickBuffer.current];
    }
  }

  async function handleLike(postId: number) {
    if (!session || likedPosts.has(postId)) return;
    setLikedPosts((prev) => new Set(prev).add(postId));
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
    setCommentInputs((prev) => ({ ...prev, [postId]: "" }));
    setShowCommentInput(null);
  }

  async function handleClickPost(postId: number, url: string) {
    if (!session) return;
    await api.recordInteraction(session.response_id, {
      post_id: postId,
      action_type: "click",
    });
    window.open(url, "_blank");
  }

  async function handleComplete() {
    if (!session) return;
    await flushClicks(session.response_id);
    await api.completeSurvey(session.response_id);
    setCompleted(true);
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-gray-400">Loading survey...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <p className="text-red-500">{error}</p>
      </div>
    );
  }

  if (completed) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-2">Thank you!</h1>
          <p className="text-gray-500">Your responses have been recorded.</p>
        </div>
      </div>
    );
  }

  if (!session) return null;

  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      <div className="mb-8 text-center">
        <h1 className="text-xl font-semibold">Social Media Survey</h1>
        <p className="text-sm text-gray-400 mt-1">
          Please view each post below and interact as you normally would on social media.
        </p>
      </div>

      {/* Posts Feed */}
      <div className="space-y-6">
        {session.posts.map((post) => {
          const title = post.display_title || post.fetched_title || "Untitled";
          const imageUrl = post.display_image_url || post.fetched_image_url;
          const source = post.fetched_source || new URL(post.original_url).hostname;
          const isLiked = likedPosts.has(post.id);

          return (
            <div key={post.id} data-post-id={post.id} className="bg-white rounded-lg border shadow-sm">
              {/* Post Header */}
              <div className="px-4 pt-4 pb-2 flex items-center gap-3">
                <div className="w-10 h-10 bg-gray-200 rounded-full flex items-center justify-center text-xs font-bold text-gray-500">
                  {source.charAt(0).toUpperCase()}
                </div>
                <div>
                  <p className="font-semibold text-sm">{source}</p>
                  <p className="text-xs text-gray-400">Sponsored</p>
                </div>
              </div>

              {/* Clickable Content → opens original article */}
              <div
                className="cursor-pointer"
                data-track="headline"
                onClick={() => handleClickPost(post.id, post.original_url)}
              >
                {imageUrl && (
                  <div data-track="image">
                    <img src={imageUrl} alt="" className="w-full h-64 object-cover" />
                  </div>
                )}
                <div className="px-4 py-3 bg-gray-50 border-t border-b">
                  <p className="text-xs text-gray-400 uppercase">{source}</p>
                  <h2 className="font-semibold mt-1">{title}</h2>
                </div>
              </div>

              {/* Engagement Counts */}
              <div className="px-4 py-2 flex items-center justify-between text-sm text-gray-500">
                <span>
                  {post.show_likes && (
                    <>👍 {(post.display_likes + (isLiked ? 1 : 0)).toLocaleString()}</>
                  )}
                </span>
                <span className="flex gap-4">
                  {post.show_comments && (
                    <span>{post.display_comments_count + post.comments.length} comments</span>
                  )}
                  {post.show_shares && <span>{post.display_shares} shares</span>}
                </span>
              </div>

              {/* Action Buttons */}
              <div className="border-t flex">
                <button
                  data-track="like"
                  onClick={() => handleLike(post.id)}
                  className={`flex-1 py-2 text-sm font-medium text-center hover:bg-gray-50 ${
                    isLiked ? "text-blue-600" : "text-gray-500"
                  }`}
                >
                  {isLiked ? "👍 Liked" : "👍 Like"}
                </button>
                <button
                  data-track="comment"
                  onClick={() => setShowCommentInput(showCommentInput === post.id ? null : post.id)}
                  className="flex-1 py-2 text-sm font-medium text-gray-500 text-center hover:bg-gray-50 border-l"
                >
                  💬 Comment
                </button>
                <button
                  data-track="share"
                  onClick={() => {
                    if (session) {
                      api.recordInteraction(session.response_id, {
                        post_id: post.id,
                        action_type: "share",
                      });
                    }
                  }}
                  className="flex-1 py-2 text-sm font-medium text-gray-500 text-center hover:bg-gray-50 border-l"
                >
                  🔗 Share
                </button>
              </div>

              {/* Fake Comments from Researcher */}
              {post.comments.length > 0 && (
                <div className="border-t px-4 py-3 space-y-2">
                  {post.comments.map((c) => (
                    <div key={c.id} className="flex gap-2">
                      <div className="w-7 h-7 bg-gray-200 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-bold text-gray-500">
                        {c.author_name.charAt(0)}
                      </div>
                      <div className="bg-gray-100 rounded-2xl px-3 py-2 text-sm">
                        <span className="font-semibold">{c.author_name}</span>{" "}
                        <span className="text-gray-700">{c.text}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Participant Comment Input */}
              {showCommentInput === post.id && (
                <div className="border-t px-4 py-3 flex gap-2">
                  <input
                    type="text"
                    value={commentInputs[post.id] || ""}
                    onChange={(e) => setCommentInputs((prev) => ({ ...prev, [post.id]: e.target.value }))}
                    placeholder="Write a comment..."
                    className="flex-1 px-3 py-2 border rounded-full text-sm"
                    onKeyDown={(e) => e.key === "Enter" && handleComment(post.id)}
                  />
                  <button
                    onClick={() => handleComment(post.id)}
                    className="px-3 py-1 bg-blue-600 text-white rounded-full text-sm"
                  >
                    Post
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Complete Button */}
      <div className="mt-10 text-center">
        <button
          onClick={handleComplete}
          className="px-8 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium"
        >
          Complete Survey
        </button>
      </div>
    </div>
  );
}
