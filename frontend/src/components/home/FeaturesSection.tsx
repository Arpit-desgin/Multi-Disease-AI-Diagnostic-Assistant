import { motion } from "framer-motion";
import { ShieldCheck, Brain, Layers, MapPin } from "lucide-react";

const features = [
  {
    icon: ShieldCheck,
    title: "Early Risk Screening",
    description: "Answer a quick health questionnaire and our AI identifies potential risk factors before symptoms appear.",
  },
  {
    icon: Brain,
    title: "AI-Based Diagnosis",
    description: "Upload medical scans and receive instant AI analysis powered by state-of-the-art deep learning models.",
  },
  {
    icon: Layers,
    title: "Explainable AI (Heatmaps)",
    description: "See exactly where the AI is looking with Grad-CAM heatmaps — transparency you can trust.",
  },
  {
    icon: MapPin,
    title: "Smart Hospital Recommendations",
    description: "Get matched with nearby hospitals and specialists based on your diagnosis and location.",
  },
];

const FeaturesSection = () => (
  <section className="py-28">
    <div className="container mx-auto px-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        className="mb-20 text-center"
      >
        <p className="mb-3 text-sm font-semibold uppercase tracking-widest text-primary">Features</p>
        <h2 className="font-display text-3xl font-bold tracking-tight text-foreground sm:text-4xl lg:text-5xl">
          Everything You Need for <span className="gradient-text">Smarter Diagnostics</span>
        </h2>
      </motion.div>

      <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
        {features.map((f, i) => (
          <motion.div
            key={f.title}
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.1 }}
            className="glass-card group cursor-default p-8"
          >
            <div className="mb-6 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary transition-all duration-300 group-hover:bg-primary group-hover:text-primary-foreground group-hover:shadow-lg group-hover:shadow-primary/20">
              <f.icon className="h-6 w-6" />
            </div>
            <h3 className="mb-3 font-display text-lg font-semibold tracking-tight text-foreground">{f.title}</h3>
            <p className="text-sm leading-relaxed text-muted-foreground">{f.description}</p>
          </motion.div>
        ))}
      </div>
    </div>
  </section>
);

export default FeaturesSection;
