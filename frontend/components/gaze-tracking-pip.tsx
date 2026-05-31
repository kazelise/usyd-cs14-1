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

const MARGIN = 0;

export function GazeTrackingPip({ snapshot, locale, videoRef }: GazeTrackingPipProps) {
  const shellRef = useRef<HTMLDivElement | null>(null);
  const dragRef = useRef<{ startX: number; startY: number; originX: number; originY: number } | null>(null);
  const [pos, setPos] = useState({ x: MARGIN, y: MARGIN });
  const [box, setBox] = useState({ w: 200, h: 260 });

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
          <span className={`h-2 w-2 shrink-0 rounded-full ${dot}`} aria-hidden />
        </div>
        {/*
          Keep the <video> MOUNTED but permanently hidden (display:none). The
          PIP is now a drag-only status chip and never expands, yet the camera
          stream binding must stay attached to this element so frames keep
          flowing to MediaPipe — unmounting it would drop the stream and the
          face would never reappear without a reload.
        */}
        <div className="relative aspect-[16/10] bg-slate-950" style={{ display: "none" }}>
          <video
            ref={videoRef as Ref<HTMLVideoElement>}
            className="h-full w-full scale-x-[-1] object-cover"
            autoPlay
            muted
            playsInline
          />
        </div>
      </div>
    </div>
  );
}
