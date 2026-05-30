"use client";

import { useCallback, useEffect, useRef, useState, type RefObject, type Ref } from "react";
import { t, type Locale } from "@/lib/i18n";
import type { GazeTrackerSnapshot, GazeTrackerStatus } from "@/app/survey/[shareCode]/useGazeTracker";

const STATUS_RING: Record<GazeTrackerStatus, string> = {
  starting: "ring-slate-300/70",
  tracking: "ring-emerald-300/70",
  weak: "ring-amber-300/70",
  lost: "ring-rose-400/70",
  stopped: "ring-slate-200/60",
};

const STATUS_DOT: Record<GazeTrackerStatus, string> = {
  starting: "bg-slate-400 animate-pulse",
  tracking: "bg-emerald-500 animate-pulse",
  weak: "bg-amber-500 animate-pulse",
  lost: "bg-rose-500",
  stopped: "bg-slate-400",
};

const STATUS_LABEL: Record<GazeTrackerStatus, "trackingStatusStarting" | "trackingStatusTracking" | "trackingStatusWeak" | "trackingStatusLost" | "trackingStatusStopped"> = {
  starting: "trackingStatusStarting",
  tracking: "trackingStatusTracking",
  weak: "trackingStatusWeak",
  lost: "trackingStatusLost",
  stopped: "trackingStatusStopped",
};

type GazeTrackingPipProps = {
  snapshot: GazeTrackerSnapshot;
  locale: Locale;
  videoRef: RefObject<HTMLVideoElement | null> | Ref<HTMLVideoElement>;
};

const MARGIN = 8;

export function GazeTrackingPip({ snapshot, locale, videoRef }: GazeTrackingPipProps) {
  const shellRef = useRef<HTMLDivElement | null>(null);
  const dragRef = useRef<{ startX: number; startY: number; originX: number; originY: number } | null>(null);
  const [pos, setPos] = useState({ x: MARGIN, y: MARGIN });
  const [box, setBox] = useState({ w: 200, h: 260 });
  const [collapsed, setCollapsed] = useState(false);

  const clampPos = useCallback(
    (x: number, y: number) => {
      const vw = window.innerWidth;
      const vh = window.innerHeight;
      const bw = box.w || 200;
      const bh = box.h || 260;
      const maxX = Math.max(MARGIN, vw - bw - MARGIN);
      const maxY = Math.max(MARGIN, vh - bh - MARGIN);
      return {
        x: Math.min(maxX, Math.max(MARGIN, x)),
        y: Math.min(maxY, Math.max(MARGIN, y)),
      };
    },
    [box.h, box.w],
  );

  useEffect(() => {
    const el = shellRef.current;
    if (!el || typeof ResizeObserver === "undefined") return;
    const measure = () => {
      const r = el.getBoundingClientRect();
      setBox({ w: r.width, h: r.height });
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    setPos((p) => clampPos(p.x, p.y));
  }, [box.h, box.w, clampPos]);

  useEffect(() => {
    function onResize() {
      setPos((p) => clampPos(p.x, p.y));
    }
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, [clampPos]);

  const onPointerDown = useCallback(
    (e: React.PointerEvent) => {
      if ((e.target as HTMLElement).closest("[data-pip-drag-handle]") == null) return;
      e.preventDefault();
      (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
      dragRef.current = {
        startX: e.clientX,
        startY: e.clientY,
        originX: pos.x,
        originY: pos.y,
      };
    },
    [pos.x, pos.y],
  );

  const onPointerMove = useCallback(
    (e: React.PointerEvent) => {
      if (!dragRef.current) return;
      const dx = e.clientX - dragRef.current.startX;
      const dy = e.clientY - dragRef.current.startY;
      setPos(clampPos(dragRef.current.originX + dx, dragRef.current.originY + dy));
    },
    [clampPos],
  );

  const onPointerUp = useCallback(() => {
    dragRef.current = null;
  }, []);

  const coveragePct = Math.round(Math.min(1, Math.max(0, snapshot.coverage)) * 100);
  const ring = STATUS_RING[snapshot.status];
  const dot = STATUS_DOT[snapshot.status];
  const labelKey = STATUS_LABEL[snapshot.status];
  const pipLiveMessage = `${t(locale, "trackingStatusTitle")}: ${t(locale, labelKey)}`;

  return (
    <div
      data-gaze-pip
      ref={shellRef}
      className="pointer-events-auto fixed z-[60] w-[min(36vw,180px)] select-none sm:w-[200px]"
      style={{ left: pos.x, top: pos.y }}
      role="region"
      aria-label={t(locale, "trackingStatusTitle")}
    >
      <p className="sr-only" aria-live="polite" aria-atomic="true">
        {pipLiveMessage}
      </p>
      <div
        className={`overflow-hidden rounded-2xl border border-slate-200 bg-black shadow-xl ring-2 ${ring} touch-none`}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
      >
        <div
          data-pip-drag-handle
          className="flex cursor-grab items-center justify-between gap-2 border-b border-white/10 bg-black/60 px-2 py-1.5 active:cursor-grabbing"
        >
          <p className="text-[9px] font-semibold uppercase tracking-[0.14em] text-white/80">
            {t(locale, "trackingStatusTitle")}
          </p>
          <div className="flex items-center gap-1.5">
            <button
              type="button"
              aria-label={collapsed ? t(locale, "pipExpand") : t(locale, "pipMinimize")}
              onClick={() => setCollapsed((c) => !c)}
              onPointerDown={(e) => e.stopPropagation()}
              className="flex h-4 w-4 items-center justify-center rounded text-[8px] text-white/60 hover:bg-white/15 hover:text-white/90"
            >
              {collapsed ? "▲" : "▼"}
            </button>
            <span className={`h-2 w-2 shrink-0 rounded-full ${dot}`} aria-hidden />
          </div>
        </div>
        {!collapsed && (
          <>
            <div className="relative aspect-[16/10] bg-slate-950">
              <video
                ref={videoRef as Ref<HTMLVideoElement>}
                className="h-full w-full scale-x-[-1] object-cover"
                autoPlay
                muted
                playsInline
              />
              {snapshot.status === "starting" && (
                // Cold-start window after a refresh: MediaPipe scripts reload
                // from CDN and the Camera wrapper hasn't bound a stream yet, so
                // the <video> is a black box. Without an explicit message,
                // participants read "my face is lost" (issue #55). The overlay
                // disappears the moment Camera.start() resolves and frames flow.
                <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center gap-1 bg-black/55 px-2 text-center text-[10px] font-semibold leading-tight text-white">
                  <span className="inline-flex h-5 w-5 animate-spin rounded-full border-2 border-white/30 border-t-white/90" aria-hidden />
                  <span>{t(locale, "trackingStatusStarting")}</span>
                </div>
              )}
              {snapshot.status === "lost" && (
                <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-black/45 px-2 text-center text-[10px] font-semibold leading-tight text-white">
                  {t(locale, "trackingStatusLost")}
                </div>
              )}
            </div>
            <div className="space-y-1 border-t border-white/10 bg-black/75 px-2 py-1.5 text-[10px] text-white/85">
              <div className="flex items-center justify-between gap-2 font-medium">
                <span className="truncate">{t(locale, labelKey)}</span>
                <span className={snapshot.faceDetected ? "text-emerald-400" : "text-rose-400"}>
                  {snapshot.faceDetected ? "●" : "○"}
                </span>
              </div>
              {snapshot.expectedSamples > 0 && (
                <div>
                  <div className="mb-0.5 flex justify-between text-[9px] uppercase tracking-[0.12em] text-white/50">
                    <span>{t(locale, "trackingCoverageLabel")}</span>
                    <span>{coveragePct}%</span>
                  </div>
                  <div className="h-1 overflow-hidden rounded-full bg-white/15">
                    <div className="h-full rounded-full bg-emerald-500/90 transition-all" style={{ width: `${coveragePct}%` }} />
                  </div>
                </div>
              )}
              <p className="leading-snug text-[9px] text-white/45">{t(locale, "trackingPrivacyNote")}</p>
            </div>
          </>
        )}
      </div>
      <p className="mt-1 text-center text-[9px] text-slate-500">{t(locale, "trackingPipDragHint")}</p>
    </div>
  );
}
