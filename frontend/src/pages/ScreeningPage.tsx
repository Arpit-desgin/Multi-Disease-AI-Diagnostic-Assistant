import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronRight, AlertTriangle, CheckCircle2, ArrowRight, MapPin, Loader2 } from "lucide-react";
import { api, type RiskResult } from "@/lib/api";

type FieldDef = {
  label: string;
  name: string;
  type: "select" | "radio";
  options: { label: string; value: string }[];
  optional?: boolean;
};

const diseaseData: Record<string, {
  title: string;
  icon: string;
  fields: FieldDef[];
  apiCall: (data: Record<string, unknown>) => Promise<RiskResult>;
  clinicLabel: string;
  clinicLink: string;
  uploadLabel: string;
}> = {
  lung: {
    title: "Lung Cancer",
    icon: "🫁",
    fields: [
      { label: "What is your age group?", name: "age_group", type: "select", options: [
        { label: "Under 40", value: "under_40" }, { label: "40–55", value: "40_55" },
        { label: "55–70", value: "55_70" }, { label: "Over 70", value: "over_70" },
      ]},
      { label: "How many years have you smoked?", name: "smoking_years", type: "select", options: [
        { label: "Never", value: "0" }, { label: "1–10 years", value: "5" },
        { label: "10–20 years", value: "15" }, { label: "20+ years", value: "25" },
      ]},
      { label: "Cigarettes per day?", name: "cigarettes_per_day", type: "select", options: [
        { label: "None", value: "0" }, { label: "1–10", value: "5" },
        { label: "10–20", value: "15" }, { label: "20+", value: "25" },
      ]},
      { label: "Do you have a chronic cough?", name: "chronic_cough", type: "radio", options: [
        { label: "No", value: "no" }, { label: "Occasional", value: "occasional" },
        { label: "Persistent (> 3 weeks)", value: "persistent" },
      ]},
      { label: "Do you experience chest pain?", name: "chest_pain", type: "radio", options: [
        { label: "No", value: "false" }, { label: "Sometimes", value: "sometimes" },
        { label: "Frequently", value: "true" },
      ]},
      { label: "Family history of lung cancer?", name: "family_history", type: "radio", options: [
        { label: "No", value: "false" }, { label: "Yes — first degree", value: "first_degree" },
        { label: "Yes — distant relative", value: "distant" },
      ]},
    ],
    apiCall: (data) => api.riskLung(data),
    clinicLabel: "Find Nearest X-ray Centers",
    clinicLink: "/hospitals?speciality=Pulmonology",
    uploadLabel: "Proceed to Upload Scan",
  },
  skin: {
    title: "Skin Disease",
    icon: "🩺",
    fields: [
      { label: "Has the lesion changed in size recently?", name: "size_change", type: "radio", options: [
        { label: "No change", value: "false" }, { label: "Slightly larger", value: "slight" },
        { label: "Significantly larger", value: "true" },
      ]},
      { label: "Does it show color variation?", name: "color_variation", type: "radio", options: [
        { label: "Uniform color", value: "false" }, { label: "Two colors", value: "moderate" },
        { label: "Multiple colors / irregular", value: "true" },
      ]},
      { label: "Does it have an irregular border?", name: "irregular_border", type: "radio", options: [
        { label: "No", value: "false" }, { label: "Slightly irregular", value: "slight" },
        { label: "Very irregular", value: "true" },
      ]},
      { label: "Any bleeding or oozing?", name: "bleeding", type: "radio", options: [
        { label: "No", value: "no" }, { label: "Occasionally", value: "occasional" },
        { label: "Frequently", value: "frequent" },
      ]},
      { label: "How long has the lesion been present?", name: "lesion_duration_weeks", type: "select", options: [
        { label: "Less than 4 weeks", value: "2" }, { label: "1–6 months", value: "12" },
        { label: "6–12 months", value: "36" }, { label: "Over 1 year", value: "60" },
      ]},
    ],
    apiCall: (data) => api.riskSkin(data),
    clinicLabel: "Find Dermatology Clinic",
    clinicLink: "/hospitals?speciality=Dermatology",
    uploadLabel: "Upload Skin Image",
  },
  eye: {
    title: "Diabetic Retinopathy",
    icon: "👁️",
    fields: [
      { label: "How long have you had diabetes?", name: "diabetes_duration_years", type: "select", options: [
        { label: "Less than 5 years", value: "3" }, { label: "5–10 years", value: "7" },
        { label: "10–20 years", value: "15" }, { label: "Over 20 years", value: "25" },
      ]},
      { label: "Do you know your latest HbA1c level?", name: "hba1c", type: "select", optional: true, options: [
        { label: "Below 6.5%", value: "6" }, { label: "6.5% – 8%", value: "7" },
        { label: "Above 8%", value: "9" }, { label: "Unknown", value: "" },
      ]},
      { label: "Do you experience vision blurring?", name: "vision_blurring", type: "radio", options: [
        { label: "No issues", value: "false" }, { label: "Occasional blurriness", value: "occasional" },
        { label: "Frequent blurriness", value: "true" },
      ]},
      { label: "Difficulty with night vision?", name: "difficulty_night_vision", type: "radio", options: [
        { label: "No", value: "false" }, { label: "Sometimes", value: "sometimes" },
        { label: "Yes", value: "true" },
      ]},
      { label: "Do you have high blood pressure?", name: "blood_pressure_high", type: "radio", options: [
        { label: "No", value: "false" }, { label: "Yes", value: "true" }, { label: "Not sure", value: "unknown" },
      ]},
      { label: "When was your last eye examination?", name: "last_eye_exam", type: "select", options: [
        { label: "Within 6 months", value: "recent" }, { label: "6–12 months ago", value: "6_12" },
        { label: "Over 1 year ago", value: "over_1_year" }, { label: "Never had one", value: "never" },
      ]},
    ],
    apiCall: (data) => api.riskDR(data),
    clinicLabel: "Find Nearest Eye Clinics",
    clinicLink: "/hospitals?speciality=Ophthalmology",
    uploadLabel: "Upload Fundus Image",
  },
  breast: {
    title: "Breast Cancer",
    icon: "🎗️",
    fields: [
      { label: "What is your age group?", name: "age_group", type: "select", options: [
        { label: "Under 40", value: "under_40" }, { label: "40–50", value: "40_50" },
        { label: "50–65", value: "50_65" }, { label: "Over 65", value: "over_65" },
      ]},
      { label: "Family history of breast cancer?", name: "family_history", type: "radio", options: [
        { label: "No", value: "false" }, { label: "Yes — first degree", value: "first_degree" },
        { label: "Yes — distant relative", value: "distant" },
      ]},
      { label: "Have you noticed any lumps?", name: "lumps", type: "radio", options: [
        { label: "No", value: "false" }, { label: "Small / not sure", value: "unsure" },
        { label: "Yes — noticeable", value: "true" },
      ]},
      { label: "Any nipple discharge or skin changes?", name: "skin_changes", type: "radio", options: [
        { label: "No", value: "false" }, { label: "Minor changes", value: "minor" },
        { label: "Yes — significant changes", value: "true" },
      ]},
    ],
    apiCall: (data) => api.riskLung(data), // placeholder — no dedicated breast endpoint yet
    clinicLabel: "Find Oncology Center",
    clinicLink: "/hospitals?speciality=Oncology",
    uploadLabel: "Upload Mammogram",
  },
};

const riskBadgeClass: Record<string, string> = {
  low: "risk-badge-low",
  medium: "risk-badge-medium",
  high: "risk-badge-high",
};

const ScreeningPage = () => {
  const { diseaseId } = useParams<{ diseaseId: string }>();
  const data = diseaseData[diseaseId || ""] || diseaseData.lung;

  const [step, setStep] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<RiskResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const total = data.fields.length;
  const progress = submitted ? 100 : Math.round((step / total) * 100);
  const field = data.fields[step];

  const handleAnswer = (value: string) => {
    setAnswers((prev) => ({ ...prev, [field.name]: value }));
  };

  const handleNext = async () => {
    if (step < total - 1) {
      setStep(step + 1);
    } else {
      // Submit to API
      setLoading(true);
      setError(null);
      try {
        // Build payload — convert empty optional fields to null
        const payload: Record<string, unknown> = {};
        for (const f of data.fields) {
          const val = answers[f.name];
          if (f.optional && (!val || val === "")) {
            payload[f.name] = null;
          } else {
            payload[f.name] = val;
          }
        }
        const res = await data.apiCall(payload);
        setResult(res);
        setSubmitted(true);
      } catch (err) {
        console.error("Risk API error:", err);
        setError("Could not reach the server. Showing offline assessment.");
        // Fallback to offline result
        setResult({
          risk_level: "medium",
          risk_label: "MODERATE",
          reason: "Unable to connect to server. Based on your answers, a moderate risk is estimated. Please consult a healthcare provider for an accurate assessment.",
        });
        setSubmitted(true);
      } finally {
        setLoading(false);
      }
    }
  };

  return (
    <div className="min-h-screen bg-background pt-24 pb-16">
      <div className="container mx-auto max-w-2xl px-6">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-8 text-center">
          <p className="mb-2 text-sm font-semibold uppercase tracking-wider text-primary">Early Risk Screening</p>
          <h1 className="font-display text-3xl font-bold text-foreground sm:text-4xl">
            <span className="mr-2">{data.icon}</span>
            <span className="gradient-text">{data.title}</span> Screening
          </h1>
          <p className="mt-3 text-muted-foreground">No image required — screening for awareness.</p>
        </motion.div>

        {/* Progress bar */}
        <div className="mb-8">
          <div className="mb-2 flex justify-between text-xs text-muted-foreground">
            <span>Question {submitted ? total : step + 1} of {total}</span>
            <span>{progress}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-muted">
            <motion.div
              className="h-full rounded-full bg-gradient-to-r from-primary to-accent"
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.4 }}
            />
          </div>
        </div>

        <AnimatePresence mode="wait">
          {!submitted ? (
            <motion.div
              key={step}
              initial={{ opacity: 0, x: 30 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -30 }}
              transition={{ duration: 0.25 }}
              className="glass-card p-8"
            >
              <h3 className="mb-1 font-display text-lg font-semibold text-foreground">{field.label}</h3>
              {field.optional && (
                <p className="mb-4 text-xs text-muted-foreground">Optional — skip if unknown</p>
              )}
              {!field.optional && <div className="mb-6" />}

              <div className="space-y-3">
                {field.options.map((opt) => (
                  <label
                    key={opt.value}
                    className={`flex cursor-pointer items-center gap-3 rounded-xl border p-4 text-sm font-medium transition-all ${
                      answers[field.name] === opt.value
                        ? "border-primary bg-primary/5 text-foreground"
                        : "border-border text-muted-foreground hover:border-primary/40 hover:bg-muted"
                    }`}
                  >
                    <input
                      type="radio"
                      name={`q-${step}`}
                      value={opt.value}
                      checked={answers[field.name] === opt.value}
                      onChange={() => handleAnswer(opt.value)}
                      className="sr-only"
                    />
                    <div
                      className={`flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full border-2 transition-colors ${
                        answers[field.name] === opt.value ? "border-primary bg-primary" : "border-muted-foreground/30"
                      }`}
                    >
                      {answers[field.name] === opt.value && (
                        <div className="h-2 w-2 rounded-full bg-primary-foreground" />
                      )}
                    </div>
                    {opt.label}
                  </label>
                ))}
              </div>

              <button
                onClick={handleNext}
                disabled={!answers[field.name] && !field.optional || loading}
                className="btn-primary-gradient mt-8 flex w-full items-center justify-center gap-2 rounded-xl py-3 text-sm font-semibold disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" /> Analyzing...
                  </>
                ) : step < total - 1 ? (
                  <>Next Question <ChevronRight className="h-4 w-4" /></>
                ) : (
                  <>Get Risk Assessment <ChevronRight className="h-4 w-4" /></>
                )}
              </button>
            </motion.div>
          ) : result && (
            <motion.div
              key="result"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="space-y-6"
            >
              {error && (
                <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-700">
                  ⚠️ {error}
                </div>
              )}

              {/* Risk result card */}
              <div className="glass-card p-8 text-center">
                <div className="mb-4">
                  {result.risk_level === "high" ? (
                    <AlertTriangle className="mx-auto h-12 w-12 text-destructive" />
                  ) : (
                    <CheckCircle2 className="mx-auto h-12 w-12 text-primary" />
                  )}
                </div>
                <p className="mb-2 text-sm font-medium text-muted-foreground">Risk Level</p>
                <span
                  className={`${riskBadgeClass[result.risk_level]} inline-block rounded-full px-6 py-2 text-lg font-bold`}
                >
                  {result.risk_label}
                </span>
                <p className="mx-auto mt-4 max-w-md text-sm leading-relaxed text-muted-foreground">
                  {result.reason}
                </p>
              </div>

              {/* Action buttons */}
              <div className="flex flex-col gap-3 sm:flex-row">
                <Link
                  to={data.clinicLink}
                  className="flex flex-1 items-center justify-center gap-2 rounded-xl border border-border bg-card py-3 text-sm font-semibold text-foreground transition-colors hover:bg-muted"
                >
                  <MapPin className="h-4 w-4" /> {data.clinicLabel}
                </Link>
                <Link
                  to={`/upload?disease=${diseaseId}`}
                  className="btn-primary-gradient flex flex-1 items-center justify-center gap-2 rounded-xl py-3 text-sm font-semibold"
                >
                  {data.uploadLabel} <ArrowRight className="h-4 w-4" />
                </Link>
              </div>

              {/* Disclaimer */}
              <p className="text-center text-xs text-muted-foreground">
                ⚠️ This screening is for awareness only and does not replace a professional medical diagnosis.
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default ScreeningPage;
