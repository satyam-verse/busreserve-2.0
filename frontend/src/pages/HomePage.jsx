import { ArrowLeftRight, Calendar, MapPin, Search, ShieldCheck, Sparkles, Ticket } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import TripCard from "../components/TripCard";
import { busApi } from "../services/api";

function getTomorrowIso() {
  const dt = new Date();
  dt.setDate(dt.getDate() + 1);
  return dt.toISOString().split("T")[0];
}

function getTodayIso() {
  return new Date().toISOString().split("T")[0];
}

export default function HomePage() {
  const navigate = useNavigate();
  const [routes, setRoutes] = useState([]);
  const [featuredTrips, setFeaturedTrips] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [source, setSource] = useState("");
  const [destination, setDestination] = useState("");
  const [travelDate, setTravelDate] = useState(getTomorrowIso());

  useEffect(() => {
    let active = true;
    async function loadInitial() {
      try {
        setLoading(true);
        const [routesResp, tripsResp] = await Promise.all([
          busApi.getRoutes(),
          busApi.searchTrips({ featured: true }),
        ]);
        if (!active) return;
        setRoutes(routesResp.routes || []);
        setFeaturedTrips(tripsResp.trips || []);
        if (routesResp.routes?.length) {
          setSource(routesResp.routes[0].source);
          setDestination(routesResp.routes[0].destination);
        }
      } catch (err) {
        if (active) setError(err.message || "Failed to load routes and featured trips.");
      } finally {
        if (active) setLoading(false);
      }
    }
    loadInitial();
    return () => {
      active = false;
    };
  }, []);

  const sources = useMemo(
    () => Array.from(new Set(routes.map((r) => r.source))).sort(),
    [routes]
  );
  const destinations = useMemo(
    () => Array.from(new Set(routes.map((r) => r.destination))).sort(),
    [routes]
  );

  const handleSwap = () => {
    setSource(destination);
    setDestination(source);
  };

  const handleSearch = (e) => {
    e.preventDefault();
    const qs = new URLSearchParams();
    if (source) qs.set("source", source);
    if (destination) qs.set("destination", destination);
    if (travelDate) qs.set("travel_date", travelDate);
    navigate(`/search?${qs.toString()}`);
  };

  return (
    <div className="space-y-12 pb-12">
      <section className="relative overflow-hidden bg-gradient-to-br from-navy-950 via-navy-900 to-navy-800 py-14 text-white sm:py-20">
        <div className="pointer-events-none absolute -right-24 -top-24 h-80 w-80 rounded-full bg-emerald-500/15 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-24 -left-24 h-72 w-72 rounded-full bg-emerald-400/10 blur-3xl" />

        <div className="relative mx-auto max-w-6xl px-4 sm:px-6">
          <div className="max-w-2xl space-y-4">
            <span className="inline-flex items-center gap-2 rounded-full border border-emerald-400/30 bg-emerald-500/10 px-3.5 py-1 text-xs font-semibold tracking-wide text-emerald-300">
              <Sparkles className="h-3.5 w-3.5" />
              PostgreSQL Transactional Seat Guarantee
            </span>
            <h1 className="font-display text-3xl font-extrabold tracking-tight sm:text-5xl">
              Reliable Intercity Bus Travel,{" "}
              <span className="text-emerald-400">Zero Double-Bookings.</span>
            </h1>
            <p className="text-base text-slate-300 sm:text-lg">
              Reserve confirmed coach seats across popular Indian corridors with instant PNR
              generation and real-time seat availability.
            </p>
          </div>

          <form
            onSubmit={handleSearch}
            className="mt-8 rounded-2xl border border-white/15 bg-white p-4 text-navy-900 shadow-2xl sm:p-6"
          >
            <div className="grid grid-cols-1 gap-4 md:grid-cols-12 md:items-end">
              <div className="md:col-span-3">
                <label className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  <MapPin className="h-3.5 w-3.5 text-emerald-600" />
                  From City
                </label>
                <select
                  value={source}
                  onChange={(e) => setSource(e.target.value)}
                  className="w-full rounded-xl border border-cream-200 bg-cream-50 px-3.5 py-3 text-sm font-semibold text-navy-900 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-200"
                >
                  <option value="">All Origin Cities</option>
                  {sources.map((city) => (
                    <option key={city} value={city}>
                      {city}
                    </option>
                  ))}
                </select>
              </div>

              <div className="flex justify-center md:col-span-1">
                <button
                  type="button"
                  onClick={handleSwap}
                  title="Swap origin and destination"
                  className="flex h-11 w-11 items-center justify-center rounded-xl border border-cream-200 bg-cream-50 text-navy-800 transition hover:border-emerald-400 hover:bg-emerald-50 hover:text-emerald-700"
                >
                  <ArrowLeftRight className="h-4 w-4" />
                </button>
              </div>

              <div className="md:col-span-3">
                <label className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  <MapPin className="h-3.5 w-3.5 text-navy-700" />
                  To City
                </label>
                <select
                  value={destination}
                  onChange={(e) => setDestination(e.target.value)}
                  className="w-full rounded-xl border border-cream-200 bg-cream-50 px-3.5 py-3 text-sm font-semibold text-navy-900 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-200"
                >
                  <option value="">All Destinations</option>
                  {destinations.map((city) => (
                    <option key={city} value={city}>
                      {city}
                    </option>
                  ))}
                </select>
              </div>

              <div className="md:col-span-3">
                <label className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  <Calendar className="h-3.5 w-3.5 text-emerald-600" />
                  Travel Date
                </label>
                <input
                  type="date"
                  min={getTodayIso()}
                  value={travelDate}
                  onChange={(e) => setTravelDate(e.target.value)}
                  className="w-full rounded-xl border border-cream-200 bg-cream-50 px-3.5 py-3 text-sm font-semibold text-navy-900 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-200"
                />
              </div>

              <div className="md:col-span-2">
                <button
                  type="submit"
                  className="flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-600 px-5 py-3 text-sm font-bold text-white shadow-md transition hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2"
                >
                  <Search className="h-4 w-4" />
                  <span>Search Buses</span>
                </button>
              </div>
            </div>
          </form>

          <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div className="flex items-start gap-3 rounded-xl border border-white/10 bg-white/5 p-4">
              <ShieldCheck className="mt-0.5 h-5 w-5 shrink-0 text-emerald-400" />
              <div>
                <h3 className="text-sm font-bold text-white">DB-Enforced Exclusivity</h3>
                <p className="text-xs text-slate-300">
                  Partial unique index &amp; row locking prevent concurrent double-bookings.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3 rounded-xl border border-white/10 bg-white/5 p-4">
              <Ticket className="mt-0.5 h-5 w-5 shrink-0 text-emerald-400" />
              <div>
                <h3 className="text-sm font-bold text-white">Instant PNR &amp; Cancel</h3>
                <p className="text-xs text-slate-300">
                  Confirmed seats get an atomic PNR; cancelling frees the seat immediately.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3 rounded-xl border border-white/10 bg-white/5 p-4">
              <MapPin className="mt-0.5 h-5 w-5 shrink-0 text-emerald-400" />
              <div>
                <h3 className="text-sm font-bold text-white">5 Major Indian Corridors</h3>
                <p className="text-xs text-slate-300">
                  Patna–Ranchi, Patna–Gaya, Delhi–Jaipur, Bengaluru–Mysuru, Pune–Mumbai.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 sm:px-6">
        <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 className="font-display text-2xl font-bold text-navy-900">
              Featured Upcoming Trips
            </h2>
            <p className="text-sm text-slate-500">
              Live schedules and real-time seat inventory directly from PostgreSQL
            </p>
          </div>
          <button
            type="button"
            onClick={() => navigate("/search")}
            className="text-sm font-semibold text-emerald-700 hover:text-emerald-800"
          >
            View all scheduled trips →
          </button>
        </div>

        {loading && (
          <div className="rounded-2xl border border-cream-200 bg-white p-8 text-center text-sm text-slate-500">
            Loading live schedules...
          </div>
        )}

        {error && (
          <div className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-800">
            {error}
          </div>
        )}

        {!loading && !error && featuredTrips.length === 0 && (
          <div className="rounded-2xl border border-cream-200 bg-white p-8 text-center text-sm text-slate-500">
            No upcoming trips found. Try running the backend seed script.
          </div>
        )}

        <div className="space-y-4">
          {featuredTrips.map((trip) => (
            <TripCard key={trip.id} trip={trip} />
          ))}
        </div>
      </section>
    </div>
  );
}
