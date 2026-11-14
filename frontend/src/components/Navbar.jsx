import {
  Bus,
  Clock,
  LayoutDashboard,
  LogIn,
  LogOut,
  Menu,
  ShieldCheck,
  Sparkles,
  Ticket,
  User,
  UserPlus,
  X,
  Navigation,
  Activity,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { getIstClockLabel } from "../utils/dates";
import NotificationBell from "./NotificationBell";

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [istClock, setIstClock] = useState(() => getIstClockLabel());

  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname, location.search]);

  useEffect(() => {
    const id = setInterval(() => setIstClock(getIstClockLabel()), 30000);
    return () => clearInterval(id);
  }, []);

  const navLinkClass = ({ isActive }) =>
    `inline-flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-medium transition-all ${
      isActive
        ? "bg-emerald-500/20 text-emerald-300 ring-1 ring-emerald-400/40"
        : "text-slate-200 hover:bg-white/10 hover:text-white"
    }`;

  async function handleLogout() {
    const wasAdmin = user?.role === "ADMIN";
    setMobileOpen(false);
    await logout();
    navigate(wasAdmin ? "/admin/login" : "/login", { replace: true });
  }

  return (
    <header className="sticky top-0 z-40 border-b border-white/10 bg-navy-950/95 text-white backdrop-blur-md">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-50 focus:rounded-xl focus:bg-emerald-500 focus:px-4 focus:py-2 focus:text-xs focus:font-bold focus:text-navy-950"
      >
        Skip to main content
      </a>

      <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <Link to="/" className="group flex items-center gap-3">
          <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-emerald-400 via-emerald-500 to-teal-600 text-navy-950 shadow-lg shadow-emerald-950/40 transition-transform group-hover:scale-105">
            <Bus className="h-5 w-5 stroke-[2.2]" />
            <span className="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full border-2 border-navy-950 bg-brass-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-display text-lg font-extrabold tracking-tight text-white">
                Bus<span className="text-emerald-400">Reserve</span>
              </span>
              <span className="rounded-md border border-brass-400/35 bg-brass-500/15 px-1.5 py-0.5 font-mono text-[10px] font-bold text-brass-400">
                2.0
              </span>
            </div>
            <p className="hidden text-[11px] font-medium tracking-wide text-slate-300/80 sm:block">
              Intercity Transit &amp; AI Concierge
            </p>
          </div>
        </Link>

        {/* Desktop Navigation */}
        <nav aria-label="Primary Navigation" className="hidden items-center gap-1 lg:flex lg:gap-1.5">
          <NavLink to="/search" className={navLinkClass}>
            <Bus className="h-4 w-4" />
            <span>Trips</span>
          </NavLink>
          <NavLink to="/pnr" className={navLinkClass}>
            <Ticket className="h-4 w-4" />
            <span>Check PNR</span>
          </NavLink>

          {!user ? (
            <>
              <NavLink to="/login" className={navLinkClass}>
                <LogIn className="h-4 w-4" />
                <span>Sign In</span>
              </NavLink>
              <NavLink
                to="/register"
                className={({ isActive }) =>
                  `inline-flex items-center gap-1.5 rounded-xl px-3.5 py-2 text-sm font-semibold transition-all ${
                    isActive
                      ? "bg-emerald-400 text-navy-950"
                      : "bg-emerald-500 text-navy-950 hover:bg-emerald-400"
                  }`
                }
              >
                <UserPlus className="h-4 w-4" />
                <span>Register</span>
              </NavLink>
              <NavLink to="/admin/login" className={navLinkClass}>
                <LayoutDashboard className="h-4 w-4" />
                <span>Admin</span>
              </NavLink>
            </>
          ) : user.role === "ADMIN" ? (
            <>
              <NavLink to="/admin" className={navLinkClass}>
                <LayoutDashboard className="h-4 w-4" />
                <span>Admin</span>
              </NavLink>
              <NavLink to="/driver" className={navLinkClass}>
                <Navigation className="h-4 w-4 text-emerald-400" />
                <span>Driver</span>
              </NavLink>
              <NavLink to="/operator" className={navLinkClass}>
                <Activity className="h-4 w-4 text-amber-400" />
                <span>Fleet</span>
              </NavLink>
              <NotificationBell />
              <button
                type="button"
                onClick={handleLogout}
                className="inline-flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-medium text-slate-200 transition-colors hover:bg-white/10 hover:text-white"
              >
                <LogOut className="h-4 w-4" />
                <span>Sign Out</span>
              </button>
            </>
          ) : user.role === "DRIVER" ? (
            <>
              <NavLink to="/driver" className={navLinkClass}>
                <Navigation className="h-4 w-4 text-emerald-400" />
                <span>Driver Console</span>
              </NavLink>
              <NotificationBell />
              <button
                type="button"
                onClick={handleLogout}
                className="inline-flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-medium text-slate-200 transition-colors hover:bg-white/10 hover:text-white"
              >
                <LogOut className="h-4 w-4" />
                <span>Sign Out</span>
              </button>
            </>
          ) : user.role === "OPERATOR" ? (
            <>
              <NavLink to="/operator" className={navLinkClass}>
                <Activity className="h-4 w-4 text-amber-400" />
                <span>Fleet Dashboard</span>
              </NavLink>
              <NotificationBell />
              <button
                type="button"
                onClick={handleLogout}
                className="inline-flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-medium text-slate-200 transition-colors hover:bg-white/10 hover:text-white"
              >
                <LogOut className="h-4 w-4" />
                <span>Sign Out</span>
              </button>
            </>
          ) : (
            <>
              <NavLink to="/assistant" className={navLinkClass}>
                <Sparkles className="h-4 w-4 text-brass-400" />
                <span>AI Assistant</span>
              </NavLink>
              <NavLink to="/dashboard" className={navLinkClass}>
                <User className="h-4 w-4" />
                <span>My Dashboard</span>
              </NavLink>
              <NotificationBell />
              <button
                type="button"
                onClick={handleLogout}
                className="inline-flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-medium text-slate-200 transition-colors hover:bg-white/10 hover:text-white"
              >
                <LogOut className="h-4 w-4" />
                <span>Sign Out</span>
              </button>
            </>
          )}

          <div className="ml-2 hidden items-center gap-2 border-l border-white/10 pl-3 xl:flex">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-white/5 px-2.5 py-1 font-mono text-[11px] font-medium text-slate-200">
              <Clock className="h-3 w-3 text-emerald-400" />
              {istClock} IST
            </span>
            <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-400/30 bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-300">
              <ShieldCheck className="h-3.5 w-3.5" />
              Atomic Lock
            </span>
          </div>
        </nav>

        {/* Mobile & Tablet Drawer Trigger */}
        <div className="flex items-center gap-2 lg:hidden">
          {user && <NotificationBell />}
          <span className="inline-flex items-center gap-1 rounded-full border border-white/15 bg-white/5 px-2 py-1 font-mono text-[10px] text-slate-200">
            <Clock className="h-3 w-3 text-emerald-400" />
            {istClock} IST
          </span>
          <button
            type="button"
            aria-label={mobileOpen ? "Close menu" : "Open menu"}
            aria-expanded={mobileOpen}
            onClick={() => setMobileOpen((prev) => !prev)}
            className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-white/15 bg-white/5 text-white transition hover:bg-white/15"
          >
            {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {/* Responsive Mobile Navigation Drawer */}
      {mobileOpen ? (
        <nav
          aria-label="Mobile Navigation"
          className="border-t border-white/10 bg-navy-950 px-4 py-4 lg:hidden"
        >
          <div className="flex flex-col gap-1.5">
            <NavLink to="/search" className={navLinkClass}>
              <Bus className="h-4 w-4" />
              <span>Search Trips</span>
            </NavLink>
            <NavLink to="/pnr" className={navLinkClass}>
              <Ticket className="h-4 w-4" />
              <span>Check PNR</span>
            </NavLink>

            {!user ? (
              <>
                <NavLink to="/login" className={navLinkClass}>
                  <LogIn className="h-4 w-4" />
                  <span>Passenger Sign In</span>
                </NavLink>
                <NavLink to="/register" className={navLinkClass}>
                  <UserPlus className="h-4 w-4" />
                  <span>Create Account</span>
                </NavLink>
                <NavLink to="/admin/login" className={navLinkClass}>
                  <LayoutDashboard className="h-4 w-4" />
                  <span>Admin Portal</span>
                </NavLink>
              </>
            ) : user.role === "ADMIN" ? (
              <>
                <NavLink to="/admin" className={navLinkClass}>
                  <LayoutDashboard className="h-4 w-4" />
                  <span>Admin Console</span>
                </NavLink>
                <NavLink to="/driver" className={navLinkClass}>
                  <Navigation className="h-4 w-4 text-emerald-400" />
                  <span>Driver Console</span>
                </NavLink>
                <NavLink to="/operator" className={navLinkClass}>
                  <Activity className="h-4 w-4 text-amber-400" />
                  <span>Fleet Dashboard</span>
                </NavLink>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="inline-flex items-center gap-2 rounded-xl px-3 py-2 text-left text-sm font-medium text-slate-200 hover:bg-white/10"
                >
                  <LogOut className="h-4 w-4" />
                  <span>Sign Out</span>
                </button>
              </>
            ) : user.role === "DRIVER" ? (
              <>
                <NavLink to="/driver" className={navLinkClass}>
                  <Navigation className="h-4 w-4 text-emerald-400" />
                  <span>Driver Console</span>
                </NavLink>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="inline-flex items-center gap-2 rounded-xl px-3 py-2 text-left text-sm font-medium text-slate-200 hover:bg-white/10"
                >
                  <LogOut className="h-4 w-4" />
                  <span>Sign Out</span>
                </button>
              </>
            ) : user.role === "OPERATOR" ? (
              <>
                <NavLink to="/operator" className={navLinkClass}>
                  <Activity className="h-4 w-4 text-amber-400" />
                  <span>Fleet Dashboard</span>
                </NavLink>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="inline-flex items-center gap-2 rounded-xl px-3 py-2 text-left text-sm font-medium text-slate-200 hover:bg-white/10"
                >
                  <LogOut className="h-4 w-4" />
                  <span>Sign Out</span>
                </button>
              </>
            ) : (
              <>
                <NavLink to="/assistant" className={navLinkClass}>
                  <Sparkles className="h-4 w-4 text-brass-400" />
                  <span>AI Assistant</span>
                </NavLink>
                <NavLink to="/dashboard" className={navLinkClass}>
                  <User className="h-4 w-4" />
                  <span>My Dashboard</span>
                </NavLink>
                <button
                  type="button"
                  onClick={handleLogout}
                  className="inline-flex items-center gap-2 rounded-xl px-3 py-2 text-left text-sm font-medium text-slate-200 hover:bg-white/10"
                >
                  <LogOut className="h-4 w-4" />
                  <span>Sign Out</span>
                </button>
              </>
            )}
          </div>
        </nav>
      ) : null}
    </header>
  );
}
