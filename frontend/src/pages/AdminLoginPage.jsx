import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import {
  ShieldCheck,
  Lock,
  AlertCircle,
  ArrowRight,
  Activity,
  Sparkles,
  Eye,
  EyeOff,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import AuthShell from "../components/auth/AuthShell";

export default function AdminLoginPage() {
  const { user, loginAdmin } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  if (user) {
    return <Navigate to={user.role === "ADMIN" ? "/admin" : "/dashboard"} replace />;
  }

  const redirectTo = location.state?.from?.pathname || "/admin";

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await loginAdmin({ email: email.trim(), password });
      navigate(redirectTo.startsWith("/admin") ? redirectTo : "/admin", { replace: true });
    } catch (err) {
      setError(err.message || "Administrator authentication failed.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthShell
      variant="admin"
      badge="Operations Control"
      title="Fleet, routes & live telemetry console."
      subtitle="Authenticated role-based workspace for managing cities, bus operators, schedules, bookings, and read-only operations AI."
      highlights={[
        {
          icon: ShieldCheck,
          title: "Strict RBAC & Session Isolation",
          desc: "Admin sessions enforce role verification and token rotation across every management endpoint.",
        },
        {
          icon: Activity,
          title: "Live Fleet & Booking Analytics",
          desc: "Inspect active schedules, occupancy, PNR status, and daily reservation activity.",
        },
        {
          icon: Sparkles,
          title: "Read-Only AI Operations Copilot",
          desc: "Ask analytics and quota health questions without mutating production database records.",
        },
      ]}
    >
      <div className="mb-6">
        <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-brass-500/30 bg-brass-50 px-3 py-1 text-[11px] font-bold uppercase tracking-[0.16em] text-brass-600">
          <ShieldCheck className="h-3.5 w-3.5 text-emerald-700" />
          <span>Restricted Operations Portal</span>
        </div>
        <h1 className="font-serif text-3xl font-normal tracking-tight text-navy-950">
          Administrator Sign In
        </h1>
        <p className="mt-1 text-sm text-navy-900/70">
          Authorized BusReserve fleet and operations staff only.
        </p>
      </div>

      {error ? (
        <div
          role="alert"
          className="mb-5 flex items-start gap-2.5 rounded-xl border border-red-200 bg-red-50 px-3.5 py-3 text-sm text-red-800"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      ) : null}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="admin-email" className="block text-xs font-semibold text-navy-900/80">
            Administrator Email
          </label>
          <input
            id="admin-email"
            type="email"
            required
            autoComplete="username"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              setError("");
            }}
            placeholder="admin@busreserve.local"
            className="mt-1.5 w-full rounded-xl border border-navy-900/15 bg-cream-50/70 px-3.5 py-2.5 text-sm text-navy-950 outline-none transition focus:border-emerald-600 focus:bg-white focus:ring-2 focus:ring-emerald-600/20"
          />
        </div>

        <div>
          <label
            htmlFor="admin-password"
            className="block text-xs font-semibold text-navy-900/80"
          >
            Password
          </label>
          <div className="relative mt-1.5">
            <input
              id="admin-password"
              type={showPassword ? "text" : "password"}
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                setError("");
              }}
              placeholder="Enter administrator password"
              className="w-full rounded-xl border border-navy-900/15 bg-cream-50/70 px-3.5 py-2.5 pr-10 text-sm text-navy-950 outline-none transition focus:border-emerald-600 focus:bg-white focus:ring-2 focus:ring-emerald-600/20"
            />
            <button
              type="button"
              onClick={() => setShowPassword((prev) => !prev)}
              aria-label={showPassword ? "Hide password" : "Show password"}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded-lg p-1.5 text-navy-900/50 transition hover:bg-cream-100 hover:text-navy-950"
            >
              {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-navy-950 px-4 py-3 text-sm font-bold text-white shadow-editorial transition hover:bg-emerald-700 disabled:opacity-60"
        >
          <Lock className="h-4 w-4 text-brass-400" />
          <span>{submitting ? "Authenticating..." : "Enter Admin Console"}</span>
          <ArrowRight className="h-4 w-4" />
        </button>
      </form>

      <div className="mt-6 border-t border-navy-900/10 pt-4 text-center text-xs text-navy-900/60">
        Passenger looking to book a seat?{" "}
        <Link to="/login" className="font-semibold text-navy-950 hover:underline">
          Use Passenger Sign In
        </Link>
      </div>
    </AuthShell>
  );
}
