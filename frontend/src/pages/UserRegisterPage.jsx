import { useState } from "react";
import { Link, Navigate } from "react-router-dom";
import {
  UserPlus,
  MailCheck,
  ArrowRight,
  AlertCircle,
  CheckCircle2,
  ShieldCheck,
  Ticket,
  Sparkles,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import AuthShell from "../components/auth/AuthShell";

export default function UserRegisterPage() {
  const { user, registerUser } = useAuth();
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    phone: "",
    password: "",
    confirm_password: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [fieldErrors, setFieldErrors] = useState({});
  const [result, setResult] = useState(null);

  if (user) {
    return <Navigate to={user.role === "ADMIN" ? "/admin" : "/dashboard"} replace />;
  }

  function handleChange(field) {
    return (e) => {
      setForm((prev) => ({ ...prev, [field]: e.target.value }));
      setError("");
      setFieldErrors((prev) => ({ ...prev, [field]: undefined }));
    };
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setFieldErrors({});

    if (form.password !== form.confirm_password) {
      setFieldErrors({ confirm_password: ["Passwords do not match."] });
      return;
    }

    setSubmitting(true);
    try {
      const payload = {
        full_name: form.full_name.trim(),
        email: form.email.trim(),
        password: form.password,
      };
      if (form.phone.trim()) {
        payload.phone = form.phone.trim();
      }
      const data = await registerUser(payload);
      setResult(data);
    } catch (err) {
      setError(err.message || "Registration failed. Please check your details.");
      if (err.details) {
        setFieldErrors(err.details);
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (result) {
    const preview = result.local_mail_preview;
    const verifyToken = preview?.token;
    return (
      <AuthShell
        variant="passenger"
        badge="Passenger Onboarding"
        title="Verify your email to start booking."
        subtitle="Your account has been created. One verification click activates saved PNR history and faster checkout."
        highlights={[
          {
            icon: Ticket,
            title: "Unified PNR & Boarding Pass History",
            desc: "View confirmed and cancelled trips in one passenger dashboard.",
          },
          {
            icon: Sparkles,
            title: "AI Travel Concierge Access",
            desc: "Compare fares, overnight coaches, and live availability in seconds.",
          },
        ]}
      >
        <div className="mb-4 inline-flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700">
          <MailCheck className="h-6 w-6" />
        </div>
        <h1 className="font-serif text-3xl font-normal tracking-tight text-navy-950">
          Verify your email address
        </h1>
        <p className="mt-2 text-sm text-navy-900/75">{result.message}</p>

        {preview ? (
          <div className="mt-6 rounded-xl border border-navy-900/10 bg-cream-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-navy-900/60">
              Local Development Mail Preview
            </p>
            <p className="mt-1 text-xs text-navy-900/75">
              SMTP is not configured in this environment. Use the single-use verification link
              below to activate <span className="font-semibold">{result.user?.email}</span>:
            </p>
            {verifyToken ? (
              <Link
                to={`/verify-email?token=${encodeURIComponent(verifyToken)}`}
                className="mt-3 inline-flex items-center gap-2 rounded-lg bg-navy-950 px-4 py-2 text-xs font-semibold text-white transition hover:bg-emerald-700"
              >
                <CheckCircle2 className="h-4 w-4" />
                <span>Verify Email Now</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            ) : null}
          </div>
        ) : (
          <p className="mt-4 text-xs text-navy-900/70">
            Check your inbox and follow the verification link to sign in.
          </p>
        )}

        <div className="mt-6 flex items-center justify-between border-t border-navy-900/10 pt-4 text-sm">
          <Link to="/verify-email" className="font-medium text-navy-800 hover:underline">
            Enter verification token manually
          </Link>
          <Link to="/login" className="font-semibold text-navy-950 hover:underline">
            Back to Sign In
          </Link>
        </div>
      </AuthShell>
    );
  }

  return (
    <AuthShell
      variant="passenger"
      badge="Passenger Account"
      title="Reserve smarter across India's 90-day IST network."
      subtitle="Create your account to track PNR tickets, prefill passenger checkout details, and chat with the AI Travel Concierge."
      highlights={[
        {
          icon: Ticket,
          title: "Instant PNR & Boarding Passes",
          desc: "Every confirmed ticket is stored automatically with one-click print and cancellation.",
        },
        {
          icon: ShieldCheck,
          title: "Verified Account Protection",
          desc: "Email verification, session controls, and atomic seat locking protect every booking.",
        },
        {
          icon: Sparkles,
          title: "Smart Trip Recommendations",
          desc: "Compare AC sleepers, fares, and seat availability using natural-language search.",
        },
      ]}
    >
      <div className="mb-6">
        <div className="mb-3 inline-flex h-11 w-11 items-center justify-center rounded-xl bg-navy-950 text-cream-50 shadow-sm">
          <UserPlus className="h-5 w-5 text-brass-400" />
        </div>
        <h1 className="font-serif text-3xl font-normal tracking-tight text-navy-950">
          Create Passenger Account
        </h1>
        <p className="mt-1 text-sm text-navy-900/70">
          Manage reservations, download PNR history, and fast-fill passenger details.
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
          <label htmlFor="reg-name" className="block text-xs font-semibold text-navy-900/80">
            Full Name
          </label>
          <input
            id="reg-name"
            type="text"
            required
            autoComplete="name"
            value={form.full_name}
            onChange={handleChange("full_name")}
            placeholder="Aarav Sharma"
            className="mt-1.5 w-full rounded-xl border border-navy-900/15 bg-cream-50/70 px-3.5 py-2.5 text-sm text-navy-950 outline-none transition focus:border-emerald-600 focus:bg-white focus:ring-2 focus:ring-emerald-600/20"
          />
          {fieldErrors.full_name ? (
            <p className="mt-1 text-xs text-red-600">{fieldErrors.full_name[0]}</p>
          ) : null}
        </div>

        <div>
          <label htmlFor="reg-email" className="block text-xs font-semibold text-navy-900/80">
            Email Address
          </label>
          <input
            id="reg-email"
            type="email"
            required
            autoComplete="email"
            value={form.email}
            onChange={handleChange("email")}
            placeholder="aarav@example.com"
            className="mt-1.5 w-full rounded-xl border border-navy-900/15 bg-cream-50/70 px-3.5 py-2.5 text-sm text-navy-950 outline-none transition focus:border-emerald-600 focus:bg-white focus:ring-2 focus:ring-emerald-600/20"
          />
          {fieldErrors.email ? (
            <p className="mt-1 text-xs text-red-600">{fieldErrors.email[0]}</p>
          ) : null}
        </div>

        <div>
          <label htmlFor="reg-phone" className="block text-xs font-semibold text-navy-900/80">
            Mobile Number <span className="font-normal text-navy-900/50">(Optional)</span>
          </label>
          <input
            id="reg-phone"
            type="tel"
            autoComplete="tel"
            value={form.phone}
            onChange={handleChange("phone")}
            placeholder="9876543210"
            className="mt-1.5 w-full rounded-xl border border-navy-900/15 bg-cream-50/70 px-3.5 py-2.5 text-sm text-navy-950 outline-none transition focus:border-emerald-600 focus:bg-white focus:ring-2 focus:ring-emerald-600/20"
          />
          {fieldErrors.phone ? (
            <p className="mt-1 text-xs text-red-600">{fieldErrors.phone[0]}</p>
          ) : null}
        </div>

        <div>
          <label htmlFor="reg-password" className="block text-xs font-semibold text-navy-900/80">
            Password
          </label>
          <input
            id="reg-password"
            type="password"
            required
            autoComplete="new-password"
            value={form.password}
            onChange={handleChange("password")}
            placeholder="Min 8 chars, upper, lower, digit, symbol"
            className="mt-1.5 w-full rounded-xl border border-navy-900/15 bg-cream-50/70 px-3.5 py-2.5 text-sm text-navy-950 outline-none transition focus:border-emerald-600 focus:bg-white focus:ring-2 focus:ring-emerald-600/20"
          />
          {fieldErrors.password ? (
            <p className="mt-1 text-xs text-red-600">{fieldErrors.password[0]}</p>
          ) : null}
        </div>

        <div>
          <label
            htmlFor="reg-confirm-password"
            className="block text-xs font-semibold text-navy-900/80"
          >
            Confirm Password
          </label>
          <input
            id="reg-confirm-password"
            type="password"
            required
            autoComplete="new-password"
            value={form.confirm_password}
            onChange={handleChange("confirm_password")}
            placeholder="Re-enter password"
            className="mt-1.5 w-full rounded-xl border border-navy-900/15 bg-cream-50/70 px-3.5 py-2.5 text-sm text-navy-950 outline-none transition focus:border-emerald-600 focus:bg-white focus:ring-2 focus:ring-emerald-600/20"
          />
          {fieldErrors.confirm_password ? (
            <p className="mt-1 text-xs text-red-600">{fieldErrors.confirm_password[0]}</p>
          ) : null}
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-navy-950 px-4 py-3 text-sm font-bold text-white shadow-editorial transition hover:bg-emerald-700 disabled:opacity-60"
        >
          <span>{submitting ? "Creating Account..." : "Create Passenger Account"}</span>
          <ArrowRight className="h-4 w-4" />
        </button>
      </form>

      <p className="mt-6 text-center text-sm text-navy-900/70">
        Already have an account?{" "}
        <Link to="/login" className="font-semibold text-navy-950 hover:underline">
          Sign in
        </Link>
      </p>
    </AuthShell>
  );
}
