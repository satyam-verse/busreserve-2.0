import { Activity, Bus, RefreshCw, ShieldAlert, Ticket, Users } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { busApi } from "../services/api";

export default function AdminOverviewPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadOverview = useCallback(async () => {
    try {
      setLoading(true);
      setError("");
      const resp = await busApi.getAdminOverview();
      setData(resp);
    } catch (err) {
      setError(err.message || "Failed to load operational overview.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadOverview();
  }, [loadOverview]);

  const summary = data?.summary;

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-bold text-navy-900">
            Operations Overview
          </h1>
          <p className="text-sm text-slate-500">
            Live trip capacity, seat occupancy, and masked booking telemetry
          </p>
        </div>
        <button
          type="button"
          onClick={loadOverview}
          className="inline-flex items-center gap-2 rounded-xl border border-cream-200 bg-white px-4 py-2 text-sm font-semibold text-navy-900 shadow-sm transition hover:bg-cream-50"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          <span>Refresh</span>
        </button>
      </div>

      <div className="flex items-start gap-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-xs font-medium text-amber-900">
        <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0 text-amber-600" />
        <div>
          <p className="font-bold">Demo-Only Local Operational View (No Auth)</p>
          <p className="mt-0.5 text-amber-800">
            This demonstration dashboard intentionally masks passenger names, emails, and omits
            phone numbers so private customer data is never exposed publicly.
          </p>
        </div>
      </div>

      {error && (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-800">
          {error}
        </div>
      )}

      {summary && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-2xl border border-cream-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-slate-400">
              <span>Scheduled Trips</span>
              <Bus className="h-4 w-4 text-emerald-600" />
            </div>
            <p className="mt-2 font-display text-3xl font-extrabold text-navy-900">
              {summary.total_trips}
            </p>
          </div>

          <div className="rounded-2xl border border-cream-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-slate-400">
              <span>Total Bookings</span>
              <Ticket className="h-4 w-4 text-navy-700" />
            </div>
            <p className="mt-2 font-display text-3xl font-extrabold text-navy-900">
              {summary.total_bookings}
            </p>
            <p className="mt-1 text-xs text-slate-500">
              {summary.confirmed_bookings} confirmed • {summary.cancelled_bookings} cancelled
            </p>
          </div>

          <div className="rounded-2xl border border-cream-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-slate-400">
              <span>Occupied Seats</span>
              <Users className="h-4 w-4 text-emerald-600" />
            </div>
            <p className="mt-2 font-display text-3xl font-extrabold text-navy-900">
              {summary.occupied_seats}
            </p>
            <p className="mt-1 text-xs text-slate-500">
              of {summary.total_seats} total fleet seats
            </p>
          </div>

          <div className="rounded-2xl border border-cream-200 bg-white p-5 shadow-sm">
            <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-slate-400">
              <span>Fleet Occupancy</span>
              <Activity className="h-4 w-4 text-emerald-600" />
            </div>
            <p className="mt-2 font-display text-3xl font-extrabold text-emerald-700">
              {summary.occupancy_rate}%
            </p>
            <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-cream-100">
              <div
                className="h-full rounded-full bg-emerald-500"
                style={{ width: `${Math.min(summary.occupancy_rate, 100)}%` }}
              />
            </div>
          </div>
        </div>
      )}

      {data && (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          <div className="rounded-2xl border border-cream-200 bg-white p-5 shadow-sm lg:col-span-6">
            <h2 className="mb-4 font-display text-lg font-bold text-navy-900">
              Recent Booking Records (Masked PII)
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-cream-200 text-slate-400 uppercase">
                    <th className="py-2 pr-3">PNR</th>
                    <th className="py-2 pr-3">Route</th>
                    <th className="py-2 pr-3">Seat</th>
                    <th className="py-2 pr-3">Passenger</th>
                    <th className="py-2">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-cream-100">
                  {data.recent_bookings.map((row) => (
                    <tr key={row.pnr} className="hover:bg-cream-50">
                      <td className="py-2.5 pr-3 font-mono font-bold text-navy-900">{row.pnr}</td>
                      <td className="py-2.5 pr-3 text-slate-600">{row.route_name}</td>
                      <td className="py-2.5 pr-3 font-semibold">{row.seat_number}</td>
                      <td className="py-2.5 pr-3 text-slate-600">
                        {row.passenger_display}
                        <div className="text-[10px] text-slate-400">
                          {row.passenger_email_masked}
                        </div>
                      </td>
                      <td className="py-2.5">
                        <span
                          className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${
                            row.status === "CONFIRMED"
                              ? "bg-emerald-100 text-emerald-800"
                              : "bg-rose-100 text-rose-800"
                          }`}
                        >
                          {row.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="rounded-2xl border border-cream-200 bg-white p-5 shadow-sm lg:col-span-6">
            <h2 className="mb-4 font-display text-lg font-bold text-navy-900">
              Trip Seat Occupancy Summary
            </h2>
            <div className="max-h-96 space-y-3 overflow-y-auto pr-1">
              {data.trip_occupancy.slice(0, 12).map((item) => (
                <div
                  key={item.trip_id}
                  className="rounded-xl border border-cream-100 bg-cream-50 p-3 text-xs"
                >
                  <div className="flex items-center justify-between font-semibold text-navy-900">
                    <span>{item.route_name}</span>
                    <span>
                      {item.occupied_seats}/{item.total_seats} ({item.occupancy_rate}%)
                    </span>
                  </div>
                  <p className="mt-0.5 text-[11px] text-slate-500">
                    {item.operator_name} • {item.travel_date} at {item.departure_time}
                  </p>
                  <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-cream-200">
                    <div
                      className="h-full rounded-full bg-emerald-600"
                      style={{ width: `${Math.min(item.occupancy_rate, 100)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
