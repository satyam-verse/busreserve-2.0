import { ArrowLeft, Bus, Home, Search, Ticket } from "lucide-react";
import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <div className="flex min-h-[75vh] flex-col items-center justify-center px-4 py-16 text-center">
      <div className="relative mb-6">
        <div className="flex h-20 w-20 items-center justify-center rounded-3xl bg-navy-950 text-white shadow-xl shadow-navy-950/20">
          <Bus className="h-10 w-10 text-emerald-400 stroke-[2.2]" />
        </div>
        <span className="absolute -bottom-1 -right-1 flex h-7 w-7 items-center justify-center rounded-full border-2 border-white bg-brass-500 font-mono text-xs font-bold text-navy-950">
          ?
        </span>
      </div>

      <span className="rounded-full bg-emerald-50 px-3 py-1 font-mono text-xs font-bold text-emerald-800 border border-emerald-200">
        404 • ROUTE NOT FOUND
      </span>

      <h1 className="mt-4 font-display text-3xl font-extrabold tracking-tight text-navy-950 sm:text-4xl">
        This Bus Stop Doesn't Exist
      </h1>

      <p className="mt-2 max-w-md text-sm text-slate-600">
        The destination or page you're trying to reach may have been moved, rescheduled, or
        never existed on the BusReserve network.
      </p>

      <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
        <Link
          to="/"
          className="inline-flex items-center gap-2 rounded-xl bg-navy-950 px-5 py-3 text-sm font-bold text-white shadow-editorial transition hover:bg-emerald-700"
        >
          <Home className="h-4 w-4" />
          <span>Return to Homepage</span>
        </Link>

        <Link
          to="/search"
          className="inline-flex items-center gap-2 rounded-xl border border-navy-900/15 bg-white px-5 py-3 text-sm font-semibold text-navy-950 shadow-xs transition hover:bg-cream-100"
        >
          <Search className="h-4 w-4 text-emerald-700" />
          <span>Browse Active Trips</span>
        </Link>

        <Link
          to="/pnr"
          className="inline-flex items-center gap-2 rounded-xl border border-navy-900/15 bg-white px-5 py-3 text-sm font-semibold text-navy-950 shadow-xs transition hover:bg-cream-100"
        >
          <Ticket className="h-4 w-4 text-brass-600" />
          <span>Track PNR</span>
        </Link>
      </div>
    </div>
  );
}
