import { ArrowRight, Clock, MapPin, Shield, Users } from "lucide-react";
import { Link } from "react-router-dom";

export default function TripCard({ trip }) {
  const soldOut = trip.available_seats <= 0;
  const seatQs = new URLSearchParams();
  if (trip.matched_boarding_stop_id) {
    seatQs.set("boarding_stop_id", String(trip.matched_boarding_stop_id));
  }
  if (trip.matched_drop_stop_id) {
    seatQs.set("drop_stop_id", String(trip.matched_drop_stop_id));
  }
  const seatLink = `/trips/${trip.id}/seats${seatQs.toString() ? `?${seatQs.toString()}` : ""}`;
  const busLabel = trip.bus_type ? trip.bus_type.replace(/_/g, " ") : "AC Coach";

  return (
    <article className="group relative overflow-hidden rounded-2xl border border-cream-200 bg-white p-5 shadow-card transition-all duration-200 hover:-translate-y-0.5 hover:border-emerald-400/70 hover:shadow-editorial">
      {/* Subtle accent rail */}
      <div
        className={`absolute bottom-0 left-0 top-0 w-1.5 ${
          soldOut ? "bg-rose-400" : "bg-gradient-to-b from-emerald-500 to-navy-900"
        }`}
      />

      <div className="flex flex-col justify-between gap-5 pl-2 md:flex-row md:items-center">
        <div className="space-y-3.5">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-display text-lg font-extrabold text-navy-950">
              {trip.operator_name}
            </h3>
            <span className="rounded-lg border border-cream-200 bg-cream-100 px-2.5 py-0.5 font-mono text-[11px] font-bold text-navy-800">
              {trip.bus_number}
            </span>
            <span className="rounded-full bg-navy-950/5 px-2.5 py-0.5 text-[11px] font-semibold text-navy-800">
              {busLabel} • {trip.seat_layout || "2+2"}
            </span>
            <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 font-mono text-[11px] font-semibold text-emerald-700">
              <Shield className="h-3 w-3" />
              {trip.travel_date}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-4 text-sm sm:gap-6">
            <div>
              <p className="font-mono text-2xl font-bold tabular-nums text-navy-950">
                {trip.departure_time}
              </p>
              <p className="mt-0.5 flex items-center gap-1 text-xs font-semibold text-slate-600">
                <MapPin className="h-3.5 w-3.5 text-emerald-600" />
                {trip.source}
              </p>
            </div>

            <div className="flex flex-col items-center px-1">
              <span className="flex items-center gap-1 font-mono text-[11px] font-semibold text-slate-500">
                <Clock className="h-3 w-3 text-brass-600" />
                {trip.duration_display}
              </span>
              <div className="my-1.5 flex items-center gap-1">
                <span className="h-2 w-2 rounded-full bg-emerald-500" />
                <span className="h-px w-16 border-t border-dashed border-navy-900/30 sm:w-20" />
                <ArrowRight className="h-3.5 w-3.5 text-navy-800" />
              </div>
              <span className="text-[10px] font-medium text-slate-400">
                {trip.stops?.length || 2} stops
              </span>
            </div>

            <div>
              <p className="font-mono text-2xl font-bold tabular-nums text-navy-950">
                {trip.arrival_time}
              </p>
              <p className="mt-0.5 flex items-center gap-1 text-xs font-semibold text-slate-600">
                <MapPin className="h-3.5 w-3.5 text-navy-700" />
                {trip.destination}
              </p>
            </div>
          </div>
        </div>

        <div className="flex flex-row items-center justify-between gap-6 border-t border-cream-200 pt-4 md:flex-col md:items-end md:border-l md:border-t-0 md:border-dashed md:pl-6 md:pt-0">
          <div className="text-left md:text-right">
            <p className="font-mono text-[10px] font-semibold uppercase tracking-widest text-slate-400">
              Confirmed Fare
            </p>
            <p className="font-display text-3xl font-extrabold tabular-nums text-navy-950">
              ₹{Number(trip.base_fare).toFixed(0)}
            </p>
            <p
              className={`mt-1 inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                soldOut
                  ? "bg-rose-50 text-rose-700"
                  : trip.available_seats <= 6
                    ? "bg-brass-50 text-brass-600"
                    : "bg-emerald-50 text-emerald-700"
              }`}
            >
              <Users className="h-3.5 w-3.5" />
              {soldOut
                ? "Sold out"
                : `${trip.available_seats} of ${trip.total_seats} seats left`}
            </p>
          </div>

          <Link
            to={seatLink}
            className={`inline-flex items-center justify-center gap-2 rounded-xl px-5 py-3 text-sm font-bold transition-all ${
              soldOut
                ? "pointer-events-none bg-slate-200 text-slate-500"
                : "bg-navy-950 text-white shadow-sm hover:bg-emerald-600 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2"
            }`}
          >
            <span>{soldOut ? "Full" : "Select Seats"}</span>
            {!soldOut && <ArrowRight className="h-4 w-4" />}
          </Link>
        </div>
      </div>
    </article>
  );
}
