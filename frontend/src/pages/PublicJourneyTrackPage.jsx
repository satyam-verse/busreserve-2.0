import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import L from "leaflet";
import {
  AlertTriangle,
  ArrowRight,
  Bus,
  Clock,
  Compass,
  Gauge,
  MapPin,
  Navigation,
  Radio,
  RefreshCw,
  Shield,
  ShieldCheck,
  Zap,
} from "lucide-react";
import { busApi } from "../services/api";

function getFreshnessBadge(status) {
  switch (status) {
    case "LIVE":
      return {
        label: "Live Telemetry",
        bg: "bg-emerald-500/15 text-emerald-700 border-emerald-300",
        dot: "bg-emerald-500 animate-pulse",
      };
    case "WEAK_SIGNAL":
      return {
        label: "Weak Signal (30s+)",
        bg: "bg-amber-500/15 text-amber-700 border-amber-300",
        dot: "bg-amber-500",
      };
    case "STALE":
      return {
        label: "Signal Stale (60s+)",
        bg: "bg-orange-500/15 text-orange-700 border-orange-300",
        dot: "bg-orange-500",
      };
    default:
      return {
        label: "Device Offline",
        bg: "bg-slate-500/15 text-slate-700 border-slate-300",
        dot: "bg-slate-400",
      };
  }
}

export default function PublicJourneyTrackPage() {
  const { token } = useParams();
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markerRef = useRef(null);
  const eventSourceRef = useRef(null);

  const [loading, setLoading] = useState(true);
  const [journeyData, setJourneyData] = useState(null);
  const [liveTracking, setLiveTracking] = useState(null);
  const [errorStatus, setErrorStatus] = useState(null);
  const [lastRefreshed, setLastRefreshed] = useState(null);

  useEffect(() => {
    if (!token) return;

    let isMounted = true;
    setLoading(true);
    setErrorStatus(null);

    async function loadSharedJourney() {
      try {
        const res = await busApi.getSharedJourney(token);
        if (isMounted) {
          setJourneyData(res);
          setLiveTracking(res.tracking);
          setLastRefreshed(new Date());
          setLoading(false);

          // Setup SSE live stream if trip id available
          if (res.trip?.id && !eventSourceRef.current) {
            try {
              const es = new EventSource(`/api/tracking/stream/${res.trip.id}`);
              eventSourceRef.current = es;

              es.addEventListener("location", (e) => {
                if (!isMounted) return;
                try {
                  const data = JSON.parse(e.data);
                  setLiveTracking(data);
                  setLastRefreshed(new Date());
                } catch {
                  // ignore
                }
              });
            } catch {
              // fallback to polling
            }
          }
        }
      } catch (err) {
        if (isMounted) {
          setErrorStatus(err.status || 404);
          setLoading(false);
        }
      }
    }

    loadSharedJourney();

    // Polling fallback
    const interval = setInterval(async () => {
      if (journeyData?.trip?.id) {
        try {
          const freshTracking = await busApi.getTripTracking(journeyData.trip.id);
          if (isMounted) {
            setLiveTracking(freshTracking);
            setLastRefreshed(new Date());
          }
        } catch {
          // ignore
        }
      }
    }, 10000);

    return () => {
      isMounted = false;
      clearInterval(interval);
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, [token, journeyData?.trip?.id]);

  // Leaflet Map Rendering
  useEffect(() => {
    if (loading || errorStatus || !mapContainerRef.current) return;

    const coords = liveTracking?.coordinates;
    const defaultLat = coords?.latitude || 25.5941;
    const defaultLng = coords?.longitude || 85.1376;

    if (!mapInstanceRef.current) {
      const map = L.map(mapContainerRef.current, {
        center: [defaultLat, defaultLng],
        zoom: coords ? 14 : 10,
        zoomControl: true,
      });

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19,
      }).addTo(map);

      mapInstanceRef.current = map;
    }

    const map = mapInstanceRef.current;

    if (coords?.latitude && coords?.longitude) {
      const pos = [coords.latitude, coords.longitude];
      const heading = liveTracking.heading || 0;
      const isDriver = liveTracking.active_source === "DRIVER";

      const iconHtml = `
        <div style="transform: rotate(${heading}deg); transition: transform 0.5s ease-out;"
             class="flex items-center justify-center w-12 h-12 rounded-full ${
               isDriver ? "bg-emerald-600" : "bg-amber-600"
             } border-2 border-white shadow-2xl text-white">
          <svg class="w-6 h-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M8 6v6"/>
            <path d="M15 6v6"/>
            <path d="M2 12h19.6"/>
            <path d="M18 18h3s.5-1.7.8-2.8c.1-.4.2-.8.2-1.2 0-.4-.1-.8-.2-1.2l-1.4-5C20.1 6.8 19.2 6 18.2 6H5.8C4.8 6 3.9 6.8 3.6 7.8L2.2 12.8c-.1.4-.2.8-.2 1.2 0 .4.1.8.2 1.2.3 1.1.8 2.8.8 2.8h3"/>
            <circle cx="7" cy="18" r="2"/>
            <circle cx="17" cy="18" r="2"/>
          </svg>
        </div>
      `;

      const busIcon = L.divIcon({
        className: "public-bus-marker",
        html: iconHtml,
        iconSize: [48, 48],
        iconAnchor: [24, 24],
      });

      if (!markerRef.current) {
        markerRef.current = L.marker(pos, { icon: busIcon }).addTo(map);
        map.setView(pos, 14);
      } else {
        markerRef.current.setLatLng(pos);
        markerRef.current.setIcon(busIcon);
        map.panTo(pos);
      }

      setTimeout(() => {
        map.invalidateSize();
      }, 300);
    }
  }, [loading, errorStatus, liveTracking]);

  // Handle Expired / Revoked / Not Found Links
  if (errorStatus === 410 || errorStatus === 404) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center p-4">
        <div className="w-full max-w-md rounded-2xl bg-white p-8 text-center shadow-xl border border-slate-200">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-amber-100 text-amber-700">
            <AlertTriangle className="h-8 w-8" />
          </div>
          <h2 className="font-display text-xl font-bold text-navy-950">
            {errorStatus === 410 ? "Tracking Link Inactive" : "Link Not Found"}
          </h2>
          <p className="mt-2 text-sm text-slate-600 leading-relaxed">
            {errorStatus === 410
              ? "This live journey link has reached its validity expiration or was revoked by the passenger."
              : "The tracking link you entered does not match any active journey record."}
          </p>
          <div className="mt-6 flex flex-col gap-3">
            <Link
              to="/"
              className="inline-flex items-center justify-center rounded-xl bg-emerald-600 px-5 py-2.5 text-sm font-bold text-white shadow-md hover:bg-emerald-700 transition"
            >
              Return to BusReserve Home
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const trip = journeyData?.trip;
  const freshness = getFreshnessBadge(liveTracking?.status || "OFFLINE");
  const speed = liveTracking?.speed != null ? Math.round(liveTracking.speed * 3.6) : null;
  const isDriver = liveTracking?.active_source === "DRIVER";

  return (
    <div className="min-h-screen bg-cream-50 py-6 px-4 sm:px-6 lg:px-8">
      <div className="max-w-6xl mx-auto space-y-6">
        {/* Top Header Card */}
        <div className="rounded-2xl bg-navy-950 p-6 text-white shadow-xl border border-navy-900">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 mb-1.5">
                <span className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-emerald-400">
                  <Bus className="h-4 w-4" />
                  Live Transit Radar
                </span>
                <span
                  className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${freshness.bg}`}
                >
                  <span className={`h-2 w-2 rounded-full ${freshness.dot}`} />
                  {freshness.label}
                </span>
              </div>
              <h1 className="font-serif text-2xl sm:text-3xl font-bold text-white flex items-center gap-2">
                <span>{trip?.source || "Origin"}</span>
                <ArrowRight className="h-5 w-5 text-emerald-400 shrink-0" />
                <span>{trip?.destination || "Destination"}</span>
              </h1>
              <p className="mt-1 text-xs text-slate-300">
                {trip?.bus_type?.replace("_", " ") || "Standard Express"} • Travel Date:{" "}
                {trip?.travel_date || "Today"} • Departure: {trip?.departure_time || "—"} IST
              </p>
            </div>

            {/* Privacy Assurance Pill */}
            <div className="flex items-center gap-2.5 rounded-xl bg-white/10 px-4 py-2.5 backdrop-blur text-xs text-slate-200 border border-white/10 shrink-0">
              <Shield className="h-4 w-4 text-emerald-400 shrink-0" />
              <span>Zero Passenger PII Exposed</span>
            </div>
          </div>
        </div>

        {/* Map & Telemetry Split Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Map Canvas (2 cols) */}
          <div className="lg:col-span-2 relative rounded-2xl overflow-hidden bg-white shadow-lg border border-slate-200 min-h-[460px] flex flex-col">
            <div ref={mapContainerRef} className="h-full w-full min-h-[460px]" />

            {/* Floating Telemetry Badge */}
            {liveTracking?.coordinates && (
              <div className="absolute top-4 left-4 z-[400] flex flex-col gap-2">
                <div className="flex items-center gap-2 rounded-xl bg-white/95 px-3.5 py-2 shadow-lg backdrop-blur border border-slate-200 text-xs">
                  <ShieldCheck
                    className={`h-4 w-4 ${isDriver ? "text-emerald-600" : "text-amber-600"}`}
                  />
                  <span className="font-bold text-navy-950">
                    {isDriver ? "Driver Device GPS" : "Operator Fleet Takeover"}
                  </span>
                </div>
              </div>
            )}

            {/* Offline Coordinates Banner */}
            {!loading && !liveTracking?.coordinates && (
              <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-white/85 p-6 text-center backdrop-blur-sm">
                <AlertTriangle className="h-8 w-8 text-amber-600 mb-2" />
                <h4 className="font-display text-base font-bold text-navy-950">
                  GPS Telemetry Not Yet Initialized
                </h4>
                <p className="text-xs text-slate-600 max-w-sm mt-1">
                  The driver has not begun broadcasting GPS coordinates for this trip. The map will update automatically when the vehicle departs.
                </p>
              </div>
            )}
          </div>

          {/* Right Sidebar: Trip Milestones & Live Metrics */}
          <div className="space-y-4">
            {/* Real-time Telemetry Card */}
            <div className="rounded-2xl bg-white p-5 shadow-sm border border-slate-200 space-y-4">
              <h3 className="font-display text-xs font-bold uppercase tracking-wider text-navy-900/70 flex items-center gap-2">
                <Radio className="h-4 w-4 text-emerald-600" />
                Live Vehicle Metrics
              </h3>
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-xl bg-slate-50 p-3 border border-slate-200/80">
                  <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase text-slate-400">
                    <Gauge className="h-3.5 w-3.5 text-emerald-600" />
                    Speed
                  </div>
                  <p className="mt-1 font-mono text-base font-extrabold text-navy-950">
                    {speed != null ? `${speed} km/h` : "—"}
                  </p>
                </div>

                <div className="rounded-xl bg-slate-50 p-3 border border-slate-200/80">
                  <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase text-slate-400">
                    <Compass className="h-3.5 w-3.5 text-blue-600" />
                    Heading
                  </div>
                  <p className="mt-1 font-mono text-base font-extrabold text-navy-950">
                    {liveTracking?.heading != null
                      ? `${Math.round(liveTracking.heading)}°`
                      : "—"}
                  </p>
                </div>
              </div>

              <div className="rounded-xl bg-slate-50 p-3 border border-slate-200/80 flex items-center justify-between">
                <div>
                  <p className="text-[11px] font-semibold uppercase text-slate-400">
                    Accuracy
                  </p>
                  <p className="font-mono text-xs font-bold text-navy-950">
                    {liveTracking?.coordinates?.accuracy != null
                      ? `±${Math.round(liveTracking.coordinates.accuracy)} meters`
                      : "Standard Satellite"}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-[11px] font-semibold uppercase text-slate-400">
                    Last Ping
                  </p>
                  <p className="text-xs font-bold text-navy-950">
                    {lastRefreshed ? lastRefreshed.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : "Waiting..."}
                  </p>
                </div>
              </div>
            </div>

            {/* Boarding & Drop Station Card */}
            <div className="rounded-2xl bg-white p-5 shadow-sm border border-slate-200 space-y-3">
              <h3 className="font-display text-xs font-bold uppercase tracking-wider text-navy-900/70 flex items-center gap-2">
                <MapPin className="h-4 w-4 text-emerald-600" />
                Transit Route
              </h3>
              <div className="space-y-3 pt-1">
                <div className="flex items-start gap-3">
                  <div className="flex h-6 w-6 items-center justify-center rounded-full bg-emerald-100 text-emerald-700 text-xs font-bold">
                    A
                  </div>
                  <div>
                    <p className="text-xs font-bold text-navy-950">
                      {trip?.boarding_stop || trip?.source || "Origin"}
                    </p>
                    <p className="text-[11px] text-slate-400">Departure: {trip?.departure_time || "—"} IST</p>
                  </div>
                </div>

                <div className="ml-3 h-6 w-0.5 bg-slate-200" />

                <div className="flex items-start gap-3">
                  <div className="flex h-6 w-6 items-center justify-center rounded-full bg-navy-100 text-navy-700 text-xs font-bold">
                    B
                  </div>
                  <div>
                    <p className="text-xs font-bold text-navy-950">
                      {trip?.drop_stop || trip?.destination || "Destination"}
                    </p>
                    <p className="text-[11px] text-slate-400">Estimated Arrival: {trip?.arrival_time || "—"} IST</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
