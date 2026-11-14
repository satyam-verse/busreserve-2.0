import { Bus, ShieldCheck, Sparkles, Ticket } from "lucide-react";
import { Link } from "react-router-dom";

export default function Footer() {
  return (
    <footer className="mt-auto border-t border-white/10 bg-navy-950 text-slate-300">
      <div className="mx-auto max-w-7xl px-4 py-10 sm:px-6">
        <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
          <div className="space-y-3 lg:col-span-2">
            <div className="flex items-center gap-2.5">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-500 text-navy-950">
                <Bus className="h-4 w-4 stroke-[2.2]" />
              </div>
              <div>
                <span className="font-display text-base font-extrabold text-white">
                  Bus<span className="text-emerald-400">Reserve</span> 2.0
                </span>
                <p className="font-mono text-[10px] uppercase tracking-widest text-slate-400">
                  Asia/Kolkata (IST) • Real-Time Ticketing
                </p>
              </div>
            </div>
            <p className="max-w-md text-xs leading-relaxed text-slate-400">
              Intercity coach ticketing built with real-time seat protection, 90-day live travel
              schedules, role-separated operations, and an always-available AI Travel Concierge.
            </p>
            <div className="flex flex-wrap items-center gap-3 text-[11px] font-medium text-slate-300">
              <span className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-2.5 py-1">
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                Zero Double-Booking Guarantee
              </span>
              <span className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-2.5 py-1">
                <Sparkles className="h-3.5 w-3.5 text-brass-400" />
                Smart AI Travel Concierge
              </span>
            </div>
          </div>

          <div className="space-y-2.5">
            <h3 className="font-mono text-[11px] font-semibold uppercase tracking-widest text-slate-400">
              Passenger Services
            </h3>
            <ul className="space-y-2 text-xs">
              <li>
                <Link to="/search" className="text-slate-300 transition hover:text-emerald-300">
                  Browse Live Schedules
                </Link>
              </li>
              <li>
                <Link to="/pnr" className="inline-flex items-center gap-1 text-slate-300 transition hover:text-emerald-300">
                  <Ticket className="h-3 w-3" />
                  Manage / Check PNR
                </Link>
              </li>
              <li>
                <Link to="/assistant" className="text-slate-300 transition hover:text-emerald-300">
                  AI Travel Concierge
                </Link>
              </li>
              <li>
                <Link to="/login" className="text-slate-300 transition hover:text-emerald-300">
                  Passenger Sign In &amp; Dashboard
                </Link>
              </li>
            </ul>
          </div>

          <div className="space-y-2.5">
            <h3 className="font-mono text-[11px] font-semibold uppercase tracking-widest text-slate-400">
              Operations &amp; Security
            </h3>
            <ul className="space-y-2 text-xs">
              <li>
                <Link to="/admin/login" className="text-slate-300 transition hover:text-emerald-300">
                  Admin Control Centre
                </Link>
              </li>
              <li>
                <Link to="/register" className="text-slate-300 transition hover:text-emerald-300">
                  Create Passenger Account
                </Link>
              </li>
              <li>
                <Link to="/forgot-password" className="text-slate-300 transition hover:text-emerald-300">
                  Password Recovery
                </Link>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-8 flex flex-col items-center justify-between gap-3 border-t border-white/10 pt-5 text-[11px] text-slate-400 sm:flex-row">
          <p>BusReserve 2.0 — Cloud Deployment, CI/CD &amp; Full-Stack Assessment Showcase.</p>
          <p className="font-mono text-brass-400">
            Demo booking &amp; refund workflows only — no real payments processed.
          </p>
        </div>
      </div>
    </footer>
  );
}
