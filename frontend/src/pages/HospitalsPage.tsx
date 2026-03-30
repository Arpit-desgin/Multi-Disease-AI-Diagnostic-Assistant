import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { motion } from "framer-motion";
import { MapPin, Phone, Clock, Star, Filter, Search, Loader2, ExternalLink } from "lucide-react";
import { api, type Hospital } from "@/lib/api";
import { toast } from "@/hooks/use-toast";

const specialities = ["All", "Pulmonology", "Oncology", "Dermatology", "Ophthalmology"];

const fallbackHospitals: Hospital[] = [
  { name: "City Medical Center", speciality: "Pulmonology", distance: "2.3 km", rating: 4.8, phone: "+1 (555) 123-4567", hours: "24/7", address: "123 Health Ave, Medical District" },
  { name: "Regional Cancer Institute", speciality: "Oncology", distance: "5.1 km", rating: 4.9, phone: "+1 (555) 234-5678", hours: "8AM – 6PM", address: "456 Research Blvd, Suite 200" },
  { name: "SkinCare Diagnostic Clinic", speciality: "Dermatology", distance: "1.8 km", rating: 4.6, phone: "+1 (555) 345-6789", hours: "9AM – 5PM", address: "789 Wellness St" },
  { name: "Vision Health Hospital", speciality: "Ophthalmology", distance: "3.4 km", rating: 4.7, phone: "+1 (555) 456-7890", hours: "8AM – 8PM", address: "321 Eye Care Pkwy" },
  { name: "Metro General Hospital", speciality: "Pulmonology", distance: "7.2 km", rating: 4.5, phone: "+1 (555) 567-8901", hours: "24/7", address: "654 Metro Center Dr" },
  { name: "Advanced Diagnostics Lab", speciality: "Oncology", distance: "4.0 km", rating: 4.4, phone: "+1 (555) 678-9012", hours: "7AM – 9PM", address: "987 Innovation Way" },
];

const HospitalsPage = () => {
  const [searchParams] = useSearchParams();
  const initialFilter = searchParams.get("speciality") || "All";

  const [filter, setFilter] = useState(initialFilter);
  const [city, setCity] = useState("");
  const [hospitals, setHospitals] = useState<Hospital[]>(fallbackHospitals);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [geoDenied, setGeoDenied] = useState(false);

  const filtered = filter === "All" ? hospitals : hospitals.filter((h) => h.speciality === filter);

  const handleSearch = async () => {
    if (!city.trim()) return;
    setLoading(true);
    setSearched(true);
    try {
      const disease = filter === "All" ? "" : filter.toLowerCase();
      const results = await api.hospitalsSearch(city, disease);
      setHospitals(results);
    } catch {
      toast({ title: "Something went wrong", description: "Please try again.", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  const handleNearby = async () => {
    if (!navigator.geolocation) {
      setGeoDenied(true);
      return;
    }
    setLoading(true);
    setSearched(true);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const disease = filter === "All" ? "" : filter.toLowerCase();
          const results = await api.hospitalsNearby(pos.coords.latitude, pos.coords.longitude, disease);
          setHospitals(results);
        } catch {
          toast({ title: "Something went wrong", description: "Please try again.", variant: "destructive" });
        } finally {
          setLoading(false);
        }
      },
      () => {
        setLoading(false);
        setGeoDenied(true);
      }
    );
  };

  return (
    <div className="min-h-screen bg-background pt-24 pb-16">
      <div className="container mx-auto px-6">
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mb-10 text-center">
          <p className="mb-2 text-sm font-semibold uppercase tracking-wider text-primary">Hospitals</p>
          <h1 className="font-display text-3xl font-bold text-foreground sm:text-4xl">
            Find a <span className="gradient-text">Specialist Near You</span>
          </h1>
        </motion.div>

        {/* Search bar */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="glass-card mb-8 p-5">
          <div className="flex flex-col gap-3 sm:flex-row">
            <div className="flex flex-1 gap-2">
              <input
                value={city}
                onChange={(e) => setCity(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                placeholder={geoDenied ? "Location denied — enter city name..." : "Enter city name..."}
                className="flex-1 rounded-xl border border-border bg-muted px-4 py-2.5 text-sm text-foreground outline-none focus:ring-2 focus:ring-primary/30"
              />
              <button onClick={handleSearch} disabled={loading} className="btn-primary-gradient flex items-center gap-2 rounded-xl px-5 py-2.5 text-sm font-medium disabled:opacity-50">
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
                Search
              </button>
            </div>
            <button onClick={handleNearby} disabled={loading} className="flex items-center justify-center gap-2 rounded-xl border border-border px-4 py-2.5 text-sm font-medium text-foreground transition-colors hover:bg-muted disabled:opacity-50">
              <MapPin className="h-4 w-4" /> Near Me
            </button>
          </div>
        </motion.div>

        {/* Filter */}
        <div className="mb-6 flex flex-wrap items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          {specialities.map((s) => (
            <button
              key={s}
              onClick={() => setFilter(s)}
              className={`rounded-full px-4 py-1.5 text-sm font-medium transition-colors ${
                filter === s
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground hover:bg-primary/10 hover:text-primary"
              }`}
            >
              {s}
            </button>
          ))}
        </div>

        {/* Hospital cards */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((h, i) => (
            <motion.div
              key={h.name + i}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="glass-card p-6"
            >
              <div className="mb-3 flex items-start justify-between">
                <h3 className="font-display text-base font-semibold text-foreground">{h.name}</h3>
                <span className="flex items-center gap-1 text-xs font-medium text-accent-foreground">
                  <Star className="h-3 w-3 fill-accent text-accent" /> {h.rating}
                </span>
              </div>
              <span className="mb-3 inline-block rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
                {h.speciality}
              </span>
              <div className="space-y-2 text-sm text-muted-foreground">
                <p className="flex items-center gap-2"><MapPin className="h-3.5 w-3.5" /> {h.address} • {h.distance}</p>
                <p className="flex items-center gap-2"><Phone className="h-3.5 w-3.5" /> {h.phone}</p>
                <p className="flex items-center gap-2"><Clock className="h-3.5 w-3.5" /> {h.hours}</p>
              </div>
              {h.maps_url && (
                <button
                  onClick={() => window.open(h.maps_url, "_blank")}
                  className="mt-4 flex w-full items-center justify-center gap-2 rounded-xl border border-border py-2 text-sm font-medium text-foreground transition-colors hover:bg-muted"
                >
                  <ExternalLink className="h-3.5 w-3.5" /> Get Directions
                </button>
              )}
            </motion.div>
          ))}
        </div>

        {filtered.length === 0 && searched && (
          <p className="mt-8 text-center text-sm text-muted-foreground">No hospitals found. Try a different search.</p>
        )}
      </div>
    </div>
  );
};

export default HospitalsPage;
