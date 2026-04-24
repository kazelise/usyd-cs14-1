"use client";
import { useEffect, useRef, useCallback } from "react";
import { api } from "@/lib/api";

interface GazeTrackerOptions {
  responseId: number;
  participantToken: string;
  intervalMs: number;
  enabled: boolean;
  flushIntervalMs?: number;
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

function loadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) { resolve(); return; }
    const s = document.createElement("script");
    s.src = src;
    s.crossOrigin = "anonymous";
    s.onload = () => resolve();
    s.onerror = () => reject(new Error(`Failed to load ${src}`));
    document.head.appendChild(s);
  });
}

const closedFaceMeshInstances = new WeakSet<object>();

function closeFaceMeshOnce(faceMesh: any) {
  if (!faceMesh || typeof faceMesh !== "object" || closedFaceMeshInstances.has(faceMesh)) return;
  closedFaceMeshInstances.add(faceMesh);
  try {
    faceMesh.close?.();
  } catch {
    // MediaPipe can throw BindingError when React cleanup races with WASM disposal.
  }
}

/**
 * Continuously captures gaze data during the survey using MediaPipe Face Mesh
 * for real iris tracking, then sends batches to POST /tracking/gaze.
 *
 * Uses the same approach as the team's Face & Iris Tracking Demo:
 * - MediaPipe Face Mesh with refineLandmarks for iris landmarks (468-477)
 * - Gaze estimation via iris-to-eye-corner ratio
 * - Webcam started internally when enabled=true, stopped on cleanup
 */
export function useGazeTracker({
  responseId,
  participantToken,
  intervalMs,
  enabled,
  flushIntervalMs = 5000,
}: GazeTrackerOptions) {
  const bufferRef = useRef<any[]>([]);
  const streamRef = useRef<MediaStream | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const faceMeshRef = useRef<any>(null);
  const captureRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const flushTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

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

  useEffect(() => {
    if (!enabled || !responseId || !participantToken) return;

    let cancelled = false;
    let cameraInstance: any = null;

    async function start() {
      // Load MediaPipe scripts
      try {
        await loadScript("https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js");
        await loadScript("https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/face_mesh.js");
      } catch (err) {
        console.error("Failed to load MediaPipe for gaze tracking:", err);
        return;
      }
      if (cancelled) return;

      const w = window as any;

      // Initialize Face Mesh
      const faceMesh = new w.FaceMesh({
        locateFile: (file: string) =>
          `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`,
      });
      faceMesh.setOptions({
        maxNumFaces: 1,
        refineLandmarks: true,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5,
      });

      faceMesh.onResults((results: any) => {
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

        // Map to screen coordinates (mirrored horizontally)
        const screenX = Math.round((1 - gazeX) * window.innerWidth);
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

      await faceMesh.initialize();
      if (cancelled) {
        closeFaceMeshOnce(faceMesh);
        return;
      }
      faceMeshRef.current = faceMesh;

      // Start webcam via MediaPipe Camera utility
      const video = document.createElement("video");
      video.setAttribute("playsinline", "");
      video.setAttribute("autoplay", "");
      video.muted = true;
      videoRef.current = video;

      cameraInstance = new w.Camera(video, {
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
        return;
      }

      // Periodically sample latest tracking data and buffer it
      captureRef.current = setInterval(() => {
        const data = latestRef.current;
        if (!data.detected) return;

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
      const faceMesh = faceMeshRef.current;
      faceMeshRef.current = null;
      closeFaceMeshOnce(faceMesh);
      if (videoRef.current) { videoRef.current.srcObject = null; videoRef.current = null; }
    };
  }, [enabled, responseId, participantToken, intervalMs, flushIntervalMs, flush, getVisiblePostId]);

  return { flush };
}
