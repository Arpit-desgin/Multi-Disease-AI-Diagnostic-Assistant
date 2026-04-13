const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";
const API_CHATBOT_BASE = import.meta.env.VITE_API_URL?.replace("/v1", "") || "http://localhost:8000/api";

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.text().catch(() => "Unknown error");
    throw new Error(`API Error (${response.status}): ${error}`);
  }
  return response.json();
}

export const api = {
  // Risk Assessment
  riskLung: (data: Record<string, unknown>) =>
    fetch(`${API_BASE}/risk/lung-cancer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }).then((r) => handleResponse<RiskResult>(r)),

  riskSkin: (data: Record<string, unknown>) =>
    fetch(`${API_BASE}/risk/skin-disease`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }).then((r) => handleResponse<RiskResult>(r)),

  riskDR: (data: Record<string, unknown>) =>
    fetch(`${API_BASE}/risk/diabetic-retinopathy`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }).then((r) => handleResponse<RiskResult>(r)),

  // Diagnosis — FormData only, no Content-Type header
  diagnoseLung: (formData: FormData) =>
    fetch(`${API_BASE}/diagnosis/lung-cancer`, {
      method: "POST",
      body: formData,
    }).then((r) => handleResponse<DiagnosisResult>(r)),

  diagnoseSkin: (formData: FormData) =>
    fetch(`${API_BASE}/diagnosis/skin-disease`, {
      method: "POST",
      body: formData,
    }).then((r) => handleResponse<DiagnosisResult>(r)),

  diagnoseDR: (formData: FormData) =>
    fetch(`${API_BASE}/diagnosis/diabetic-retinopathy`, {
      method: "POST",
      body: formData,
    }).then((r) => handleResponse<DiagnosisResult>(r)),

  // Grad-CAM — FormData only, no Content-Type header
  gradcam: (formData: FormData) =>
    fetch(`${API_BASE}/diagnosis/gradcam`, {
      method: "POST",
      body: formData,
    }).then((r) => handleResponse<GradcamResult>(r)),

  // Report
  explainReport: (formData: FormData) =>
    fetch(`${API_BASE}/report/explain`, {
      method: "POST",
      body: formData,
    }).then((r) => handleResponse<ReportExplanation>(r)),

  // Hospitals
  hospitalsNearby: (lat: number, lon: number, disease: string) =>
    fetch(`${API_BASE}/hospitals/nearby?lat=${lat}&lon=${lon}&disease=${disease}`).then((r) =>
      handleResponse<Hospital[]>(r)
    ),

  hospitalsSearch: (city: string, disease: string) =>
    fetch(`${API_BASE}/hospitals/search?city=${city}&disease=${disease}`).then((r) =>
      handleResponse<Hospital[]>(r)
    ),

  // Chatbot — Uses /api/chatbot prefix (not /api/v1)
  chat: (data: { message: string; session_id: string; diagnosis_context?: ActiveDiagnosis | null }) =>
    fetch(`${API_CHATBOT_BASE}/chatbot/message`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }).then((r) => handleResponse<ChatResponse>(r)),

  clearChat: (sessionId: string) =>
    fetch(`${API_CHATBOT_BASE}/chatbot/session/${sessionId}`, { method: "DELETE" }).then((r) =>
      handleResponse<{ success: boolean }>(r)
    ),
};

// ─── Types ────────────────────────────────────────────────────────────────────

export type RiskResult = {
  risk_level: "low" | "medium" | "high";
  risk_label: string;
  reason: string;
  score?: number;
};

/** Raw stage result returned by skin/DR endpoints – can be a string or {label, confidence} */
export type StageResult = string | { label: string; confidence?: number } | null;

export type DiagnosisResult = {
  mock?: boolean;
  prediction?: string;
  confidence?: number;
  risk_level?: string;
  stage1_result?: StageResult;
  stage2_result?: StageResult;
  class_probabilities?: Record<string, number>;
  explanation?: string;
  gradcam_image?: string;
  gradcam_regions?: Array<{ x: number; y: number; width: number; height: number; score: number }>;
};

export type GradcamResult = {
  gradcam_image: string;
};

export type ReportExplanation = {
  explanation: string;
};

export type Hospital = {
  id: string;
  name: string;
  distance: number;
  city: string;
  state: string;
  rating: number;
};

export type ChatResponse = {
  message: string;
  session_id: string;
};

/** What we persist in global context for the chatbot */
export type ActiveDiagnosis = {
  prediction: string;
  confidence: number;
};

/** Legacy alias kept for DiagnosisContext */
export type DiagnosisContext = ActiveDiagnosis;