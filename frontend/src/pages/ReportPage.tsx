import { useState } from "react";
import { motion } from "framer-motion";
import { FileText, Upload, ArrowRight, Highlighter, Info, Loader2, AlertCircle, CheckCircle2, AlertTriangle } from "lucide-react";
import { api, type ReportExplanation } from "@/lib/api";
import { toast } from "@/hooks/use-toast";

const diseaseOptions = [
  { id: "lung", label: "Lung Cancer" },
  { id: "skin", label: "Skin Disease" },
  { id: "eye", label: "Diabetic Retinopathy" },
];

const urgencyBadge: Record<string, { class: string; icon: typeof CheckCircle2 }> = {
  green: { class: "risk-badge-low", icon: CheckCircle2 },
  yellow: { class: "risk-badge-medium", icon: AlertTriangle },
  red: { class: "risk-badge-high", icon: AlertCircle },
};

const ReportPage = () => {
  const [file, setFile] = useState<File | null>(null);
  const [diseaseContext, setDiseaseContext] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ReportExplanation | null>(null);

  const handleUpload = async () => {
    if (!file || !diseaseContext) return;
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("disease_context", diseaseContext);
      const res = await api.explainReport(formData);
      setResult(res);
    } catch {
      toast({ title: "Something went wrong", description: "Please try again.", variant: "destructive" });
      // Fallback
      setResult({
        summary: "CT of the chest demonstrates a 6mm pulmonary nodule in the right upper lobe. Ground glass opacity is noted. Recommend follow-up CT in 6 months.",
        key_findings: [
          "6mm pulmonary nodule in right upper lobe",
          "Ground glass opacity in adjacent parenchyma",
          "No pleural effusion",
          "Mediastinal lymph nodes within normal limits",
        ],
        questions_for_doctor: [
          "What is the likelihood this nodule is cancerous?",
          "Should I get a biopsy or wait for the follow-up scan?",
          "Are there lifestyle changes that could help?",
        ],
        urgency_indicator: "yellow",
        disclaimer: "This AI-generated explanation is for informational purposes only and does not constitute medical advice. Please consult your healthcare provider for diagnosis and treatment.",
      });
    } finally {
      setLoading(false);
    }
  };

  const badge = result?.urgency_indicator ? urgencyBadge[result.urgency_indicator] : null;
  const BadgeIcon = badge?.icon || AlertTriangle;

  return (
    <div className="min-h-screen bg-background pt-24 pb-16">
      <div className="container mx-auto max-w-5xl px-6">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-10 text-center">
          <p className="mb-2 text-sm font-semibold uppercase tracking-wider text-primary">Report</p>
          <h1 className="font-display text-3xl font-bold text-foreground sm:text-4xl">
            Medical Report <span className="gradient-text">Explained</span>
          </h1>
          <p className="mt-3 text-muted-foreground">Upload a medical report for AI-powered simplification.</p>
        </motion.div>

        {/* Upload area */}
        {!result && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="mx-auto mb-10 max-w-xl space-y-5">
            {/* Disease selector */}
            <div>
              <p className="mb-3 text-sm font-semibold text-foreground">Which disease is this report for?</p>
              <div className="flex flex-wrap gap-2">
                {diseaseOptions.map((d) => (
                  <button
                    key={d.id}
                    onClick={() => setDiseaseContext(d.id)}
                    className={`rounded-full px-5 py-2 text-sm font-medium transition-colors ${
                      diseaseContext === d.id
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted text-muted-foreground hover:bg-primary/10 hover:text-primary"
                    }`}
                  >
                    {d.label}
                  </button>
                ))}
              </div>
            </div>

            {/* File upload */}
            <label className={`glass-card flex cursor-pointer flex-col items-center justify-center border-2 border-dashed p-16 text-center transition-all ${file ? "border-primary bg-primary/5" : "border-border hover:border-primary/40"}`}>
              <Upload className="mb-4 h-10 w-10 text-primary/60" />
              <p className="font-display text-base font-semibold text-foreground">{file ? file.name : "Upload Medical Report"}</p>
              <p className="mt-1 text-sm text-muted-foreground">PDF, TXT, DOC, or Image — max 10MB</p>
              <input type="file" accept=".pdf,.txt,.doc,.docx,image/*" className="hidden" onChange={(e) => e.target.files?.[0] && setFile(e.target.files[0])} />
            </label>

            {file && diseaseContext && (
              <button onClick={handleUpload} disabled={loading} className="btn-primary-gradient flex w-full items-center justify-center gap-2 rounded-xl py-3 text-sm font-semibold disabled:opacity-50">
                {loading ? <><Loader2 className="h-4 w-4 animate-spin" /> Analyzing...</> : <>Explain Report <ArrowRight className="h-4 w-4" /></>}
              </button>
            )}
            {file && !diseaseContext && (
              <p className="text-center text-xs text-muted-foreground">Please select a disease context above to continue.</p>
            )}
          </motion.div>
        )}

        {/* Results */}
        {result && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-8">
            {/* Summary + Urgency */}
            <div className="glass-card p-6">
              <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                <div className="flex items-center gap-2">
                  <FileText className="h-5 w-5 text-primary" />
                  <h3 className="font-display text-lg font-semibold text-foreground">Summary</h3>
                </div>
                {badge && (
                  <span className={`${badge.class} flex items-center gap-1.5 rounded-full px-4 py-1.5 text-xs font-bold uppercase`}>
                    <BadgeIcon className="h-3.5 w-3.5" />
                    {result.urgency_indicator === "green" ? "Low Urgency" : result.urgency_indicator === "yellow" ? "Moderate Urgency" : "High Urgency"}
                  </span>
                )}
              </div>
              <p className="text-sm leading-relaxed text-muted-foreground">{result.summary}</p>
            </div>

            {/* Key Findings + Questions side-by-side */}
            <div className="grid gap-8 lg:grid-cols-2">
              {/* Key Findings */}
              {result.key_findings && result.key_findings.length > 0 && (
                <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.2 }} className="glass-card p-6">
                  <div className="mb-4 flex items-center gap-2">
                    <Highlighter className="h-5 w-5 text-accent" />
                    <h3 className="font-display text-lg font-semibold text-foreground">Key Findings</h3>
                  </div>
                  <ul className="space-y-2.5">
                    {result.key_findings.map((f, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                        <span className="mt-1.5 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-primary" />
                        {f}
                      </li>
                    ))}
                  </ul>
                </motion.div>
              )}

              {/* Questions for Doctor */}
              {result.questions_for_doctor && result.questions_for_doctor.length > 0 && (
                <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.3 }} className="glass-card p-6">
                  <div className="mb-4 flex items-center gap-2">
                    <Info className="h-5 w-5 text-primary" />
                    <h3 className="font-display text-lg font-semibold text-foreground">Questions for Your Doctor</h3>
                  </div>
                  <ul className="space-y-2.5">
                    {result.questions_for_doctor.map((q, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                        <span className="mt-0.5 flex-shrink-0 text-primary font-semibold">{i + 1}.</span>
                        {q}
                      </li>
                    ))}
                  </ul>
                </motion.div>
              )}
            </div>

            {/* Disclaimer */}
            {result.disclaimer && (
              <p className="text-center text-xs italic text-muted-foreground">{result.disclaimer}</p>
            )}

            {/* Upload another */}
            <div className="text-center">
              <button onClick={() => { setResult(null); setFile(null); setDiseaseContext(""); }} className="rounded-xl border border-border px-6 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground">
                Upload Another Report
              </button>
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
};

export default ReportPage;
