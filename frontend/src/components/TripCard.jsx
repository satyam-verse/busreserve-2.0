import { ArrowRight, Clock, MapPin, Shield, Users } from "lucide-react";
import { Link } from "react-router-dom";

export default function TripCard({ trip }) {
  const soldOut = trip.available_seats <= 0;

  return (
    <div className="group rounded-2xl border border-cream-200 bg-white p-5 shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:border-emerald-300 hover:shadow-md">
      <div className="flex flex-col justify-between gap-5 md:flex-row md:items-center">
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2.5">
            <h3 className="font-display text-lg font-bold text-navy-900">
              {trip.operator_name}
            </h3>
            <span className="rounded-full bg-cream-100 px-2.5 py-0.5 text-xs font-semibold text-navy-800">
              {trip.bus_number}
            </span>
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-medium text-emerald-700">
              <Shield className="h-3 w-3" />
              {trip.travel_date}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-4 text-sm">
            <div>
              <p className="text-xl font-bold tabular-nums text-navy-900">
                {trip.departure_time}
              </p>
              <p className="flex items-center gap-1 text-xs font-medium text-slate-500">
                <MapPin className="h-3 w-3 text-emerald-600" />
                {trip.source}
              </p>
            </div>

            <div className="flex flex-col items-center px-2">
              <span className="flex items-center gap-1 text-xs font-medium text-slate-500">
                <Clock className="h-3 w-3" />
                {trip.duration_display}
              </span>
              <div className="my-1 flex items-center gap-1 text-slate-300">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                <span className="h-px w-14 bg-slate-300" />
                <ArrowRight className="h-3.5 w-3.5 text-navy-700" />
              </div>
            </div>

            <div>
              <p className="text-xl font-bold tabular-nums text-navy-900">
                {trip.arrival_time}
              </p>
              <p className="flex items-center gap-1 text-xs font-medium text-slate-500">
                <MapPin className="h-3 w-3 text-navy-700" />
                {trip.destination}
              </p>
            </div>
          </div>
        </div>

        <div className="flex flex-row items-center justify-between gap-6 border-t border-cream-100 pt-4 md:flex-col md:items-end md:border-t-0 md:pt-0">
          <div className="text-left md:text-right">
            <p className="text-xs font-medium uppercase tracking-wider text-slate-400">
              Fare per seat
            </p>
            <p className="font-display text-2xl font-extrabold tabular-nums text-navy-900">
              ₹{Number(trip.base_fare).toFixed(0)}
            </p>
            <p
              className={`mt-0.5 inline-flex items-center gap-1 text-xs font-semibold ${
                soldOut ? "text-rose-600" : "text-emerald-700"
              }`}
            >
              <Users className="h-3.5 w-3.5" />
              {soldOut
                ? "Sold out"
                : `${trip.available_seats} of ${trip.total_seats} seats left`}
            </p>
          </div>

          <Link
            to={`/trips/${trip.id}/seats`}
            className={`inline-flex items-center justify-center gap-2 rounded-xl px-5 py-2.5 text-sm font-semibold transition-all ${
              soldOut
                ? "pointer-events-none bg-slate-200 text-slate-500"
                : "bg-emerald-600 text-white shadow-sm hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2"
            }`}
          >
            <span>{soldOut ? "Full" : "Select Seats"}</span>
            {!soldOut && <ArrowRight className="h-4 w-4" />}
          </Link>
        </div>
      </div>
    </div>
  );
}
