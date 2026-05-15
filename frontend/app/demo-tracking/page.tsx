"use client";

import { useEffect, useRef, useState } from "react";
import { acquireSharedFaceMesh, releaseSharedFaceMesh } from "@/lib/mediapipe-face-mesh";

const LEFT_IRIS = [468, 469, 470, 471, 472];
const RIGHT_IRIS = [473, 474, 475, 476, 477];
const FACE_OVAL = [
  [10,338],[338,297],[297,332],[332,284],[284,251],[251,389],
  [389,356],[356,454],[454,323],[323,361],[361,288],[288,397],
  [397,365],[365,379],[379,378],[378,400],[400,377],[377,152],
  [152,148],[148,176],[176,149],[149,150],[150,136],[136,172],
  [172,58],[58,132],[132,93],[93,234],[234,127],[127,162],
  [162,21],[21,54],[54,103],[103,67],[67,109],[109,10],
];

export default function DemoTrackingPage() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const gazeDotRef = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState("Loading MediaPipe Face Mesh...");
  const [running, setRunning] = useState(false);
  const [showMesh, setShowMesh] = useState(true);
  const [showIris, setShowIris] = useState(true);
  const [showGaze, setShowGaze] = useState(false);
  const [metrics, setMetrics] = useState({ leftIris: "--", rightIris: "--", gaze: "--", face: "--" });

  const faceMeshRef = useRef<any>(null);
  const faceMeshOwnerRef = useRef<symbol | null>(null);
  const cameraRef = useRef<any>(null);
  const fpsRef = useRef({ count: 0, last: performance.now(), fps: 0 });
  const showMeshRef = useRef(true);
  const showIrisRef = useRef(true);
  const showGazeRef = useRef(false);

  useEffect(() => { showMeshRef.current = showMesh; }, [showMesh]);
  useEffect(() => { showIrisRef.current = showIris; }, [showIris]);
  useEffect(() => { showGazeRef.current = showGaze; }, [showGaze]);

  useEffect(() => {
    let cancelled = false;

    async function init() {
      try {
        const acquired = await acquireSharedFaceMesh(onResults);
        if (cancelled) {
          releaseSharedFaceMesh(acquired.owner);
          return;
        }
        faceMeshRef.current = acquired.faceMesh;
        faceMeshOwnerRef.current = acquired.owner;
        setStatus("Ready - click Start Camera");
      } catch (error) {
        setStatus(error instanceof Error ? error.message : "MediaPipe failed to load.");
      }
    }
    init();
    return () => {
      cancelled = true;
      cameraRef.current?.stop();
      releaseSharedFaceMesh(faceMeshOwnerRef.current);
      faceMeshOwnerRef.current = null;
    };
  }, []);

  function onResults(results: any) {
    const canvas = canvasRef.current;
    const dot = gazeDotRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    fpsRef.current.count++;
    const now = performance.now();
    if (now - fpsRef.current.last >= 1000) {
      fpsRef.current.fps = fpsRef.current.count;
      fpsRef.current.count = 0;
      fpsRef.current.last = now;
    }

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (!results.multiFaceLandmarks?.length) {
      setMetrics({ leftIris: "--", rightIris: "--", gaze: "--", face: `No face | ${fpsRef.current.fps} FPS` });
      if (dot) dot.style.display = "none";
      return;
    }

    const lm = results.multiFaceLandmarks[0];

    if (showMeshRef.current) {
      ctx.strokeStyle = "rgba(0, 167, 160, 0.42)";
      ctx.lineWidth = 1;
      for (const [i, j] of FACE_OVAL) {
        ctx.beginPath();
        ctx.moveTo(lm[i].x * canvas.width, lm[i].y * canvas.height);
        ctx.lineTo(lm[j].x * canvas.width, lm[j].y * canvas.height);
        ctx.stroke();
      }
      ctx.fillStyle = "rgba(0, 132, 127, 0.28)";
      for (let i = 0; i < 468; i++) {
        ctx.beginPath();
        ctx.arc(lm[i].x * canvas.width, lm[i].y * canvas.height, 0.8, 0, 2 * Math.PI);
        ctx.fill();
      }
    }

    const leftC = lm[468], rightC = lm[473];

    if (showIrisRef.current) {
      for (const indices of [LEFT_IRIS, RIGHT_IRIS]) {
        const center = lm[indices[0]];
        let radius = 0;
        for (let i = 1; i < indices.length; i++) {
          const dx = (lm[indices[i]].x - center.x) * canvas.width;
          const dy = (lm[indices[i]].y - center.y) * canvas.height;
          radius += Math.sqrt(dx * dx + dy * dy);
        }
        radius /= (indices.length - 1);
        ctx.beginPath();
        ctx.arc(center.x * canvas.width, center.y * canvas.height, radius, 0, 2 * Math.PI);
        ctx.strokeStyle = "#00a7a0"; ctx.lineWidth = 2; ctx.stroke();
        ctx.beginPath();
        ctx.arc(center.x * canvas.width, center.y * canvas.height, 3, 0, 2 * Math.PI);
        ctx.fillStyle = "#0f3146"; ctx.fill();
      }
    }

    const lRatioX = (leftC.x - lm[33].x) / (lm[133].x - lm[33].x);
    const rRatioX = (rightC.x - lm[263].x) / (lm[362].x - lm[263].x);
    const lRatioY = (leftC.y - lm[159].y) / (lm[145].y - lm[159].y);
    const rRatioY = (rightC.y - lm[386].y) / (lm[374].y - lm[386].y);
    const gazeX = (lRatioX + rRatioX) / 2;
    const gazeY = (lRatioY + rRatioY) / 2;
    const screenX = Math.round(gazeX * window.innerWidth);
    const screenY = Math.round(gazeY * window.innerHeight);

    setMetrics({
      leftIris: `(${leftC.x.toFixed(3)}, ${leftC.y.toFixed(3)})`,
      rightIris: `(${rightC.x.toFixed(3)}, ${rightC.y.toFixed(3)})`,
      gaze: `(${screenX}, ${screenY})`,
      face: `Detected | ${fpsRef.current.fps} FPS`,
    });

    if (dot) {
      if (showGazeRef.current) {
        dot.style.display = "block";
        dot.style.left = screenX + "px";
        dot.style.top = screenY + "px";
      } else {
        dot.style.display = "none";
      }
    }
  }

  async function startCamera() {
    if (!faceMeshRef.current || !videoRef.current) return;
    const w = window as any;
    const CameraCtor = typeof w.Camera === "function" ? w.Camera : w.Camera?.Camera;
    if (typeof CameraCtor !== "function") {
      setStatus("MediaPipe camera utils failed to load.");
      return;
    }

    const cam = new CameraCtor(videoRef.current, {
      onFrame: async () => {
        if (faceMeshRef.current) await faceMeshRef.current.send({ image: videoRef.current });
      },
      width: 640, height: 480,
    });
    await cam.start();
    cameraRef.current = cam;
    setRunning(true);
    setStatus("Tracking active");
  }

  function stopCamera() {
    cameraRef.current?.stop();
    cameraRef.current = null;
    setRunning(false);
    setStatus("Camera stopped");
    canvasRef.current?.getContext("2d")?.clearRect(0, 0, 640, 480);
    if (gazeDotRef.current) gazeDotRef.current.style.display = "none";
  }

  return (
    <div className="flex min-h-screen flex-col items-center bg-[var(--app-bg)] p-5 text-[var(--app-text)]">
      <div className="mb-5 text-center">
        <p className="section-kicker text-[var(--app-accent)]">Survey Engine</p>
        <h1 className="page-title mt-2">Face & Iris Tracking Demo</h1>
        <p className="mt-2 text-sm text-[var(--app-muted-strong)]">{status}</p>
      </div>

      <div className="surface-panel relative overflow-hidden bg-slate-950">
        <video ref={videoRef} width={640} height={480} autoPlay playsInline className="block" />
        <canvas ref={canvasRef} width={640} height={480} className="absolute top-0 left-0" />
      </div>

      <div ref={gazeDotRef} className="pointer-events-none fixed z-[9999] h-8 w-8 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-[var(--app-accent)] bg-[rgba(0,167,160,0.22)] shadow-[0_0_28px_rgba(0,167,160,0.5)]" style={{ display: "none" }} />

      <div className="surface-panel mt-5 w-[640px] max-w-[90vw] p-5">
        <h2 className="section-title mb-3">Real-time Metrics</h2>
        <div className="grid grid-cols-2 gap-3">
          {[
            { label: "Left Iris (x, y)", value: metrics.leftIris },
            { label: "Right Iris (x, y)", value: metrics.rightIris },
            { label: "Estimated Gaze (screen)", value: metrics.gaze },
            { label: "Face Detected / FPS", value: metrics.face },
          ].map((m) => (
            <div key={m.label} className="rounded-[16px] border bg-[var(--app-panel-muted)] px-4 py-3">
              <p className="text-xs uppercase tracking-[0.18em] text-[var(--app-muted)]">{m.label}</p>
              <p className="mt-1 text-lg font-semibold text-[var(--app-text)]">{m.value}</p>
            </div>
          ))}
        </div>

        <div className="mt-4 flex flex-wrap gap-5 text-sm text-[var(--app-muted-strong)]">
          <label className="flex cursor-pointer items-center gap-2">
            <input className="accent-[var(--app-accent)]" type="checkbox" checked={showMesh} onChange={(e) => setShowMesh(e.target.checked)} /> Face Mesh
          </label>
          <label className="flex cursor-pointer items-center gap-2">
            <input className="accent-[var(--app-accent)]" type="checkbox" checked={showIris} onChange={(e) => setShowIris(e.target.checked)} /> Iris Points
          </label>
          <label className="flex cursor-pointer items-center gap-2">
            <input className="accent-[var(--app-accent)]" type="checkbox" checked={showGaze} onChange={(e) => setShowGaze(e.target.checked)} /> Gaze Dot
          </label>
        </div>

        <div className="mt-4 flex gap-3">
          <button onClick={startCamera} disabled={running} className="primary-button px-5 py-2 disabled:opacity-50">
            Start Camera
          </button>
          <button onClick={stopCamera} disabled={!running} className="secondary-button px-5 py-2 disabled:opacity-50">
            Stop
          </button>
        </div>
      </div>
    </div>
  );
}
