"use client";

import { useEffect, useRef, useState } from "react";

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

function loadScript(src: string): Promise<void> {
  return new Promise((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) { resolve(); return; }
    const s = document.createElement("script");
    s.src = src; s.crossOrigin = "anonymous";
    s.onload = () => resolve();
    s.onerror = () => reject(new Error(`Failed to load ${src}`));
    document.head.appendChild(s);
  });
}

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
  const cameraRef = useRef<any>(null);
  const fpsRef = useRef({ count: 0, last: performance.now(), fps: 0 });
  const showMeshRef = useRef(true);
  const showIrisRef = useRef(true);
  const showGazeRef = useRef(false);

  useEffect(() => { showMeshRef.current = showMesh; }, [showMesh]);
  useEffect(() => { showIrisRef.current = showIris; }, [showIris]);
  useEffect(() => { showGazeRef.current = showGaze; }, [showGaze]);

  useEffect(() => {
    async function init() {
      await loadScript("https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js");
      await loadScript("https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/face_mesh.js");

      const w = window as any;
      const fm = new w.FaceMesh({
        locateFile: (file: string) => `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`,
      });
      fm.setOptions({ maxNumFaces: 1, refineLandmarks: true, minDetectionConfidence: 0.5, minTrackingConfidence: 0.5 });
      fm.onResults(onResults);
      await fm.initialize();
      faceMeshRef.current = fm;
      setStatus("Ready — click Start Camera");
    }
    init();
    return () => { cameraRef.current?.stop(); faceMeshRef.current?.close(); };
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
      ctx.strokeStyle = "rgba(100, 200, 255, 0.4)";
      ctx.lineWidth = 1;
      for (const [i, j] of FACE_OVAL) {
        ctx.beginPath();
        ctx.moveTo(lm[i].x * canvas.width, lm[i].y * canvas.height);
        ctx.lineTo(lm[j].x * canvas.width, lm[j].y * canvas.height);
        ctx.stroke();
      }
      ctx.fillStyle = "rgba(100, 200, 255, 0.25)";
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
        ctx.strokeStyle = "#00ff88"; ctx.lineWidth = 2; ctx.stroke();
        ctx.beginPath();
        ctx.arc(center.x * canvas.width, center.y * canvas.height, 3, 0, 2 * Math.PI);
        ctx.fillStyle = "#ff3232"; ctx.fill();
      }
    }

    const lRatioX = (leftC.x - lm[33].x) / (lm[133].x - lm[33].x);
    const rRatioX = (rightC.x - lm[263].x) / (lm[362].x - lm[263].x);
    const lRatioY = (leftC.y - lm[159].y) / (lm[145].y - lm[159].y);
    const rRatioY = (rightC.y - lm[386].y) / (lm[374].y - lm[386].y);
    const gazeX = (lRatioX + rRatioX) / 2;
    const gazeY = (lRatioY + rRatioY) / 2;
    const screenX = Math.round((1 - gazeX) * window.innerWidth);
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
    const cam = new w.Camera(videoRef.current, {
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
    <div className="min-h-screen bg-[#1a1a2e] text-white flex flex-col items-center p-5">
      <h1 className="text-2xl font-semibold mb-2">Face & Iris Tracking Demo</h1>
      <p className="text-amber-300 text-sm mb-4">{status}</p>

      <div className="relative rounded-xl overflow-hidden shadow-2xl">
        <video ref={videoRef} width={640} height={480} autoPlay playsInline className="block" style={{ transform: "scaleX(-1)" }} />
        <canvas ref={canvasRef} width={640} height={480} className="absolute top-0 left-0" style={{ transform: "scaleX(-1)" }} />
      </div>

      <div ref={gazeDotRef} className="fixed w-8 h-8 rounded-full border-2 border-red-500 bg-red-500/30 -translate-x-1/2 -translate-y-1/2 pointer-events-none z-[9999]" style={{ display: "none" }} />

      <div className="mt-5 bg-[#16213e] rounded-xl p-5 w-[640px] max-w-[90vw]">
        <h2 className="text-amber-300 font-medium mb-3">Real-time Metrics</h2>
        <div className="grid grid-cols-2 gap-3">
          {[
            { label: "Left Iris (x, y)", value: metrics.leftIris },
            { label: "Right Iris (x, y)", value: metrics.rightIris },
            { label: "Estimated Gaze (screen)", value: metrics.gaze },
            { label: "Face Detected / FPS", value: metrics.face },
          ].map((m) => (
            <div key={m.label} className="bg-[#1a1a2e] rounded-lg px-4 py-3">
              <p className="text-xs text-slate-500 uppercase">{m.label}</p>
              <p className="text-lg font-semibold mt-1">{m.value}</p>
            </div>
          ))}
        </div>

        <div className="mt-4 flex gap-5 text-sm">
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={showMesh} onChange={(e) => setShowMesh(e.target.checked)} /> Face Mesh
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={showIris} onChange={(e) => setShowIris(e.target.checked)} /> Iris Points
          </label>
          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={showGaze} onChange={(e) => setShowGaze(e.target.checked)} /> Gaze Dot
          </label>
        </div>

        <div className="mt-4 flex gap-3">
          <button onClick={startCamera} disabled={running} className="px-5 py-2 rounded-lg bg-rose-500 text-white font-medium hover:bg-rose-600 disabled:opacity-50 disabled:cursor-not-allowed">
            Start Camera
          </button>
          <button onClick={stopCamera} disabled={!running} className="px-5 py-2 rounded-lg bg-[#16213e] text-white border border-slate-600 font-medium hover:bg-[#1a1a2e] disabled:opacity-50 disabled:cursor-not-allowed">
            Stop
          </button>
        </div>
      </div>
    </div>
  );
}
