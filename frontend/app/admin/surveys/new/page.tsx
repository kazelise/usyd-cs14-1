"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

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
      router.push(`/admin/surveys/${survey.id}`);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-lg">
      <h1 className="text-2xl font-bold mb-6">Create New Survey</h1>
      <form onSubmit={handleCreate} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">Title</label>
          <input
            type="text" value={title} onChange={(e) => setTitle(e.target.value)}
            className="w-full px-4 py-2 border rounded-lg" placeholder="e.g. Fake News Trust Study 2026"
            required
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Description (optional)</label>
          <textarea
            value={description} onChange={(e) => setDescription(e.target.value)}
            className="w-full px-4 py-2 border rounded-lg" rows={3}
            placeholder="Brief description of the study..."
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Number of A/B Test Groups</label>
          <select
            value={numGroups} onChange={(e) => setNumGroups(Number(e.target.value))}
            className="w-full px-4 py-2 border rounded-lg"
          >
            <option value={1}>1 (No A/B testing)</option>
            <option value={2}>2 groups</option>
            <option value={3}>3 groups</option>
            <option value={4}>4 groups</option>
          </select>
          {numGroups > 1 && (
            <p className="text-xs text-gray-400 mt-1">
              Participants will be randomly assigned to a group when they open the survey.
            </p>
          )}
        </div>
        {error && <p className="text-red-500 text-sm">{error}</p>}
        <button
          type="submit" disabled={loading}
          className="w-full py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "Creating..." : "Create Survey"}
        </button>
      </form>
    </div>
  );
}
