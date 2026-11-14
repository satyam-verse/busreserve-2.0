import { useState } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import {
  LogIn,
  AlertCircle,
  ArrowRight,
  MailWarning,
  CheckCircle2,
  Eye,
  EyeOff,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import AuthShell from "../components/auth/AuthShell";
import { busApi } from "../services/api";

export default function UserLoginPage() {
  const { user, loginUser } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [needsVerification, setNeedsVerification] = useState(false);
  const [resendPreview, setResendPreview] = useState(null);
  const [resending, setResending] = useState(false);

  if (user) {
    return <Navigate to={user.role === "ADMIN" ? "/admin" : "/dashboard"} replace />;
  }

  const redirectTo = location.state?.from?.pathname || "/dashboard";

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setNeedsVerification(false);
    setResendPreview(null);
    setSubmitting(true);

    try {
      await loginUser({ email: email.trim(), password });
      navigate(redirectTo === "/admin" ? "/dashboard" : redirectTo, { replace: true });
    } catch (err) {
      setError(err.message || "Unable to sign in.");
      if (err.code === "email_not_verified") {
        setNeedsVerification(true);
      }
    } finally {
      setSubmitting(false);
    }
  }

  async function handleResend() {
    if (!email.trim()) return;
    setResending(true);
    try {
      const data = await busApi.resendVerification(email.trim());
      setResendPreview(data);
    } catch (err) {
      setError(err.message || "Could not resend verification email.");
    } finally {
      setResending(false);
    }
  }

  return (
    <AuthShell
      variant="passenger"
      badge="Passenger Portal"
      title="Welcome back to your journey log."
      subtitle="Access confirmed PNRs, print boarding passes, adjust upcoming trips, and consult our smart travel concierge."
      highlights={[
        {
          icon: CheckCircle2,
          title: "Instant PNR & Boarding Passes",
          desc: "Download or cancel confirmed reservations in seconds with transparent rules.",
        },
        {
          icon: LogIn,
          title: "Faster Passenger Checkout",
          desc: "Signed-in passengers get prefilled contact details and unified booking history.",
        },
      ]}
    >
      <div className="mb-6">
        <div className="mb-3 inline-flex h-11 w-11 items-center justify-center rounded-xl bg-navy-950 text-cream-50 shadow-sm">
          <LogIn className="h-5 w-5 text-brass-400" />
        </div>
        <h1 className="font-serif text-3xl font-normal tracking-tight text-navy-950">
          Passenger Sign In
        </h1>
        <p className="mt-1 text-sm text-navy-900/70">
          Access your trips, PNRs, and profile settings.
        </p>
      </div>

      {error ? (
        <div
          role="alert"
          className="mb-5 rounded-xl border border-red-200 bg-red-50 px-3.5 py-3 text-sm text-red-800"
        >
          <div className="flex items-start gap-2.5">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
          {needsVerification ? (
            <div className="mt-3 border-t border-red-200/80 pt-2.5">
              <button
                type="button"
                onClick={handleResend}
                disabled={resending}
                className="inline-flex items-center gap-1.5 text-xs font-semibold text-red-900 underline hover:no-underline"
              >
                <MailWarning className="h-3.5 w-3.5" />
                <span>{resending ? "Sending verification..." : "Resend verification link"}</span>
              </button>
            </div>
          ) : null}
        </div>
      ) : null}

      {resendPreview ? (
        <div className="mb-5 rounded-xl border border-emerald-200 bg-emerald-50 px-3.5 py-3 text-xs text-emerald-900">
          <p className="font-medium">{resendPreview.message}</p>
          {resendPreview.local_mail_preview?.token ? (
            <Link
              to={`/verify-email?token=${encodeURIComponent(resendPreview.local_mail_preview.token)}`}
              className="mt-2 inline-flex items-center gap-1 font-semibold underline"
            >
              <CheckCircle2 className="h-3.5 w-3.5" />
              <span>Verify Email Now</span>
            </Link>
          ) : null}
        </div>
      ) : null}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="login-email" className="block text-xs font-semibold text-navy-900/80">
            Email Address
          </label>
          <input
            id="login-email"
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              setError("");
            }}
            placeholder="passenger@example.com"
            className="mt-1.5 w-full rounded-xl border border-navy-900/15 bg-cream-50/70 px-3.5 py-2.5 text-sm text-navy-950 outline-none transition focus:border-emerald-600 focus:bg-white focus:ring-2 focus:ring-emerald-600/20"
          />
        </div>

        <div>
          <div className="flex items-center justify-between">
            <label
              htmlFor="login-password"
              className="block text-xs font-semibold text-navy-900/80"
            >
              Password
            </label>
            <Link
              to="/forgot-password"
              className="text-xs font-medium text-navy-800 hover:underline"
            >
              Forgot password?
            </Link>
          </div>
          <div className="relative mt-1.5">
            <input
              id="login-password"
              type={showPassword ? "text" : "password"}
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                setError("");
              }}
              placeholder="Enter your password"
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
          <span>{submitting ? "Signing in..." : "Sign In"}</span>
          <ArrowRight className="h-4 w-4" />
        </button>
      </form>

      <div className="mt-6 space-y-2 border-t border-navy-900/10 pt-4 text-center text-sm text-navy-900/70">
        <p>
          New to BusReserve?{" "}
          <Link to="/register" className="font-semibold text-navy-950 hover:underline">
            Create an account
          </Link>
        </p>
        <p className="text-xs text-navy-900/50">
          Staff &amp; operations team?{" "}
          <Link to="/admin/login" className="font-medium text-navy-800 hover:underline">
            Admin Sign In
          </Link>
        </p>
      </div>
    </AuthShell>
  );
}
