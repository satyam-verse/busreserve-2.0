import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  LockKeyhole,
  AlertCircle,
  CheckCircle2,
  ArrowRight,
  Eye,
  EyeOff,
  ShieldCheck,
} from "lucide-react";
import { busApi } from "../services/api";
import AuthShell from "../components/auth/AuthShell";

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const [token, setToken] = useState(searchParams.get("token") || "");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    if (newPassword !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setSubmitting(true);
    try {
      await busApi.resetPassword({
        token: token.trim(),
        new_password: newPassword,
      });
      setDone(true);
    } catch (err) {
      setError(err.message || "Could not reset password.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthShell
      variant="passenger"
      badge="Credential Update"
      title="Set a fresh, strong password."
      subtitle="Completing a reset immediately invalidates all prior sessions across devices."
      highlights={[
        {
          icon: ShieldCheck,
          title: "Session revocation on reset",
          desc: "Every active token version increments so stale cookies are rejected cleanly.",
        },
      ]}
    >
      <div className="mb-6">
        <div className="mb-3 inline-flex h-11 w-11 items-center justify-center rounded-xl bg-navy-950 text-cream-50 shadow-sm">
          <LockKeyhole className="h-5 w-5 text-brass-400" />
        </div>
        <h1 className="font-serif text-3xl font-normal tracking-tight text-navy-950">
          Set New Password
        </h1>
        <p className="mt-1 text-sm text-navy-900/70">
          Updating your password signs out all existing active sessions.
        </p>
      </div>

      {error ? (
        <div className="mb-5 flex items-start gap-2.5 rounded-xl border border-red-200 bg-red-50 p-3.5 text-sm text-red-800">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      ) : null}

      {done ? (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
          <div className="flex items-start gap-2.5">
            <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-700" />
            <p>Password updated successfully. You can now sign in with your new credentials.</p>
          </div>
          <Link
            to="/login"
            className="mt-4 inline-flex items-center gap-2 rounded-xl bg-navy-950 px-4 py-2 text-xs font-semibold text-white transition hover:bg-emerald-700"
          >
            <span>Sign In</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="reset-token"
              className="block text-xs font-bold uppercase tracking-wider text-navy-900/65"
            >
              Reset Token
            </label>
            <input
              id="reset-token"
              type="text"
              required
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="Paste reset token"
              className="mt-1.5 w-full rounded-xl border border-navy-900/15 bg-cream-50/70 px-3.5 py-2.5 font-mono text-xs text-navy-950 outline-none transition focus:border-emerald-600 focus:bg-white focus:ring-2 focus:ring-emerald-600/20"
            />
          </div>

          <div>
            <label
              htmlFor="reset-new-pw"
              className="block text-xs font-bold uppercase tracking-wider text-navy-900/65"
            >
              New Password
            </label>
            <div className="relative mt-1.5">
              <input
                id="reset-new-pw"
                type={showNewPassword ? "text" : "password"}
                required
                autoComplete="new-password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Min 8 chars, upper, lower, digit, symbol"
                className="w-full rounded-xl border border-navy-900/15 bg-cream-50/70 px-3.5 py-2.5 pr-10 text-sm text-navy-950 outline-none transition focus:border-emerald-600 focus:bg-white focus:ring-2 focus:ring-emerald-600/20"
              />
              <button
                type="button"
                onClick={() => setShowNewPassword((prev) => !prev)}
                aria-label={showNewPassword ? "Hide new password" : "Show new password"}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded-lg p-1.5 text-navy-900/50 transition hover:bg-cream-100 hover:text-navy-950"
              >
                {showNewPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          <div>
            <label
              htmlFor="reset-confirm-pw"
              className="block text-xs font-bold uppercase tracking-wider text-navy-900/65"
            >
              Confirm New Password
            </label>
            <div className="relative mt-1.5">
              <input
                id="reset-confirm-pw"
                type={showConfirmPassword ? "text" : "password"}
                required
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Re-enter password"
                className="w-full rounded-xl border border-navy-900/15 bg-cream-50/70 px-3.5 py-2.5 pr-10 text-sm text-navy-950 outline-none transition focus:border-emerald-600 focus:bg-white focus:ring-2 focus:ring-emerald-600/20"
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword((prev) => !prev)}
                aria-label={showConfirmPassword ? "Hide confirm password" : "Show confirm password"}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded-lg p-1.5 text-navy-900/50 transition hover:bg-cream-100 hover:text-navy-950"
              >
                {showConfirmPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded-xl bg-navy-950 px-4 py-3 text-sm font-bold text-white shadow-editorial transition hover:bg-emerald-700 disabled:opacity-60"
          >
            {submitting ? "Updating Password..." : "Update Password"}
          </button>
        </form>
      )}
    </AuthShell>
  );
}
