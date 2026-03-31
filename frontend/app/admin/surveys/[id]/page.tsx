"use client";
import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { api } from "@/lib/api";

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
  description: string | null;
  title: string;
  status: string;
  share_code: string;
  num_groups: number;
  gaze_tracking_enabled: boolean;
  gaze_interval_ms: number;
  click_tracking_enabled: boolean;
  calibration_enabled: boolean;
  calibration_points: number;
}

export default function SurveyEditPage() {
  const router = useRouter();
  const params = useParams();
  const surveyId = Number(params.id);

  const [survey, setSurvey] = useState<Survey | null>(null);
  const [posts, setPosts] = useState<Post[]>([]);
  const [newUrl, setNewUrl] = useState("");
  const [addingPost, setAddingPost] = useState(false);
  const [error, setError] = useState("");
  const [savingSettings, setSavingSettings] = useState(false);
  const [settingsSaved, setSettingsSaved] = useState("");

  const [surveyTitle, setSurveyTitle] = useState("");
  const [surveyDescription, setSurveyDescription] = useState("");
  const [gazeTrackingEnabled, setGazeTrackingEnabled] = useState(true);
  const [clickTrackingEnabled, setClickTrackingEnabled] = useState(true);
  const [calibrationEnabled, setCalibrationEnabled] = useState(true);
  const [gazeIntervalMs, setGazeIntervalMs] = useState(1000);
  const [calibrationPoints, setCalibrationPoints] = useState(9);

  // Edit post state
  const [editingPost, setEditingPost] = useState<number | null>(null);
  const [editLikes, setEditLikes] = useState(0);
  const [editComments, setEditComments] = useState(0);
  const [editShares, setEditShares] = useState(0);
  const [editTitle, setEditTitle] = useState("");

  // A/B group visibility state
  const [editingGroups, setEditingGroups] = useState<number | null>(null);
  const [groupVisibility, setGroupVisibility] = useState<number[]>([]);
  const [groupOverrides, setGroupOverrides] = useState<Record<string, { display_likes: number; display_comments_count: number; display_shares: number }>>({});

  // Add comment state
  const [commentPostId, setCommentPostId] = useState<number | null>(null);
  const [commentAuthor, setCommentAuthor] = useState("");
  const [commentText, setCommentText] = useState("");

  useEffect(() => {
    loadData();
  }, [surveyId]);

  async function loadData() {
    try {
      const [s, p] = await Promise.all([
        api.getSurvey(surveyId),
        api.listPosts(surveyId),
      ]);
      setSurvey(s);
      setSurveyTitle(s.title);
      setSurveyDescription(s.description || "");
      setGazeTrackingEnabled(s.gaze_tracking_enabled);
      setClickTrackingEnabled(s.click_tracking_enabled);
      setCalibrationEnabled(s.calibration_enabled);
      setGazeIntervalMs(s.gaze_interval_ms);
      setCalibrationPoints(s.calibration_points);
      setPosts(p);
    } catch {
      router.push("/auth");
    }
  }

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
    await api.addComment(surveyId, commentPostId, {
      author_name: commentAuthor,
      text: commentText,
    });
    setCommentPostId(null);
    setCommentAuthor("");
    setCommentText("");
    await loadData();
  }

  function startEditGroups(post: Post) {
    setEditingGroups(post.id);
    // Initialize with all groups visible if not set
    const allGroups = Array.from({ length: survey?.num_groups || 1 }, (_, i) => i + 1);
    setGroupVisibility(post.visible_to_groups || allGroups);
    // Initialize group overrides
    const overrides: Record<string, { display_likes: number; display_comments_count: number; display_shares: number }> = {};
    for (const g of allGroups) {
      const existing = (post as any).group_overrides?.[String(g)];
      overrides[String(g)] = {
        display_likes: existing?.display_likes ?? post.display_likes,
        display_comments_count: existing?.display_comments_count ?? post.display_comments_count,
        display_shares: existing?.display_shares ?? post.display_shares,
      };
    }
    setGroupOverrides(overrides);
  }

  async function saveGroupSettings(postId: number) {
    // Only send group_overrides if values actually differ between groups
    const vals = Object.values(groupOverrides);
    const allSame = vals.every(
      (v) => v.display_likes === vals[0].display_likes &&
        v.display_comments_count === vals[0].display_comments_count &&
        v.display_shares === vals[0].display_shares
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
    await loadData();
  }

  async function saveSurveySettings() {
    setSavingSettings(true);
    setSettingsSaved("");
    try {
      await api.updateSurvey(surveyId, {
        title: surveyTitle,
        description: surveyDescription || null,
        gaze_tracking_enabled: gazeTrackingEnabled,
        click_tracking_enabled: clickTrackingEnabled,
        calibration_enabled: calibrationEnabled,
        gaze_interval_ms: gazeIntervalMs,
        calibration_points: calibrationPoints,
      });
      setSettingsSaved("Camera settings saved.");
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save survey settings.");
    } finally {
      setSavingSettings(false);
    }
  }

  if (!survey) return <p className="text-gray-400 mt-10">Loading...</p>;

  const shareUrl = typeof window !== "undefined"
    ? `${window.location.origin}/survey/${survey.share_code}`
    : "";

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">{survey.title}</h1>
          <p className="text-sm text-gray-400 mt-1">
            {survey.num_groups > 1 ? `${survey.num_groups} A/B groups` : "No A/B testing"} ·{" "}
            {posts.length} post(s)
          </p>
        </div>
        <div className="flex items-center gap-3">
          {survey.status === "published" && (
            <div className="text-sm bg-gray-100 px-3 py-1 rounded-lg font-mono">
              {shareUrl}
            </div>
          )}
          {survey.status === "draft" && (
            <button
              onClick={publishSurvey}
              disabled={posts.length === 0}
              className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 text-sm"
            >
              Publish Survey
            </button>
          )}
          <span
            className={`text-xs px-2 py-1 rounded-full ${
              survey.status === "published" ? "bg-green-100 text-green-700" : "bg-yellow-100 text-yellow-700"
            }`}
          >
            {survey.status}
          </span>
        </div>
      </div>

      {/* Add Post by URL */}
      <section className="mb-8 grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_340px]">
        <div className="overflow-hidden rounded-[28px] border border-slate-200 bg-white shadow-[0_20px_60px_rgba(15,23,42,0.08)]">
          <div className="border-b border-slate-100 bg-[linear-gradient(135deg,#f8fafc_0%,#ecfeff_100%)] px-6 py-5">
            <p className="text-xs uppercase tracking-[0.28em] text-sky-600">Camera Configuration</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight text-slate-900">Webcam calibration UI</h2>
            <p className="mt-2 max-w-2xl text-sm leading-7 text-slate-500">
              Configure the participant-facing camera permission, face detection, calibration dots, and quality review flow.
            </p>
          </div>

          <div className="grid gap-6 p-6 lg:grid-cols-2">
            <div className="space-y-4">
              <div>
                <label className="mb-1 block text-[11px] font-semibold uppercase tracking-[0.26em] text-slate-400">
                  Survey title
                </label>
                <input
                  type="text"
                  value={surveyTitle}
                  onChange={(e) => setSurveyTitle(e.target.value)}
                  className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-sky-400"
                />
              </div>
              <div>
                <label className="mb-1 block text-[11px] font-semibold uppercase tracking-[0.26em] text-slate-400">
                  Survey description
                </label>
                <textarea
                  value={surveyDescription}
                  onChange={(e) => setSurveyDescription(e.target.value)}
                  rows={4}
                  className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-sky-400"
                />
              </div>
              <div>
                <label className="mb-1 block text-[11px] font-semibold uppercase tracking-[0.26em] text-slate-400">
                  Gaze sampling interval
                </label>
                <input
                  type="number"
                  min={250}
                  step={250}
                  value={gazeIntervalMs}
                  onChange={(e) => setGazeIntervalMs(Number(e.target.value))}
                  className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-sky-400"
                />
              </div>
            </div>

            <div className="space-y-4">
              {[
                {
                  label: "Calibration required",
                  description: "Participant must pass the webcam setup before the survey feed unlocks.",
                  checked: calibrationEnabled,
                  onChange: setCalibrationEnabled,
                },
                {
                  label: "Gaze tracking enabled",
                  description: "Allows continuous gaze samples during survey participation.",
                  checked: gazeTrackingEnabled,
                  onChange: setGazeTrackingEnabled,
                },
                {
                  label: "Click tracking enabled",
                  description: "Records participant click coordinates and target metadata.",
                  checked: clickTrackingEnabled,
                  onChange: setClickTrackingEnabled,
                },
              ].map((item) => (
                <label key={item.label} className="flex items-start gap-4 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-4">
                  <input
                    type="checkbox"
                    checked={item.checked}
                    onChange={(e) => item.onChange(e.target.checked)}
                    className="mt-1 h-4 w-4 rounded border-slate-300 text-slate-900"
                  />
                  <div>
                    <p className="text-sm font-semibold text-slate-900">{item.label}</p>
                    <p className="mt-1 text-sm leading-6 text-slate-500">{item.description}</p>
                  </div>
                </label>
              ))}

              <div>
                <label className="mb-1 block text-[11px] font-semibold uppercase tracking-[0.26em] text-slate-400">
                  Calibration points
                </label>
                <select
                  value={calibrationPoints}
                  onChange={(e) => setCalibrationPoints(Number(e.target.value))}
                  className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm outline-none transition focus:border-sky-400"
                >
                  <option value={5}>5 points</option>
                  <option value={9}>9 points</option>
                </select>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between border-t border-slate-100 px-6 py-4">
            <div className="text-sm text-slate-500">{settingsSaved || "Changes stay local until you publish the survey."}</div>
            <button
              onClick={saveSurveySettings}
              disabled={savingSettings}
              className="rounded-full bg-slate-900 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-700 disabled:opacity-50"
            >
              {savingSettings ? "Saving..." : "Save Camera Settings"}
            </button>
          </div>
        </div>

        <div className="rounded-[28px] border border-slate-200 bg-slate-950 p-6 text-white shadow-[0_20px_60px_rgba(15,23,42,0.12)]">
          <p className="text-xs uppercase tracking-[0.28em] text-cyan-300">Participant Preview</p>
          <h3 className="mt-3 text-2xl font-semibold tracking-tight">Calibration pipeline</h3>
          <div className="mt-6 space-y-4 text-sm text-slate-300">
            <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
              <p className="font-medium text-white">1. Camera permission</p>
              <p className="mt-1 leading-6">Request webcam access and create the calibration session after the stream is live.</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
              <p className="font-medium text-white">2. Face detected indicator</p>
              <p className="mt-1 leading-6">Show live status, brightness diagnostics, and stability feedback before dot capture starts.</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
              <p className="font-medium text-white">3. Calibration dots animation</p>
              <p className="mt-1 leading-6">Capture 12 samples per point and submit each point to the tracking API.</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
              <p className="font-medium text-white">4. Quality score display</p>
              <p className="mt-1 leading-6">Present backend quality metrics before unlocking the participant survey feed.</p>
            </div>
          </div>
        </div>
      </section>

      {survey.status === "draft" && (
        <form onSubmit={addPost} className="mb-8 bg-white p-4 rounded-lg border">
          <label className="block text-sm font-medium mb-2">
            Add a social media post — paste a news article URL
          </label>
          <div className="flex gap-2">
            <input
              type="url" value={newUrl} onChange={(e) => setNewUrl(e.target.value)}
              placeholder="https://www.bbc.com/news/article-example"
              className="flex-1 px-4 py-2 border rounded-lg text-sm" required
            />
            <button
              type="submit" disabled={addingPost}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 text-sm whitespace-nowrap"
            >
              {addingPost ? "Fetching..." : "Add Post"}
            </button>
          </div>
          {error && <p className="text-red-500 text-sm mt-2">{error}</p>}
          <p className="text-xs text-gray-400 mt-2">
            The platform will automatically fetch the headline, image, and source from the link.
          </p>
        </form>
      )}

      {/* Posts */}
      <div className="space-y-4">
        {posts.map((post) => (
          <div key={post.id} className="bg-white rounded-lg border overflow-hidden">
            {/* Post Preview Card */}
            <div className="p-4">
              <div className="flex items-start gap-4">
                {(post.display_image_url || post.fetched_image_url) && (
                  <img
                    src={post.display_image_url || post.fetched_image_url || ""}
                    alt="" className="w-32 h-20 object-cover rounded"
                  />
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-gray-400 mb-1">
                    {post.fetched_source || new URL(post.original_url).hostname}
                  </p>
                  <h3 className="font-semibold text-sm leading-tight">
                    {post.display_title || post.fetched_title || "Untitled"}
                  </h3>
                  <a
                    href={post.original_url} target="_blank" rel="noopener noreferrer"
                    className="text-xs text-blue-500 hover:underline mt-1 inline-block truncate max-w-md"
                  >
                    {post.original_url}
                  </a>
                </div>
                {survey.status === "draft" && (
                  <button onClick={() => deletePost(post.id)} className="text-gray-300 hover:text-red-500 text-lg">
                    ×
                  </button>
                )}
              </div>

              {/* Engagement Numbers */}
              <div className="flex gap-6 mt-3 text-sm text-gray-500 border-t pt-3">
                {post.show_likes && <span>👍 {post.display_likes.toLocaleString()} likes</span>}
                {post.show_comments && <span>💬 {post.display_comments_count} comments</span>}
                {post.show_shares && <span>🔗 {post.display_shares} shares</span>}
              </div>

              {/* Researcher Comments */}
              {post.comments.length > 0 && (
                <div className="mt-3 border-t pt-3 space-y-2">
                  {post.comments.map((c) => (
                    <div key={c.id} className="text-sm">
                      <span className="font-medium">{c.author_name}</span>{" "}
                      <span className="text-gray-600">{c.text}</span>
                    </div>
                  ))}
                </div>
              )}

              {/* Group Visibility */}
              {post.visible_to_groups && (
                <p className="text-xs text-gray-400 mt-2">
                  Visible to groups: {post.visible_to_groups.join(", ")}
                </p>
              )}
            </div>

            {/* Edit Controls */}
            {survey.status === "draft" && (
              <div className="bg-gray-50 border-t px-4 py-2 flex gap-2">
                {editingPost === post.id ? (
                  <div className="flex flex-wrap gap-2 items-center w-full">
                    <input
                      type="text" value={editTitle} onChange={(e) => setEditTitle(e.target.value)}
                      placeholder="Override title" className="flex-1 px-2 py-1 border rounded text-sm min-w-48"
                    />
                    <div className="flex gap-2 items-center">
                      <label className="text-xs text-gray-500">Likes</label>
                      <input type="number" value={editLikes} onChange={(e) => setEditLikes(Number(e.target.value))}
                        className="w-20 px-2 py-1 border rounded text-sm" />
                      <label className="text-xs text-gray-500">Comments</label>
                      <input type="number" value={editComments} onChange={(e) => setEditComments(Number(e.target.value))}
                        className="w-20 px-2 py-1 border rounded text-sm" />
                      <label className="text-xs text-gray-500">Shares</label>
                      <input type="number" value={editShares} onChange={(e) => setEditShares(Number(e.target.value))}
                        className="w-20 px-2 py-1 border rounded text-sm" />
                    </div>
                    <button onClick={() => saveEdit(post.id)}
                      className="px-3 py-1 bg-blue-600 text-white rounded text-sm">Save</button>
                    <button onClick={() => setEditingPost(null)}
                      className="px-3 py-1 text-gray-500 text-sm">Cancel</button>
                  </div>
                ) : (
                  <>
                    <button onClick={() => startEdit(post)}
                      className="text-xs text-blue-600 hover:underline">Edit Numbers</button>
                    <button onClick={() => { setCommentPostId(post.id); setCommentAuthor(""); setCommentText(""); }}
                      className="text-xs text-blue-600 hover:underline">Add Comment</button>
                    {survey.num_groups > 1 && (
                      <button onClick={() => startEditGroups(post)}
                        className="text-xs text-purple-600 hover:underline">A/B Groups</button>
                    )}
                  </>
                )}
              </div>
            )}

            {/* Add Comment Form */}
            {/* A/B Group Settings Panel */}
            {editingGroups === post.id && survey.num_groups > 1 && (
              <div className="bg-purple-50 border-t px-4 py-3 space-y-3">
                <p className="text-sm font-medium text-purple-700">A/B Group Settings</p>
                {/* Visibility checkboxes */}
                <div className="flex gap-4 items-center">
                  <span className="text-xs text-gray-500">Visible to:</span>
                  {Array.from({ length: survey.num_groups }, (_, i) => i + 1).map((g) => (
                    <label key={g} className="flex items-center gap-1 text-sm">
                      <input
                        type="checkbox"
                        checked={groupVisibility.includes(g)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setGroupVisibility((prev) => [...prev, g].sort());
                          } else {
                            setGroupVisibility((prev) => prev.filter((x) => x !== g));
                          }
                        }}
                      />
                      Group {g}
                    </label>
                  ))}
                </div>
                {/* Per-group number overrides */}
                <div className="space-y-2">
                  <span className="text-xs text-gray-500">Per-group engagement numbers:</span>
                  {Array.from({ length: survey.num_groups }, (_, i) => i + 1)
                    .filter((g) => groupVisibility.includes(g))
                    .map((g) => (
                    <div key={g} className="flex gap-2 items-center">
                      <span className="text-xs font-medium w-16">Group {g}:</span>
                      <label className="text-xs text-gray-500">Likes</label>
                      <input
                        type="number"
                        value={groupOverrides[String(g)]?.display_likes ?? 0}
                        onChange={(e) => setGroupOverrides((prev) => ({
                          ...prev,
                          [String(g)]: { ...prev[String(g)], display_likes: Number(e.target.value) },
                        }))}
                        className="w-20 px-2 py-1 border rounded text-sm"
                      />
                      <label className="text-xs text-gray-500">Comments</label>
                      <input
                        type="number"
                        value={groupOverrides[String(g)]?.display_comments_count ?? 0}
                        onChange={(e) => setGroupOverrides((prev) => ({
                          ...prev,
                          [String(g)]: { ...prev[String(g)], display_comments_count: Number(e.target.value) },
                        }))}
                        className="w-20 px-2 py-1 border rounded text-sm"
                      />
                      <label className="text-xs text-gray-500">Shares</label>
                      <input
                        type="number"
                        value={groupOverrides[String(g)]?.display_shares ?? 0}
                        onChange={(e) => setGroupOverrides((prev) => ({
                          ...prev,
                          [String(g)]: { ...prev[String(g)], display_shares: Number(e.target.value) },
                        }))}
                        className="w-20 px-2 py-1 border rounded text-sm"
                      />
                    </div>
                  ))}
                </div>
                <div className="flex gap-2">
                  <button onClick={() => saveGroupSettings(post.id)}
                    className="px-3 py-1 bg-purple-600 text-white rounded text-sm">Save Groups</button>
                  <button onClick={() => setEditingGroups(null)}
                    className="px-3 py-1 text-gray-500 text-sm">Cancel</button>
                </div>
              </div>
            )}

            {commentPostId === post.id && (
              <form onSubmit={addComment} className="bg-blue-50 border-t px-4 py-3 flex gap-2 items-end">
                <input type="text" value={commentAuthor} onChange={(e) => setCommentAuthor(e.target.value)}
                  placeholder="Commenter name" className="w-36 px-2 py-1 border rounded text-sm" required />
                <input type="text" value={commentText} onChange={(e) => setCommentText(e.target.value)}
                  placeholder="Comment text" className="flex-1 px-2 py-1 border rounded text-sm" required />
                <button type="submit" className="px-3 py-1 bg-blue-600 text-white rounded text-sm">Add</button>
                <button type="button" onClick={() => setCommentPostId(null)}
                  className="px-3 py-1 text-gray-500 text-sm">Cancel</button>
              </form>
            )}
          </div>
        ))}
      </div>

      {posts.length === 0 && survey.status === "draft" && (
        <div className="text-center text-gray-400 py-10">
          No posts yet. Paste a news article URL above to add the first post.
        </div>
      )}
    </div>
  );
}
