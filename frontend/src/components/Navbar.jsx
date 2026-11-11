import { Bus, ShieldCheck, Ticket, LayoutDashboard } from "lucide-react";
import { Link, NavLink } from "react-router-dom";

export default function Navbar() {
  const navLinkClass = ({ isActive }) =>
    `inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
      isActive
        ? "bg-white/15 text-emerald-300"
        : "text-slate-200 hover:bg-white/10 hover:text-white"
    }`;

  return (
    <header className="sticky top-0 z-30 border-b border-navy-800/80 bg-navy-900/95 text-white backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3.5 sm:px-6">
        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-400 to-emerald-600 text-navy-950 shadow-md shadow-emerald-950/30 transition-transform group-hover:scale-105">
            <Bus className="h-5 w-5 stroke-[2.2]" />
          </div>
          <div>
            <span className="font-display text-lg font-bold tracking-tight text-white">
              Bus<span className="text-emerald-400">Reserve</span>
            </span>
            <p className="hidden text-[11px] font-medium tracking-wide text-slate-300 sm:block">
              Cloud-Native Intercity Booking
            </p>
          </div>
        </Link>

        <nav className="flex items-center gap-1 sm:gap-2">
          <NavLink to="/search" className={navLinkClass}>
            <Bus className="h-4 w-4" />
            <span>Trips</span>
          </NavLink>
          <NavLink to="/pnr" className={navLinkClass}>
            <Ticket className="h-4 w-4" />
            <span>Check PNR</span>
          </NavLink>
          <NavLink to="/admin" className={navLinkClass}>
            <LayoutDashboard className="h-4 w-4" />
            <span className="hidden sm:inline">Admin Demo</span>
            <span className="sm:hidden">Admin</span>
          </NavLink>
          <span className="ml-2 hidden items-center gap-1.5 rounded-full border border-emerald-400/30 bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-300 md:inline-flex">
            <ShieldCheck className="h-3.5 w-3.5" />
            Atomic Seat Lock
          </span>
        </nav>
      </div>
    </header>
  );
}
