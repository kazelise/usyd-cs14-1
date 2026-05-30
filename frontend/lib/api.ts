const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
const PARTICIPANT_TOKEN_HEADER = "X-Participant-Token";

function participantAuthHeaders(participantToken: string): Record<string, string> {
  return { [PARTICIPANT_TOKEN_HEADER]: participantToken };
}

type SurveyExportFilters = {
  condition?: number;
  assigned_group?: number;
  language?: string;
  response_status?: string;
  calibration_passed?: boolean;
  include_preview?: boolean;
};

function appendFilterParams(params: URLSearchParams, filters: SurveyExportFilters) {
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      params.set(key, String(value));
    }
  });
}

function surveyExportPath(id: number, format: "json" | "csv", filters: SurveyExportFilters = {}) {
  const params = new URLSearchParams({ format });
  appendFilterParams(params, filters);
  return `/surveys/${id}/export?${params.toString()}`;
}

function analyticsSummaryPath(id: number, filters: SurveyExportFilters = {}) {
  const params = new URLSearchParams();
  appendFilterParams(params, filters);
  const query = params.toString();
  return query
    ? `/surveys/${id}/analytics-summary?${query}`
    : `/surveys/${id}/analytics-summary`;
}

function handleUnauthorized() {
  if (typeof window === "undefined") return;
  localStorage.removeItem("token");
  if (window.location.pathname !== "/auth") {
    window.location.href = "/auth";
  }
}

function errorMessageFromPayload(payload: any, fallback: string) {
  const detail = payload?.detail ?? payload?.error?.message;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => item?.msg || item?.message || JSON.stringify(item))
      .filter(Boolean)
      .join("; ");
  }
  if (detail && typeof detail === "object") return JSON.stringify(detail);
  return fallback;
}

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
    if (res.status === 401) handleUnauthorized();
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorMessageFromPayload(err, "Request failed"));
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
    if (res.status === 401) handleUnauthorized();
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorMessageFromPayload(err, "Request failed"));
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
  listSurveys: (limit = 1000, offset = 0) => request(`/surveys?limit=${limit}&offset=${offset}`),
  createSurvey: (data: any) =>
    request("/surveys", { method: "POST", body: JSON.stringify(data) }),
  getSurvey: (id: number) => request(`/surveys/${id}`),
  updateSurvey: (id: number, data: any) =>
    request(`/surveys/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteSurvey: (id: number) => request(`/surveys/${id}`, { method: "DELETE" }),
  publishSurvey: (id: number) =>
    request(`/surveys/${id}/publish`, { method: "POST" }),
  closeSurvey: (id: number) =>
    request(`/surveys/${id}/close`, { method: "POST" }),
  reopenSurvey: (id: number) =>
    request(`/surveys/${id}/reopen`, { method: "POST" }),
  getSurveyAnalytics: (id: number, filters?: SurveyExportFilters) =>
    request(analyticsSummaryPath(id, filters)),
  getSurveyParticipantComments: (id: number) => request(`/surveys/${id}/participant-comments`),
  exportSurveyDataJson: (id: number, filters?: SurveyExportFilters) =>
    request(surveyExportPath(id, "json", filters)),
  exportSurveyDataCsv: (id: number, filters?: SurveyExportFilters) =>
    requestText(surveyExportPath(id, "csv", filters)),
  previewSurvey: (id: number, assignedGroup = 1, language = "en") =>
    request(`/surveys/${id}/preview?assigned_group=${assignedGroup}&language=${encodeURIComponent(language)}&is_preview=true`),
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
  createQuestion: (surveyId: number, postId: number, data: any) =>
    request(`/surveys/${surveyId}/posts/${postId}/questions`, { method: "POST", body: JSON.stringify(data) }),
  updateQuestion: (surveyId: number, postId: number, questionId: number, data: any) =>
    request(`/surveys/${surveyId}/posts/${postId}/questions/${questionId}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteQuestion: (surveyId: number, postId: number, questionId: number) =>
    request(`/surveys/${surveyId}/posts/${postId}/questions/${questionId}`, { method: "DELETE" }),
  createSurveyQuestion: (surveyId: number, data: any) =>
    request(`/surveys/${surveyId}/questions`, { method: "POST", body: JSON.stringify(data) }),
  updateSurveyQuestion: (surveyId: number, questionId: number, data: any) =>
    request(`/surveys/${surveyId}/questions/${questionId}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteSurveyQuestion: (surveyId: number, questionId: number) =>
    request(`/surveys/${surveyId}/questions/${questionId}`, { method: "DELETE" }),

  // Participant
  startSurvey: (
    shareCode: string,
    data?: {
      language?: string;
      screen_width?: number;
      screen_height?: number;
      user_agent?: string;
      participant_token?: string;
      is_preview?: boolean;
      preview_assigned_group?: number;
    },
  ) => request(`/surveys/${shareCode}/start`, { method: "POST", body: JSON.stringify(data || {}) }),
  getPublicSurvey: (shareCode: string, language?: string) =>
    request(`/surveys/public/${shareCode}${language ? `?language=${encodeURIComponent(language)}` : ""}`),
  getResponseState: (responseId: number, participantToken: string) =>
    request(`/surveys/responses/${responseId}/state`, {
      headers: participantAuthHeaders(participantToken),
    }),
  toggleLike: (responseId: number, postId: number, participantToken: string) =>
    request(`/surveys/responses/${responseId}/likes/toggle`, {
      method: "POST",
      body: JSON.stringify({ post_id: postId, participant_token: participantToken }),
    }),
  createParticipantComment: (
    responseId: number,
    data: { post_id: number; text: string; author_name?: string; participant_token: string }
  ) => request(`/surveys/responses/${responseId}/comments`, { method: "POST", body: JSON.stringify(data) }),
  updateParticipantComment: (
    responseId: number,
    commentId: number,
    text: string,
    participantToken: string
  ) => request(`/surveys/responses/${responseId}/comments/${commentId}`, {
    method: "PATCH",
    body: JSON.stringify({ text, participant_token: participantToken }),
  }),
  deleteParticipantComment: (responseId: number, commentId: number, participantToken: string) =>
    request(`/surveys/responses/${responseId}/comments/${commentId}`, {
      method: "DELETE",
      headers: participantAuthHeaders(participantToken),
    }),
  recordInteraction: (
    responseId: number,
    data: { post_id: number; action_type: string; comment_text?: string; participant_token: string }
  ) => request(`/surveys/responses/${responseId}/interact`, { method: "POST", body: JSON.stringify(data) }),
  completeSurvey: (
    responseId: number,
    participantToken: string,
    attentionSummary?: {
      active_ms: number;
      expected_samples: number;
      detected_samples: number;
      missing_ms: number;
      no_face_periods: number;
    } | null,
  ) =>
    request(`/surveys/responses/${responseId}/complete`, {
      method: "POST",
      body: JSON.stringify({
        participant_token: participantToken,
        attention_summary: attentionSummary ?? null,
      }),
    }),
  submitAttentionSummary: (
    responseId: number,
    participantToken: string,
    summary: {
      active_ms: number;
      expected_samples: number;
      detected_samples: number;
      missing_ms: number;
      no_face_periods: number;
    },
  ) =>
    request(`/surveys/responses/${responseId}/attention-summary`, {
      method: "POST",
      body: JSON.stringify({ participant_token: participantToken, summary }),
    }),

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
    data: { question_id: number; participant_token?: string; answer_text?: string; answer_value?: number; answer_choices?: any[] }
  ) => request(`/surveys/responses/${responseId}/questions/${questionId}/answer`, { method: "POST", body: JSON.stringify(data) }),
};
