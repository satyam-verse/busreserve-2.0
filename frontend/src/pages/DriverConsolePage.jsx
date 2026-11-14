import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  Bus,
  Calendar,
  CheckCircle2,
  Clock,
  Compass,
  Gauge,
  MapPin,
  Navigation,
  Play,
  Radio,
  RefreshCw,
  Send,
  ShieldCheck,
  Square,
  Zap,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { busApi } from "../services/api";

function getHeadingCardinal(deg) {
  if (deg == null) return "N/A";
  const directions = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"];
  const index = Math.round(((deg % 360) / 22.5)) % 16;
  return `${directions[index]} (${Math.round(deg)}°)`;
}

export default function DriverConsolePage() {
  const { user } = useAuth();

  const [trips, setTrips] = useState([]);
  const [selectedTripId, setSelectedTripId] = useState("");
  const [loadingTrips, setLoadingTrips] = useState(true);
  const [tripsError, setTripsError] = useState(null);

  // GPS Telemetry State
  const [isBroadcasting, setIsBroadcasting] = useState(false);
  const [coords, setCoords] = useState(null);
  const [sequenceNumber, setSequenceNumber] = useState(1);
  const [lastAck, setLastAck] = useState(null);
  const [pingCount, setPingCount] = useState(0);
  const [gpsError, setGpsError] = useState(null);
  const [wakeLockActive, setWakeLockActive] = useState(false);

  // Dispatch Actions State
  const [actionLoading, setActionLoading] = useState(false);
  const [actionResult, setActionResult] = useState(null);

  const watchIdRef = useRef(null);
  const intervalIdRef = useRef(null);
  const wakeLockRef = useRef(null);
  const seqRef = useRef(1);
  const latestCoordsRef = useRef(null);

  // Load driver's assigned trips
  const loadTrips = async () => {
    setLoadingTrips(true);
    setTripsError(null);
    try {
      const data = await busApi.getDriverTrips();
      const tripList = data.trips || [];
      setTrips(tripList);
      if (tripList.length > 0 && !selectedTripId) {
        setSelectedTripId(String(tripList[0].id));
      }
    } catch (err) {
      setTripsError(err.message || "Failed to load assigned trips.");
    } finally {
      setLoadingTrips(false);
    }
  };

  useEffect(() => {
    loadTrips();
  }, []);

  const selectedTrip = trips.find((t) => String(t.id) === String(selectedTripId));

  // Request screen wake lock
  const requestWakeLock = async () => {
    if ("wakeLock" in navigator) {
      try {
        const lock = await navigator.wakeLock.request("screen");
        wakeLockRef.current = lock;
        setWakeLockActive(true);
        lock.addEventListener("release", () => {
          setWakeLockActive(false);
        });
      } catch {
        // Wake lock is optional
      }
    }
  };

  const releaseWakeLock = () => {
    if (wakeLockRef.current) {
      wakeLockRef.current.release().catch(() => {});
      wakeLockRef.current = null;
      setWakeLockActive(false);
    }
  };

  // Transmit location ping to backend
  const sendLocationPing = async (loc) => {
    if (!selectedTripId || !loc) return;

    const payload = {
      trip_id: Number(selectedTripId),
      sequence_number: seqRef.current,
      client_timestamp: new Date().toISOString(),
      latitude: Number(loc.latitude.toFixed(6)),
      longitude: Number(loc.longitude.toFixed(6)),
      accuracy: loc.accuracy != null ? Number(loc.accuracy.toFixed(1)) : null,
      speed: loc.speed != null ? Math.max(0, Number(loc.speed.toFixed(1))) : null,
      heading: loc.heading != null && !isNaN(loc.heading) ? Number(loc.heading.toFixed(1)) : null,
    };

    try {
      const res = await busApi.sendDriverLocation(payload);
      setLastAck({
        time: new Date(),
        status: res.status || "ACCEPTED",
        sequence: seqRef.current,
      });
      setPingCount((prev) => prev + 1);
      seqRef.current += 1;
      setSequenceNumber(seqRef.current);
      setGpsError(null);
    } catch (err) {
      setGpsError(`Ping failed: ${err.message || "Network error"}`);
    }
  };

  // Start GPS Broadcasting
  const startBroadcasting = () => {
    if (!selectedTripId) {
      alert("Please select a trip before starting GPS broadcasting.");
      return;
    }

    if (!navigator.geolocation) {
      setGpsError("Geolocation is not supported by your browser or device.");
      return;
    }

    setIsBroadcasting(true);
    setGpsError(null);
    requestWakeLock();

    // Watch position
    watchIdRef.current = navigator.geolocation.watchPosition(
      (pos) => {
        const c = {
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
          speed: pos.coords.speed,
          heading: pos.coords.heading,
        };
        setCoords(c);
        latestCoordsRef.current = c;
      },
      (err) => {
        setGpsError(`GPS Error: ${err.message} (Code ${err.code})`);
      },
      {
        enableHighAccuracy: true,
        maximumAge: 0,
        timeout: 15000,
      }
    );

    // Heartbeat transmission every 15 seconds
    intervalIdRef.current = setInterval(() => {
      if (latestCoordsRef.current) {
        sendLocationPing(latestCoordsRef.current);
      }
    }, 15000);

    // Initial immediate ping if location is quickly available
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const c = {
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
          speed: pos.coords.speed,
          heading: pos.coords.heading,
        };
        setCoords(c);
        latestCoordsRef.current = c;
        sendLocationPing(c);
      },
      () => {},
      { enableHighAccuracy: true, timeout: 5000 }
    );
  };

  // Stop GPS Broadcasting
  const stopBroadcasting = () => {
    if (watchIdRef.current !== null) {
      navigator.geolocation.clearWatch(watchIdRef.current);
      watchIdRef.current = null;
    }
    if (intervalIdRef.current) {
      clearInterval(intervalIdRef.current);
      intervalIdRef.current = null;
    }
    releaseWakeLock();
    setIsBroadcasting(false);
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopBroadcasting();
    };
  }, []);

  // Handle Mark Trip Departed
  const handleDepartTrip = async () => {
    if (!selectedTripId) return;
    if (!window.confirm("Confirm departure for this trip? Departure alerts will be dispatched to all ticketed passengers.")) return;

    setActionLoading(true);
    setActionResult(null);
    try {
      const res = await busApi.markTripDeparted(Number(selectedTripId));
      setActionResult({
        type: "success",
        title: "Trip Departure Confirmed",
        message: res.message || "Departure recorded successfully.",
        details: res.delivery_status,
      });
      loadTrips();
    } catch (err) {
      setActionResult({
        type: "error",
        title: "Departure Failed",
        message: err.message || "Failed to record departure.",
      });
    } finally {
      setActionLoading(false);
    }
  };

  // Handle Mark Trip Arrived
  const handleArriveTrip = async () => {
    if (!selectedTripId) return;
    if (!window.confirm("Confirm arrival at destination? This will set trip status to COMPLETED and alert passengers.")) return;

    setActionLoading(true);
    setActionResult(null);
    try {
      const res = await busApi.markTripArrived(Number(selectedTripId));
      setActionResult({
        type: "success",
        title: "Trip Arrival Confirmed",
        message: res.message || "Arrival recorded successfully. Trip is now COMPLETED.",
        details: res.delivery_status,
      });
      stopBroadcasting();
      loadTrips();
    } catch (err) {
      setActionResult({
        type: "error",
        title: "Arrival Confirmation Failed",
        message: err.message || "Failed to confirm arrival.",
      });
    } finally {
      setActionLoading(false);
    }
  };

  // Fallback simulator ping for dev environments without physical GPS
  const handleSimulatePing = () => {
    const simLat = 25.6120 + (Math.random() - 0.5) * 0.005;
    const simLon = 85.1440 + (Math.random() - 0.5) * 0.005;
    const simCoords = {
      latitude: simLat,
      longitude: simLon,
      accuracy: 8.5,
      speed: 12.5, // 45 km/h
      heading: 90.0,
    };
    setCoords(simCoords);
    latestCoordsRef.current = simCoords;
    sendLocationPing(simCoords);
  };

  return (
    <div className="min-h-screen bg-cream-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-4xl space-y-6">
        {/* Header Banner */}
        <div className="rounded-2xl bg-navy-950 p-6 text-white shadow-xl">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-500/20 text-emerald-400">
                <Bus className="h-6 w-6" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="font-display text-xl font-bold text-white">
                    Driver GPS Telemetry Console
                  </h1>
                  <span className="rounded-full bg-emerald-500/20 px-2.5 py-0.5 text-xs font-semibold text-emerald-300">
                    DRIVER CONSOLE
                  </span>
                </div>
                <p className="text-xs text-slate-300">
                  Signed in as: <span className="font-semibold text-white">{user?.full_name || user?.email}</span>
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {wakeLockActive && (
                <span className="inline-flex items-center gap-1 rounded-full bg-amber-400/20 px-2.5 py-1 text-xs font-semibold text-amber-300">
                  <Zap className="h-3 w-3" /> Screen Kept Awake
                </span>
              )}
              <button
                type="button"
                onClick={loadTrips}
                disabled={loadingTrips}
                className="inline-flex items-center gap-1.5 rounded-lg border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-medium text-white hover:bg-white/20"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${loadingTrips ? "animate-spin" : ""}`} />
                <span>Refresh</span>
              </button>
            </div>
          </div>
        </div>

        {/* Action Result Notification */}
        {actionResult && (
          <div
            className={`rounded-xl border p-4 text-sm ${
              actionResult.type === "success"
                ? "border-emerald-300 bg-emerald-50 text-emerald-900"
                : "border-rose-300 bg-rose-50 text-rose-900"
            }`}
          >
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-2.5">
                {actionResult.type === "success" ? (
                  <CheckCircle2 className="h-5 w-5 text-emerald-600 mt-0.5 shrink-0" />
                ) : (
                  <AlertCircle className="h-5 w-5 text-rose-600 mt-0.5 shrink-0" />
                )}
                <div>
                  <h4 className="font-bold">{actionResult.title}</h4>
                  <p className="text-xs mt-0.5">{actionResult.message}</p>
                  {actionResult.details && (
                    <div className="mt-2 flex flex-wrap gap-2 text-[11px] font-mono">
                      <span className="rounded bg-white px-2 py-0.5 border border-emerald-200">
                        Sent: {actionResult.details.sent}
                      </span>
                      <span className="rounded bg-white px-2 py-0.5 border border-amber-200 text-amber-800">
                        Mock: {actionResult.details.mock}
                      </span>
                      <span className="rounded bg-white px-2 py-0.5 border border-slate-200 text-slate-700">
                        Pending: {actionResult.details.not_configured}
                      </span>
                    </div>
                  )}
                </div>
              </div>
              <button
                type="button"
                onClick={() => setActionResult(null)}
                className="text-xs font-bold hover:underline"
              >
                Dismiss
              </button>
            </div>
          </div>
        )}

        {/* Trip Selection Card */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-3">
            Assigned Schedule
          </h2>

          {loadingTrips ? (
            <p className="text-sm text-slate-500">Loading assigned trips...</p>
          ) : trips.length === 0 ? (
            <div className="rounded-xl border border-dashed border-amber-300 bg-amber-50/50 p-6 text-center">
              <AlertTriangle className="mx-auto h-8 w-8 text-amber-600" />
              <h3 className="mt-2 text-sm font-bold text-slate-900">No Trips Assigned</h3>
              <p className="mt-1 text-xs text-slate-600">
                You do not currently have any active trips assigned. Contact your fleet operator to assign a route.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <label htmlFor="trip-select" className="block text-xs font-semibold text-slate-700 mb-1">
                  Select Active Trip
                </label>
                <select
                  id="trip-select"
                  value={selectedTripId}
                  onChange={(e) => {
                    setSelectedTripId(e.target.value);
                    seqRef.current = 1;
                    setSequenceNumber(1);
                  }}
                  disabled={isBroadcasting}
                  className="w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm font-medium text-slate-900 shadow-sm focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 disabled:bg-slate-100"
                >
                  {trips.map((t) => (
                    <option key={t.id} value={t.id}>
                      Trip #{t.id} — {t.route?.name || `${t.source} → ${t.destination}`} ({t.travel_date} at {t.departure_time})
                    </option>
                  ))}
                </select>
              </div>

              {selectedTrip && (
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 rounded-xl bg-slate-50 p-3.5 text-xs text-slate-600 border border-slate-200">
                  <div>
                    <span className="block font-medium text-slate-400">Route</span>
                    <span className="font-bold text-slate-900 truncate block">
                      {selectedTrip.source} → {selectedTrip.destination}
                    </span>
                  </div>
                  <div>
                    <span className="block font-medium text-slate-400">Departure</span>
                    <span className="font-bold text-slate-900">
                      {selectedTrip.travel_date} • {selectedTrip.departure_time}
                    </span>
                  </div>
                  <div>
                    <span className="block font-medium text-slate-400">Bus Type</span>
                    <span className="font-bold text-slate-900">{selectedTrip.bus_type || "Express"}</span>
                  </div>
                  <div>
                    <span className="block font-medium text-slate-400">Status</span>
                    <span className="inline-flex rounded-full bg-emerald-100 px-2 py-0.5 font-bold text-emerald-800">
                      {selectedTrip.status}
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* GPS Live Telemetry HUD */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm space-y-5">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-slate-100 pb-4">
            <div>
              <h2 className="font-display text-base font-bold text-slate-900">
                Real-Time GPS Broadcast
              </h2>
              <p className="text-xs text-slate-500">
                Broadcasts high-frequency satellite telemetry to passenger maps and operator tracking.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <span
                className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-bold ${
                  isBroadcasting
                    ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                    : "bg-slate-100 text-slate-600 border border-slate-300"
                }`}
              >
                <span
                  className={`h-2.5 w-2.5 rounded-full ${
                    isBroadcasting ? "bg-emerald-500 animate-ping" : "bg-slate-400"
                  }`}
                />
                {isBroadcasting ? "BROADCASTING LIVE" : "STANDBY"}
              </span>
            </div>
          </div>

          {gpsError && (
            <div className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-xs text-rose-700 flex items-center gap-2">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{gpsError}</span>
            </div>
          )}

          {/* Telemetry Gauges Grid */}
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            <div className="rounded-xl bg-slate-50 p-4 border border-slate-200 text-center">
              <Gauge className="mx-auto h-5 w-5 text-emerald-600 mb-1" />
              <span className="block text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                Ground Speed
              </span>
              <span className="font-mono text-xl font-black text-slate-900">
                {coords?.speed != null ? Math.round(coords.speed * 3.6) : "--"}
              </span>
              <span className="text-[10px] text-slate-500 ml-1">km/h</span>
            </div>

            <div className="rounded-xl bg-slate-50 p-4 border border-slate-200 text-center">
              <Compass className="mx-auto h-5 w-5 text-navy-800 mb-1" />
              <span className="block text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                Heading
              </span>
              <span className="font-mono text-base font-bold text-slate-900">
                {getHeadingCardinal(coords?.heading)}
              </span>
            </div>

            <div className="rounded-xl bg-slate-50 p-4 border border-slate-200 text-center">
              <Radio className="mx-auto h-5 w-5 text-amber-600 mb-1" />
              <span className="block text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                GPS Accuracy
              </span>
              <span className="font-mono text-lg font-bold text-slate-900">
                {coords?.accuracy != null ? `±${Math.round(coords.accuracy)}m` : "--"}
              </span>
            </div>

            <div className="rounded-xl bg-slate-50 p-4 border border-slate-200 text-center">
              <Send className="mx-auto h-5 w-5 text-emerald-600 mb-1" />
              <span className="block text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                Telemetry Pings
              </span>
              <span className="font-mono text-lg font-bold text-emerald-700">
                #{sequenceNumber - 1} ({pingCount} ACKs)
              </span>
            </div>
          </div>

          {/* Coordinates and Server Status */}
          <div className="rounded-xl bg-navy-950 p-3.5 text-xs text-white flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
            <div className="flex items-center gap-2 font-mono">
              <MapPin className="h-4 w-4 text-emerald-400 shrink-0" />
              <span>
                {coords
                  ? `Lat: ${coords.latitude.toFixed(6)}, Lon: ${coords.longitude.toFixed(6)}`
                  : "Awaiting GPS satellite fix..."}
              </span>
            </div>
            <div className="text-[11px] text-slate-300">
              {lastAck ? (
                <span className="inline-flex items-center gap-1 text-emerald-400">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  Last ACK: {lastAck.time.toLocaleTimeString()} (Seq #{lastAck.sequence})
                </span>
              ) : (
                "No pings acknowledged yet"
              )}
            </div>
          </div>

          {/* Control Buttons */}
          <div className="flex flex-wrap items-center gap-3 pt-2">
            {!isBroadcasting ? (
              <button
                type="button"
                onClick={startBroadcasting}
                disabled={!selectedTripId}
                className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-5 py-3 text-sm font-bold text-white shadow-md transition hover:bg-emerald-700 disabled:opacity-50"
              >
                <Play className="h-4 w-4 fill-white" />
                <span>Start GPS Broadcast</span>
              </button>
            ) : (
              <button
                type="button"
                onClick={stopBroadcasting}
                className="inline-flex items-center gap-2 rounded-xl bg-rose-600 px-5 py-3 text-sm font-bold text-white shadow-md transition hover:bg-rose-700"
              >
                <Square className="h-4 w-4 fill-white" />
                <span>Pause GPS Broadcast</span>
              </button>
            )}

            {/* Dev Simulator Button */}
            <button
              type="button"
              onClick={handleSimulatePing}
              disabled={!selectedTripId}
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-300 bg-white px-3.5 py-3 text-xs font-bold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
              title="Transmit a test GPS ping with simulated coordinates (ideal for development without live satellite fix)"
            >
              <Navigation className="h-3.5 w-3.5 text-navy-800" />
              <span>Send Single Test Ping</span>
            </button>
          </div>
        </div>

        {/* Trip Dispatch Controls */}
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm space-y-4">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500">
            Trip Dispatch Controls
          </h2>
          <p className="text-xs text-slate-600">
            Dispatch lifecycle events for passengers. When you record departure or arrival, SMS and in-app alerts are sent automatically.
          </p>

          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={handleDepartTrip}
              disabled={actionLoading || !selectedTripId}
              className="inline-flex items-center gap-2 rounded-xl border border-emerald-600/30 bg-emerald-50 px-4 py-2.5 text-xs font-bold text-emerald-800 hover:bg-emerald-100 disabled:opacity-50"
            >
              <Play className="h-3.5 w-3.5" />
              <span>Mark Trip Departed (Alert Passengers)</span>
            </button>

            <button
              type="button"
              onClick={handleArriveTrip}
              disabled={actionLoading || !selectedTripId}
              className="inline-flex items-center gap-2 rounded-xl border border-navy-950/20 bg-navy-950 px-4 py-2.5 text-xs font-bold text-white hover:bg-navy-900 disabled:opacity-50"
            >
              <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
              <span>Confirm Arrival at Destination</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
