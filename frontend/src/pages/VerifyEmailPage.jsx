import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { MailCheck, CheckCircle2, AlertCircle, ArrowRight, ShieldCheck } from "lucide-react";
import { busApi } from "../services/api";
import AuthShell from "../components/auth/AuthShell";

export default function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const initialToken = searchParams.get("token") || "";

  const [token, setToken] = useState(initialToken);
  const [status, setStatus] = useState("idle"); // idle | verifying | success | error
  const [message, setMessage] = useState("");

  async function verify(tokenValue) {
    const cleaned = tokenValue.trim();
    if (!cleaned) return;
    setStatus("verifying");
    setMessage("");
    try {
      const data = await busApi.verifyEmail(cleaned);
      setStatus("success");
      setMessage(data.message || "Email verified successfully.");
    } catch (err) {
      setStatus("error");
      setMessage(err.message || "Verification link is invalid or expired.");
    }
  }

  useEffect(() => {
    if (initialToken) {
      verify(initialToken);
    }
  }, [initialToken]);

  function handleManualSubmit(e) {
    e.preventDefault();
    verify(token);
  }

  return (
    <AuthShell
      variant="passenger"
      badge="Passenger Onboarding"
      title="Activate your passenger account."
      subtitle="Verify your email address once to unlock booking history, profile controls, and the AI Travel Concierge."
      highlights={[
        {
          icon: ShieldCheck,
          title: "Verified passenger ledger",
          desc: "Ties PNRs and cancellations securely to your confirmed identity.",
        },
      ]}
    >
      <div className="mb-6">
        <div className="mb-3 inline-flex h-11 w-11 items-center justify-center rounded-xl bg-navy-950 text-cream-50 shadow-sm">
          <MailCheck className="h-5 w-5 text-emerald-400" />
        </div>
        <h1 className="font-serif text-3xl font-normal tracking-tight text-navy-950">
          Email Verification
        </h1>
        <p className="mt-1 text-sm text-navy-900/70">
          Confirm your email address to enable passenger sign-in.
        </p>
      </div>

      {status === "verifying" ? (
        <div className="mb-6 flex items-center gap-3 rounded-xl border border-navy-900/10 bg-cream-50 p-4 text-sm text-navy-900">
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-navy-950 border-t-transparent" />
          <span>Verifying token...</span>
        </div>
      ) : null}

      {status === "success" ? (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
          <div className="flex items-start gap-2.5">
            <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-700" />
            <div>
              <p className="font-semibold">Account Activated</p>
              <p className="mt-1 text-xs">{message}</p>
            </div>
          </div>
          <Link
            to="/login"
            className="mt-4 inline-flex items-center gap-2 rounded-xl bg-navy-950 px-4 py-2 text-xs font-semibold text-white transition hover:bg-emerald-700"
          >
            <span>Proceed to Sign In</span>
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      ) : null}

      {status === "error" ? (
        <div className="mb-6 flex items-start gap-2.5 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{message}</span>
        </div>
      ) : null}

      {status !== "success" ? (
        <form onSubmit={handleManualSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="verify-token"
              className="block text-xs font-bold uppercase tracking-wider text-navy-900/65"
            >
              Verification Token
            </label>
            <input
              id="verify-token"
              type="text"
              required
              value={token}
              onChange={(e) => setToken(e.target.value)}
              placeholder="Paste your verification token"
              className="mt-1.5 w-full rounded-xl border border-navy-900/15 bg-cream-50/70 px-3.5 py-2.5 font-mono text-xs text-navy-950 outline-none transition focus:border-emerald-600 focus:bg-white focus:ring-2 focus:ring-emerald-600/20"
            />
          </div>
          <button
            type="submit"
            disabled={status === "verifying"}
            className="w-full rounded-xl bg-navy-950 px-4 py-3 text-sm font-bold text-white shadow-editorial transition hover:bg-emerald-700 disabled:opacity-60"
          >
            Verify Email
          </button>
        </form>
      ) : null}
    </AuthShell>
  );
}
