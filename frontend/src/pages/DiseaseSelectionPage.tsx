import { motion } from "framer-motion";
import { Link } from "react-router-dom";
import { Scan, BadgeCheck, Clock, ArrowRight } from "lucide-react";

const diseases = [
  {
    id: "lung",
    name: "Lung Cancer",
    icon: "🫁",
    scan: "CT Scan / X-Ray",
    description: "Two-stage AI model for nodule detection and malignancy classification with 94% accuracy.",
    gradient: "from-blue-500/10 to-cyan-500/10",
    borderGlow: "group-hover:shadow-[0_0_30px_hsl(192_85%_55%/0.15)]",
    twoStage: true,
    earlyDetection: true,
  },
  {
    id: "skin",
    name: "Skin Disease",
    icon: "🩺",
    scan: "Dermatoscopic Image",
    description: "Classifies 7+ skin conditions including melanoma with visual explainability maps.",
    gradient: "from-orange-500/10 to-amber-500/10",
    borderGlow: "group-hover:shadow-[0_0_30px_hsl(30_90%_55%/0.15)]",
    twoStage: true,
    earlyDetection: true,
  },
  {
    id: "eye",
    name: "Diabetic Retinopathy",
    icon: "👁️",
    scan: "Fundus Image",
    description: "Detects retinal damage stages from no DR to proliferative DR with severity grading.",
    gradient: "from-emerald-500/10 to-teal-500/10",
    borderGlow: "group-hover:shadow-[0_0_30px_hsl(160_60%_45%/0.15)]",
    twoStage: true,
    earlyDetection: true,
  },
  {
    id: "breast",
    name: "Breast Cancer",
    icon: "🎗️",
    scan: "Mammogram / Histopathology",
    description: "Identifies malignant vs benign lesions using advanced convolutional neural networks.",
    gradient: "from-pink-500/10 to-rose-500/10",
    borderGlow: "group-hover:shadow-[0_0_30px_hsl(340_70%_55%/0.15)]",
    twoStage: false,
    earlyDetection: true,
  },
];

const DiseaseSelectionPage = () => (
  <div className="min-h-screen bg-background pt-24 pb-16">
    <div className="container mx-auto max-w-5xl px-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-12 text-center"
      >
        <p className="mb-2 text-sm font-semibold uppercase tracking-wider text-primary">
          Select Condition
        </p>
        <h1 className="font-display text-3xl font-bold text-foreground sm:text-4xl">
          Choose Your <span className="gradient-text">Diagnostic Path</span>
        </h1>
        <p className="mx-auto mt-3 max-w-xl text-muted-foreground">
          Select a condition to begin early risk screening or upload a medical scan for AI-powered diagnosis.
        </p>
      </motion.div>

      <div className="grid gap-6 sm:grid-cols-2">
        {diseases.map((d, i) => (
          <motion.div
            key={d.id}
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1 }}
            className={`glass-card group relative overflow-hidden p-8 ${d.borderGlow}`}
          >
            <div
              className={`absolute inset-0 bg-gradient-to-br ${d.gradient} opacity-0 transition-opacity duration-300 group-hover:opacity-100`}
            />

            <div className="relative">
              <div className="mb-4 text-4xl">{d.icon}</div>

              <h3 className="mb-2 font-display text-xl font-bold text-foreground">
                {d.name}
              </h3>
              <p className="mb-5 text-sm leading-relaxed text-muted-foreground">
                {d.description}
              </p>

              {/* Badges */}
              <div className="mb-6 flex flex-wrap gap-2">
                <span className="flex items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
                  <Scan className="h-3 w-3" /> {d.scan}
                </span>
                {d.earlyDetection && (
                  <span className="flex items-center gap-1.5 rounded-full bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-700">
                    <Clock className="h-3 w-3" /> Early Detection ✅
                  </span>
                )}
                {d.twoStage && (
                  <span className="flex items-center gap-1.5 rounded-full bg-accent/10 px-3 py-1 text-xs font-medium text-accent-foreground">
                    <BadgeCheck className="h-3 w-3" /> Two-Stage AI ✅
                  </span>
                )}
              </div>

              {/* Actions */}
              <div className="flex flex-col gap-2 sm:flex-row">
                <Link
                  to={`/screening/${d.id}`}
                  className="btn-primary-gradient flex items-center justify-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold"
                >
                  Start Screening <ArrowRight className="h-4 w-4" />
                </Link>
                <Link
                  to={`/upload?disease=${d.id}`}
                  className="flex items-center justify-center gap-2 rounded-xl border border-border bg-card px-5 py-2.5 text-sm font-semibold text-foreground transition-colors hover:bg-muted"
                >
                  Upload Scan
                </Link>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  </div>
);

export default DiseaseSelectionPage;
