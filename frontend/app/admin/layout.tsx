"use client";
import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import {
  ArchiveIcon,
  BellIcon,
  ChartIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  DraftIcon,
  HelpIcon,
  PlusIcon,
  SettingsIcon,
  SupportIcon,
  SurveyIcon,
  UsersIcon,
  WorkspaceIcon,
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
  const [authed, setAuthed] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [activeFilter, setActiveFilter] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("token");
    const savedCollapsed = localStorage.getItem("admin-sidebar-collapsed");
    if (!token) {
      router.replace("/auth");
    } else {
      setAuthed(true);
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

  if (!authed) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-sm uppercase tracking-[0.24em] text-slate-400">Checking authentication</p>
      </div>
    );
  }

  return (
    <div className="h-screen overflow-hidden">
      <header className="border-b border-slate-200 bg-[rgba(255,255,255,0.92)] backdrop-blur">
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
              className={`rounded-full px-3 py-2 text-[14px] transition ${
                pathname.startsWith("/admin/surveys")
                  ? "bg-[#effcfb] font-semibold text-[#0f3146]"
                  : "text-slate-500 hover:bg-slate-50"
              }`}
            >
              Surveys
            </Link>
            <Link
              href="/admin/templates"
              className={`rounded-full px-3 py-2 text-[14px] transition ${
                pathname.startsWith("/admin/templates")
                  ? "bg-[#effcfb] font-semibold text-[#0f3146]"
                  : "text-slate-500 hover:bg-slate-50"
              }`}
            >
              Templates
            </Link>
            <Link
              href="/admin/analytics"
              className={`rounded-full px-3 py-2 text-[14px] transition ${
                pathname.startsWith("/admin/analytics")
                  ? "bg-[#effcfb] font-semibold text-[#0f3146]"
                  : "text-slate-500 hover:bg-slate-50"
              }`}
            >
              Analytics
            </Link>
          </nav>
          <div className="hidden rounded-full border border-slate-200 bg-slate-50 px-3 py-2 text-[12px] font-medium text-slate-500 xl:block">
            Experience Management Workspace
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
            <div className="flex h-9 w-9 items-center justify-center rounded-full border border-slate-200 bg-gradient-to-br from-white to-slate-100 text-[13px] font-semibold text-[#0f3146]">
              S
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
                <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-500">Workspace</p>
                <p className="mt-1 text-sm font-medium text-[#0f3146]">Control panel</p>
              </div>
            )}
            <button
              type="button"
              onClick={toggleSidebar}
              className="flex h-9 w-9 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-500 transition hover:bg-slate-50 hover:text-[#0f3146]"
              aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
              title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            >
              {collapsed ? <ChevronRightIcon className="h-4 w-4" /> : <ChevronLeftIcon className="h-4 w-4" />}
            </button>
          </div>

          <div className={`surface-panel-soft mt-4 flex items-center ${collapsed ? "justify-center px-0 py-3.5" : "gap-3 px-3.5 py-3.5"}`}>
            <div className="flex h-9 w-9 items-center justify-center rounded-2xl bg-[#0f3146] text-white">
              <WorkspaceIcon className="h-4 w-4" />
            </div>
            {!collapsed && (
              <div className="min-w-0">
                <p className="text-[14px] font-semibold tracking-[-0.03em] text-black">Workspace</p>
                <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-500">Premium Plan</p>
              </div>
            )}
          </div>

          <Link
            href="/admin/surveys/new"
            className={`primary-button mt-4 ${
              collapsed ? "h-10 w-10 self-center p-0" : "w-[146px] self-center justify-center gap-2 px-0 py-2"
            }`}
            title="Create Survey"
          >
            <PlusIcon className="h-4 w-4 shrink-0" />
            {!collapsed && <span>Create Survey</span>}
          </Link>

          <nav className="mt-6 space-y-1.5">
            <Link
              href="/admin/surveys"
              onClick={() => setActiveFilter(null)}
              className={navItemClass(pathname === "/admin/surveys" && !activeFilter, collapsed)}
              title="All Surveys"
            >
              <SurveyIcon className="h-5 w-5" />
              {!collapsed && <span>All Surveys</span>}
            </Link>
            <Link
              href="/admin/surveys?filter=published"
              onClick={() => setActiveFilter("published")}
              className={navItemClass(activeFilter === "published", collapsed)}
              title="Published"
            >
              <UsersIcon className="h-5 w-5" />
              {!collapsed && <span>Published</span>}
            </Link>
            <Link
              href="/admin/surveys?filter=draft"
              onClick={() => setActiveFilter("draft")}
              className={navItemClass(activeFilter === "draft", collapsed)}
              title="Drafts"
            >
              <DraftIcon className="h-5 w-5" />
              {!collapsed && <span>Drafts</span>}
            </Link>
            <Link
              href="/admin/surveys?filter=closed"
              onClick={() => setActiveFilter("closed")}
              className={navItemClass(activeFilter === "closed", collapsed)}
              title="Archived"
            >
              <ArchiveIcon className="h-5 w-5" />
              {!collapsed && <span>Archived</span>}
            </Link>
          </nav>

          <div className="mt-auto space-y-1.5 pt-6">
            <Link href="/admin/surveys" className={navItemClass(false, collapsed)} title="Settings">
              <SettingsIcon className="h-5 w-5" />
              {!collapsed && <span>Settings</span>}
            </Link>
            <Link href="/admin/surveys" className={navItemClass(false, collapsed)} title="Support">
              <SupportIcon className="h-5 w-5" />
              {!collapsed && <span>Support</span>}
            </Link>
            <button onClick={logout} className={navItemClass(false, collapsed)} title="Logout">
              <ChartIcon className="h-5 w-5" />
              {!collapsed && <span>Logout</span>}
            </button>
          </div>
        </aside>

        <main className="h-full overflow-y-auto px-4 py-5 md:px-7 md:py-6">
          <div className="mx-auto w-full max-w-[1240px]">{children}</div>
        </main>
      </div>
    </div>
  );
}
