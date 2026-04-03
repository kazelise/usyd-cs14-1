"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api } from "@/lib/api";

interface Survey {
  id: number;
  title: string;
  status: string;
  share_code: string;
  num_groups: number;
  created_at: string;
}

export default function SurveysPage() {
  const router = useRouter();
  const [surveys, setSurveys] = useState<Survey[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.listSurveys()
      .then((res) => setSurveys(res.items))
      .catch(() => router.push("/auth"))
      .finally(() => setLoading(false));
  }, [router]);

  if (loading) return <p className="text-gray-400 mt-10">Loading...</p>;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">My Surveys</h1>
        <Link
          href="/admin/surveys/new"
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
        >
          + New Survey
        </Link>
      </div>

      {surveys.length === 0 ? (
        <div className="bg-white rounded-lg p-10 text-center text-gray-400 border">
          No surveys yet. Create your first one.
        </div>
      ) : (
        <div className="space-y-3">
          {surveys.map((s) => (
            <Link
              key={s.id}
              href={`/admin/surveys/${s.id}`}
              className="block bg-white rounded-lg border p-4 hover:border-blue-300 transition"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="font-semibold">{s.title}</h2>
                  <p className="text-sm text-gray-400 mt-1">
                    {s.num_groups > 1 ? `${s.num_groups} groups` : "No A/B testing"} · Created{" "}
                    {new Date(s.created_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  {s.status === "published" && (
                    <span className="text-xs text-gray-400 font-mono">
                      /{s.share_code}
                    </span>
                  )}
                  <span
                    className={`text-xs px-2 py-1 rounded-full ${
                      s.status === "published"
                        ? "bg-green-100 text-green-700"
                        : s.status === "closed"
                        ? "bg-gray-100 text-gray-500"
                        : "bg-yellow-100 text-yellow-700"
                    }`}
                  >
                    {s.status}
                  </span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
