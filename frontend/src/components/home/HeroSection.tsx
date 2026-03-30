import { useState } from "react";
import { motion, useScroll, useTransform, AnimatePresence } from "framer-motion";
import { ArrowRight, FileText, Stethoscope, Eye, Brain, X } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { useRef } from "react";
import heroBg from "@/assets/hero-bg.jpg";

const FloatingIcon = ({ icon: Icon, className }: { icon: any; className: string }) => (
  <div className={`absolute hidden lg:flex items-center justify-center rounded-2xl glass-card p-4 ${className}`}>
    <Icon className="h-7 w-7 text-primary" />
  </div>
);

const diseaseOptions = [
  { id: "lung", label: "🫁 Lung Cancer" },
  { id: "skin", label: "🩺 Skin Disease" },
  { id: "eye", label: "👁️ Diabetic Retinopathy" },
];

const HeroSection = () => {
  const ref = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end start"] });
  const bgY = useTransform(scrollYProgress, [0, 1], ["0%", "30%"]);
  const navigate = useNavigate();
  const [showReportModal, setShowReportModal] = useState(false);

  return (
    <section ref={ref} className="relative min-h-screen overflow-hidden">
      {/* Parallax Background */}
      <motion.div className="absolute inset-0" style={{ y: bgY }}>
        <img src={heroBg} alt="" className="h-[130%] w-full object-cover" />
        <div className="absolute inset-0 bg-gradient-to-b from-background/20 via-background/60 to-background" />
      </motion.div>

      {/* Grid overlay */}
      <div className="absolute inset-0 medical-grid animate-grid-flow opacity-30" />

      {/* Content */}
      <div className="container relative mx-auto flex min-h-screen flex-col items-center justify-center px-6 pt-20 text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="mb-8 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-5 py-2.5 text-sm font-medium text-primary backdrop-blur-sm"
        >
          <span className="glow-dot" />
          Trusted by 50,000+ healthcare professionals
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.1 }}
          className="max-w-4xl font-display text-4xl font-bold leading-[1.1] tracking-tight text-foreground sm:text-5xl md:text-6xl lg:text-7xl"
        >
          AI-Powered Early Detection &{" "}
          <span className="gradient-text">Diagnostic Assistant</span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.25 }}
          className="mt-8 max-w-2xl text-lg leading-relaxed text-muted-foreground sm:text-xl"
        >
          Screen → Diagnose → Understand → Act. Our AI analyzes medical images and risk factors to provide early detection insights with explainable results.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.4 }}
          className="mt-12 flex flex-col gap-4 sm:flex-row"
        >
          <Link
            to="/diseases"
            className="btn-primary-gradient flex items-center justify-center gap-3 rounded-2xl px-8 py-4 text-base font-semibold shadow-lg shadow-primary/30 transition-all hover:shadow-xl hover:shadow-primary/40 active:scale-95"
          >
            Get Started
            <ArrowRight className="h-4 w-4" />
          </Link>
          <button
            onClick={() => setShowReportModal(true)}
            className="flex items-center justify-center gap-2.5 rounded-2xl border border-border/80 bg-card/80 px-10 py-4.5 text-base font-semibold text-foreground shadow-sm backdrop-blur-sm transition-all hover:bg-card hover:shadow-md"
          >
            <FileText className="h-4 w-4" />
            Upload Medical Report
          </button>
        </motion.div>

        {/* Floating icons */}
        <FloatingIcon icon={Stethoscope} className="left-[10%] top-[35%] animate-float" />
        <FloatingIcon icon={Eye} className="right-[8%] top-[30%] animate-float-delay" />
        <FloatingIcon icon={Brain} className="left-[15%] bottom-[25%] animate-float-delay" />
      </div>

      {/* Report Disease Selection Modal */}
      <AnimatePresence>
        {showReportModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-background/60 backdrop-blur-sm"
            onClick={() => setShowReportModal(false)}
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              onClick={(e) => e.stopPropagation()}
              className="glass-card mx-4 w-full max-w-md p-8"
            >
              <div className="flex items-center justify-between mb-6">
                <h3 className="font-display text-lg font-semibold text-foreground">Which disease is this report for?</h3>
                <button onClick={() => setShowReportModal(false)} className="rounded-lg p-1 text-muted-foreground hover:text-foreground" title="Close">
                  <X className="h-5 w-5" />
                </button>
              </div>
              <div className="space-y-3">
                {diseaseOptions.map((d) => (
                  <button
                    key={d.id}
                    onClick={() => {
                      setShowReportModal(false);
                      navigate(`/report?disease=${d.id}`);
                    }}
                    className="flex w-full items-center gap-3 rounded-xl border border-border p-4 text-sm font-medium text-foreground transition-all hover:border-primary/40 hover:bg-primary/5"
                  >
                    {d.label}
                    <ArrowRight className="ml-auto h-4 w-4 text-muted-foreground" />
                  </button>
                ))}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
};

export default HeroSection;
