import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import {
  AlertTriangle,
  Compass,
  Gauge,
  Navigation,
  Radio,
  RefreshCw,
  ShieldCheck,
  X,
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

export default function LiveTrackingModal({ isOpen, onClose, tripId, tripInfo = {} }) {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markerRef = useRef(null);
  const eventSourceRef = useRef(null);

  const [trackingData, setTrackingData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastRefreshed, setLastRefreshed] = useState(null);

  // Initialize or update tracking
  useEffect(() => {
    if (!isOpen || !tripId) return;

    let isMounted = true;
    setLoading(true);
    setError(null);

    // Initial HTTP fetch
    async function fetchTracking() {
      try {
        const res = await busApi.getTripTracking(tripId);
        if (isMounted) {
          setTrackingData(res);
          setLastRefreshed(new Date());
          setLoading(false);
        }
      } catch (err) {
        if (isMounted) {
          setError(err.message || "Failed to load live tracking coordinates.");
          setLoading(false);
        }
      }
    }

    fetchTracking();

    // Setup Server-Sent Events (SSE) Stream
    try {
      const sseUrl = `/api/tracking/stream/${tripId}`;
      const es = new EventSource(sseUrl);
      eventSourceRef.current = es;

      es.addEventListener("location", (e) => {
        if (!isMounted) return;
        try {
          const data = JSON.parse(e.data);
          setTrackingData(data);
          setLastRefreshed(new Date());
          setLoading(false);
        } catch {
          // ignore stream parse errors
        }
      });

      es.onerror = () => {
        // SSE disconnected, fallback to polling
        if (es.readyState === EventSource.CLOSED) {
          es.close();
        }
      };
    } catch {
      // Fallback
    }

    // Polling interval fallback (every 10s)
    const pollInterval = setInterval(() => {
      fetchTracking();
    }, 10000);

    return () => {
      isMounted = false;
      clearInterval(pollInterval);
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, [isOpen, tripId]);

  // Leaflet Map Initialization & Marker Updates
  useEffect(() => {
    if (!isOpen || !mapContainerRef.current) return;

    const coords = trackingData?.coordinates;
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

    // Update marker if coordinates are available
    if (coords?.latitude && coords?.longitude) {
      const pos = [coords.latitude, coords.longitude];
      const heading = trackingData.heading || 0;
      const isDriver = trackingData.active_source === "DRIVER";

      const iconHtml = `
        <div style="transform: rotate(${heading}deg); transition: transform 0.5s ease-out;"
             class="flex items-center justify-center w-11 h-11 rounded-full ${
               isDriver ? "bg-emerald-600" : "bg-amber-600"
             } border-2 border-white shadow-xl text-white">
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
        className: "bus-custom-marker",
        html: iconHtml,
        iconSize: [44, 44],
        iconAnchor: [22, 22],
      });

      if (!markerRef.current) {
        markerRef.current = L.marker(pos, { icon: busIcon }).addTo(map);
        map.setView(pos, 14);
      } else {
        markerRef.current.setLatLng(pos);
        markerRef.current.setIcon(busIcon);
        map.panTo(pos);
      }

      // Invalidate map size after modal animation
      setTimeout(() => {
        map.invalidateSize();
      }, 300);
    }

    return () => {
      // Map cleanup on unmount
    };
  }, [isOpen, trackingData]);

  // Cleanup map instance when modal closes
  useEffect(() => {
    if (!isOpen && mapInstanceRef.current) {
      mapInstanceRef.current.remove();
      mapInstanceRef.current = null;
      markerRef.current = null;
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const freshness = getFreshnessBadge(trackingData?.status || "OFFLINE");
  const isDriver = trackingData?.active_source === "DRIVER";
  const speed = trackingData?.speed != null ? Math.round(trackingData.speed * 3.6) : null; // m/s to km/h

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 bg-navy-950/70 backdrop-blur-sm animate-fade-in">
      <div className="relative flex flex-col w-full max-w-4xl max-h-[92vh] overflow-hidden rounded-2xl bg-white shadow-2xl border border-slate-200">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-200 bg-navy-950 px-5 py-4 text-white">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/20 text-emerald-400">
              <Navigation className="h-5 w-5 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-display text-base font-bold text-white">
                  Live Bus Tracking
                </h3>
                <span
                  className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${freshness.bg}`}
                >
                  <span className={`h-2 w-2 rounded-full ${freshness.dot}`} />
                  {freshness.label}
                </span>
              </div>
              <p className="text-xs text-slate-300">
                {tripInfo.source && tripInfo.destination
                  ? `${tripInfo.source} → ${tripInfo.destination} • Trip #${tripId}`
                  : `Trip #${tripId} • Real-time GPS Telemetry`}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close modal"
            className="rounded-lg p-2 text-slate-300 hover:bg-white/10 hover:text-white transition"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="relative flex-1 min-h-[380px] sm:min-h-[460px] w-full bg-slate-100">
          {/* Map canvas */}
          <div ref={mapContainerRef} className="h-full w-full min-h-[380px] sm:min-h-[460px]" />

          {/* Offline / No GPS coordinates overlay */}
          {!loading && !trackingData?.coordinates && (
            <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-white/85 p-6 text-center backdrop-blur-sm">
              <div className="mb-3 flex h-14 w-14 items-center justify-center rounded-2xl bg-amber-100 text-amber-700">
                <AlertTriangle className="h-7 w-7" />
              </div>
              <h4 className="font-display text-lg font-bold text-navy-950">
                GPS Signal Awaiting Ingestion
              </h4>
              <p className="mt-1 max-w-md text-sm text-slate-600">
                The driver has not yet broadcast live GPS coordinates for this trip. Tracking updates will automatically render as soon as the driver initiates transit telemetry.
              </p>
            </div>
          )}

          {/* Loading overlay */}
          {loading && (
            <div className="absolute inset-0 z-20 flex flex-col items-center justify-center bg-white/80 backdrop-blur-sm">
              <RefreshCw className="h-8 w-8 text-emerald-600 animate-spin" />
              <p className="mt-3 text-sm font-semibold text-navy-950">
                Acquiring live satellite coordinates...
              </p>
            </div>
          )}

          {/* Floating Source & Freshness Pill */}
          {trackingData?.coordinates && (
            <div className="absolute top-4 left-4 z-[400] flex flex-col gap-2">
              <div className="flex items-center gap-2 rounded-xl bg-white/95 px-3.5 py-2 shadow-lg backdrop-blur border border-slate-200">
                <ShieldCheck
                  className={`h-4 w-4 ${isDriver ? "text-emerald-600" : "text-amber-600"}`}
                />
                <div className="text-xs">
                  <span className="font-bold text-navy-950">
                    {isDriver ? "Driver GPS" : "Operator Fleet Takeover"}
                  </span>
                  <span className="ml-1.5 text-slate-500 font-mono">
                    (Seq #{trackingData.driver_sequence_number || trackingData.operator_sequence_number || 1})
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Telemetry Footer Grid */}
        <div className="border-t border-slate-200 bg-slate-50 p-4">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="flex items-center gap-2.5 rounded-xl bg-white p-3 border border-slate-200/80 shadow-xs">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-50 text-emerald-700">
                <Gauge className="h-4 w-4" />
              </div>
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                  Speed
                </p>
                <p className="font-mono text-sm font-bold text-navy-950">
                  {speed != null ? `${speed} km/h` : "—"}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2.5 rounded-xl bg-white p-3 border border-slate-200/80 shadow-xs">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-50 text-blue-700">
                <Compass className="h-4 w-4" />
              </div>
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                  Heading
                </p>
                <p className="font-mono text-sm font-bold text-navy-950">
                  {trackingData?.heading != null
                    ? `${Math.round(trackingData.heading)}°`
                    : "—"}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2.5 rounded-xl bg-white p-3 border border-slate-200/80 shadow-xs">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-purple-50 text-purple-700">
                <Radio className="h-4 w-4" />
              </div>
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                  Accuracy
                </p>
                <p className="font-mono text-sm font-bold text-navy-950">
                  {trackingData?.coordinates?.accuracy != null
                    ? `±${Math.round(trackingData.coordinates.accuracy)}m`
                    : "—"}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2.5 rounded-xl bg-white p-3 border border-slate-200/80 shadow-xs">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-amber-50 text-amber-700">
                <Zap className="h-4 w-4" />
              </div>
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
                  Updates
                </p>
                <p className="text-xs font-semibold text-navy-950">
                  {lastRefreshed ? lastRefreshed.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : "Waiting..."}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
