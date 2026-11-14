import { BarChart3, Users, Ticket, Bus, TrendingUp, AlertTriangle } from "lucide-react";

export default function AdminAnalyticsPanel({ overview, loading, onCancelTrip }) {
  if (loading && !overview) {
    return (
      <div className="space-y-4" aria-busy="true" aria-label="Loading live operations analytics">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div className="h-24 animate-pulse rounded-2xl border border-navy-900/10 bg-white" />
          <div className="h-24 animate-pulse rounded-2xl border border-navy-900/10 bg-white" />
          <div className="h-24 animate-pulse rounded-2xl border border-navy-900/10 bg-white" />
          <div className="h-24 animate-pulse rounded-2xl border border-navy-900/10 bg-white" />
        </div>
        <div className="h-56 animate-pulse rounded-2xl border border-navy-900/10 bg-white" />
      </div>
    );
  }

  const s = overview?.summary || {};
  const popularRoutes = overview?.popular_routes || [];
  const trends = overview?.booking_trends || [];
  const occupancy = overview?.trip_occupancy || [];
  const recentBookings = overview?.recent_bookings || [];

  const maxTrendBookings = Math.max(
    1,
    ...trends.map((d) => (d.confirmed_bookings || 0) + (d.cancelled_bookings || 0))
  );
  const maxRouteBookings = Math.max(1, ...popularRoutes.map((r) => r.confirmed_bookings || 0));

  return (
    <div className="space-y-6">
      <div className="flex items-start gap-2.5 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-xs text-amber-900">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" />
        <span>
          <strong>Demo Revenue &amp; Refund Ledger:</strong>{" "}
          {s.revenue_disclaimer ||
            "Revenue and refund totals represent simulated booking figures only; no live payments are processed."}
        </span>
      </div>

      {/* Primary KPI Grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-2xl border border-navy-900/10 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wide text-navy-900/55">
            <span>Total Bookings</span>
            <Ticket className="h-4 w-4 text-navy-700" />
          </div>
          <p className="mt-2 text-2xl font-bold text-navy-950">{s.total_bookings ?? 0}</p>
          <p className="mt-1 text-xs text-navy-900/65">
            {s.confirmed_bookings ?? 0} confirmed • {s.cancelled_bookings ?? 0} cancelled
          </p>
        </div>

        <div className="rounded-2xl border border-navy-900/10 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wide text-navy-900/55">
            <span>Demo Net Revenue</span>
            <TrendingUp className="h-4 w-4 text-emerald-700" />
          </div>
          <p className="mt-2 text-2xl font-bold text-navy-950">
            ₹{Number(s.demo_net_revenue || 0).toLocaleString("en-IN")}
          </p>
          <p className="mt-1 text-xs text-navy-900/65">
            Demo refunded: ₹{Number(s.demo_refunded_amount || 0).toLocaleString("en-IN")} (
            {s.pending_refunds_count ?? 0} pending)
          </p>
        </div>

        <div className="rounded-2xl border border-navy-900/10 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wide text-navy-900/55">
            <span>Available Seats</span>
            <Bus className="h-4 w-4 text-navy-700" />
          </div>
          <p className="mt-2 text-2xl font-bold text-navy-950">
            {Number(s.available_seats || 0).toLocaleString("en-IN")}
          </p>
          <p className="mt-1 text-xs text-navy-900/65">
            {s.occupancy_rate ?? 0}% filled of {Number(s.total_seats || 0).toLocaleString("en-IN")}{" "}
            seats
          </p>
        </div>

        <div className="rounded-2xl border border-navy-900/10 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wide text-navy-900/55">
            <span>User Statistics</span>
            <Users className="h-4 w-4 text-navy-700" />
          </div>
          <p className="mt-2 text-2xl font-bold text-navy-950">{s.total_users ?? 0} Passengers</p>
          <p className="mt-1 text-xs text-navy-900/65">
            {s.active_users ?? 0} active • {s.suspended_users ?? 0} suspended •{" "}
            {s.verified_users ?? 0} verified ({s.new_users_7d ?? 0} new 7d)
          </p>
        </div>
      </div>

      {/* Network Counters */}
      <div className="grid gap-4 sm:grid-cols-4">
        {[
          { label: "Searchable Cities", value: `${s.active_cities ?? 0} / ${s.total_cities ?? 0} active` },
          { label: "Configured Routes", value: s.total_routes ?? 0 },
          { label: "Registered Buses", value: `${s.active_buses ?? 0} / ${s.total_buses ?? 0} active` },
          {
            label: "Schedules & Trips",
            value: `${s.total_schedules ?? 0} sched / ${s.total_trips ?? 0} trips`,
          },
        ].map((stat) => (
          <div
            key={stat.label}
            className="rounded-2xl border border-navy-900/10 bg-cream-50/80 px-4 py-3.5 shadow-sm transition hover:border-emerald-600/30 hover:bg-white"
          >
            <p className="text-[11px] font-bold uppercase tracking-wider text-navy-900/55">
              {stat.label}
            </p>
            <p className="mt-1 font-mono text-base font-bold text-navy-950">{stat.value}</p>
          </div>
        ))}
      </div>

      {/* Popular Routes & 14-Day Booking Trends */}
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="min-w-0 rounded-3xl border border-navy-900/10 bg-white p-6 shadow-card">
          <div className="mb-5 flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <div className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-cream-100 text-navy-950">
                <BarChart3 className="h-4 w-4 text-emerald-700" />
              </div>
              <h2 className="font-serif text-xl font-normal tracking-tight text-navy-950">
                Popular Routes
              </h2>
            </div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-navy-900/45">
              Top Corridors
            </span>
          </div>
          {popularRoutes.length === 0 ? (
            <p className="text-sm text-navy-900/60">No confirmed route bookings yet.</p>
          ) : (
            <div className="space-y-3.5">
              {popularRoutes.map((r) => {
                const pct = Math.max(8, Math.round((r.confirmed_bookings / maxRouteBookings) * 100));
                return (
                  <div key={r.route_id} className="space-y-1.5 text-xs">
                    <div className="flex items-center justify-between gap-2 font-semibold text-navy-950">
                      <span>{r.route_name}</span>
                      <span className="font-mono text-[11px] text-navy-900/75">
                        {r.confirmed_bookings} bookings • Demo ₹
                        {r.demo_revenue.toLocaleString("en-IN")}
                      </span>
                    </div>
                    <div className="h-2.5 w-full overflow-hidden rounded-full bg-cream-100">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-navy-950 to-emerald-700 transition-all duration-500"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="min-w-0 rounded-3xl border border-navy-900/10 bg-white p-6 shadow-card">
          <div className="mb-5 flex items-center justify-between gap-2">
            <h2 className="font-serif text-xl font-normal tracking-tight text-navy-950">
              14-Day Booking Trend
            </h2>
            <span className="rounded-full border border-navy-900/10 bg-cream-50 px-2.5 py-0.5 font-mono text-[10px] font-bold text-navy-900/65">
              Asia/Kolkata IST
            </span>
          </div>
          <div className="flex h-36 items-end gap-1 border-b border-navy-900/10 pb-2 sm:gap-1.5">
            {trends.map((day) => {
              const totalDay = (day.confirmed_bookings || 0) + (day.cancelled_bookings || 0);
              const heightPct =
                totalDay === 0 ? 4 : Math.max(12, Math.round((totalDay / maxTrendBookings) * 100));
              return (
                <div
                  key={day.date}
                  title={`${day.date}: ${day.confirmed_bookings} confirmed, ${day.cancelled_bookings} cancelled (Demo ₹${day.demo_revenue})`}
                  className="group flex h-full flex-1 flex-col items-center justify-end gap-1"
                >
                  <span className="font-mono text-[10px] font-semibold text-navy-900/70">
                    {totalDay > 0 ? totalDay : ""}
                  </span>
                  <div
                    className={`w-full rounded-t-md transition-all ${
                      totalDay > 0
                        ? "bg-emerald-600 group-hover:bg-brass-500"
                        : "bg-navy-900/10"
                    }`}
                    style={{ height: `${heightPct}%` }}
                  />
                </div>
              );
            })}
          </div>
          <div className="mt-2.5 flex justify-between font-mono text-[10px] text-navy-900/55">
            <span>{trends[0]?.date || ""}</span>
            <span className="font-sans">Hover bars for daily breakdown</span>
            <span>{trends[trends.length - 1]?.date || ""}</span>
          </div>
        </div>
      </div>

      {/* Upcoming Trip Occupancy & Recent Bookings */}
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="min-w-0 rounded-3xl border border-navy-900/10 bg-white p-6 shadow-card">
          <h2 className="mb-4 font-serif text-xl font-normal tracking-tight text-navy-950">
            Upcoming Trip Occupancy
          </h2>
          <div className="space-y-3">
            {occupancy.map((t) => (
              <div
                key={t.trip_id}
                className="rounded-2xl border border-navy-900/10 bg-cream-50/75 p-4 transition hover:border-navy-900/20 hover:bg-white"
              >
                <div className="flex items-center justify-between gap-2 text-sm">
                  <span className="font-bold text-navy-950">{t.route_name}</span>
                  <span className="font-mono text-xs text-navy-900/75">
                    {t.travel_date} • {t.departure_time}
                  </span>
                </div>
                <div className="mt-1.5 flex flex-wrap items-center justify-between gap-2 text-xs text-navy-900/65">
                  <span>
                    {t.operator_name} ({t.bus_number} • {t.seat_layout})
                  </span>
                  <div className="flex items-center gap-3">
                    <span className="rounded-full bg-navy-900/5 px-2.5 py-0.5 font-mono text-[11px] font-semibold text-navy-900">
                      {t.occupied_seats}/{t.total_seats} ({t.occupancy_rate}%)
                    </span>
                    <button
                      type="button"
                      onClick={() => onCancelTrip(t.trip_id)}
                      className="font-semibold text-red-700 hover:underline"
                    >
                      Cancel Trip
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="min-w-0 rounded-3xl border border-navy-900/10 bg-white p-6 shadow-card">
          <h2 className="mb-4 font-serif text-xl font-normal tracking-tight text-navy-950">
            Recent Reservations
          </h2>
          <div className="space-y-3">
            {recentBookings.map((b) => (
              <div
                key={b.pnr}
                className="flex items-center justify-between gap-3 rounded-2xl border border-navy-900/10 bg-cream-50/75 p-4 text-sm transition hover:border-navy-900/20 hover:bg-white"
              >
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-md bg-navy-950 px-2 py-0.5 font-mono text-xs font-bold text-cream-50">
                      {b.pnr}
                    </span>
                    <span
                      className={`rounded-full px-2.5 py-0.5 text-[11px] font-bold ${
                        b.status === "CONFIRMED"
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-red-100 text-red-800"
                      }`}
                    >
                      {b.status}
                    </span>
                    {b.refund_status && b.refund_status !== "NONE" ? (
                      <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-[10px] font-bold text-amber-800">
                        Refund: {b.refund_status}
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-1 truncate text-xs text-navy-900/75">
                    {b.passenger_name} • {b.passenger_email} • Seat{" "}
                    <span className="font-mono font-semibold">{b.seat_number}</span>
                  </p>
                </div>
                <div className="shrink-0 font-mono text-base font-bold text-emerald-700">
                  ₹{Number(b.total_fare).toFixed(0)}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
