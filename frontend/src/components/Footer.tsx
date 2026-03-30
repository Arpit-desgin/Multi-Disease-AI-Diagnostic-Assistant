import { Activity, Heart } from "lucide-react";
import { Link } from "react-router-dom";

const Footer = () => (
  <footer className="border-t border-border bg-card">
    <div className="container mx-auto px-6 py-16">
      <div className="grid gap-12 md:grid-cols-4">
        <div className="md:col-span-1">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary">
              <Activity className="h-5 w-5 text-primary-foreground" />
            </div>
            <span className="font-display text-lg font-bold tracking-tight text-foreground">
              Medi<span className="gradient-text">AI</span>
            </span>
          </Link>
          <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
            AI-powered early detection and diagnostic assistant. Screen, diagnose, understand, and act — all in one platform.
          </p>
        </div>

        <div>
          <h4 className="mb-4 font-display text-sm font-semibold tracking-tight text-foreground">Platform</h4>
          <ul className="space-y-3 text-sm text-muted-foreground">
            <li><Link to="/upload" className="transition-colors hover:text-primary">Upload Scan</Link></li>
            <li><Link to="/report" className="transition-colors hover:text-primary">Report Explanation</Link></li>
            <li><Link to="/hospitals" className="transition-colors hover:text-primary">Find Hospitals</Link></li>
          </ul>
        </div>

        <div>
          <h4 className="mb-4 font-display text-sm font-semibold tracking-tight text-foreground">Company</h4>
          <ul className="space-y-3 text-sm text-muted-foreground">
            <li><a href="#" className="transition-colors hover:text-primary">About Us</a></li>
            <li><a href="#" className="transition-colors hover:text-primary">Research</a></li>
            <li><a href="#" className="transition-colors hover:text-primary">Careers</a></li>
            <li><a href="#" className="transition-colors hover:text-primary">Contact</a></li>
          </ul>
        </div>

        <div>
          <h4 className="mb-4 font-display text-sm font-semibold tracking-tight text-foreground">Legal</h4>
          <ul className="space-y-3 text-sm text-muted-foreground">
            <li><a href="#" className="transition-colors hover:text-primary">Privacy Policy</a></li>
            <li><a href="#" className="transition-colors hover:text-primary">Terms of Service</a></li>
            <li><a href="#" className="transition-colors hover:text-primary">HIPAA Compliance</a></li>
            <li><a href="#" className="transition-colors hover:text-primary">Disclaimer</a></li>
          </ul>
        </div>
      </div>

      <div className="mt-12 flex flex-col items-center justify-between gap-4 border-t border-border pt-8 md:flex-row">
        <p className="text-xs text-muted-foreground">
          © 2026 MediAI. This tool is for educational purposes and does not replace professional medical advice.
        </p>
        <p className="flex items-center gap-1 text-xs text-muted-foreground">
          Made with <Heart className="h-3 w-3 text-destructive" /> for better healthcare
        </p>
      </div>
    </div>
  </footer>
);

export default Footer;
