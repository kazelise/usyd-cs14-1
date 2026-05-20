"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { ChartIcon, CheckCircleIcon, SurveyIcon, WorkspaceIcon } from "@/components/icons";
import { useLocale } from "@/components/locale-provider";

export default function AuthPage() {
  const router = useRouter();
  const { locale } = useLocale();
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const text =
    locale === "zh"
      ? {
          product: "CS14 问卷平台",
          workspace: "受控社交媒体研究工作台",
          command: "研究工作台",
          headline: "用更清晰的界面设计并追踪社交媒体实验。",
          intro: "从文章链接创建问卷，配置面向参与者的帖子信息流，并在同一个后台中查看交互信号。",
          studies: "构建",
          completion: "校准",
          insights: "导出",
          signIn: "登录",
          register: "注册",
          welcomeBack: "欢迎回来",
          createWorkspace: "创建研究空间",
          signInCopy: "进入问卷后台，管理面向参与者的帖子信息流。",
          registerCopy: "创建研究者账号后即可开始起草、发布和追踪实验。",
          researcherName: "研究者姓名",
          email: "邮箱地址",
          password: "密码",
          working: "处理中...",
          signInButton: "登录后台",
          createAccount: "创建账号",
          accessNote: "已通过验证的研究者可访问问卷后台（演示环境）。",
          namePlaceholder: "张三",
          emailPlaceholder: "researcher@lab.edu",
          passwordPlaceholder: "请输入密码",
        }
      : {
          product: "CS14 Survey Platform",
          workspace: "Research workspace for controlled social studies",
          command: "Research Command",
          headline: "Design and track social media experiments with a calmer interface.",
          intro: "Build surveys from article links, shape participant-facing post feeds, and review interaction signals from one dashboard.",
          studies: "Builder",
          completion: "Calibration",
          insights: "Export",
          signIn: "Sign in",
          register: "Register",
          welcomeBack: "Welcome back",
          createWorkspace: "Create your workspace",
          signInCopy: "Access your survey dashboard and manage participant-facing post feeds.",
          registerCopy: "Set up a researcher account to begin drafting, publishing, and tracking studies.",
          researcherName: "Researcher name",
          email: "Email address",
          password: "Password",
          working: "Working...",
          signInButton: "Sign in to dashboard",
          createAccount: "Create account",
          accessNote: "Authenticated researchers access the CS14 survey dashboard (demo-safe).",
          namePlaceholder: "Jane Smith",
          emailPlaceholder: "researcher@lab.edu",
          passwordPlaceholder: "Enter your password",
        };

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
      <div className="mx-auto grid min-w-0 max-w-7xl overflow-hidden rounded-[28px] border border-black/5 bg-white shadow-[0_35px_90px_rgba(17,24,39,0.08)] lg:grid-cols-[1.02fr_0.98fr]">
        <section className="flex min-w-0 flex-col justify-between bg-[linear-gradient(180deg,#111111_0%,#1f1f1f_100%)] px-8 py-10 text-white lg:px-12 lg:py-12">
          <div>
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[16px] bg-white/10">
                <WorkspaceIcon className="h-5 w-5" />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-semibold uppercase tracking-[0.24em] text-white/65">
                  {text.product}
                </p>
                <p className="mt-1 text-sm text-white/55">{text.workspace}</p>
              </div>
            </div>

            <div className="mt-16 max-w-xl">
              <p className="section-kicker text-white/45">{text.command}</p>
              <h1 className="mt-4 text-[34px] font-semibold tracking-[-0.06em] text-white md:text-[44px]">
                {text.headline}
              </h1>
              <p className="mt-5 max-w-lg text-[14px] leading-7 text-white/70">
                {text.intro}
              </p>
            </div>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-[18px] border border-white/10 bg-white/5 p-5">
              <SurveyIcon className="h-5 w-5 text-white/80" />
              <p className="mt-5 text-[12px] uppercase tracking-[0.22em] text-white/45">{text.studies}</p>
              <p className="mt-2 text-[18px] font-semibold tracking-[-0.03em]">Survey CRUD</p>
            </div>
            <div className="rounded-[18px] border border-white/10 bg-white/5 p-5">
              <ChartIcon className="h-5 w-5 text-white/80" />
              <p className="mt-5 text-[12px] uppercase tracking-[0.22em] text-white/45">{text.completion}</p>
              <p className="mt-2 text-[18px] font-semibold tracking-[-0.03em]">Webcam flow</p>
            </div>
            <div className="rounded-[18px] border border-white/10 bg-white/5 p-5">
              <CheckCircleIcon className="h-5 w-5 text-white/80" />
              <p className="mt-5 text-[12px] uppercase tracking-[0.22em] text-white/45">{text.insights}</p>
              <p className="mt-2 text-[18px] font-semibold tracking-[-0.03em]">CSV / JSON</p>
            </div>
          </div>
        </section>

        <section className="flex min-w-0 items-center px-6 py-8 lg:px-12 lg:py-12">
          <div className="mx-auto w-full min-w-0 max-w-xl">
            <div className="flex items-center gap-3 rounded-full bg-stone-100 p-1">
              <button
                className={`flex-1 rounded-full px-4 py-3 text-sm font-medium transition ${
                  isLogin ? "bg-white text-black shadow-sm" : "text-slate-500"
                }`}
                onClick={() => setIsLogin(true)}
              >
                {text.signIn}
              </button>
              <button
                className={`flex-1 rounded-full px-4 py-3 text-sm font-medium transition ${
                  !isLogin ? "bg-white text-black shadow-sm" : "text-slate-500"
                }`}
                onClick={() => setIsLogin(false)}
              >
                {text.register}
              </button>
            </div>

            <div className="mt-8">
              <h2 className="page-title">
                {isLogin ? text.welcomeBack : text.createWorkspace}
              </h2>
              <p className="page-subtitle mt-3">
                {isLogin
                  ? text.signInCopy
                  : text.registerCopy}
              </p>
            </div>

            <form onSubmit={handleSubmit} className="mt-8 space-y-4">
              {!isLogin && (
                <div>
                  <label htmlFor="researcher-name" className="mb-2 block text-sm font-medium text-slate-600">{text.researcherName}</label>
                  <input
                    id="researcher-name"
                    type="text"
                    placeholder={text.namePlaceholder}
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="field-input"
                    required
                  />
                </div>
              )}

              <div>
                <label htmlFor="email-address" className="mb-2 block text-sm font-medium text-slate-600">{text.email}</label>
                <input
                  id="email-address"
                  type="email"
                  placeholder={text.emailPlaceholder}
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="field-input"
                  required
                />
              </div>

              <div>
                <label htmlFor="password" className="mb-2 block text-sm font-medium text-slate-600">{text.password}</label>
                <input
                  id="password"
                  type="password"
                  placeholder={text.passwordPlaceholder}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="field-input"
                  required
                />
              </div>

              {error && <p className="rounded-2xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-600">{error}</p>}

              <button type="submit" disabled={loading} className="primary-button w-full py-3">
                {loading ? text.working : isLogin ? text.signInButton : text.createAccount}
              </button>
            </form>

            <p className="mt-6 text-center text-xs leading-relaxed text-slate-500">{text.accessNote}</p>
          </div>
        </section>
      </div>
    </div>
  );
}
