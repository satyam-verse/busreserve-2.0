import { useState } from "react";
import { Link } from "react-router-dom";
import { KeyRound, AlertCircle, CheckCircle2, ArrowRight, ShieldCheck, Clock } from "lucide-react";
import { busApi } from "../services/api";
import AuthShell from "../components/auth/AuthShell";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [response, setResponse] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setResponse(null);
    setSubmitting(true);
    try {
      const data = await busApi.forgotPassword(email.trim());
      setResponse(data);
    } catch (err) {
      setError(err.message || "Unable to process password reset request.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthShell
      variant="passenger"
      badge="Account Recovery"
      title="Regain access to your bookings."
      subtitle="Request a single-use password reset token linked to your verified passenger account."
      highlights={[
        {
          icon: ShieldCheck,
          title: "Single-use cryptographic token",
          desc: "Reset tokens expire automatically and invalidate prior sessions once used.",
        },
        {
          icon: Clock,
          title: "Confirmed PNRs remain safe",
          desc: "Your existing seat reservations and travel history stay untouched during recovery.",
        },
      ]}
    >
      <div className="mb-6">
        <div className="mb-3 inline-flex h-11 w-11 items-center justify-center rounded-xl bg-navy-950 text-cream-50 shadow-sm">
          <KeyRound className="h-5 w-5 text-brass-400" />
        </div>
        <h1 className="font-serif text-3xl font-normal tracking-tight text-navy-950">
          Reset Password
        </h1>
        <p className="mt-1 text-sm text-navy-900/70">
          Enter your registered email to receive password reset instructions.
        </p>
      </div>

      {error ? (
        <div className="mb-5 flex items-start gap-2.5 rounded-xl border border-red-200 bg-red-50 p-3.5 text-sm text-red-800">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      ) : null}

      {response ? (
        <div className="mb-5 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
          <div className="flex items-start gap-2.5">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-700" />
            <p className="text-xs leading-relaxed">{response.message}</p>
          </div>
          {response.local_mail_preview?.token ? (
            <div className="mt-3 border-t border-emerald-200 pt-3">
              <p className="text-[11px] font-bold uppercase tracking-wider text-emerald-800">
                Local Development Reset Preview
              </p>
              <Link
                to={`/reset-password?token=${encodeURIComponent(response.local_mail_preview.token)}`}
                className="mt-2 inline-flex items-center gap-1.5 rounded-xl bg-navy-950 px-3.5 py-2 text-xs font-semibold text-white transition hover:bg-emerald-700"
              >
                <span>Choose New Password</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          ) : null}
        </div>
      ) : null}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label
            htmlFor="forgot-email"
            className="block text-xs font-bold uppercase tracking-wider text-navy-900/65"
          >
            Email Address
          </label>
          <input
            id="forgot-email"
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="passenger@example.com"
            className="mt-1.5 w-full rounded-xl border border-navy-900/15 bg-cream-50/70 px-3.5 py-2.5 text-sm text-navy-950 outline-none transition focus:border-emerald-600 focus:bg-white focus:ring-2 focus:ring-emerald-600/20"
          />
        </div>
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-xl bg-navy-950 px-4 py-3 text-sm font-bold text-white shadow-editorial transition hover:bg-emerald-700 disabled:opacity-60"
        >
          {submitting ? "Sending Reset Instructions..." : "Send Reset Link"}
        </button>
      </form>

      <p className="mt-6 border-t border-navy-900/10 pt-4 text-center text-sm text-navy-900/70">
        Remembered it?{" "}
        <Link to="/login" className="font-semibold text-navy-950 hover:text-emerald-700 hover:underline">
          Back to Sign In
        </Link>
      </p>
    </AuthShell>
  );
}
