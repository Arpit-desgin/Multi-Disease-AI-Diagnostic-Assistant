import { motion } from "framer-motion";
import { Lock, Eye, UserCheck, ShieldCheck } from "lucide-react";

const items = [
  { icon: Lock, title: "Data Privacy", desc: "Your medical data is encrypted end-to-end and never shared with third parties." },
  { icon: Eye, title: "Explainable AI", desc: "See exactly how the AI reaches its conclusions with visual heatmaps and confidence scores." },
  { icon: UserCheck, title: "Not a Replacement for Doctors", desc: "MediAI is a screening assistant. Always consult a qualified healthcare professional." },
  { icon: ShieldCheck, title: "Secure & Confidential", desc: "HIPAA-aligned practices with enterprise-grade security and audit logging." },
];

const TrustSection = () => (
  <section className="bg-muted/40 py-28">
    <div className="container mx-auto px-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        className="mb-20 text-center"
      >
        <p className="mb-3 text-sm font-semibold uppercase tracking-widest text-primary">Trust & Ethics</p>
        <h2 className="font-display text-3xl font-bold tracking-tight text-foreground sm:text-4xl lg:text-5xl">
          Built on <span className="gradient-text">Trust & Transparency</span>
        </h2>
      </motion.div>

      <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
        {items.map((item, i) => (
          <motion.div
            key={item.title}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: i * 0.1 }}
            className="glass-card p-8 text-center"
          >
            <div className="mx-auto mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
              <item.icon className="h-7 w-7" />
            </div>
            <h3 className="mb-3 font-display text-base font-semibold tracking-tight text-foreground">{item.title}</h3>
            <p className="text-sm leading-relaxed text-muted-foreground">{item.desc}</p>
          </motion.div>
        ))}
      </div>
    </div>
  </section>
);

export default TrustSection;
