"use client";

type FaceMeshResultsHandler = (results: any) => void;

const CAMERA_UTILS_URL = "https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js";
const FACE_MESH_BASE_URL = "https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh";
const FACE_MESH_SCRIPT_URL = `${FACE_MESH_BASE_URL}/face_mesh.js`;

const scriptPromises = new Map<string, Promise<void>>();
let sharedFaceMeshPromise: Promise<any> | null = null;
let sharedFaceMesh: any = null;
let activeOwner: symbol | null = null;

function loadScript(src: string): Promise<void> {
  const existing = scriptPromises.get(src);
  if (existing) return existing;

  const promise = new Promise<void>((resolve, reject) => {
    if (document.querySelector(`script[src="${src}"]`)) {
      resolve();
      return;
    }

    const script = document.createElement("script");
    script.src = src;
    script.crossOrigin = "anonymous";
    script.onload = () => resolve();
    script.onerror = () => reject(new Error(`Failed to load ${src}`));
    document.head.appendChild(script);
  });

  scriptPromises.set(src, promise);
  return promise;
}

async function ensureMediaPipeScripts() {
  await loadScript(CAMERA_UTILS_URL);
  await loadScript(FACE_MESH_SCRIPT_URL);
}

async function createSharedFaceMesh() {
  await ensureMediaPipeScripts();
  const browserWindow = window as any;
  const faceMesh = new browserWindow.FaceMesh({
    locateFile: (file: string) => `${FACE_MESH_BASE_URL}/${file}`,
  });

  faceMesh.setOptions({
    maxNumFaces: 1,
    refineLandmarks: true,
    minDetectionConfidence: 0.5,
    minTrackingConfidence: 0.5,
  });
  await faceMesh.initialize();
  sharedFaceMesh = faceMesh;
  return faceMesh;
}

export async function acquireSharedFaceMesh(onResults: FaceMeshResultsHandler) {
  if (!sharedFaceMeshPromise) {
    sharedFaceMeshPromise = createSharedFaceMesh().catch((error) => {
      sharedFaceMeshPromise = null;
      sharedFaceMesh = null;
      throw error;
    });
  }

  const faceMesh = await sharedFaceMeshPromise;
  const owner = Symbol("face-mesh-owner");
  activeOwner = owner;
  faceMesh.onResults((results: any) => {
    if (activeOwner === owner) {
      onResults(results);
    }
  });

  return { faceMesh, owner };
}

export function releaseSharedFaceMesh(owner: symbol | null) {
  if (!owner || activeOwner !== owner) return;
  activeOwner = null;
  sharedFaceMesh?.onResults(() => undefined);
}
