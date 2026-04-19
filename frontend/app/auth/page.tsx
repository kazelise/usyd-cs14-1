"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { ChartIcon, CheckCircleIcon, SurveyIcon, WorkspaceIcon } from "@/components/icons";

const benefits = [
  "Configure article cards from real URLs",
  "Control visible metrics, comments, and A/B groups",
  "Track participant clicks, comments, and calibration quality",
];

export default function AuthPage() {
  const router = useRouter();
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (isLogin) {
        const res = await api.login({ email, password });
        localStorage.setItem("token", res.access_token);
      } else {
        await api.register({ email, password, name });
        const res = await api.login({ email, password });
        localStorage.setItem("token", res.access_token);
      }
      router.push("/admin/surveys");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen px-4 py-8 lg:px-8 lg:py-10">
      <div className="mx-auto grid max-w-7xl overflow-hidden rounded-[28px] border border-black/5 bg-white shadow-[0_35px_90px_rgba(17,24,39,0.08)] lg:grid-cols-[1.02fr_0.98fr]">
        <section className="flex flex-col justify-between bg-[linear-gradient(180deg,#111111_0%,#1f1f1f_100%)] px-8 py-10 text-white lg:px-12 lg:py-12">
          <div>
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-[16px] bg-white/10">
                <WorkspaceIcon className="h-5 w-5" />
              </div>
              <div>
                <p className="text-sm font-semibold uppercase tracking-[0.24em] text-white/65">
                  CS14 Survey Platform
                </p>
                <p className="mt-1 text-sm text-white/55">Research workspace for controlled social studies</p>
              </div>
            </div>

            <div className="mt-16 max-w-xl">
              <p className="section-kicker text-white/45">Research Command</p>
              <h1 className="mt-4 text-[34px] font-semibold tracking-[-0.06em] text-white md:text-[44px]">
                Design and track social media experiments with a calmer interface.
              </h1>
              <p className="mt-5 max-w-lg text-[14px] leading-7 text-white/70">
                Build surveys from article links, shape participant-facing post feeds, and review interaction signals
                from one dashboard.
              </p>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-[18px] border border-white/10 bg-white/5 p-5">
              <SurveyIcon className="h-5 w-5 text-white/80" />
              <p className="mt-5 text-[12px] uppercase tracking-[0.22em] text-white/45">Studies</p>
              <p className="mt-2 text-[28px] font-semibold tracking-[-0.05em]">14</p>
            </div>
            <div className="rounded-[18px] border border-white/10 bg-white/5 p-5">
              <ChartIcon className="h-5 w-5 text-white/80" />
              <p className="mt-5 text-[12px] uppercase tracking-[0.22em] text-white/45">Completion</p>
              <p className="mt-2 text-[28px] font-semibold tracking-[-0.05em]">68.4%</p>
            </div>
            <div className="rounded-[18px] border border-white/10 bg-white/5 p-5">
              <CheckCircleIcon className="h-5 w-5 text-white/80" />
              <p className="mt-5 text-[12px] uppercase tracking-[0.22em] text-white/45">Insights</p>
              <p className="mt-2 text-[28px] font-semibold tracking-[-0.05em]">242</p>
            </div>
          </div>
        </section>

        <section className="flex items-center px-6 py-8 lg:px-12 lg:py-12">
          <div className="mx-auto w-full max-w-xl">
            <div className="flex items-center gap-3 rounded-full bg-stone-100 p-1">
              <button
                className={`flex-1 rounded-full px-4 py-3 text-sm font-medium transition ${
                  isLogin ? "bg-white text-black shadow-sm" : "text-slate-500"
                }`}
                onClick={() => setIsLogin(true)}
              >
                Sign in
              </button>
              <button
                className={`flex-1 rounded-full px-4 py-3 text-sm font-medium transition ${
                  !isLogin ? "bg-white text-black shadow-sm" : "text-slate-500"
                }`}
                onClick={() => setIsLogin(false)}
              >
                Register
              </button>
            </div>

            <div className="mt-8">
              <h2 className="page-title">
                {isLogin ? "Welcome back" : "Create your workspace"}
              </h2>
              <p className="page-subtitle mt-3">
                {isLogin
                  ? "Access your survey dashboard and manage participant-facing post feeds."
                  : "Set up a researcher account to begin drafting, publishing, and tracking studies."}
              </p>
            </div>

            <form onSubmit={handleSubmit} className="mt-8 space-y-4">
              {!isLogin && (
                <div>
                  <label className="mb-2 block text-sm font-medium text-slate-600">Researcher name</label>
                  <input
                    type="text"
                    placeholder="Jane Smith"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="field-input"
                    required
                  />
                </div>
              )}

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-600">Email address</label>
                <input
                  type="email"
                  placeholder="researcher@lab.edu"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="field-input"
                  required
                />
              </div>

              <div>
                <label className="mb-2 block text-sm font-medium text-slate-600">Password</label>
                <input
                  type="password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="field-input"
                  required
                />
              </div>

              {error && <p className="rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>}

              <button type="submit" disabled={loading} className="primary-button w-full py-3">
                {loading ? "Working..." : isLogin ? "Sign in to dashboard" : "Create account"}
              </button>
            </form>

            <div className="mt-8 rounded-[20px] border border-black/5 bg-stone-50 p-6">
              <p className="section-kicker">Included in this workspace</p>
              <div className="mt-4 space-y-3">
                {benefits.map((item) => (
                  <div key={item} className="flex items-start gap-3">
                    <CheckCircleIcon className="mt-0.5 h-4 w-4 text-black" />
                    <p className="text-[14px] leading-6 text-slate-600">{item}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}