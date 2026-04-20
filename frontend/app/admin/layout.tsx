"use client";
import { useEffect, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { useLocale } from "@/components/locale-provider";
import { api } from "@/lib/api";
import {
  ArchiveIcon,
  BellIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  DraftIcon,
  HelpIcon,
  PlusIcon,
  SurveyIcon,
  UsersIcon,
} from "@/components/icons";

function navItemClass(active: boolean, collapsed: boolean) {
  return [
    "group flex items-center rounded-[14px] text-[13px] font-medium transition",
    collapsed ? "justify-center px-2.5 py-2.5" : "gap-3 px-3.5 py-2.5",
    active
      ? "border border-[#9ddfd8] bg-[#effcfb] text-[#0f3146] shadow-sm"
      : "border border-transparent text-slate-500 hover:border-slate-200 hover:bg-white hover:text-[#0f3146]",
  ].join(" ");
}

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { locale, setLocale } = useLocale();
  const [authed, setAuthed] = useState(false);
  const [profileName, setProfileName] = useState("S");
  const [profileEmail, setProfileEmail] = useState("");
  const [draftName, setDraftName] = useState("");
  const [profileOpen, setProfileOpen] = useState(false);
  const [savingProfile, setSavingProfile] = useState(false);
  const [profileMessage, setProfileMessage] = useState("");
  const [collapsed, setCollapsed] = useState(false);
  const [activeFilter, setActiveFilter] = useState<string | null>(null);
  const profileRef = useRef<HTMLDivElement | null>(null);
  const text =
    locale === "zh"
      ? {
          checkingAuth: "正在检查登录状态",
          surveys: "问卷",
          templates: "模板",
          analytics: "分析",
          workspaceBadge: "实验管理工作台",
          workspace: "工作区",
          controlPanel: "控制面板",
          expandSidebar: "展开侧栏",
          collapseSidebar: "收起侧栏",
          createSurvey: "新建问卷",
          allSurveys: "全部问卷",
          published: "已发布",
          drafts: "草稿",
          archived: "已归档",
          language: "语言切换",
          english: "English",
          chinese: "中文",
          profile: "个人资料",
          profileHint: "管理账号信息",
          displayName: "用户名",
          email: "邮箱",
          save: "保存",
          saving: "保存中...",
          saved: "用户名已更新",
          close: "关闭",
          nameRequired: "用户名不能为空",
          logout: "退出登录",
        }
      : {
          checkingAuth: "Checking authentication",
          surveys: "Surveys",
          templates: "Templates",
          analytics: "Analytics",
          workspaceBadge: "Experience Management Workspace",
          workspace: "Workspace",
          controlPanel: "Control panel",
          expandSidebar: "Expand sidebar",
          collapseSidebar: "Collapse sidebar",
          createSurvey: "Create Survey",
          allSurveys: "All Surveys",
          published: "Published",
          drafts: "Drafts",
          archived: "Archived",
          language: "Language",
          english: "English",
          chinese: "中文",
          profile: "Profile",
          profileHint: "Manage your account",
          displayName: "Display name",
          email: "Email",
          save: "Save",
          saving: "Saving...",
          saved: "Name updated",
          close: "Close",
          nameRequired: "Name cannot be empty",
          logout: "Logout",
        };

  useEffect(() => {
    const token = localStorage.getItem("token");
    const savedCollapsed = localStorage.getItem("admin-sidebar-collapsed");
    if (!token) {
      router.replace("/auth");
    } else {
      setAuthed(true);
      api
        .me()
        .then((researcher) => {
          setProfileName(researcher.name || "S");
          setDraftName(researcher.name || "");
          setProfileEmail(researcher.email || "");
        })
        .catch(() => {
          router.replace("/auth");
        });
    }
    if (savedCollapsed === "1") {
      setCollapsed(true);
    }
  }, [router]);

  useEffect(() => {
    if (typeof window !== "undefined") {
      setActiveFilter(new URLSearchParams(window.location.search).get("filter"));
    }
  }, [pathname]);

  useEffect(() => {
    function handlePointerDown(event: MouseEvent) {
      if (!profileRef.current?.contains(event.target as Node)) {
        setProfileOpen(false);
      }
    }

    if (profileOpen) {
      document.addEventListener("mousedown", handlePointerDown);
    }
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
    };
  }, [profileOpen]);

  function logout() {
    localStorage.removeItem("token");
    router.push("/auth");
  }

  function toggleSidebar() {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem("admin-sidebar-collapsed", next ? "1" : "0");
      return next;
    });
  }

  async function saveProfileName() {
    const nextName = draftName.trim();
    if (!nextName) {
      setProfileMessage(text.nameRequired);
      return;
    }

    setSavingProfile(true);
    setProfileMessage("");
    try {
      const researcher = await api.updateMe({ name: nextName });
      setProfileName(researcher.name);
      setDraftName(researcher.name);
      setProfileMessage(text.saved);
    } catch (err: any) {
      setProfileMessage(err.message || text.nameRequired);
    } finally {
      setSavingProfile(false);
    }
  }

  const avatarLetter = (profileName.trim()[0] || "S").toUpperCase();

  if (!authed) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-sm uppercase tracking-[0.24em] text-slate-400">{text.checkingAuth}</p>
      </div>
    );
  }

  return (
    <div className="h-screen overflow-hidden">
      <header className="relative z-[220] border-b border-slate-200 bg-[rgba(255,255,255,0.92)] backdrop-blur">
        <div className="mx-auto flex h-[68px] max-w-[1560px] items-center gap-7 px-4 md:px-5">
          <Link
            href="/admin/surveys"
            className="shrink-0 text-[14px] font-semibold uppercase tracking-[0.14em] text-[#0f3146] md:text-[15px]"
          >
            CS14 Survey Platform
          </Link>
          <nav className="hidden items-center gap-7 lg:flex">
            <Link
              href="/admin/surveys"
              className={`liquid-nav-link ${pathname.startsWith("/admin/surveys") ? "liquid-nav-link-active" : ""}`}
            >
              {text.surveys}
            </Link>
            <Link
              href="/admin/templates"
              className={`liquid-nav-link ${pathname.startsWith("/admin/templates") ? "liquid-nav-link-active" : ""}`}
            >
              {text.templates}
            </Link>
            <Link
              href="/admin/analytics"
              className={`liquid-nav-link ${pathname.startsWith("/admin/analytics") ? "liquid-nav-link-active" : ""}`}
            >
              {text.analytics}
            </Link>
          </nav>
          <div className="hidden rounded-full border border-slate-200 bg-slate-50 px-3 py-2 text-[12px] font-medium text-slate-500 xl:block">
            {text.workspaceBadge}
          </div>
          <div className="ml-auto flex items-center gap-3">
            <button
              type="button"
              className="flex h-9 w-9 items-center justify-center rounded-full border border-slate-200 bg-white text-[#0f3146] transition hover:bg-slate-50"
            >
              <BellIcon className="h-4 w-4" />
            </button>
            <button
              type="button"
              className="flex h-9 w-9 items-center justify-center rounded-full border border-slate-200 bg-white text-[#0f3146] transition hover:bg-slate-50"
            >
              <HelpIcon className="h-4 w-4" />
            </button>
            <div className="relative" ref={profileRef}>
              <button
                type="button"
                onClick={() => {
                  setProfileMessage("");
                  setDraftName(profileName);
                  setProfileOpen((prev) => !prev);
                }}
                className="flex h-9 w-9 items-center justify-center rounded-full border border-slate-200 bg-gradient-to-br from-white to-slate-100 text-[13px] font-semibold text-[#0f3146] transition hover:border-[#9ddfd8] hover:bg-white"
                aria-label={text.profile}
                title={text.profile}
              >
                {avatarLetter}
              </button>

              {profileOpen && (
                <div className="fixed inset-0 z-[260]">
                  <button
                    type="button"
                    aria-label={text.close}
                    onClick={() => setProfileOpen(false)}
                    className="absolute inset-0 bg-transparent"
                  />
                  <div className="absolute right-5 top-20 w-[280px] rounded-[20px] border border-slate-200 bg-white p-4 shadow-[0_28px_80px_rgba(15,49,70,0.16)]">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-[16px] font-semibold tracking-[-0.03em] text-[#0f3146]">{profileName}</p>
                        <p className="mt-1 text-[12px] text-slate-400">{text.profileHint}</p>
                      </div>
                      <button
                        type="button"
                        onClick={() => setProfileOpen(false)}
                        className="rounded-full border border-slate-200 px-2.5 py-1 text-[12px] text-slate-500 transition hover:bg-slate-50 hover:text-[#0f3146]"
                      >
                        {text.close}
                      </button>
                    </div>

                    <div className="mt-4 space-y-4">
                      <div>
                        <p className="mb-2 text-[12px] font-semibold uppercase tracking-[0.18em] text-slate-400">
                          {text.displayName}
                        </p>
                        <input
                          type="text"
                          value={draftName}
                          onChange={(e) => setDraftName(e.target.value)}
                          className="field-input"
                        />
                      </div>
                      <div>
                        <p className="mb-2 text-[12px] font-semibold uppercase tracking-[0.18em] text-slate-400">
                          {text.email}
                        </p>
                        <p className="rounded-[16px] border border-slate-200 bg-slate-50 px-4 py-3 text-[14px] text-slate-500">
                          {profileEmail}
                        </p>
                      </div>
                    </div>

                    {profileMessage && (
                      <p className="mt-4 rounded-[14px] bg-slate-50 px-4 py-3 text-[13px] text-slate-500">{profileMessage}</p>
                    )}

                    <div className="mt-4 flex gap-3">
                      <button
                        type="button"
                        onClick={saveProfileName}
                        disabled={savingProfile}
                        className="primary-button flex-1 justify-center"
                      >
                        {savingProfile ? text.saving : text.save}
                      </button>
                      <button
                        type="button"
                        onClick={logout}
                        className="secondary-button flex-1 justify-center"
                      >
                        {text.logout}
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      <div className="mx-auto grid h-[calc(100vh-68px)] max-w-[1560px] grid-cols-[auto_minmax(0,1fr)]">
        <aside
          className={`flex h-full flex-col border-r border-slate-200 bg-[rgba(250,252,254,0.72)] px-4 py-5 transition-[width] duration-200 ${
            collapsed ? "w-[78px]" : "w-[212px]"
          }`}
        >
          <div className={`flex items-center ${collapsed ? "justify-center" : "justify-between"} gap-3`}>
            {!collapsed && (
              <div className="min-w-0">
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">{text.workspace}</p>
                <p className="mt-1 text-sm font-medium text-[#0f3146]">{text.controlPanel}</p>
              </div>
            )}
            <button
              type="button"
              onClick={toggleSidebar}
              className="flex h-9 w-9 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-500 transition hover:bg-slate-50 hover:text-[#0f3146]"
              aria-label={collapsed ? text.expandSidebar : text.collapseSidebar}
              title={collapsed ? text.expandSidebar : text.collapseSidebar}
            >
              {collapsed ? <ChevronRightIcon className="h-4 w-4" /> : <ChevronLeftIcon className="h-4 w-4" />}
            </button>
          </div>

          <Link
            href="/admin/surveys/new"
            className={`primary-button mt-5 ${
              collapsed ? "h-10 w-10 self-center p-0" : "w-full justify-center gap-2 px-0 py-2"
            }`}
            title={text.createSurvey}
          >
            <PlusIcon className="h-4 w-4 shrink-0" />
            {!collapsed && <span>{text.createSurvey}</span>}
          </Link>

          <nav className="mt-6 space-y-1.5">
            <Link
              href="/admin/surveys"
              onClick={() => setActiveFilter(null)}
              className={navItemClass(pathname === "/admin/surveys" && !activeFilter, collapsed)}
              title={text.allSurveys}
            >
              <SurveyIcon className="h-5 w-5" />
              {!collapsed && <span>{text.allSurveys}</span>}
            </Link>
            <Link
              href="/admin/surveys?filter=published"
              onClick={() => setActiveFilter("published")}
              className={navItemClass(activeFilter === "published", collapsed)}
              title={text.published}
            >
              <UsersIcon className="h-5 w-5" />
              {!collapsed && <span>{text.published}</span>}
            </Link>
            <Link
              href="/admin/surveys?filter=draft"
              onClick={() => setActiveFilter("draft")}
              className={navItemClass(activeFilter === "draft", collapsed)}
              title={text.drafts}
            >
              <DraftIcon className="h-5 w-5" />
              {!collapsed && <span>{text.drafts}</span>}
            </Link>
            <Link
              href="/admin/surveys?filter=closed"
              onClick={() => setActiveFilter("closed")}
              className={navItemClass(activeFilter === "closed", collapsed)}
              title={text.archived}
            >
              <ArchiveIcon className="h-5 w-5" />
              {!collapsed && <span>{text.archived}</span>}
            </Link>
          </nav>

          <div className="mt-auto pt-6">
            <div
              className={`rounded-[14px] border border-slate-200 bg-white/80 p-1 ${
                collapsed ? "mx-auto w-[52px]" : "w-full"
              }`}
              title={text.language}
            >
              <div className={`grid gap-1 ${collapsed ? "grid-cols-1" : "grid-cols-2"}`}>
                <button
                  type="button"
                  onClick={() => setLocale("en")}
                  className={`rounded-[10px] px-3 py-2 text-[13px] font-medium transition ${
                    locale === "en"
                      ? "bg-[#effcfb] text-[#0f3146] shadow-sm"
                      : "text-slate-500 hover:bg-slate-50 hover:text-[#0f3146]"
                  }`}
                >
                  {collapsed ? "EN" : text.english}
                </button>
                <button
                  type="button"
                  onClick={() => setLocale("zh")}
                  className={`rounded-[10px] px-3 py-2 text-[13px] font-medium transition ${
                    locale === "zh"
                      ? "bg-[#effcfb] text-[#0f3146] shadow-sm"
                      : "text-slate-500 hover:bg-slate-50 hover:text-[#0f3146]"
                  }`}
                >
                  {collapsed ? "中" : text.chinese}
                </button>
              </div>
            </div>
          </div>
        </aside>

        <main className="h-full overflow-y-auto px-4 py-5 md:px-7 md:py-6">
          <div className="mx-auto w-full max-w-[1240px]">{children}</div>
        </main>
      </div>
    </div>
  );
}
