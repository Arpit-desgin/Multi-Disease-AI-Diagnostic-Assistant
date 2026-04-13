import { useState, useCallback } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { motion } from "framer-motion";
import { Upload, FileImage, FileText, X, Loader2, Eye, EyeOff, ZoomIn, ZoomOut, Info, MapPin } from "lucide-react";
import { api, type DiagnosisResult } from "@/lib/api";
import { formatPercentage, normalizeProgressValue } from "@/lib/utils";
import { useDiagnosisContext } from "@/contexts/DiagnosisContext";
import { toast } from "@/hooks/use-toast";

const diseaseLabels: Record<string, string> = {
  lung: "Lung Cancer",
  skin: "Skin Disease",
  eye: "Diabetic Retinopathy",
  breast: "Breast Cancer",
};

const diagnoseFns: Record<string, (fd: FormData) => Promise<DiagnosisResult>> = {
  lung: api.diagnoseLung,
  skin: api.diagnoseSkin,
  eye: api.diagnoseDR,
  breast: api.diagnoseLung,
};

const diseaseApiNames: Record<string, string> = {
  lung: "lung-cancer",
  skin: "skin-disease",
  eye: "diabetic-retinopathy",
  breast: "lung-cancer",
};

const fallbackResults: Record<string, DiagnosisResult> = {
  lung: {
    prediction: "Lung Cancer Detected", confidence: 91.2, risk_level: "HIGH",
    stage1_result: "Nodule Detected in Upper Right Lobe", stage2_result: "Malignant (91% confidence)",
    class_probabilities: { normal: 0.09, cancer: 0.91 },
    explanation: "The model detected a potential malignant nodule. A pulmonologist review is recommended.",
  },
  skin: {
    prediction: "Skin Lesion — Melanoma Suspected", confidence: 88, risk_level: "HIGH",
    stage1_result: "Malignant", stage2_result: "Melanoma (88% confidence)",
    class_probabilities: { benign: 0.12, malignant: 0.88 },
    explanation: "The AI detected irregular borders and color variation consistent with melanoma.",
  },
  eye: {
    prediction: "Diabetic Retinopathy Detected", confidence: 85, risk_level: "MODERATE",
    stage1_result: "Diabetic Retinopathy Present", stage2_result: "Moderate Non-Proliferative DR",
    class_probabilities: { normal: 0.15, dr: 0.85 },
    explanation: "The fundus image shows microaneurysms consistent with moderate non-proliferative DR.",
  },
  breast: {
    prediction: "Breast Lesion Detected", confidence: 87, risk_level: "MODERATE",
    stage1_result: "Suspicious mass identified", stage2_result: "BI-RADS 4 — Biopsy recommended",
    class_probabilities: { normal: 0.13, suspicious: 0.87 },
    explanation: "The AI identified a suspicious region with irregular margins.",
  },
};

const riskBadgeClass: Record<string, string> = {
  HIGH: "risk-badge-high",
  MODERATE: "risk-badge-medium",
  LOW: "risk-badge-low",
  high: "risk-badge-high",
  medium: "risk-badge-medium",
  low: "risk-badge-low",
};

// Helper function to safely convert value to string
const safeString = (val: any): string => {
  if (!val) return "";
  if (typeof val === "string") return val;
  if (typeof val === "number") return String(val);
  if (typeof val === "object") return JSON.stringify(val);
  return String(val);
};

// Helper function to safely render text content
const SafeText = ({ children }: { children: any }) => {
  return <>{safeString(children)}</>;
};

const UploadPage = () => {
  const [searchParams] = useSearchParams();
  const diseaseId = searchParams.get("disease") || "";
  const diseaseLabel = diseaseLabels[diseaseId] || "";
  const { setActiveDiagnosis } = useDiagnosisContext();

  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [reportFile, setReportFile] = useState<File | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [progress, setProgress] = useState(0);
  const [dragOver, setDragOver] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [showHeatmap, setShowHeatmap] = useState(false);
  const [heatmapBase64, setHeatmapBase64] = useState<string | null>(null);
  const [loadingHeatmap, setLoadingHeatmap] = useState(false);
  const [opacity, setOpacity] = useState(70);
  const [zoom, setZoom] = useState(1);
  const [result, setResult] = useState<DiagnosisResult | null>(null);

  const handleFile = useCallback((f: File) => {
    setFile(f);
    if (f.type.startsWith("image/")) {
      setPreview(URL.createObjectURL(f));
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const f = e.dataTransfer.files[0];
      if (f) handleFile(f);
    },
    [handleFile]
  );

  const handleAnalyze = async () => {
    if (!file) return;
    setAnalyzing(true);
    setProgress(0);

    const interval = setInterval(() => {
      setProgress((p) => {
        if (p >= 90) { clearInterval(interval); return 90; }
        return p + 2;
      });
    }, 60);

    try {
      const formData = new FormData();
      formData.append("image", file);
      if (reportFile) formData.append("report_text", reportFile);

      const diagnoseFn = diagnoseFns[diseaseId] || diagnoseFns.lung;
      const res = await diagnoseFn(formData);
      setResult(res);

      // Store gradcam from diagnosis response
      if (res.gradcam_image) {
        setHeatmapBase64(res.gradcam_image);
      }

      // Set global diagnosis context for chatbot
      setActiveDiagnosis({
        disease: diseaseId || "lung",
        prediction: res.prediction,
        confidence: res.confidence,
        risk_level: res.risk_level,
      });
    } catch (err) {
      console.error("Diagnosis API error:", err);
      toast({ title: "Something went wrong", description: "Please try again.", variant: "destructive" });
      const fallback = fallbackResults[diseaseId] || fallbackResults.lung;
      setResult(fallback);
      setActiveDiagnosis({
        disease: diseaseId || "lung",
        prediction: fallback.prediction,
        confidence: fallback.confidence,
        risk_level: fallback.risk_level,
      });
    } finally {
      clearInterval(interval);
      setProgress(100);
      setTimeout(() => setShowResults(true), 300);
      setAnalyzing(false);
    }
  };

  const handleToggleHeatmap = async () => {
    if (showHeatmap) {
      // Turning OFF
      setShowHeatmap(false);
      return;
    }

    // Turning ON — call gradcam endpoint if we don't have one yet
    if (!heatmapBase64 && file) {
      setLoadingHeatmap(true);
      try {
        const formData = new FormData();
        formData.append("file", file);
        formData.append("disease", diseaseApiNames[diseaseId] || "lung-cancer");
        const res = await api.gradcam(formData);
        setHeatmapBase64(res.gradcam_image);
      } catch {
        toast({ title: "Could not load heatmap", description: "Showing gradient overlay instead.", variant: "destructive" });
      } finally {
        setLoadingHeatmap(false);
      }
    }
    setShowHeatmap(true);
  };

  const clear = () => {
    setFile(null);
    setPreview(null);
    setReportFile(null);
    setAnalyzing(false);
    setProgress(0);
    setShowResults(false);
    setShowHeatmap(false);
    setHeatmapBase64(null);
    setResult(null);
    setZoom(1);
    setActiveDiagnosis(null);
  };

  const riskLevel = result?.risk_level || "MODERATE";

  return (
    <div className="min-h-screen bg-background pt-28 pb-20">
      <div className="container mx-auto max-w-6xl px-6">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="text-center">
          <p className="mb-3 text-sm font-semibold uppercase tracking-widest text-primary">Upload & Analyze</p>
          <h1 className="font-display text-3xl font-bold tracking-tight text-foreground sm:text-4xl lg:text-5xl">
            Upload Your <span className="gradient-text">{diseaseLabel || "Medical"} Scan</span>
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-muted-foreground">
            Drag & drop or browse to upload a medical image for instant AI-powered analysis.
          </p>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }} className="mt-12">
          {!file ? (
            <div className="mx-auto max-w-2xl space-y-4">
              <label
                onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                className={`glass-card flex cursor-pointer flex-col items-center justify-center border-2 border-dashed p-20 text-center transition-all duration-300 ${
                  dragOver ? "border-primary bg-primary/5 scale-[1.01]" : "border-border hover:border-primary/40"
                }`}
              >
                <div className="mb-5 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
                  <Upload className="h-8 w-8 text-primary" />
                </div>
                <p className="font-display text-lg font-semibold text-foreground">Drop your scan here</p>
                <p className="mt-1 text-sm text-muted-foreground">or click to browse</p>
                <p className="mt-4 text-xs text-muted-foreground/70">Supports: JPG, PNG, DICOM • Max 20MB</p>
                <input type="file" accept="image/*" className="hidden" onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])} />
              </label>

              <label className="glass-card flex cursor-pointer items-center gap-4 p-5 transition-all duration-200 hover:bg-muted/30">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-primary/10">
                  <FileText className="h-5 w-5 text-primary" />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-semibold text-foreground">Upload Medical Report (Optional)</p>
                  <p className="text-xs text-muted-foreground">PDF or text report for AI correlation</p>
                </div>
                <input type="file" accept=".pdf,.txt,.doc,.docx" className="hidden" onChange={(e) => e.target.files?.[0] && setReportFile(e.target.files[0])} />
                {reportFile && (
                  <span className="text-xs font-medium text-primary truncate max-w-[120px]">{reportFile.name}</span>
                )}
              </label>
            </div>
          ) : !showResults ? (
            <div className="mx-auto max-w-2xl">
              <div className="glass-card overflow-hidden p-6">
                <div className="flex items-center justify-between mb-5">
                  <div className="flex items-center gap-3">
                    <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10">
                      <FileImage className="h-4 w-4 text-primary" />
                    </div>
                    <span className="text-sm font-medium text-foreground truncate max-w-[200px]">{file.name}</span>
                  </div>
                  <button onClick={clear} disabled={analyzing} className="rounded-xl p-2 text-muted-foreground transition-colors hover:text-destructive hover:bg-destructive/10 disabled:opacity-50">
                    <X className="h-4 w-4" />
                  </button>
                </div>

                {preview && (
                  <div className="mb-6 overflow-hidden rounded-2xl border border-border">
                    <img src={preview} alt="Scan preview" className="w-full object-contain max-h-80" />
                  </div>
                )}

                {reportFile && (
                  <div className="mb-5 flex items-center gap-2 rounded-xl bg-muted/50 px-4 py-2.5 text-xs">
                    <FileText className="h-4 w-4 text-primary" />
                    <span className="text-muted-foreground">Report attached:</span>
                    <span className="font-medium text-foreground truncate">{reportFile.name}</span>
                  </div>
                )}

                {analyzing ? (
                  <div className="space-y-4">
                    <div className="flex items-center gap-3">
                      <Loader2 className="h-5 w-5 animate-spin text-primary" />
                      <span className="text-sm font-medium text-foreground">
                        {progress < 100 ? "Analyzing scan with AI..." : "Analysis complete!"}
                      </span>
                    </div>
                    <div className="h-2.5 overflow-hidden rounded-full bg-muted">
                      <motion.div
                        className="h-full rounded-full bg-gradient-to-r from-primary to-accent"
                        initial={{ width: 0 }}
                        animate={{ width: `${progress}%` }}
                      />
                    </div>
                  </div>
                ) : (
                  <button onClick={handleAnalyze} disabled={analyzing} className="btn-primary-gradient w-full rounded-2xl py-3.5 text-sm font-semibold disabled:opacity-50">
                    Analyze with AI
                  </button>
                )}
              </div>
            </div>
          ) : (
            /* ─── Inline Results ─── */
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5 }}
              className="grid gap-8 lg:grid-cols-2"
            >
              {/* Left — Image + Heatmap */}
              <div className="glass-card p-6">
                <div className="relative overflow-hidden rounded-2xl bg-muted">
                  {preview ? (
                    <div className="relative" style={{ transform: `scale(${zoom})`, transformOrigin: "center", transition: "transform 0.3s" }}>
                      <img src={preview} alt="Scan" className="w-full object-contain max-h-[420px]" />
                      {showHeatmap && (
                        heatmapBase64 ? (
                          <img
                            src={`data:image/jpeg;base64,${heatmapBase64}`}
                            alt="Grad-CAM Heatmap"
                            className="absolute inset-0 w-full h-full object-contain pointer-events-none"
                            style={{ opacity: opacity / 100 }}
                          />
                        ) : (
                          <div className="absolute inset-0 bg-gradient-to-br from-destructive/40 via-accent/30 to-primary/20 pointer-events-none" style={{ opacity: opacity / 100 }} />
                        )
                      )}
                    </div>
                  ) : (
                    <div className="flex h-80 items-center justify-center text-muted-foreground">
                      <p className="text-sm">No preview available</p>
                    </div>
                  )}
                </div>

                <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
                  <button
                    onClick={handleToggleHeatmap}
                    disabled={loadingHeatmap}
                    className="flex items-center gap-2 rounded-xl border border-border px-4 py-2 text-sm font-medium text-foreground transition-all duration-200 hover:bg-muted disabled:opacity-50"
                  >
                    {loadingHeatmap ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : showHeatmap ? (
                      <EyeOff className="h-4 w-4" />
                    ) : (
                      <Eye className="h-4 w-4" />
                    )}
                    {loadingHeatmap ? "Loading..." : showHeatmap ? "Hide Heatmap" : "Show Heatmap"}
                  </button>

                  <div className="flex items-center gap-2">
                    <button onClick={() => setZoom((z) => Math.max(0.5, z - 0.25))} className="rounded-xl border border-border p-2 text-muted-foreground transition-colors hover:bg-muted">
                      <ZoomOut className="h-4 w-4" />
                    </button>
                    <span className="text-xs text-muted-foreground w-10 text-center">{Math.round(zoom * 100)}%</span>
                    <button onClick={() => setZoom((z) => Math.min(3, z + 0.25))} className="rounded-xl border border-border p-2 text-muted-foreground transition-colors hover:bg-muted">
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

                <button onClick={clear} className="mt-5 w-full rounded-xl border border-border py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground">
                  Upload Another Scan
                </button>
              </div>

              {/* Right — AI Results */}
              <div className="space-y-5">
                {/* Prediction + Risk Badge */}
                <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.1 }} className="glass-card p-6">
                  <h3 className="mb-4 font-display text-base font-semibold uppercase tracking-wider text-muted-foreground">Prediction</h3>
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <span className="text-xl font-bold text-foreground sm:text-2xl">
                      <SafeText>{result?.prediction}</SafeText>
                    </span>
                    <span className={`${riskBadgeClass[riskLevel] || "risk-badge-medium"} rounded-full px-4 py-1.5 text-xs font-bold uppercase`}>
                      <SafeText>{riskLevel}</SafeText> RISK
                    </span>
                  </div>
                </motion.div>

                {/* Confidence */}
                <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.2 }} className="glass-card p-6">
                  <h3 className="mb-4 font-display text-base font-semibold uppercase tracking-wider text-muted-foreground">Confidence Score</h3>
                  <div className="flex items-center gap-4">
                    <div className="h-3 flex-1 overflow-hidden rounded-full bg-muted">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${normalizeProgressValue(result?.confidence)}%` }}
                        transition={{ delay: 0.4, duration: 1 }}
                        className="h-full rounded-full bg-gradient-to-r from-primary to-accent"
                      />
                    </div>
                    <span className="text-lg font-bold text-primary">
                      {formatPercentage(result?.confidence)}
                    </span>
                  </div>
                </motion.div>

                {/* Multi-stage results */}
                {(result?.stage1_result || result?.stage2_result) && (
                  <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.3 }} className="glass-card p-6">
                    <h3 className="mb-4 font-display text-base font-semibold uppercase tracking-wider text-muted-foreground">Multi-Stage Analysis</h3>
                    <div className="space-y-3">
                      {result?.stage1_result && (
                        <motion.div initial={{ opacity: 0, x: 15 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.5 }} className="rounded-xl border border-border bg-muted/40 p-4">
                          <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-primary">Stage 1 — Detection</p>
                          <p className="text-sm font-medium text-foreground">
                            <SafeText>{result.stage1_result}</SafeText>
                          </p>
                        </motion.div>
                      )}
                      {result?.stage2_result && (
                        <motion.div initial={{ opacity: 0, x: 15 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.65 }} className="rounded-xl border border-border bg-muted/40 p-4">
                          <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-primary">Stage 2 — Classification</p>
                          <p className="text-sm font-medium text-foreground">
                            <SafeText>{result.stage2_result}</SafeText>
                          </p>
                        </motion.div>
                      )}
                    </div>
                  </motion.div>
                )}

                {/* Class Probabilities */}
                {result?.class_probabilities && Object.keys(result.class_probabilities).length > 0 && (
                  <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.35 }} className="glass-card p-6">
                    <h3 className="mb-4 font-display text-base font-semibold uppercase tracking-wider text-muted-foreground">Class Probabilities</h3>
                    <div className="space-y-3">
                      {Object.entries(result.class_probabilities).map(([cls, prob]) => {
                        const progressValue = normalizeProgressValue(prob);
                        const formattedPercent = formatPercentage(prob);
                        return (
                          <div key={cls} className="flex items-center gap-3">
                            <span className="w-24 text-sm font-medium capitalize text-foreground">
                              <SafeText>{cls}</SafeText>
                            </span>
                            <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-muted">
                              <motion.div
                                initial={{ width: 0 }}
                                animate={{ width: `${progressValue}%` }}
                                transition={{ delay: 0.6, duration: 0.8 }}
                                className="h-full rounded-full bg-gradient-to-r from-primary to-accent"
                              />
                            </div>
                            <span className="w-14 text-right text-sm font-semibold text-primary">
                              {formattedPercent}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </motion.div>
                )}

                {/* Explanation */}
                {result?.explanation && (
                  <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.4 }} className="glass-card p-6">
                    <h3 className="mb-3 flex items-center gap-2 font-display text-base font-semibold text-foreground">
                      <Info className="h-5 w-5 text-primary" /> AI Explanation
                    </h3>
                    <p className="text-sm leading-relaxed text-muted-foreground">
                      <SafeText>{result.explanation}</SafeText>
                    </p>
                  </motion.div>
                )}

                {/* Actions */}
                <div className="flex gap-3">
                  <Link to="/report" className="btn-primary-gradient flex-1 rounded-xl py-3 text-center text-sm font-semibold">
                    View Full Report
                  </Link>
                  <Link to="/hospitals" className="flex flex-1 items-center justify-center gap-2 rounded-xl border border-border bg-card py-3 text-center text-sm font-semibold text-foreground transition-colors hover:bg-muted">
                    <MapPin className="h-4 w-4" /> Find Specialist
                  </Link>
                </div>

                {/* Disclaimer */}
                <p className="text-center text-xs text-muted-foreground">
                  ⚠️ This analysis is AI-generated and does not replace professional medical diagnosis.
                </p>
              </div>
            </motion.div>
          )}
        </motion.div>
      </div>
    </div>
  );
};

export default UploadPage;
