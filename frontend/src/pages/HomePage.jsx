import {
  ArrowLeftRight,
  ArrowRight,
  Bot,
  CalendarClock,
  Compass,
  Database,
  Lock,
  MapPin,
  Search,
  ShieldCheck,
  Sparkles,
  Ticket,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import CityAutocompleteInput from "../components/CityAutocompleteInput";
import InteractiveBookingCalendar from "../components/InteractiveBookingCalendar";
import TripCard from "../components/TripCard";
import CorridorMapIllustration from "../components/brand/CorridorMapIllustration";
import { useAuth } from "../context/AuthContext";
import { busApi } from "../services/api";
import { addDaysIstIso, getTodayIstIso } from "../utils/dates";

const AI_SHOWCASE_PROMPTS = [
  "Cheapest AC bus from Patna to Ranchi tomorrow",
  "Find overnight sleeper buses under ₹900",
  "Check my upcoming booking and PNR status",
];

export default function HomePage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [featuredTrips, setFeaturedTrips] = useState([]);
  const [routes, setRoutes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [horizonDays, setHorizonDays] = useState(90);
  const [minDate, setMinDate] = useState(getTodayIstIso());
  const [maxDate, setMaxDate] = useState(addDaysIstIso(90));

  const [source, setSource] = useState("Patna");
  const [destination, setDestination] = useState("Ranchi");
  const [travelDate, setTravelDate] = useState(addDaysIstIso(1));

  useEffect(() => {
    let active = true;
    async function loadInitial() {
      try {
        setLoading(true);
        const [citiesResp, tripsResp, routesResp] = await Promise.all([
          busApi.getCities("", 15),
          busApi.searchTrips({ featured: true }),
          busApi.getRoutes().catch(() => ({ routes: [] })),
        ]);
        if (!active) return;
        setFeaturedTrips(tripsResp.trips || []);
        setRoutes(routesResp.routes || []);
        if (citiesResp.booking_horizon_days) {
          setHorizonDays(citiesResp.booking_horizon_days);
        }
        if (citiesResp.min_date) setMinDate(citiesResp.min_date);
        if (citiesResp.max_date) setMaxDate(citiesResp.max_date);
        if (citiesResp.min_date && citiesResp.max_date) {
          setTravelDate((prev) => {
            if (!prev || prev < citiesResp.min_date) return citiesResp.min_date;
            if (prev > citiesResp.max_date) return citiesResp.max_date;
            return prev;
          });
        }
      } catch (err) {
        if (active) setError(err.message || "Failed to load live schedules.");
      } finally {
        if (active) setLoading(false);
      }
    }
    loadInitial();
    return () => {
      active = false;
    };
  }, []);

  const handleSwap = () => {
    setSource(destination);
    setDestination(source);
  };

  const handleCorridorPrefill = (fromCity, toCity) => {
    setSource(fromCity);
    setDestination(toCity);
  };

  const handleSearch = (e) => {
    e.preventDefault();
    const qs = new URLSearchParams();
    if (source.trim()) qs.set("source", source.trim());
    if (destination.trim()) qs.set("destination", destination.trim());
    if (travelDate) qs.set("travel_date", travelDate);
    navigate(`/search?${qs.toString()}`);
  };

  const assistantEntryPath = user?.role === "USER" ? "/assistant" : "/login";

  return (
    <div className="space-y-16 pb-16">
      {/* Editorial Asymmetric Hero + Live Topology Map */}
      <section className="relative z-10 overflow-visible bg-navy-950 bg-navy-grid py-10 text-white sm:py-12 lg:py-12">
        <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
          <div className="absolute -right-24 -top-24 h-96 w-96 rounded-full bg-emerald-500/15 blur-3xl" />
          <div className="absolute -bottom-32 left-1/4 h-80 w-80 rounded-full bg-brass-500/10 blur-3xl" />
        </div>

        <div className="relative mx-auto max-w-7xl px-4 sm:px-6">
          <div className="grid grid-cols-1 items-center gap-10 lg:grid-cols-12">
            <div className="animate-fade-up space-y-6 lg:col-span-7">
              <div className="inline-flex flex-wrap items-center gap-2">
                <span className="inline-flex items-center gap-2 rounded-full border border-emerald-400/35 bg-emerald-500/10 px-3.5 py-1 text-xs font-semibold tracking-wide text-emerald-300">
                  <Sparkles className="h-3.5 w-3.5" />
                  BusReserve 2.0 • Asia/Kolkata (IST)
                </span>
                <span className="inline-flex items-center gap-1.5 rounded-full border border-brass-400/30 bg-brass-500/10 px-3 py-1 font-mono text-[11px] font-semibold text-brass-400">
                  {horizonDays}-Day Live Horizon
                </span>
              </div>

              <h1 className="font-display text-4xl font-extrabold leading-[1.08] tracking-tight sm:text-5xl lg:text-6xl">
                Intercity Coach Travel,{" "}
                <span className="font-serif text-[1.08em] font-normal italic text-emerald-300">
                  Engineered
                </span>{" "}
                for Zero Double-Bookings.
              </h1>

              <p className="max-w-2xl text-base leading-relaxed text-slate-300 sm:text-lg">
                Search dynamic Indian city corridors, reserve exact coach seats with instant
                double-booking protection, and ask our Smart Travel Concierge for optimal fares and
                overnight options.
              </p>

              <div className="grid max-w-xl grid-cols-3 gap-3 border-t border-white/10 pt-5">
                <div>
                  <p className="font-mono text-2xl font-bold text-emerald-400">
                    {routes.length || "12"}
                  </p>
                  <p className="text-xs text-slate-400">Active Corridors</p>
                </div>
                <div>
                  <p className="font-mono text-2xl font-bold text-white">{horizonDays}d</p>
                  <p className="text-xs text-slate-400">IST Advance Window</p>
                </div>
                <div>
                  <p className="font-mono text-2xl font-bold text-brass-400">100%</p>
                  <p className="text-xs text-slate-400">Seat Lock Guarantee</p>
                </div>
              </div>
            </div>

            <div className="animate-fade-up-delay-1 lg:col-span-5">
              <CorridorMapIllustration onSelectCorridor={handleCorridorPrefill} />
            </div>
          </div>

          {/* Intelligent Glass-Ivory Search Bar */}
          <form
            onSubmit={handleSearch}
            className="animate-fade-up-delay-2 relative z-20 mt-8 rounded-3xl border border-cream-200/80 bg-white p-5 text-navy-950 shadow-editorial sm:p-6"
          >
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2 border-b border-cream-200 pb-3">
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-navy-800">
                <Compass className="h-4 w-4 text-emerald-600" />
                <span>Intelligent Corridor &amp; Calendar Search</span>
              </div>
              <span className="font-mono text-[11px] text-slate-500">
                Window: {minDate} → {maxDate} (IST)
              </span>
            </div>

            <div className="grid grid-cols-1 gap-4 md:grid-cols-12 md:items-start">
              <div className="md:col-span-3">
                <CityAutocompleteInput
                  label="From City"
                  value={source}
                  onChange={setSource}
                  placeholder="Enter origin city"
                  iconTone="text-emerald-600"
                />
              </div>

              <div className="flex items-center justify-center md:col-span-1 md:pt-6">
                <button
                  type="button"
                  onClick={handleSwap}
                  title="Swap origin and destination"
                  aria-label="Swap origin and destination cities"
                  className="flex h-11 w-11 items-center justify-center rounded-xl border border-cream-200 bg-cream-50 text-navy-900 transition hover:rotate-180 hover:border-emerald-500 hover:bg-emerald-50 hover:text-emerald-700"
                >
                  <ArrowLeftRight className="h-4 w-4" />
                </button>
              </div>

              <div className="md:col-span-3">
                <CityAutocompleteInput
                  label="To City"
                  value={destination}
                  onChange={setDestination}
                  placeholder="Enter destination city"
                  iconTone="text-navy-700"
                />
              </div>

              <div className="md:col-span-3">
                <InteractiveBookingCalendar
                  label="Travel Date"
                  value={travelDate}
                  onChange={setTravelDate}
                  minDate={minDate}
                  maxDate={maxDate}
                  horizonDays={horizonDays}
                />
              </div>

              <div className="md:col-span-2 md:pt-6">
                <button
                  type="submit"
                  className="flex h-[46px] w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 px-5 text-sm font-bold text-white shadow-md shadow-emerald-700/20 transition hover:from-emerald-500 hover:to-teal-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2"
                >
                  <Search className="h-4 w-4" />
                  <span>Search Buses</span>
                </button>
              </div>
            </div>
          </form>
        </div>
      </section>

      {/* Dynamic Route Discovery */}
      <section className="mx-auto max-w-7xl px-4 sm:px-6">
        <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="font-mono text-xs font-semibold uppercase tracking-widest text-emerald-700">
              Live Route Network
            </p>
            <h2 className="mt-1 font-display text-2xl font-extrabold text-navy-950 sm:text-3xl">
              Live Route{" "}
              <span className="font-serif text-[1.08em] font-normal italic text-emerald-700">
                Discovery
              </span>
            </h2>
            <p className="mt-1 text-sm text-slate-600">
              Every corridor below reflects real-time scheduled services — including new routes as
              soon as they open for booking.
            </p>
          </div>
          <Link
            to="/search"
            className="inline-flex items-center gap-1.5 rounded-xl border border-navy-900/15 bg-white px-4 py-2 text-xs font-bold text-navy-950 transition hover:border-emerald-400 hover:bg-emerald-50"
          >
            <span>Browse Full Schedule Directory</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        {routes.length > 0 ? (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {routes.slice(0, 6).map((route) => (
              <div
                key={route.id}
                className="group flex flex-col justify-between rounded-2xl border border-cream-200 bg-white p-5 shadow-card transition hover:-translate-y-0.5 hover:border-emerald-300"
              >
                <div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="rounded-full bg-cream-100 px-2.5 py-0.5 font-mono text-[11px] font-semibold text-navy-800">
                      CORRIDOR #{route.id}
                    </span>
                    {route.distance_km ? (
                      <span className="font-mono text-xs font-semibold text-slate-500">
                        {route.distance_km} km
                      </span>
                    ) : null}
                  </div>
                  <h3 className="mt-3 font-display text-lg font-bold text-navy-950">
                    {route.source}{" "}
                    <ArrowRight className="inline h-4 w-4 text-emerald-600" />{" "}
                    {route.destination}
                  </h3>
                  <p className="mt-0.5 text-xs font-medium text-slate-500">{route.name}</p>

                  {route.stops && route.stops.length > 0 ? (
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {route.stops.slice(0, 4).map((st) => (
                        <span
                          key={st.id}
                          className="inline-flex items-center gap-1 rounded-md border border-cream-200 bg-cream-50 px-2 py-0.5 text-[11px] text-navy-800"
                        >
                          <MapPin className="h-2.5 w-2.5 text-emerald-600" />
                          {st.city_name || st.stop_name}
                        </span>
                      ))}
                      {route.stops.length > 4 ? (
                        <span className="px-1.5 py-0.5 text-[11px] font-medium text-slate-400">
                          +{route.stops.length - 4} stops
                        </span>
                      ) : null}
                    </div>
                  ) : null}
                </div>

                <div className="mt-4 border-t border-cream-100 pt-3">
                  <Link
                    to={`/search?source=${encodeURIComponent(route.source)}&destination=${encodeURIComponent(route.destination)}&travel_date=${encodeURIComponent(travelDate || minDate)}`}
                    className="inline-flex items-center gap-1.5 text-xs font-bold text-emerald-700 transition group-hover:text-emerald-800"
                  >
                    <span>Explore Departures on {travelDate || minDate}</span>
                    <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="rounded-2xl border border-cream-200 bg-white p-6 text-sm text-slate-500">
            Loading active transit corridors...
          </div>
        )}
      </section>

      {/* AI Travel Concierge Entry Point */}
      <section className="mx-auto max-w-7xl px-4 sm:px-6">
        <div className="relative overflow-hidden rounded-3xl border border-navy-900/15 bg-gradient-to-br from-navy-950 via-navy-900 to-emerald-950 p-7 text-white shadow-editorial sm:p-10">
          <div className="pointer-events-none absolute -right-12 -top-12 h-64 w-64 rounded-full bg-emerald-400/15 blur-3xl" />

          <div className="relative grid items-center gap-8 lg:grid-cols-12">
            <div className="space-y-4 lg:col-span-7">
              <span className="inline-flex items-center gap-2 rounded-full border border-brass-400/35 bg-brass-500/15 px-3 py-1 text-xs font-semibold text-brass-400">
                <Bot className="h-3.5 w-3.5" />
                Live Travel Intelligence • Always Available
              </span>
              <h2 className="font-display text-2xl font-extrabold sm:text-3xl">
                Meet Your Grounded{" "}
                <span className="font-serif text-[1.08em] font-normal italic text-emerald-300">
                  AI Travel Concierge
                </span>
              </h2>
              <p className="max-w-xl text-sm leading-relaxed text-slate-300">
                Ask naturally in plain English for cheapest fares, overnight sleeper coaches, or
                instant checks on your own PNR — strictly grounded in live schedules and seat
                availability with zero fabricated buses or routes.
              </p>

              <div className="flex flex-wrap gap-3 pt-1">
                <Link
                  to={assistantEntryPath}
                  className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-5 py-3 text-sm font-bold text-navy-950 shadow-lg shadow-emerald-950/30 transition hover:bg-emerald-400"
                >
                  <Sparkles className="h-4 w-4" />
                  <span>
                    {user?.role === "USER" ? "Open AI Concierge" : "Sign In to Launch AI Concierge"}
                  </span>
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <Link
                  to="/pnr"
                  className="inline-flex items-center gap-2 rounded-xl border border-white/20 bg-white/10 px-4 py-3 text-sm font-semibold text-white transition hover:bg-white/15"
                >
                  <Ticket className="h-4 w-4 text-emerald-300" />
                  <span>Check PNR Directly</span>
                </Link>
              </div>
            </div>

            <div className="space-y-2.5 lg:col-span-5">
              <p className="font-mono text-[11px] font-semibold uppercase tracking-widest text-emerald-300">
                Sample Concierge Prompts
              </p>
              {AI_SHOWCASE_PROMPTS.map((prompt) => (
                <Link
                  key={prompt}
                  to={assistantEntryPath}
                  className="flex items-center justify-between gap-3 rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-xs font-medium text-slate-100 transition hover:border-emerald-400/50 hover:bg-white/10"
                >
                  <span>&ldquo;{prompt}&rdquo;</span>
                  <ArrowRight className="h-3.5 w-3.5 shrink-0 text-emerald-300" />
                </Link>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Featured Upcoming Departures */}
      <section className="mx-auto max-w-7xl px-4 sm:px-6">
        <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="font-mono text-xs font-semibold uppercase tracking-widest text-brass-600">
              Real-Time Inventory
            </p>
            <h2 className="mt-1 font-display text-2xl font-extrabold text-navy-950 sm:text-3xl">
              Featured Upcoming Trips
            </h2>
          </div>
          <button
            type="button"
            onClick={() => navigate("/search")}
            className="text-sm font-bold text-emerald-700 hover:text-emerald-800 hover:underline"
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

        {!loading && !error && (
          <div className="space-y-4">
            {featuredTrips.map((trip) => (
              <TripCard key={trip.id} trip={trip} />
            ))}
          </div>
        )}
      </section>

      {/* Architecture & Trust Strip */}
      <section className="mx-auto max-w-7xl px-4 sm:px-6">
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div className="rounded-2xl border border-cream-200 bg-white p-6 shadow-card">
            <div className="mb-3 inline-flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700">
              <Database className="h-5 w-5" />
            </div>
            <h3 className="font-display text-base font-bold text-navy-950">
              Guaranteed Seat Protection
            </h3>
            <p className="mt-1.5 text-xs leading-relaxed text-slate-600">
              Every reservation locks your chosen seat at confirmation so two passengers can never
              be booked on the same seat simultaneously.
            </p>
          </div>
          <div className="rounded-2xl border border-cream-200 bg-white p-6 shadow-card">
            <div className="mb-3 inline-flex h-10 w-10 items-center justify-center rounded-xl bg-brass-50 text-brass-600">
              <CalendarClock className="h-5 w-5" />
            </div>
            <h3 className="font-display text-base font-bold text-navy-950">
              IST-Safe {horizonDays}-Day Window
            </h3>
            <p className="mt-1.5 text-xs leading-relaxed text-slate-600">
              Consistent <code className="font-mono">Asia/Kolkata</code> calendar math eliminates
              midnight UTC drift across search, admin scheduling, and tickets.
            </p>
          </div>
          <div className="rounded-2xl border border-cream-200 bg-white p-6 shadow-card">
            <div className="mb-3 inline-flex h-10 w-10 items-center justify-center rounded-xl bg-navy-950 text-white">
              <Lock className="h-5 w-5 text-emerald-300" />
            </div>
            <h3 className="font-display text-base font-bold text-navy-950">
              Role-Isolated Portals
            </h3>
            <p className="mt-1.5 text-xs leading-relaxed text-slate-600">
              Separate Passenger &amp; Administrator login flows backed by strict HTTP-only JWT
              authentication and RBAC enforcement.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
