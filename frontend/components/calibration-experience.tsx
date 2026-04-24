"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";

type CalibrationStep = "permission" | "detection" | "calibration" | "results";

type CalibrationResult = {
  session_id: number;
  status: string;
  quality: {
    total_points: number;
    valid_points: number;
    avg_samples_per_point: number;
    face_detection_rate: number;
    overall_quality: string;
  };
  completed_at: string;
};

type CalibrationExperienceProps = {
  responseId: number;
  participantToken?: string;
  expectedPoints?: number;
  onComplete: (result: CalibrationResult) => void;
};

type CameraSnapshot = {
  faceDetected: boolean;
  brightness: number;
};

type IrisReading = {
  detected: boolean;
  leftIrisX: number;
  leftIrisY: number;
  rightIrisX: number;
  rightIrisY: number;
  headYaw: number;
  headPitch: number;
};

// MediaPipe Face Mesh landmark indices
const LEFT_IRIS_CENTER = 468;
const RIGHT_IRIS_CENTER = 473;
const NOSE_TIP = 1;
const FOREHEAD = 10;
const CHIN = 152;
const LEFT_CHEEK = 234;
const RIGHT_CHEEK = 454;

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

const POINT_LAYOUT = [
  { x: 0.12, y: 0.14, label: "Top left" },
  { x: 0.5, y: 0.14, label: "Top center" },
  { x: 0.88, y: 0.14, label: "Top right" },
  { x: 0.16, y: 0.5, label: "Middle left" },
  { x: 0.5, y: 0.5, label: "Center" },
  { x: 0.84, y: 0.5, label: "Middle right" },
  { x: 0.12, y: 0.86, label: "Bottom left" },
  { x: 0.5, y: 0.86, label: "Bottom center" },
  { x: 0.88, y: 0.86, label: "Bottom right" },
];

function sleep(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

export function CalibrationExperience({
  responseId,
  participantToken,
  expectedPoints = 9,
  onComplete,
}: CalibrationExperienceProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const faceMeshRef = useRef<any>(null);
  const detectionHistoryRef = useRef<boolean[]>([]);
  // Latest iris reading from MediaPipe, updated every frame
  const latestIrisRef = useRef<IrisReading>({
    detected: false,
    leftIrisX: 0, leftIrisY: 0,
    rightIrisX: 0, rightIrisY: 0,
    headYaw: 0, headPitch: 0,
  });
  const [step, setStep] = useState<CalibrationStep>("permission");
  const [permissionState, setPermissionState] = useState<"idle" | "granted" | "denied">("idle");
  const [cameraError, setCameraError] = useState("");
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [faceDetected, setFaceDetected] = useState(false);
  const [detectionStable, setDetectionStable] = useState(false);
  const [qualityScore, setQualityScore] = useState(0);
  const [brightnessScore, setBrightnessScore] = useState(0);
  const [activePointIndex, setActivePointIndex] = useState(0);
  const [pointsCompleted, setPointsCompleted] = useState(0);
  const [calibrating, setCalibrating] = useState(false);
  const [result, setResult] = useState<CalibrationResult | null>(null);
  const [busyMessage, setBusyMessage] = useState("");

  const points = useMemo(
    () => POINT_LAYOUT.slice(0, Math.min(expectedPoints, POINT_LAYOUT.length)),
    [expectedPoints],
  );

  useEffect(() => {
    return () => {
      stopCamera();
      faceMeshRef.current?.close();
    };
  }, []);

  useEffect(() => {
    if (permissionState !== "granted" || !videoRef.current) return;

    let cancelled = false;
    let creatingSession = false;
    const intervalId = window.setInterval(async () => {
      if (cancelled) return;
      const snapshot = analyzeFrame();
      if (cancelled) return;

      const nextHistory = [...detectionHistoryRef.current, snapshot.faceDetected].slice(-8);
      detectionHistoryRef.current = nextHistory;

      const stableDetections = nextHistory.filter(Boolean).length;
      const nextStable = stableDetections >= 4 && nextHistory.slice(-4).filter(Boolean).length >= 3;
      const detectionRate = nextHistory.length ? stableDetections / nextHistory.length : 0;
      const nextQuality = Math.round(Math.min(100, detectionRate * 70 + snapshot.brightness * 0.3));

      setFaceDetected(snapshot.faceDetected);
      setDetectionStable(nextStable);
      setBrightnessScore(snapshot.brightness);
      setQualityScore(nextQuality);

      if (sessionId === null && responseId <= 0) {
        setSessionId(0);
        return;
      }

      if (
        sessionId === null &&
        participantToken &&
        !creatingSession &&
        videoRef.current &&
        videoRef.current.videoWidth > 0
      ) {
        creatingSession = true;
        try {
          const session = await api.createCalibrationSession({
            response_id: responseId,
            participant_token: participantToken,
            screen_width: window.innerWidth,
            screen_height: window.innerHeight,
            camera_width: videoRef.current.videoWidth,
            camera_height: videoRef.current.videoHeight,
          });
          if (!cancelled) {
            setSessionId(session.session_id);
          }
        } catch (error) {
          if (!cancelled) {
            setCameraError(error instanceof Error ? error.message : "Failed to start calibration session.");
          }
        }
        creatingSession = false;
      }
    }, 700);

    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [participantToken, permissionState, responseId, sessionId]);

  async function requestCameraAccess() {
    setCameraError("");
    setBusyMessage("Loading MediaPipe Face Mesh...");
    try {
      // Load MediaPipe scripts
      await loadScript("https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js");
      await loadScript("https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/face_mesh.js");

      const w = window as any;
      const faceMesh = new w.FaceMesh({
        locateFile: (file: string) =>
          `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`,
      });
      faceMesh.setOptions({
        maxNumFaces: 1,
        refineLandmarks: true, // enables iris landmarks 468-477
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5,
      });
      faceMesh.onResults((results: any) => {
        if (!results.multiFaceLandmarks || results.multiFaceLandmarks.length === 0) {
          latestIrisRef.current = { ...latestIrisRef.current, detected: false };
          return;
        }
        const lm = results.multiFaceLandmarks[0];
        const leftIris = lm[LEFT_IRIS_CENTER];
        const rightIris = lm[RIGHT_IRIS_CENTER];
        // Head rotation estimation from face landmarks
        const nose = lm[NOSE_TIP];
        const forehead = lm[FOREHEAD];
        const chin = lm[CHIN];
        const leftCheek = lm[LEFT_CHEEK];
        const rightCheek = lm[RIGHT_CHEEK];
        const yaw = (leftCheek.x - rightCheek.x) !== 0
          ? ((nose.x - (leftCheek.x + rightCheek.x) / 2) / Math.abs(leftCheek.x - rightCheek.x)) * 45
          : 0;
        const pitch = (chin.y - forehead.y) !== 0
          ? ((nose.y - (forehead.y + chin.y) / 2) / Math.abs(chin.y - forehead.y)) * 45
          : 0;

        latestIrisRef.current = {
          detected: true,
          leftIrisX: leftIris.x,
          leftIrisY: leftIris.y,
          rightIrisX: rightIris.x,
          rightIrisY: rightIris.y,
          headYaw: Number(yaw.toFixed(2)),
          headPitch: Number(pitch.toFixed(2)),
        };
      });
      await faceMesh.initialize();
      faceMeshRef.current = faceMesh;

      setBusyMessage("Requesting camera permission");
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
        audio: false,
      });
      streamRef.current = stream;
      setPermissionState("granted");
      setStep("detection");
      setBusyMessage("");

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }

      // Start sending frames to MediaPipe continuously
      startMediaPipeLoop();
    } catch (error) {
      setPermissionState("denied");
      setBusyMessage("");
      setCameraError(error instanceof Error ? error.message : "Camera permission was denied.");
    }
  }

  function startMediaPipeLoop() {
    let sending = false;
    const interval = window.setInterval(async () => {
      if (sending || !videoRef.current || !faceMeshRef.current || videoRef.current.readyState < 2) return;
      sending = true;
      try {
        await faceMeshRef.current.send({ image: videoRef.current });
      } catch { /* skip frame */ }
      sending = false;
    }, 33); // ~30 fps for responsive tracking
    // Store interval so we can clean up
    const origStop = stopCamera;
    // eslint-disable-next-line react-hooks/exhaustive-deps
    stopCamera = () => {
      window.clearInterval(interval);
      origStop();
    };
  }

  // eslint-disable-next-line prefer-const
  let stopCamera = () => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
  };

  function analyzeFrame(): CameraSnapshot {
    const video = videoRef.current;
    if (!video || video.readyState < 2 || !video.videoWidth || !video.videoHeight) {
      return { faceDetected: false, brightness: 0 };
    }

    // Brightness from canvas
    const canvas = document.createElement("canvas");
    canvas.width = 160;
    canvas.height = 120;
    const context = canvas.getContext("2d", { willReadFrequently: true });
    let brightness = 0;
    if (context) {
      context.drawImage(video, 0, 0, canvas.width, canvas.height);
      const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
      let acc = 0;
      for (let index = 0; index < pixels.length; index += 32) {
        acc += (pixels[index] + pixels[index + 1] + pixels[index + 2]) / 3;
      }
      const sampleCount = pixels.length / 32;
      brightness = sampleCount ? Math.round(acc / sampleCount) : 0;
    }

    // Face detection from MediaPipe (latestIrisRef is updated by onResults callback)
    const detected = latestIrisRef.current.detected;
    return { faceDetected: detected, brightness };
  }

  function buildSample() {
    const iris = latestIrisRef.current;
    return {
      timestamp_ms: Date.now(),
      left_iris_x: Number(iris.leftIrisX.toFixed(4)),
      left_iris_y: Number(iris.leftIrisY.toFixed(4)),
      right_iris_x: Number(iris.rightIrisX.toFixed(4)),
      right_iris_y: Number(iris.rightIrisY.toFixed(4)),
      face_detected: iris.detected,
      head_rotation: {
        yaw: iris.headYaw,
        pitch: iris.headPitch,
        roll: 0,
      },
    };
  }

  async function runCalibration() {
    if (sessionId === null || calibrating) return;
    setCalibrating(true);
    setStep("calibration");
    setBusyMessage("Capturing gaze samples");

    try {
      for (const [index, point] of points.entries()) {
        setActivePointIndex(index);
        const targetX = Math.round(window.innerWidth * point.x);
        const targetY = Math.round(window.innerHeight * point.y);

        // Dwell: let participant look at the dot
        await sleep(1200);

        // Record 12 samples
        const samples = [];
        for (let sampleIndex = 0; sampleIndex < 12; sampleIndex += 1) {
          await sleep(120);
          const snapshot = analyzeFrame();
          setFaceDetected(snapshot.faceDetected);
          setBrightnessScore(snapshot.brightness);
          setQualityScore((previous) => Math.max(previous, Math.round(snapshot.brightness * 0.35)));
          samples.push(buildSample());
        }

        if (sessionId > 0 && participantToken) {
          await api.recordCalibrationPoint(sessionId, {
            participant_token: participantToken,
            point_index: index + 1,
            target_screen_x: targetX,
            target_screen_y: targetY,
            samples,
          });
        }
        setPointsCompleted(index + 1);
        await sleep(200);
      }

      const completeResult =
        sessionId > 0 && participantToken
          ? await api.completeCalibration(sessionId, { participant_token: participantToken })
          : {
              session_id: sessionId,
              status: "completed",
              quality: {
                total_points: points.length,
                valid_points: points.length,
                avg_samples_per_point: 12,
                face_detection_rate: faceDetected ? 1 : 0,
                overall_quality: faceDetected ? "good" : "poor",
              },
              completed_at: new Date().toISOString(),
            };
      setResult(completeResult);
      setBusyMessage("");
      setStep("results");
      stopCamera();
    } catch (error) {
      setCameraError(error instanceof Error ? error.message : "Calibration failed.");
      setBusyMessage("");
      setCalibrating(false);
      return;
    }
    setCalibrating(false);
  }

  const qualityTone =
    result?.quality.overall_quality === "good"
      ? "text-emerald-300"
      : result?.quality.overall_quality === "acceptable"
        ? "text-amber-300"
        : "text-rose-300";

  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,#1f2937_0%,#0f172a_48%,#020617_100%)] text-white">
      <div className="mx-auto flex min-h-screen max-w-7xl flex-col px-5 py-6 lg:px-8">
        <div className="mb-6 flex items-center justify-between text-sm text-slate-300">
          <div>
            <p className="font-mono uppercase tracking-[0.3em] text-cyan-300">Survey Engine</p>
            <h1 className="mt-2 text-[28px] font-semibold tracking-tight text-white">Webcam Calibration</h1>
          </div>
          <div className="rounded-full border border-white/10 bg-white/5 px-4 py-2">
            Step{" "}
            {step === "permission"
              ? "1"
              : step === "detection"
                ? "2"
                : step === "calibration"
                  ? "3"
                  : "4"}{" "}
            of 4
          </div>
        </div>

        <div className="grid flex-1 gap-6 lg:grid-cols-[260px_minmax(0,1fr)]">
          <aside className="rounded-[20px] border border-white/10 bg-white/6 p-5 shadow-2xl shadow-cyan-950/20 backdrop-blur">
            <p className="text-xs uppercase tracking-[0.28em] text-slate-400">Calibration Progress</p>
            <div className="mt-6 space-y-3">
              {[
                { key: "permission", label: "Camera permission" },
                { key: "detection", label: "Face detection" },
                { key: "calibration", label: "Calibration dots" },
                { key: "results", label: "Quality score" },
              ].map((item, index) => {
                const itemStep = item.key as CalibrationStep;
                const active = itemStep === step;
                const complete =
                  (itemStep === "permission" && permissionState === "granted") ||
                  (itemStep === "detection" && detectionStable) ||
                  (itemStep === "calibration" && pointsCompleted === points.length) ||
                  (itemStep === "results" && Boolean(result));

                return (
                  <div
                    key={item.key}
                    className={`rounded-[18px] border px-4 py-3 transition ${
                      active
                        ? "border-cyan-300/40 bg-cyan-400/10 text-white"
                        : complete
                          ? "border-emerald-400/20 bg-emerald-400/10 text-emerald-100"
                          : "border-white/8 bg-white/4 text-slate-400"
                    }`}
                  >
                    <p className="text-[11px] uppercase tracking-[0.24em]">Stage {index + 1}</p>
                    <p className="mt-1 text-sm font-medium">{item.label}</p>
                  </div>
                );
              })}
            </div>

            <div className="mt-8 rounded-[18px] border border-white/8 bg-slate-950/40 p-4">
              <p className="text-xs uppercase tracking-[0.24em] text-slate-400">Live Metrics</p>
              <div className="mt-4 space-y-4">
                <div>
                  <div className="mb-1 flex items-center justify-between text-xs text-slate-400">
                    <span>Face lock</span>
                    <span className={faceDetected ? "text-emerald-300" : "text-rose-300"}>
                      {faceDetected ? "Detected" : "Searching"}
                    </span>
                  </div>
                  <div className="h-2 rounded-full bg-white/10">
                    <div
                      className={`h-2 rounded-full transition-all ${faceDetected ? "bg-emerald-400" : "bg-rose-400"}`}
                      style={{ width: `${faceDetected ? 100 : 24}%` }}
                    />
                  </div>
                </div>
                <div>
                  <div className="mb-1 flex items-center justify-between text-xs text-slate-400">
                    <span>Environment quality</span>
                    <span>{qualityScore}%</span>
                  </div>
                  <div className="h-2 rounded-full bg-white/10">
                    <div className="h-2 rounded-full bg-cyan-300 transition-all" style={{ width: `${qualityScore}%` }} />
                  </div>
                </div>
                  <div className="grid grid-cols-2 gap-3 text-xs text-slate-300">
                  <div className="rounded-[16px] border border-white/8 bg-white/4 p-3">
                    <p className="text-slate-400">Brightness</p>
                    <p className="mt-1 text-lg font-semibold text-white">{brightnessScore}</p>
                  </div>
                  <div className="rounded-[16px] border border-white/8 bg-white/4 p-3">
                    <p className="text-slate-400">Dots done</p>
                    <p className="mt-1 text-lg font-semibold text-white">
                      {pointsCompleted}/{points.length}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </aside>

          <section className="relative overflow-hidden rounded-[24px] border border-white/10 bg-slate-950/55 shadow-2xl shadow-slate-950/50 backdrop-blur">
            <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_10%,rgba(34,211,238,0.16),transparent_32%),radial-gradient(circle_at_80%_20%,rgba(56,189,248,0.12),transparent_28%),linear-gradient(135deg,rgba(15,23,42,0.92),rgba(2,6,23,0.97))]" />
            <div className="relative flex h-full flex-col p-6 lg:p-8">
              <div className="mb-6 flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs uppercase tracking-[0.3em] text-cyan-300">
                    {step === "permission"
                      ? "Camera access"
                      : step === "detection"
                        ? "Face alignment"
                        : step === "calibration"
                          ? "Eye tracking"
                          : "Calibration summary"}
                  </p>
                  <h2 className="mt-2 text-[22px] font-semibold tracking-tight text-white">
                    {step === "permission" && "Allow camera access to begin calibration."}
                    {step === "detection" && "Center your face in the frame and keep still."}
                    {step === "calibration" && "Follow the active dot with your eyes only."}
                    {step === "results" && "Calibration finished. Review the capture quality."}
                  </h2>
                </div>
                {busyMessage && (
                  <div className="rounded-full border border-cyan-300/20 bg-cyan-300/10 px-4 py-2 text-xs uppercase tracking-[0.22em] text-cyan-100">
                    {busyMessage}
                  </div>
                )}
              </div>

              <div className="grid flex-1 gap-6 xl:grid-cols-[minmax(0,1fr)_240px]">
                <div className="relative min-h-[520px] overflow-hidden rounded-[20px] border border-white/10 bg-slate-900/80">
                  <video ref={videoRef} className="h-full w-full object-cover" autoPlay muted playsInline />
                  <div className="absolute inset-0 bg-[linear-gradient(180deg,rgba(2,6,23,0.08),rgba(2,6,23,0.4))]" />

                  {step !== "results" && (
                    <div className="pointer-events-none absolute inset-0">
                      <div className="absolute left-1/2 top-1/2 h-[58%] w-[42%] -translate-x-1/2 -translate-y-1/2 rounded-[48%_48%_42%_42%/58%_58%_34%_34%] border-2 border-dashed border-white/35" />
                      <div className="absolute left-6 top-6 rounded-full border border-white/10 bg-slate-950/60 px-3 py-1 text-[11px] uppercase tracking-[0.24em] text-white">
                        {faceDetected ? "Face detected" : "Searching for face"}
                      </div>
                    </div>
                  )}

                  {step === "calibration" && (
                    <>
                      <div className="absolute inset-0 grid grid-cols-3 grid-rows-3 opacity-10">
                        {points.map((point) => (
                          <div key={point.label} className="border border-white/10" />
                        ))}
                      </div>
                      {points.map((point, index) => {
                        const active = index === activePointIndex;
                        const complete = index < pointsCompleted;
                        return (
                          <div
                            key={point.label}
                            className="absolute -translate-x-1/2 -translate-y-1/2 transition-all duration-500"
                            style={{ left: `${point.x * 100}%`, top: `${point.y * 100}%` }}
                          >
                            <div
                              className={`relative flex h-20 w-20 items-center justify-center rounded-full ${
                                active ? "scale-100 opacity-100" : complete ? "scale-75 opacity-35" : "scale-75 opacity-18"
                              }`}
                            >
                              <div className={`absolute inset-0 rounded-full ${active ? "animate-ping bg-cyan-300/20" : "bg-transparent"}`} />
                              <div
                                className={`absolute inset-3 rounded-full border ${
                                  active ? "border-cyan-200" : complete ? "border-emerald-300/40" : "border-white/30"
                                }`}
                              />
                              <div
                                className={`h-4 w-4 rounded-full ${
                                  active ? "bg-cyan-200 shadow-[0_0_24px_rgba(103,232,249,0.8)]" : complete ? "bg-emerald-300" : "bg-white/50"
                                }`}
                              />
                            </div>
                          </div>
                        );
                      })}
                    </>
                  )}

                  {step === "results" && result && (
                    <div className="absolute inset-0 flex items-center justify-center bg-slate-950/70 backdrop-blur-sm">
                      <div className="w-full max-w-xl rounded-[20px] border border-white/10 bg-slate-950/80 p-8 shadow-2xl">
                        <p className={`text-xs uppercase tracking-[0.28em] ${qualityTone}`}>Overall quality</p>
                        <h3 className="mt-3 text-4xl font-semibold capitalize text-white">
                          {result.quality.overall_quality}
                        </h3>
                        <div className="mt-6 grid gap-4 sm:grid-cols-2">
                          <div className="rounded-[16px] border border-white/8 bg-white/4 p-4">
                            <p className="text-sm text-slate-400">Face detection rate</p>
                            <p className="mt-2 text-3xl font-semibold text-white">
                              {Math.round(result.quality.face_detection_rate * 100)}%
                            </p>
                          </div>
                          <div className="rounded-[16px] border border-white/8 bg-white/4 p-4">
                            <p className="text-sm text-slate-400">Avg samples / point</p>
                            <p className="mt-2 text-3xl font-semibold text-white">
                              {result.quality.avg_samples_per_point}
                            </p>
                          </div>
                        </div>
                        <div className="mt-4 rounded-[16px] border border-white/8 bg-white/4 p-4 text-sm text-slate-300">
                          {result.quality.valid_points} of {result.quality.total_points} points reached the required
                          sample threshold.
                        </div>
                        {result.quality.overall_quality === "poor" && (
                          <div className="mt-4 rounded-[16px] border border-rose-400/20 bg-rose-400/10 p-4 text-sm text-rose-200">
                            Low quality detected. Please ensure your face is visible and well-lit, then retry.
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>

                <div className="flex flex-col justify-between rounded-[20px] border border-white/10 bg-white/6 p-5">
                  <div>
                    <p className="text-xs uppercase tracking-[0.26em] text-slate-400">Operator Notes</p>
                    <div className="mt-4 space-y-3 text-sm leading-6 text-slate-300">
                      {step === "permission" && (
                        <>
                          <p>Chrome or Edge gives the best local result because FaceDetector support is stronger.</p>
                          <p>The calibration session is created only after the webcam stream is live.</p>
                        </>
                      )}
                      {step === "detection" && (
                        <>
                          <p>Keep your forehead and chin inside the guide outline.</p>
                          <p>A stable face lock will unlock the dot sequence and improve the quality score.</p>
                        </>
                      )}
                      {step === "calibration" && (
                        <>
                          <p>Do not move your head. Only track the active dot with your eyes.</p>
                          <p>The system records 12 samples for each point and submits them to the backend session.</p>
                        </>
                      )}
                      {step === "results" && result && (
                        <>
                          <p>The backend quality score is based on face detection rate and valid point coverage.</p>
                          <p>Once you continue, the survey feed starts and click tracking resumes from that point.</p>
                        </>
                      )}
                    </div>

                    {cameraError && (
                      <div className="mt-5 rounded-[16px] border border-rose-400/20 bg-rose-400/10 px-4 py-3 text-sm text-rose-100">
                        {cameraError}
                      </div>
                    )}
                  </div>

                  <div className="mt-8">
                    {step === "permission" && (
                      <button
                        onClick={requestCameraAccess}
                        className="w-full rounded-[16px] bg-cyan-300 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-cyan-200"
                      >
                        Allow Camera Access
                      </button>
                    )}
                    {step === "detection" && (
                      <button
                        onClick={runCalibration}
                        disabled={!detectionStable || sessionId === null}
                        className="w-full rounded-[16px] bg-white px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:bg-white/15 disabled:text-slate-500"
                      >
                        Start Calibration Dots
                      </button>
                    )}
                    {step === "calibration" && (
                      <div className="rounded-[16px] border border-white/8 bg-slate-950/50 px-4 py-3 text-sm text-slate-300">
                        Recording point {Math.min(activePointIndex + 1, points.length)} of {points.length}
                      </div>
                    )}
                    {step === "results" && result && (
                      <div className="space-y-3">
                        {result.quality.overall_quality === "poor" && (
                          <button
                            onClick={async () => {
                              setResult(null);
                              setSessionId(null);
                              setPointsCompleted(0);
                              setActivePointIndex(0);
                              setCalibrating(false);
                              setStep("detection");
                              setDetectionStable(false);
                              detectionHistoryRef.current = [];
                              // Camera is already stopped, restart it
                              if (streamRef.current) {
                                if (videoRef.current) {
                                  videoRef.current.srcObject = streamRef.current;
                                  await videoRef.current.play();
                                }
                                setPermissionState("granted");
                                startMediaPipeLoop();
                              } else {
                                await requestCameraAccess();
                              }
                            }}
                            className="w-full rounded-[16px] bg-amber-300 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-amber-200"
                          >
                            Retry Calibration
                          </button>
                        )}
                        <button
                          onClick={() => onComplete(result)}
                          className="w-full rounded-[16px] bg-emerald-300 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-emerald-200"
                        >
                          Continue to Survey
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
