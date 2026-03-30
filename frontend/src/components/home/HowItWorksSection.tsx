import { motion } from "framer-motion";
import { ClipboardList, Stethoscope, Upload, BarChart3, CheckCircle } from "lucide-react";

const steps = [
  { icon: ClipboardList, title: "Answer Risk Questions", desc: "Complete a quick health assessment form" },
  { icon: Stethoscope, title: "Get Recommended Scan", desc: "AI suggests the right diagnostic scan" },
  { icon: Upload, title: "Upload Medical Image", desc: "Drag & drop your scan securely" },
  { icon: BarChart3, title: "AI Analysis + Heatmap", desc: "Get instant results with visual explanation" },
  { icon: CheckCircle, title: "Get Clear Next Steps", desc: "Actionable recommendations & referrals" },
];

const HowItWorksSection = () => (
  <section className="py-28">
    <div className="container mx-auto px-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        className="mb-20 text-center"
      >
        <p className="mb-3 text-sm font-semibold uppercase tracking-widest text-primary">Process</p>
        <h2 className="font-display text-3xl font-bold tracking-tight text-foreground sm:text-4xl lg:text-5xl">
          How It <span className="gradient-text">Works</span>
        </h2>
      </motion.div>

      <div className="relative mx-auto max-w-4xl">
        <div className="absolute left-8 top-0 hidden h-full w-px bg-gradient-to-b from-primary/10 via-primary/40 to-primary/10 md:left-1/2 md:block" />

        <div className="space-y-16">
          {steps.map((step, i) => (
            <motion.div
              key={step.title}
              initial={{ opacity: 0, x: i % 2 === 0 ? -30 : 30 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1 }}
              className={`flex items-center gap-8 ${i % 2 !== 0 ? "md:flex-row-reverse" : ""}`}
            >
              <div className={`flex-1 ${i % 2 !== 0 ? "md:text-right" : ""}`}>
                <div className={`glass-card inline-block p-7 ${i % 2 !== 0 ? "md:ml-auto" : ""}`}>
                  <h3 className="mb-2 font-display text-lg font-semibold tracking-tight text-foreground">{step.title}</h3>
                  <p className="text-sm text-muted-foreground">{step.desc}</p>
                </div>
              </div>

              <div className="relative z-10 hidden flex-shrink-0 md:block">
                <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary text-primary-foreground shadow-lg shadow-primary/20">
                  <step.icon className="h-7 w-7" />
                </div>
                <span className="absolute -top-2 -right-2 flex h-6 w-6 items-center justify-center rounded-full bg-accent text-xs font-bold text-accent-foreground">
                  {i + 1}
                </span>
              </div>

              <div className="hidden flex-1 md:block" />
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  </section>
);

export default HowItWorksSection;
