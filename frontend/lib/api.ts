const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

async function request(path: string, options: RequestInit = {}) {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...options, headers });
  } catch {
    throw new Error("Network request failed. Please try again.");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || err.error?.message || "Request failed");
  }
  if (res.status === 204) return null;
  return res.json();
}

async function requestText(path: string, options: RequestInit = {}) {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...options, headers });
  } catch {
    throw new Error("Network request failed. Please try again.");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || err.error?.message || "Request failed");
  }
  return res.text();
}

export const api = {
  // Auth
  register: (data: { email: string; password: string; name: string }) =>
    request("/auth/register", { method: "POST", body: JSON.stringify(data) }),
  login: (data: { email: string; password: string }) =>
    request("/auth/login", { method: "POST", body: JSON.stringify(data) }),
  me: () => request("/auth/me"),
  updateMe: (data: { name: string }) =>
    request("/auth/me", { method: "PATCH", body: JSON.stringify(data) }),

  // Surveys
  listSurveys: () => request("/surveys"),
  createSurvey: (data: any) =>
    request("/surveys", { method: "POST", body: JSON.stringify(data) }),
  getSurvey: (id: number) => request(`/surveys/${id}`),
  updateSurvey: (id: number, data: any) =>
    request(`/surveys/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteSurvey: (id: number) => request(`/surveys/${id}`, { method: "DELETE" }),
  publishSurvey: (id: number) =>
    request(`/surveys/${id}/publish`, { method: "POST" }),
  getSurveyAnalytics: (id: number) => request(`/surveys/${id}/analytics-summary`),
  getSurveyParticipantComments: (id: number) => request(`/surveys/${id}/participant-comments`),
  exportTranslationsJson: (id: number, language = "zh") =>
    request(`/surveys/${id}/translations/export?format=json&language=${encodeURIComponent(language)}`),
  exportTranslationsCsv: (id: number, language = "zh") =>
    requestText(`/surveys/${id}/translations/export?format=csv&language=${encodeURIComponent(language)}`),
  importTranslationsJson: (id: number, payload: any) =>
    request(`/surveys/${id}/translations/import?format=json`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  importTranslationsCsv: (id: number, csvText: string, language?: string) =>
    request(`/surveys/${id}/translations/import?format=csv${language ? `&language=${encodeURIComponent(language)}` : ""}`, {
      method: "POST",
      headers: { "Content-Type": "text/csv" },
      body: csvText,
    }),

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
  startSurvey: (
    shareCode: string,
    data?: {
      language?: string;
      screen_width?: number;
      screen_height?: number;
      user_agent?: string;
    },
  ) => request(`/surveys/${shareCode}/start`, { method: "POST", body: JSON.stringify(data || {}) }),
  getPublicSurvey: (shareCode: string, language?: string) =>
    request(`/surveys/public/${shareCode}${language ? `?language=${encodeURIComponent(language)}` : ""}`),
  getResponseState: (responseId: number) => request(`/surveys/responses/${responseId}/state`),
  toggleLike: (responseId: number, postId: number) =>
    request(`/surveys/responses/${responseId}/likes/toggle`, { method: "POST", body: JSON.stringify({ post_id: postId }) }),
  createParticipantComment: (
    responseId: number,
    data: { post_id: number; text: string; author_name?: string }
  ) => request(`/surveys/responses/${responseId}/comments`, { method: "POST", body: JSON.stringify(data) }),
  updateParticipantComment: (
    responseId: number,
    commentId: number,
    text: string
  ) => request(`/surveys/responses/${responseId}/comments/${commentId}`, { method: "PATCH", body: JSON.stringify({ text }) }),
  deleteParticipantComment: (responseId: number, commentId: number) =>
    request(`/surveys/responses/${responseId}/comments/${commentId}`, { method: "DELETE" }),
  recordInteraction: (responseId: number, data: { post_id: number; action_type: string; comment_text?: string }) =>
    request(`/surveys/responses/${responseId}/interact`, { method: "POST", body: JSON.stringify(data) }),
  completeSurvey: (responseId: number) =>
    request(`/surveys/responses/${responseId}/complete`, { method: "POST" }),

  // Tracking
  createCalibrationSession: (data: {
    response_id: number;
    participant_token: string;
    screen_width: number;
    screen_height: number;
    camera_width?: number;
    camera_height?: number;
  }) => request("/tracking/calibration/sessions", { method: "POST", body: JSON.stringify(data) }),
  recordCalibrationPoint: (
    sessionId: number,
    data: {
      point_index: number;
      participant_token: string;
      target_screen_x: number;
      target_screen_y: number;
      samples: any[];
    }
  ) => request(`/tracking/calibration/sessions/${sessionId}/points`, { method: "POST", body: JSON.stringify(data) }),
  completeCalibration: (sessionId: number, data: { participant_token: string }) =>
    request(`/tracking/calibration/sessions/${sessionId}/complete`, { method: "POST", body: JSON.stringify(data) }),
  recordGaze: (data: { response_id: number; participant_token: string; data: any[] }) =>
    request("/tracking/gaze", { method: "POST", body: JSON.stringify(data) }),
  recordClicks: (data: { response_id: number; participant_token: string; data: any[] }) =>
    request("/tracking/clicks", { method: "POST", body: JSON.stringify(data) }),

  // Question responses
  submitQuestionResponse: (
    responseId: number,
    questionId: number,
    data: { question_id: number; answer_text?: string; answer_value?: number; answer_choices?: any[] }
  ) => request(`/surveys/responses/${responseId}/questions/${questionId}/answer`, { method: "POST", body: JSON.stringify(data) }),
};
