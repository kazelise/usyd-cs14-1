const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

async function request(path: string, options: RequestInit = {}) {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || err.error?.message || "Request failed");
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  // Auth
  register: (data: { email: string; password: string; name: string }) =>
    request("/auth/register", { method: "POST", body: JSON.stringify(data) }),
  login: (data: { email: string; password: string }) =>
    request("/auth/login", { method: "POST", body: JSON.stringify(data) }),
  me: () => request("/auth/me"),

  // Surveys
  listSurveys: () => request("/surveys"),
  createSurvey: (data: any) =>
    request("/surveys", { method: "POST", body: JSON.stringify(data) }),
  getSurvey: (id: number) => request(`/surveys/${id}`),
  updateSurvey: (id: number, data: any) =>
    request(`/surveys/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  publishSurvey: (id: number) =>
    request(`/surveys/${id}/publish`, { method: "POST" }),

  // Posts
  listPosts: (surveyId: number) => request(`/surveys/${surveyId}/posts`),
  createPost: (surveyId: number, data: { original_url: string; order: number }) =>
    request(`/surveys/${surveyId}/posts`, { method: "POST", body: JSON.stringify(data) }),
  updatePost: (surveyId: number, postId: number, data: any) =>
    request(`/surveys/${surveyId}/posts/${postId}`, { method: "PATCH", body: JSON.stringify(data) }),
  deletePost: (surveyId: number, postId: number) =>
    request(`/surveys/${surveyId}/posts/${postId}`, { method: "DELETE" }),
  addComment: (surveyId: number, postId: number, data: { author_name: string; text: string }) =>
    request(`/surveys/${surveyId}/posts/${postId}/comments`, { method: "POST", body: JSON.stringify(data) }),

  // Participant
  startSurvey: (shareCode: string) =>
    request(`/surveys/${shareCode}/start`, { method: "POST" }),
  recordInteraction: (responseId: number, data: { post_id: number; action_type: string; comment_text?: string }) =>
    request(`/surveys/responses/${responseId}/interact`, { method: "POST", body: JSON.stringify(data) }),
  completeSurvey: (responseId: number) =>
    request(`/surveys/responses/${responseId}/complete`, { method: "POST" }),

  // Tracking
  createCalibrationSession: (data: {
    response_id: number;
    screen_width: number;
    screen_height: number;
    camera_width?: number | null;
    camera_height?: number | null;
  }) => request("/tracking/calibration/sessions", { method: "POST", body: JSON.stringify(data) }),
  recordCalibrationPoint: (
    sessionId: number,
    data: {
      point_index: number;
      target_screen_x: number;
      target_screen_y: number;
      samples: Array<{
        timestamp_ms: number;
        left_iris_x: number;
        left_iris_y: number;
        right_iris_x: number;
        right_iris_y: number;
        face_detected: boolean;
        head_rotation?: Record<string, number> | null;
      }>;
    },
  ) =>
    request(`/tracking/calibration/sessions/${sessionId}/points`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  completeCalibration: (sessionId: number) =>
    request(`/tracking/calibration/sessions/${sessionId}/complete`, { method: "POST" }),
  recordGaze: (data: { response_id: number; data: any[] }) =>
    request("/tracking/gaze", { method: "POST", body: JSON.stringify(data) }),
  recordClicks: (data: { response_id: number; data: any[] }) =>
    request("/tracking/clicks", { method: "POST", body: JSON.stringify(data) }),
};
