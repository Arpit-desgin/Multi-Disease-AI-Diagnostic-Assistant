const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

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

  // Diagnosis
  diagnoseLung: (formData: FormData) =>
    fetch(`${API_BASE}/diagnosis/lung-cancer`, { method: "POST", body: formData }).then((r) =>
      handleResponse<DiagnosisResult>(r)
    ),

  diagnoseSkin: (formData: FormData) =>
    fetch(`${API_BASE}/diagnosis/skin-disease`, { method: "POST", body: formData }).then((r) =>
      handleResponse<DiagnosisResult>(r)
    ),

  diagnoseDR: (formData: FormData) =>
    fetch(`${API_BASE}/diagnosis/diabetic-retinopathy`, { method: "POST", body: formData }).then((r) =>
      handleResponse<DiagnosisResult>(r)
    ),

  // Grad-CAM (separate endpoint, not full diagnosis)
  gradcam: (formData: FormData) =>
    fetch(`${API_BASE}/diagnosis/gradcam`, { method: "POST", body: formData }).then((r) =>
      handleResponse<GradcamResult>(r)
    ),

  // Report explanation
  explainReport: (formData: FormData) =>
    fetch(`${API_BASE}/report/explain`, { method: "POST", body: formData }).then((r) =>
      handleResponse<ReportExplanation>(r)
    ),

  // Hospitals
  hospitalsNearby: (lat: number, lon: number, disease: string) =>
    fetch(`${API_BASE}/hospitals/nearby?lat=${lat}&lon=${lon}&disease=${disease}`).then((r) =>
      handleResponse<Hospital[]>(r)
    ),

  hospitalsSearch: (city: string, disease: string) =>
    fetch(`${API_BASE}/hospitals/search?city=${city}&disease=${disease}`).then((r) =>
      handleResponse<Hospital[]>(r)
    ),

  // Chatbot
  chat: (data: { message: string; session_id: string; diagnosis_context?: DiagnosisContext | null }) =>
    fetch(`${API_BASE}/chatbot/message`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }).then((r) => handleResponse<ChatResponse>(r)),

  clearChat: (sessionId: string) =>
    fetch(`${API_BASE}/chatbot/session/${sessionId}`, { method: "DELETE" }).then((r) =>
      handleResponse<{ success: boolean }>(r)
    ),
};

// Types

export type RiskResult = {
  risk_level: "low" | "medium" | "high";
  risk_label: string;
  reason: string;
  score?: number;
};

export type DiagnosisResult = {
  prediction: string;
  confidence: number;
  risk_level: string; // "HIGH" | "MODERATE" | "LOW"
  gradcam_image?: string; // base64 string
  stage1_result?: string | null;
  stage2_result?: string | null;
  class_probabilities?: Record<string, number>;
  explanation?: string;
};

export type GradcamResult = {
  gradcam_image: string; // base64 string
};

export type ReportExplanation = {
  summary: string;
  key_findings: string[];
  questions_for_doctor: string[];
  urgency_indicator: "green" | "yellow" | "red";
  disclaimer: string;
  // Legacy fields for fallback
  original?: string;
  simplified?: string;
  keywords?: { term: string; explanation: string }[];
  correlation?: string;
};

export type Hospital = {
  name: string;
  speciality: string;
  distance: string;
  rating: number;
  phone: string;
  hours: string;
  address: string;
  maps_url?: string;
  lat?: number;
  lon?: number;
};

export type DiagnosisContext = {
  disease: string;
  prediction: string;
  confidence: number;
  risk_level: string;
};

export type ChatResponse = {
  reply: string;
  session_id: string;
  suggested_questions?: string[];
  disclaimer?: string;
};
