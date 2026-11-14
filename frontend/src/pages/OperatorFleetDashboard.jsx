import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Activity,
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  Bus,
  CheckCircle2,
  Clock,
  Compass,
  Gauge,
  MapPin,
  Navigation,
  Radio,
  RefreshCw,
  Search,
  Shield,
  ShieldAlert,
  ShieldCheck,
  UserCheck,
  Users,
  Zap,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { busApi } from "../services/api";

function getStatusBadge(status) {
  switch (status) {
    case "LIVE":
      return {
        label: "Live (0-30s)",
        classes: "bg-emerald-100 text-emerald-800 border-emerald-300",
        dot: "bg-emerald-500 animate-pulse",
      };
    case "WEAK_SIGNAL":
      return {
        label: "Weak Signal (31-60s)",
        classes: "bg-amber-100 text-amber-800 border-amber-300",
        dot: "bg-amber-500",
      };
    case "STALE":
      return {
        label: "Stale (61-120s)",
        classes: "bg-orange-100 text-orange-800 border-orange-300",
        dot: "bg-orange-500",
      };
    default:
      return {
        label: "Offline (>120s)",
        classes: "bg-slate-100 text-slate-700 border-slate-300",
        dot: "bg-slate-400",
      };
  }
}

export default function OperatorFleetDashboard() {
  const { user } = useAuth();

  const [fleet, setFleet] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchFilter, setSearchFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");

  // Takeover Modal State
  const [takeoverBus, setTakeoverBus] = useState(null);
  const [takeoverLat, setTakeoverLat] = useState("");
  const [takeoverLon, setTakeoverLon] = useState("");
  const [takeoverSeq, setTakeoverSeq] = useState("1");
  const [takeoverLoading, setTakeoverLoading] = useState(false);
  const [takeoverMessage, setTakeoverMessage] = useState(null);

  // Driver Assignment Modal State
  const [assignTrip, setAssignTrip] = useState(null);
  const [driverIdInput, setDriverIdInput] = useState("");
  const [assignLoading, setAssignLoading] = useState(false);
  const [assignMessage, setAssignMessage] = useState(null);

  const loadFleet = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await busApi.getOperatorFleet();
      setFleet(data.fleet || []);
    } catch (err) {
      setError(err.message || "Failed to load operator fleet data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadFleet();
    const interval = setInterval(loadFleet, 15000); // 15s periodic fleet refresh
    return () => clearInterval(interval);
  }, []);

  // Filter fleet
  const filteredFleet = fleet.filter((item) => {
    const bus = item.bus || {};
    const trip = item.active_trip || {};
    const tracking = item.tracking || {};
    const q = searchFilter.toLowerCase();

    const matchesQuery =
      (bus.registration_number || "").toLowerCase().includes(q) ||
      (bus.name || "").toLowerCase().includes(q) ||
      (trip.source || "").toLowerCase().includes(q) ||
      (trip.destination || "").toLowerCase().includes(q);

    if (!matchesQuery) return false;

    if (statusFilter === "ALL") return true;
    return (tracking.status || "OFFLINE") === statusFilter;
  });

  // Calculate KPIs
  const totalBuses = fleet.length;
  const activeTripsCount = fleet.filter((f) => f.active_trip).length;
  const liveCount = fleet.filter(
    (f) => f.tracking && (f.tracking.status === "LIVE" || f.tracking.status === "WEAK_SIGNAL")
  ).length;
  const takeoverEligibleCount = fleet.filter(
    (f) =>
      f.active_trip &&
      (!f.tracking || f.tracking.status === "STALE" || f.tracking.status === "OFFLINE")
  ).length;

  // Handle Operator Takeover Submission
  const handleTakeoverSubmit = async (e) => {
    e.preventDefault();
    if (!takeoverBus?.active_trip) return;

    setTakeoverLoading(true);
    setTakeoverMessage(null);

    const payload = {
      trip_id: takeoverBus.active_trip.id,
      sequence_number: Number(takeoverSeq) || 1,
      client_timestamp: new Date().toISOString(),
      latitude: Number(parseFloat(takeoverLat).toFixed(6)),
      longitude: Number(parseFloat(takeoverLon).toFixed(6)),
      accuracy: 10.0,
      speed: 15.0,
      heading: 90.0,
    };

    try {
      const res = await busApi.sendOperatorLocation(payload);
      setTakeoverMessage({
        type: "success",
        text: `Operator GPS takeover accepted! Active source: ${res.active_source || "OPERATOR"}. Sequence #${res.sequence_number}.`,
      });
      loadFleet();
      setTimeout(() => {
        setTakeoverBus(null);
        setTakeoverMessage(null);
      }, 2000);
    } catch (err) {
      setTakeoverMessage({
        type: "error",
        text: err.message || "Takeover failed. Ensure driver is stale (>60s) or sequence is monotonic.",
      });
    } finally {
      setTakeoverLoading(false);
    }
  };

  // Handle Driver Assignment
  const handleAssignDriver = async (e) => {
    e.preventDefault();
    if (!assignTrip || !driverIdInput) return;

    setAssignLoading(true);
    setAssignMessage(null);

    try {
      const res = await busApi.assignDriverToTrip({
        trip_id: assignTrip.id,
        driver_id: Number(driverIdInput),
      });
      setAssignMessage({
        type: "success",
        text: res.message || "Driver successfully assigned to trip.",
      });
      loadFleet();
      setTimeout(() => {
        setAssignTrip(null);
        setAssignMessage(null);
      }, 2000);
    } catch (err) {
      setAssignMessage({
        type: "error",
        text: err.message || "Failed to assign driver. Verify user ID belongs to a DRIVER.",
      });
    } finally {
      setAssignLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-cream-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        {/* Header */}
        <div className="rounded-2xl bg-navy-950 p-6 text-white shadow-xl">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-500/20 text-emerald-400">
                <Activity className="h-6 w-6" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="font-display text-xl font-bold text-white">
                    Operator Fleet Telemetry &amp; Takeover
                  </h1>
                  <span className="rounded-full bg-emerald-500/20 px-2.5 py-0.5 text-xs font-semibold text-emerald-300">
                    OPERATOR PORTAL
                  </span>
                </div>
                <p className="text-xs text-slate-300">
                  Fleet supervisor: <span className="font-semibold text-white">{user?.full_name || user?.email}</span>
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={loadFleet}
                disabled={loading}
                className="inline-flex items-center gap-1.5 rounded-lg border border-white/20 bg-white/10 px-3 py-1.5 text-xs font-medium text-white hover:bg-white/20"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
                <span>Auto-Refresh (15s)</span>
              </button>
            </div>
          </div>
        </div>

        {/* KPI Cards Grid */}
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between text-slate-500 text-xs font-bold uppercase tracking-wider mb-2">
              <span>Total Buses</span>
              <Bus className="h-4 w-4 text-navy-800" />
            </div>
            <div className="text-2xl font-black text-slate-900">{totalBuses}</div>
            <p className="text-[11px] text-slate-400 mt-1">Fleet assets registered</p>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between text-slate-500 text-xs font-bold uppercase tracking-wider mb-2">
              <span>Active Trips</span>
              <Navigation className="h-4 w-4 text-emerald-600" />
            </div>
            <div className="text-2xl font-black text-slate-900">{activeTripsCount}</div>
            <p className="text-[11px] text-slate-400 mt-1">Scheduled / In-transit</p>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between text-slate-500 text-xs font-bold uppercase tracking-wider mb-2">
              <span>Broadcasting Live</span>
              <Radio className="h-4 w-4 text-emerald-600 animate-pulse" />
            </div>
            <div className="text-2xl font-black text-emerald-600">{liveCount}</div>
            <p className="text-[11px] text-emerald-700/80 mt-1">Active GPS pings &lt;60s</p>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between text-slate-500 text-xs font-bold uppercase tracking-wider mb-2">
              <span>Takeover Eligible</span>
              <ShieldAlert className="h-4 w-4 text-orange-600" />
            </div>
            <div className="text-2xl font-black text-orange-600">{takeoverEligibleCount}</div>
            <p className="text-[11px] text-orange-700/80 mt-1">Stale / Offline trips</p>
          </div>
        </div>

        {/* Filter Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3.5 top-2.5 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Filter by bus registration, name, route or city..."
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              className="w-full rounded-xl border border-slate-300 bg-slate-50 pl-9 pr-3.5 py-2 text-xs font-medium text-slate-900 placeholder-slate-400 focus:border-emerald-500 focus:bg-white focus:outline-none focus:ring-1 focus:ring-emerald-500"
            />
          </div>

          <div className="flex flex-wrap items-center gap-1.5 text-xs font-semibold">
            {["ALL", "LIVE", "WEAK_SIGNAL", "STALE", "OFFLINE"].map((st) => (
              <button
                key={st}
                type="button"
                onClick={() => setStatusFilter(st)}
                className={`rounded-lg px-3 py-1.5 transition ${
                  statusFilter === st
                    ? "bg-navy-950 text-white"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                {st === "ALL" ? "All Statuses" : st.replace("_", " ")}
              </button>
            ))}
          </div>
        </div>

        {/* Fleet Table / Grid */}
        {loading && fleet.length === 0 ? (
          <div className="rounded-2xl border border-slate-200 bg-white p-12 text-center text-slate-500">
            <RefreshCw className="mx-auto h-8 w-8 animate-spin text-slate-400 mb-2" />
            <p className="text-sm font-semibold">Loading operator fleet telemetry...</p>
          </div>
        ) : filteredFleet.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-12 text-center">
            <Bus className="mx-auto h-8 w-8 text-slate-400 mb-2" />
            <h3 className="text-sm font-bold text-slate-900">No buses matching filter</h3>
            <p className="text-xs text-slate-500 mt-1">Adjust search parameters or refresh fleet.</p>
          </div>
        ) : (
          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-slate-200 bg-slate-50 font-semibold uppercase tracking-wider text-slate-500">
                  <tr>
                    <th className="py-3 px-4">Bus &amp; Plate</th>
                    <th className="py-3 px-4">Scheduled Route</th>
                    <th className="py-3 px-4">GPS Signal Health</th>
                    <th className="py-3 px-4">Telemetry Source</th>
                    <th className="py-3 px-4">Coordinates &amp; Speed</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-700">
                  {filteredFleet.map((item) => {
                    const bus = item.bus || {};
                    const trip = item.active_trip;
                    const tracking = item.tracking || {};
                    const badge = getStatusBadge(tracking.status || "OFFLINE");
                    const isTakeoverEligible =
                      trip && (tracking.status === "STALE" || tracking.status === "OFFLINE" || !tracking.status);

                    return (
                      <tr key={bus.id} className="hover:bg-slate-50/70 transition">
                        <td className="py-3.5 px-4 font-medium text-slate-900">
                          <div className="flex items-center gap-2.5">
                            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-navy-950 text-white font-mono text-xs font-bold">
                              {bus.bus_type?.[0] || "B"}
                            </div>
                            <div>
                              <div className="font-bold text-slate-900">{bus.name || `Bus #${bus.id}`}</div>
                              <div className="font-mono text-[11px] text-slate-500">
                                {bus.registration_number || "REG-PENDING"} • {bus.capacity} Seats
                              </div>
                            </div>
                          </div>
                        </td>

                        <td className="py-3.5 px-4">
                          {trip ? (
                            <div>
                              <div className="font-bold text-slate-900">
                                {trip.source} → {trip.destination}
                              </div>
                              <div className="text-[11px] text-slate-500">
                                Trip #{trip.id} • {trip.travel_date} at {trip.departure_time}
                              </div>
                            </div>
                          ) : (
                            <span className="text-slate-400 italic">No scheduled trip</span>
                          )}
                        </td>

                        <td className="py-3.5 px-4">
                          <span
                            className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold ${badge.classes}`}
                          >
                            <span className={`h-2 w-2 rounded-full ${badge.dot}`} />
                            {badge.label}
                          </span>
                        </td>

                        <td className="py-3.5 px-4">
                          {tracking.active_source ? (
                            <span
                              className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-mono text-[11px] font-bold ${
                                tracking.active_source === "DRIVER"
                                  ? "bg-blue-100 text-blue-800"
                                  : "bg-purple-100 text-purple-800"
                              }`}
                            >
                              <Shield className="h-3 w-3" />
                              {tracking.active_source}
                            </span>
                          ) : (
                            <span className="text-slate-400">None</span>
                          )}
                        </td>

                        <td className="py-3.5 px-4 font-mono text-[11px]">
                          {tracking.coordinates?.latitude ? (
                            <div>
                              <div>
                                {tracking.coordinates.latitude.toFixed(4)}, {tracking.coordinates.longitude.toFixed(4)}
                              </div>
                              <div className="text-slate-400">
                                {tracking.speed != null ? `${Math.round(tracking.speed * 3.6)} km/h` : "-- km/h"} •{" "}
                                {tracking.last_updated ? new Date(tracking.last_updated).toLocaleTimeString() : "--"}
                              </div>
                            </div>
                          ) : (
                            <span className="text-slate-400">No telemetry</span>
                          )}
                        </td>

                        <td className="py-3.5 px-4 text-right">
                          <div className="flex items-center justify-end gap-2">
                            {trip && (
                              <button
                                type="button"
                                onClick={() => {
                                  setAssignTrip(trip);
                                  setAssignMessage(null);
                                }}
                                className="inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                              >
                                <UserCheck className="h-3.5 w-3.5 text-navy-800" />
                                <span>Assign</span>
                              </button>
                            )}

                            {trip && (
                              <button
                                type="button"
                                onClick={() => {
                                  setTakeoverBus(item);
                                  const currentLat = tracking.coordinates?.latitude || 25.6120;
                                  const currentLon = tracking.coordinates?.longitude || 85.1440;
                                  setTakeoverLat(String(currentLat));
                                  setTakeoverLon(String(currentLon));
                                  setTakeoverSeq(String((tracking.operator_sequence_number || 0) + 1));
                                  setTakeoverMessage(null);
                                }}
                                className={`inline-flex items-center gap-1 rounded-lg px-2.5 py-1 text-xs font-semibold ${
                                  isTakeoverEligible
                                    ? "bg-orange-600 text-white hover:bg-orange-700 shadow-sm"
                                    : "border border-slate-300 bg-slate-50 text-slate-500 hover:bg-slate-100"
                                }`}
                              >
                                <Zap className="h-3.5 w-3.5" />
                                <span>Takeover GPS</span>
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Takeover Modal */}
        {takeoverBus && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/70 backdrop-blur-sm animate-fade-in">
            <div className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-2xl border border-slate-200 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div className="flex items-center gap-2">
                  <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-orange-100 text-orange-700">
                    <Zap className="h-5 w-5" />
                  </div>
                  <h3 className="font-display text-base font-bold text-slate-900">
                    Operator GPS Takeover
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={() => setTakeoverBus(null)}
                  className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                >
                  ✕
                </button>
              </div>

              {/* Takeover Governance Rules Callout */}
              <div className="rounded-xl border border-amber-200 bg-amber-50/70 p-3.5 text-xs text-amber-900 space-y-1">
                <div className="font-bold flex items-center gap-1.5 text-amber-950">
                  <ShieldAlert className="h-4 w-4 text-amber-700" />
                  Takeover Priority Rules:
                </div>
                <p>
                  1. Operator takeover is authorized when driver signal is <strong>STALE (&gt;60s)</strong> or <strong>OFFLINE</strong>.
                </p>
                <p>
                  2. <strong>Driver Priority:</strong> If driver resumes broadcasting, driver coordinates automatically regain priority and supersede operator telemetry.
                </p>
              </div>

              {takeoverMessage && (
                <div
                  className={`rounded-xl border p-3 text-xs ${
                    takeoverMessage.type === "success"
                      ? "border-emerald-300 bg-emerald-50 text-emerald-900"
                      : "border-rose-300 bg-rose-50 text-rose-900"
                  }`}
                >
                  {takeoverMessage.text}
                </div>
              )}

              <form onSubmit={handleTakeoverSubmit} className="space-y-3.5 text-xs">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Target Trip</label>
                  <input
                    type="text"
                    readOnly
                    value={`Trip #${takeoverBus.active_trip?.id}: ${takeoverBus.active_trip?.source} → ${takeoverBus.active_trip?.destination}`}
                    className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-slate-600 font-medium"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block font-bold text-slate-700 mb-1">Latitude</label>
                    <input
                      type="number"
                      step="0.000001"
                      required
                      value={takeoverLat}
                      onChange={(e) => setTakeoverLat(e.target.value)}
                      className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-slate-900 font-mono focus:border-emerald-500 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="block font-bold text-slate-700 mb-1">Longitude</label>
                    <input
                      type="number"
                      step="0.000001"
                      required
                      value={takeoverLon}
                      onChange={(e) => setTakeoverLon(e.target.value)}
                      className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-slate-900 font-mono focus:border-emerald-500 focus:outline-none"
                    />
                  </div>
                </div>

                <div>
                  <label className="block font-bold text-slate-700 mb-1">
                    Operator Monotonic Sequence Number
                  </label>
                  <input
                    type="number"
                    min="1"
                    required
                    value={takeoverSeq}
                    onChange={(e) => setTakeoverSeq(e.target.value)}
                    className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-slate-900 font-mono focus:border-emerald-500 focus:outline-none"
                  />
                  <p className="mt-1 text-[11px] text-slate-500">
                    Must strictly exceed previous operator sequence number.
                  </p>
                </div>

                <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setTakeoverBus(null)}
                    className="rounded-xl border border-slate-300 px-4 py-2 font-semibold text-slate-700 hover:bg-slate-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={takeoverLoading}
                    className="rounded-xl bg-orange-600 px-4 py-2 font-bold text-white hover:bg-orange-700 disabled:opacity-50"
                  >
                    {takeoverLoading ? "Ingesting..." : "Confirm GPS Takeover"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Driver Assignment Modal */}
        {assignTrip && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/70 backdrop-blur-sm animate-fade-in">
            <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-2xl border border-slate-200 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                <div className="flex items-center gap-2">
                  <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-100 text-emerald-700">
                    <UserCheck className="h-5 w-5" />
                  </div>
                  <h3 className="font-display text-base font-bold text-slate-900">
                    Assign Driver to Trip #{assignTrip.id}
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={() => setAssignTrip(null)}
                  className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                >
                  ✕
                </button>
              </div>

              {assignMessage && (
                <div
                  className={`rounded-xl border p-3 text-xs ${
                    assignMessage.type === "success"
                      ? "border-emerald-300 bg-emerald-50 text-emerald-900"
                      : "border-rose-300 bg-rose-50 text-rose-900"
                  }`}
                >
                  {assignMessage.text}
                </div>
              )}

              <form onSubmit={handleAssignDriver} className="space-y-4 text-xs">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Route &amp; Date</label>
                  <div className="rounded-xl bg-slate-50 p-2.5 text-slate-700 font-medium border border-slate-200">
                    {assignTrip.source} → {assignTrip.destination} ({assignTrip.travel_date} at {assignTrip.departure_time})
                  </div>
                </div>

                <div>
                  <label htmlFor="driver-id" className="block font-bold text-slate-700 mb-1">
                    Driver User ID
                  </label>
                  <input
                    id="driver-id"
                    type="number"
                    min="1"
                    required
                    placeholder="Enter driver user ID (e.g. 2 or 3)"
                    value={driverIdInput}
                    onChange={(e) => setDriverIdInput(e.target.value)}
                    className="w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-slate-900 font-mono focus:border-emerald-500 focus:outline-none"
                  />
                  <p className="mt-1 text-[11px] text-slate-500">
                    User must have the DRIVER role. Existing active assignment for this trip will be updated.
                  </p>
                </div>

                <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-100">
                  <button
                    type="button"
                    onClick={() => setAssignTrip(null)}
                    className="rounded-xl border border-slate-300 px-4 py-2 font-semibold text-slate-700 hover:bg-slate-50"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={assignLoading}
                    className="rounded-xl bg-navy-950 px-4 py-2 font-bold text-white hover:bg-emerald-700 disabled:opacity-50"
                  >
                    {assignLoading ? "Assigning..." : "Assign Driver"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
