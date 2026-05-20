"use client";
import { useCallback, useEffect, useRef, useState, type RefObject } from "react";
import { api } from "@/lib/api";
import { acquireSharedFaceMesh, releaseSharedFaceMesh } from "@/lib/mediapipe-face-mesh";

export type GazeTrackerStatus =
  | "starting"
  | "tracking"
  | "weak"
  | "lost"
  | "stopped";

export interface GazeTrackerSnapshot {
  status: GazeTrackerStatus;
  faceDetected: boolean;
  expectedSamples: number;
  detectedSamples: number;
  activeMs: number;
  missingMs: number;
  noFacePeriods: number;
  coverage: number;
}

export interface GazeTrackerSummary {
  active_ms: number;
  expected_samples: number;
  detected_samples: number;
  missing_ms: number;
  no_face_periods: number;
}

interface GazeTrackerOptions {
  responseId: number;
  participantToken: string;
  intervalMs: number;
  enabled: boolean;
  flushIntervalMs?: number;
  /** When set, gaze capture uses this mounted `<video>` (e.g. picture-in-picture preview). */
  pipVideoRef?: RefObject<HTMLVideoElement | null>;
}

// MediaPipe iris landmark indices
const LEFT_IRIS_CENTER = 468;
const RIGHT_IRIS_CENTER = 473;
// Eye corner landmarks for gaze ratio computation
const LEFT_EYE_INNER = 133;
const LEFT_EYE_OUTER = 33;
const RIGHT_EYE_INNER = 362;
const RIGHT_EYE_OUTER = 263;
const LEFT_EYE_TOP = 159;
const LEFT_EYE_BOTTOM = 145;
const RIGHT_EYE_TOP = 386;
const RIGHT_EYE_BOTTOM = 374;

// How many consecutive missed-sample windows count as a "tracking dropout"
// rather than a transient blink/turn-of-head.
const DROPOUT_WINDOWS = 2;
// How long (ms) we'll wait for the camera to deliver the first detection
// before downgrading status from "starting" to "weak".
const STARTUP_GRACE_MS = 2500;

/**
 * Continuously captures gaze data during the survey using MediaPipe Face Mesh
 * for real iris tracking, then sends batches to POST /tracking/gaze.
 *
 * Beyond raw samples, the hook tracks per-window detection state so the UI
 * can surface "face detected / weak / lost" indicators and the survey
 * completion handler can persist a coverage-based confidence score. Raw
 * webcam frames are never persisted or rendered — only numeric counts.
 */
export function useGazeTracker({
  responseId,
  participantToken,
  intervalMs,
  enabled,
  flushIntervalMs = 5000,
  pipVideoRef,
}: GazeTrackerOptions) {
  const bufferRef = useRef<any[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const usesExternalVideoRef = useRef(false);
  const faceMeshRef = useRef<any>(null);
  const faceMeshOwnerRef = useRef<symbol | null>(null);
  const captureRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const flushTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startedAtRef = useRef<number | null>(null);
  const lastDetectedAtRef = useRef<number | null>(null);
  const consecutiveMissesRef = useRef(0);
  const inDropoutRef = useRef(false);
  const summaryRef = useRef({
    expectedSamples: 0,
    detectedSamples: 0,
    activeMs: 0,
    missingMs: 0,
    noFacePeriods: 0,
  });

  const [snapshot, setSnapshot] = useState<GazeTrackerSnapshot>({
    status: "stopped",
    faceDetected: false,
    expectedSamples: 0,
    detectedSamples: 0,
    activeMs: 0,
    missingMs: 0,
    noFacePeriods: 0,
    coverage: 0,
  });

  // Latest tracking result updated by MediaPipe onResults callback
  const latestRef = useRef<{
    detected: boolean;
    leftIrisX: number;
    leftIrisY: number;
    rightIrisX: number;
    rightIrisY: number;
    screenX: number;
    screenY: number;
  }>({
    detected: false,
    leftIrisX: 0, leftIrisY: 0,
    rightIrisX: 0, rightIrisY: 0,
    screenX: 0, screenY: 0,
  });

  const getVisiblePostId = useCallback((): number | null => {
    const posts = document.querySelectorAll("[data-post-id]");
    let bestId: number | null = null;
    let bestVisible = 0;
    posts.forEach((el) => {
      const rect = el.getBoundingClientRect();
      const visible = Math.max(0, Math.min(window.innerHeight, rect.bottom) - Math.max(0, rect.top));
      if (visible > bestVisible) {
        bestVisible = visible;
        bestId = Number(el.getAttribute("data-post-id"));
      }
    });
    return bestId;
  }, []);

  const flush = useCallback(async () => {
    if (bufferRef.current.length === 0) return;
    const batch = [...bufferRef.current];
    bufferRef.current = [];
    try {
      await api.recordGaze({ response_id: responseId, participant_token: participantToken, data: batch });
    } catch {
      bufferRef.current = [...batch, ...bufferRef.current];
    }
  }, [participantToken, responseId]);

  const getSummary = useCallback((): GazeTrackerSummary => {
    const summary = summaryRef.current;
    return {
      active_ms: Math.round(summary.activeMs),
      expected_samples: summary.expectedSamples,
      detected_samples: summary.detectedSamples,
      missing_ms: Math.round(summary.missingMs),
      no_face_periods: summary.noFacePeriods,
    };
  }, []);

  useEffect(() => {
    if (!enabled || !responseId || !participantToken) return;

    let cancelled = false;
    let cameraInstance: any = null;

    // Reset summary for this session.
    summaryRef.current = {
      expectedSamples: 0,
      detectedSamples: 0,
      activeMs: 0,
      missingMs: 0,
      noFacePeriods: 0,
    };
    consecutiveMissesRef.current = 0;
    inDropoutRef.current = false;
    lastDetectedAtRef.current = null;
    startedAtRef.current = Date.now();
    setSnapshot((prev) => ({ ...prev, status: "starting", faceDetected: false }));

    async function start() {
      // Acquire the shared Face Mesh instance. The CDN WASM runtime is brittle when
      // reinitialized after calibration, so calibration and gaze tracking reuse it.
      const browserWindow = window as any;
      let faceMesh: any;
      try {
        const acquired = await acquireSharedFaceMesh((results: any) => {
          if (!results.multiFaceLandmarks || results.multiFaceLandmarks.length === 0) {
            latestRef.current = { ...latestRef.current, detected: false };
            return;
          }

          const lm = results.multiFaceLandmarks[0];
          const leftIris = lm[LEFT_IRIS_CENTER];
          const rightIris = lm[RIGHT_IRIS_CENTER];

          // Gaze estimation: iris position relative to eye corners
          const leftOuter = lm[LEFT_EYE_OUTER];
          const leftInner = lm[LEFT_EYE_INNER];
          const rightOuter = lm[RIGHT_EYE_OUTER];
          const rightInner = lm[RIGHT_EYE_INNER];

          const leftRatioX = (leftIris.x - leftOuter.x) / (leftInner.x - leftOuter.x);
          const rightRatioX = (rightIris.x - rightOuter.x) / (rightInner.x - rightOuter.x);

          const leftTop = lm[LEFT_EYE_TOP];
          const leftBottom = lm[LEFT_EYE_BOTTOM];
          const rightTop = lm[RIGHT_EYE_TOP];
          const rightBottom = lm[RIGHT_EYE_BOTTOM];

          const leftRatioY = (leftIris.y - leftTop.y) / (leftBottom.y - leftTop.y);
          const rightRatioY = (rightIris.y - rightTop.y) / (rightBottom.y - rightTop.y);

          const gazeX = (leftRatioX + rightRatioX) / 2;
          const gazeY = (leftRatioY + rightRatioY) / 2;

          // Map to screen coordinates in the same orientation as the camera frame.
          const screenX = Math.round(gazeX * window.innerWidth);
          const screenY = Math.round(gazeY * window.innerHeight);

          latestRef.current = {
            detected: true,
            leftIrisX: leftIris.x,
            leftIrisY: leftIris.y,
            rightIrisX: rightIris.x,
            rightIrisY: rightIris.y,
            screenX,
            screenY,
          };
        });
        faceMesh = acquired.faceMesh;
        faceMeshOwnerRef.current = acquired.owner;
      } catch (err) {
        console.error("Failed to load MediaPipe for gaze tracking:", err);
        setSnapshot((prev) => ({ ...prev, status: "lost", faceDetected: false }));
        return;
      }
      if (cancelled) {
        releaseSharedFaceMesh(faceMeshOwnerRef.current);
        faceMeshOwnerRef.current = null;
        return;
      }
      faceMeshRef.current = faceMesh;

      const external = pipVideoRef?.current ?? null;
      usesExternalVideoRef.current = Boolean(external);
      const video =
        external ??
        (() => {
          const el = document.createElement("video");
          el.setAttribute("playsinline", "");
          el.setAttribute("autoplay", "");
          el.muted = true;
          return el;
        })();
      videoRef.current = video;

      cameraInstance = new browserWindow.Camera(video, {
        onFrame: async () => {
          if (faceMeshRef.current) {
            try { await faceMeshRef.current.send({ image: video }); } catch {}
          }
        },
        width: 640,
        height: 480,
      });

      try {
        await cameraInstance.start();
      } catch (err) {
        console.error("Gaze tracker camera error:", err);
        setSnapshot((prev) => ({ ...prev, status: "lost", faceDetected: false }));
        return;
      }

      // Periodically sample latest tracking data and buffer it
      captureRef.current = setInterval(() => {
        const data = latestRef.current;
        const summary = summaryRef.current;
        summary.expectedSamples += 1;
        summary.activeMs += intervalMs;

        if (data.detected) {
          summary.detectedSamples += 1;
          lastDetectedAtRef.current = Date.now();
          if (inDropoutRef.current) {
            inDropoutRef.current = false;
          }
          consecutiveMissesRef.current = 0;
          bufferRef.current.push({
            post_id: getVisiblePostId(),
            timestamp_ms: Date.now(),
            screen_x: data.screenX,
            screen_y: data.screenY,
            left_iris_x: data.leftIrisX,
            left_iris_y: data.leftIrisY,
            right_iris_x: data.rightIrisX,
            right_iris_y: data.rightIrisY,
          });
        } else {
          summary.missingMs += intervalMs;
          consecutiveMissesRef.current += 1;
          if (
            !inDropoutRef.current
            && consecutiveMissesRef.current >= DROPOUT_WINDOWS
          ) {
            inDropoutRef.current = true;
            summary.noFacePeriods += 1;
          }
        }

        // Compute a snapshot for the UI.
        const coverage =
          summary.expectedSamples === 0
            ? 0
            : summary.detectedSamples / summary.expectedSamples;
        const sinceStart =
          startedAtRef.current === null ? 0 : Date.now() - startedAtRef.current;
        let status: GazeTrackerStatus;
        if (data.detected) {
          status = consecutiveMissesRef.current === 0 && coverage >= 0.6 ? "tracking" : "weak";
        } else if (
          lastDetectedAtRef.current === null
          && sinceStart < STARTUP_GRACE_MS
        ) {
          status = "starting";
        } else if (consecutiveMissesRef.current >= DROPOUT_WINDOWS) {
          status = "lost";
        } else {
          status = "weak";
        }

        setSnapshot({
          status,
          faceDetected: data.detected,
          expectedSamples: summary.expectedSamples,
          detectedSamples: summary.detectedSamples,
          activeMs: summary.activeMs,
          missingMs: summary.missingMs,
          noFacePeriods: summary.noFacePeriods,
          coverage,
        });
      }, intervalMs);

      // Periodic flush to backend
      flushTimerRef.current = setInterval(flush, flushIntervalMs);
    }

    start();

    return () => {
      cancelled = true;
      if (captureRef.current) clearInterval(captureRef.current);
      if (flushTimerRef.current) clearInterval(flushTimerRef.current);
      flush();
      if (cameraInstance) { try { cameraInstance.stop(); } catch {} }
      faceMeshRef.current = null;
      releaseSharedFaceMesh(faceMeshOwnerRef.current);
      faceMeshOwnerRef.current = null;
      if (videoRef.current) {
        videoRef.current.srcObject = null;
        if (!usesExternalVideoRef.current) {
          videoRef.current = null;
        }
      }
      usesExternalVideoRef.current = false;
      setSnapshot((prev) => ({ ...prev, status: "stopped", faceDetected: false }));
    };
  }, [enabled, responseId, participantToken, intervalMs, flushIntervalMs, pipVideoRef, flush, getVisiblePostId]);

  return { flush, snapshot, getSummary };
}
