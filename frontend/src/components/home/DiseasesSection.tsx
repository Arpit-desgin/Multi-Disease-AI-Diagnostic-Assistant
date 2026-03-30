import { motion } from "framer-motion";
import { Scan, BadgeCheck, Clock } from "lucide-react";

const diseases = [
  {
    name: "Lung Cancer Detection",
    scan: "CT Scan / X-Ray",
    description: "Two-stage AI model for nodule detection and malignancy classification with 94% accuracy.",
    color: "from-primary/5 to-accent/5",
  },
  {
    name: "Skin Disease Analysis",
    scan: "Dermatoscopic Image",
    description: "Classifies 7+ skin conditions including melanoma with visual explainability maps.",
    color: "from-primary/5 to-accent/5",
  },
  {
    name: "Diabetic Retinopathy",
    scan: "Fundus Image",
    description: "Detects retinal damage stages from no DR to proliferative DR with severity grading.",
    color: "from-accent/5 to-primary/5",
  },
  {
    name: "Breast Cancer Screening",
    scan: "Mammogram / Histopathology",
    description: "Identifies malignant vs benign lesions using advanced convolutional neural networks.",
    color: "from-accent/5 to-primary/5",
  },
];

const DiseasesSection = () => (
  <section className="bg-muted/40 py-28">
    <div className="container mx-auto px-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        className="mb-20 text-center"
      >
        <p className="mb-3 text-sm font-semibold uppercase tracking-widest text-primary">Supported Conditions</p>
        <h2 className="font-display text-3xl font-bold tracking-tight text-foreground sm:text-4xl lg:text-5xl">
          Multi-Disease <span className="gradient-text">AI Detection</span>
        </h2>
      </motion.div>

      <div className="grid gap-8 sm:grid-cols-2">
        {diseases.map((d, i) => (
          <motion.div
            key={d.name}
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.1 }}
            className="glass-card group relative overflow-hidden p-8"
          >
            <div className={`absolute inset-0 bg-gradient-to-br ${d.color} opacity-0 transition-opacity duration-500 group-hover:opacity-100`} />
            <div className="relative">
              <h3 className="mb-3 font-display text-xl font-bold tracking-tight text-foreground">{d.name}</h3>
              <p className="mb-5 text-sm leading-relaxed text-muted-foreground">{d.description}</p>
              <div className="flex flex-wrap gap-2">
                <span className="flex items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1.5 text-xs font-medium text-primary">
                  <Scan className="h-3 w-3" /> {d.scan}
                </span>
                <span className="flex items-center gap-1.5 rounded-full bg-accent/10 px-3 py-1.5 text-xs font-medium text-accent-foreground">
                  <BadgeCheck className="h-3 w-3" /> Two-Stage AI
                </span>
                <span className="flex items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1.5 text-xs font-medium text-primary">
                  <Clock className="h-3 w-3" /> Early Detection
                </span>
              </div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  </section>
);

export default DiseasesSection;
