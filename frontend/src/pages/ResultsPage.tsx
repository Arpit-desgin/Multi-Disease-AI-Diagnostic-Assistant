import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";
import { Eye, EyeOff, Info, ZoomIn, ZoomOut } from "lucide-react";

type DiseaseResult = {
  prediction: string;
  confidence: number;
  risk: "low" | "medium" | "high";
  stages: { label: string; value: string }[];
  explanation: string;
};

const diseaseResults: Record<string, DiseaseResult> = {
  lung: {
    prediction: "Lung Cancer Detected",
    confidence: 91,
    risk: "high",
    stages: [
      { label: "Stage 1 — Detection", value: "Nodule Detected in Upper Right Lobe" },
      { label: "Stage 2 — Classification", value: "Malignant (91% confidence)" },
    ],
    explanation:
      "The model detected a potential malignant nodule in the upper-right lobe region. The Grad-CAM heatmap highlights areas of concern with warm colors. A pulmonologist review is recommended within 30 days.",
  },
  skin: {
    prediction: "Skin Lesion — Melanoma Suspected",
    confidence: 88,
    risk: "high",
    stages: [
      { label: "Stage 1 — Benign vs Malignant", value: "Malignant" },
      { label: "Stage 2 — Classification", value: "Melanoma (88% confidence)" },
    ],
    explanation:
      "The AI detected irregular borders and color variation consistent with melanoma. Immediate dermatological evaluation is strongly recommended.",
  },
  eye: {
    prediction: "Diabetic Retinopathy Detected",
    confidence: 85,
    risk: "medium",
    stages: [
      { label: "Stage 1 — DR Detection", value: "Diabetic Retinopathy Present" },
      { label: "Stage 2 — Severity", value: "Moderate Non-Proliferative DR" },
    ],
    explanation:
      "The fundus image shows microaneurysms and hard exudates consistent with moderate non-proliferative diabetic retinopathy. Follow-up with an ophthalmologist within 3 months.",
  },
  breast: {
    prediction: "Breast Lesion Detected",
    confidence: 87,
    risk: "medium",
    stages: [
      { label: "Detection", value: "Suspicious mass identified" },
      { label: "Classification", value: "BI-RADS 4 — Biopsy recommended" },
    ],
    explanation:
      "The AI identified a suspicious region with irregular margins. Further evaluation through biopsy is recommended to determine malignancy.",
  },
};

const riskBadgeClass: Record<string, string> = {
  low: "risk-badge-low",
  medium: "risk-badge-medium",
  high: "risk-badge-high",
};

const ResultsPage = () => {
  const [searchParams] = useSearchParams();
  const diseaseId = searchParams.get("disease") || "lung";
  const result = diseaseResults[diseaseId] || diseaseResults.lung;

  const [showHeatmap, setShowHeatmap] = useState(false);
  const [opacity, setOpacity] = useState(70);
  const [zoom, setZoom] = useState(1);

  return (
    <div className="min-h-screen bg-background pt-24 pb-16">
      <div className="container mx-auto px-6">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-10 text-center">
          <p className="mb-2 text-sm font-semibold uppercase tracking-wider text-primary">Analysis</p>
          <h1 className="font-display text-3xl font-bold text-foreground sm:text-4xl">
            AI <span className="gradient-text">Diagnostic Results</span>
          </h1>
        </motion.div>

        <div className="grid gap-8 lg:grid-cols-2">
          {/* Left — Image */}
          <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.2 }} className="glass-card p-6">
            <div className="relative overflow-hidden rounded-xl bg-muted aspect-square flex items-center justify-center">
              <div
                className="text-center p-8 transition-transform duration-300"
                style={{ transform: `scale(${zoom})` }}
              >
                <Eye className="mx-auto mb-3 h-12 w-12 text-muted-foreground/50" />
                <p className="text-sm text-muted-foreground">Medical scan preview</p>
                <p className="mt-1 text-xs text-muted-foreground">Upload a scan to see results here</p>
              </div>
              {showHeatmap && (
                <div
                  className="absolute inset-0 bg-gradient-to-br from-red-500/40 via-yellow-500/30 to-green-500/20 rounded-xl pointer-events-none"
                  style={{ opacity: opacity / 100 }}
                />
              )}
            </div>

            <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
              <button
                onClick={() => setShowHeatmap(!showHeatmap)}
                className="flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted"
              >
                {showHeatmap ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                {showHeatmap ? "Hide" : "Show"} Heatmap
              </button>

              <div className="flex items-center gap-2">
                <button onClick={() => setZoom((z) => Math.max(0.5, z - 0.25))} className="rounded-lg border border-border p-2 text-muted-foreground hover:bg-muted">
                  <ZoomOut className="h-4 w-4" />
                </button>
                <span className="text-xs text-muted-foreground w-10 text-center">{Math.round(zoom * 100)}%</span>
                <button onClick={() => setZoom((z) => Math.min(3, z + 0.25))} className="rounded-lg border border-border p-2 text-muted-foreground hover:bg-muted">
                  <ZoomIn className="h-4 w-4" />
                </button>
              </div>

              {showHeatmap && (
                <div className="flex items-center gap-3">
                  <span className="text-xs text-muted-foreground">Opacity</span>
                  <input
                    type="range"
                    min={10}
                    max={100}
                    value={opacity}
                    onChange={(e) => setOpacity(Number(e.target.value))}
                    className="h-1.5 w-24 appearance-none rounded-full bg-muted accent-primary"
                  />
                </div>
              )}
            </div>
          </motion.div>

          {/* Right — Results */}
          <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.3 }} className="space-y-5">
            {/* Prediction */}
            <div className="glass-card p-6">
              <h3 className="mb-4 font-display text-lg font-semibold text-foreground">Prediction</h3>
              <div className="flex flex-wrap items-center justify-between gap-3">
                <span className="text-xl font-bold text-foreground sm:text-2xl">{result.prediction}</span>
                <span className={`${riskBadgeClass[result.risk]} rounded-full px-4 py-1.5 text-xs font-bold uppercase`}>
                  {result.risk} RISK
                </span>
              </div>
            </div>

            {/* Confidence */}
            <div className="glass-card p-6">
              <h3 className="mb-4 font-display text-lg font-semibold text-foreground">Confidence Score</h3>
              <div className="flex items-center gap-4">
                <div className="h-3 flex-1 overflow-hidden rounded-full bg-muted">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${result.confidence}%` }}
                    transition={{ delay: 0.5, duration: 1 }}
                    className="h-full rounded-full bg-gradient-to-r from-primary to-accent"
                  />
                </div>
                <span className="text-lg font-bold text-primary">{result.confidence}%</span>
              </div>
            </div>

            {/* Multi-stage results */}
            <div className="glass-card p-6">
              <h3 className="mb-4 font-display text-lg font-semibold text-foreground">Multi-Stage Analysis</h3>
              <div className="space-y-4">
                {result.stages.map((s, i) => (
                  <motion.div
                    key={s.label}
                    initial={{ opacity: 0, x: 15 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.6 + i * 0.15 }}
                    className="rounded-xl border border-border bg-muted/50 p-4"
                  >
                    <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-primary">{s.label}</p>
                    <p className="text-sm font-medium text-foreground">{s.value}</p>
                  </motion.div>
                ))}
              </div>
            </div>

            {/* Explanation */}
            <div className="glass-card p-6">
              <h3 className="mb-3 flex items-center gap-2 font-display text-lg font-semibold text-foreground">
                <Info className="h-5 w-5 text-primary" /> AI Explanation
              </h3>
              <p className="text-sm leading-relaxed text-muted-foreground">{result.explanation}</p>
            </div>

            {/* Actions */}
            <div className="flex gap-3">
              <a href="/report" className="btn-primary-gradient flex-1 rounded-xl py-3 text-center text-sm font-semibold">
                View Full Report
              </a>
              <a href="/hospitals" className="flex-1 rounded-xl border border-border bg-card py-3 text-center text-sm font-semibold text-foreground transition-colors hover:bg-muted">
                Find Specialist
              </a>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
};

export default ResultsPage;
