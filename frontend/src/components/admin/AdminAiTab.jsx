import { useCallback, useEffect, useState } from "react";
import {
  Sparkles,
  Send,
  Trash2,
  Activity,
  ShieldCheck,
  AlertCircle,
  Lock,
  RefreshCw,
} from "lucide-react";
import { busApi } from "../../services/api";
import { renderFormattedAiText } from "../../utils/formatAiText";
import {
  formatMessageProviderLabel,
  getAdminAiPresentation,
} from "../../utils/aiStatusDisplay";

const ADMIN_PROMPTS = [
  "Summarize confirmed bookings, demo net revenue, and pending refunds",
  "Which routes have the most bookings and highest upcoming occupancy?",
  "Report AI provider health, fallback status, and daily quota usage",
];

export default function AdminAiTab({ onNotify }) {
  const [status, setStatus] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [error, setError] = useState("");

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [statusPayload, historyPayload] = await Promise.all([
        busApi.getAdminAiStatus(),
        busApi.getAdminAiHistory(20),
      ]);
      setStatus(statusPayload);
      setMessages(historyPayload.messages || []);
    } catch (err) {
      setError(err.message || "Failed to load Admin AI Copilot telemetry.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  async function submitPrompt(promptText) {
    const trimmed = promptText.trim();
    if (!trimmed || sending) return;
    setError("");
    setSending(true);
    setInput("");

    const optimisticUser = {
      id: `tmp-admin-u-${Date.now()}`,
      role: "user",
      content: trimmed,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimisticUser]);

    try {
      const res = await busApi.adminAiChat({ message: trimmed });
      if (res.data?.ai_status) {
        setStatus({
          provider: res.provider,
          mode: res.mode,
          model: res.model,
          fallback_used: res.fallback_used,
          status: res.data.ai_status,
        });
      }
      setMessages((prev) => [
        ...prev,
        {
          id: `tmp-admin-a-${Date.now()}`,
          role: "assistant",
          content: res.message,
          provider: res.provider,
          mode: res.mode,
          intent: res.intent,
          fallback_used: res.fallback_used,
          created_at: new Date().toISOString(),
        },
      ]);
    } catch (err) {
      setError(err.message || "Admin AI request failed.");
      setMessages((prev) => prev.filter((m) => m.id !== optimisticUser.id));
    } finally {
      setSending(false);
    }
  }

  async function handleClear() {
    setClearing(true);
    try {
      await busApi.clearAdminAiHistory();
      setMessages([]);
      onNotify?.("success", "Admin AI copilot history cleared.");
    } catch (err) {
      setError(err.message || "Could not clear history.");
    } finally {
      setClearing(false);
    }
  }

  const telemetry = status?.status || {};
  const quota = telemetry.quota || {};
  const aiDisplay = getAdminAiPresentation(status);

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div className="rounded-2xl border border-navy-900/10 bg-white p-4 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-navy-900/55">
            Active Provider
          </p>
          <p className="mt-1 text-lg font-bold text-navy-950">
            {aiDisplay.providerTitle}
          </p>
          <p className="mt-1 text-xs text-navy-900/65">
            {aiDisplay.modeSummary}
          </p>
        </div>

        <div className="rounded-2xl border border-navy-900/10 bg-white p-4 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-navy-900/55">
            Provider Health
          </p>
          <p
            className={`mt-1 text-lg font-bold ${
              aiDisplay.healthTone === "emerald" ? "text-emerald-700" : "text-brass-600"
            }`}
          >
            {aiDisplay.healthLabel}
          </p>
          <p className="mt-1 text-xs text-navy-900/65">
            {aiDisplay.healthDetail}
          </p>
        </div>

        <div className="rounded-2xl border border-navy-900/10 bg-white p-4 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-navy-900/55">
            Daily AI Quota
          </p>
          <p className="mt-1 text-lg font-bold text-navy-950">
            {quota.global_used_today ?? 0} / {quota.daily_limit ?? 200}
          </p>
          <p className="mt-1 text-xs text-navy-900/65">
            Remaining today (IST): {quota.global_remaining_today ?? 0}
          </p>
        </div>

        <div className="rounded-2xl border border-navy-900/10 bg-white p-4 shadow-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-navy-900/55">
            Guardrail Mode
          </p>
          <p className="mt-1 inline-flex items-center gap-1.5 text-lg font-bold text-navy-950">
            <Lock className="h-4 w-4 text-emerald-600" />
            Read-Only Copilot
          </p>
          <p className="mt-1 text-xs text-navy-900/65">
            RBAC Admin only • Read-only insights
          </p>
        </div>
      </div>

      <div className="rounded-2xl border border-navy-900/10 bg-white p-5 shadow-card">
        <div className="flex flex-col justify-between gap-3 border-b border-navy-900/10 pb-4 sm:flex-row sm:items-center">
          <div className="flex flex-wrap items-center gap-2">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-navy-950 px-3 py-1 text-xs font-semibold text-white">
              <Sparkles className="h-3.5 w-3.5 text-emerald-400" />
              Admin Operations AI Copilot
            </span>
            <span className="inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-800">
              <Activity className="h-3.5 w-3.5" />
              Live Operations Grounded
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-2 self-start">
            <button
              type="button"
              onClick={loadData}
              disabled={loading}
              className="inline-flex items-center gap-1.5 rounded-xl border border-navy-900/15 bg-white px-3 py-1.5 text-xs font-semibold text-navy-950 transition hover:bg-cream-50 disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
              <span>Refresh Status</span>
            </button>
            <button
              type="button"
              onClick={handleClear}
              disabled={clearing || messages.length === 0}
              className="inline-flex items-center gap-1.5 rounded-xl border border-navy-900/15 bg-cream-50 px-3 py-1.5 text-xs font-semibold text-navy-950 transition hover:bg-cream-100 disabled:opacity-50"
            >
              <Trash2 className="h-3.5 w-3.5" />
              <span>{clearing ? "Clearing..." : "Clear Copilot History"}</span>
            </button>
          </div>
        </div>

        <div className="mt-3 flex flex-wrap gap-2">
          {ADMIN_PROMPTS.map((q) => (
            <button
              key={q}
              type="button"
              onClick={() => submitPrompt(q)}
              disabled={sending}
              className="rounded-full border border-navy-900/10 bg-cream-50 px-3 py-1 text-xs font-medium text-navy-900/80 transition hover:bg-emerald-50"
            >
              {q}
            </button>
          ))}
        </div>

        {error ? (
          <div
            role="alert"
            className="mt-4 flex flex-wrap items-center justify-between gap-2 rounded-xl border border-red-200 bg-red-50 px-3.5 py-2.5 text-xs text-red-800"
          >
            <div className="flex items-start gap-2">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
            <button
              type="button"
              onClick={loadData}
              className="inline-flex items-center gap-1 rounded-lg border border-red-300 bg-white px-2.5 py-1 font-semibold text-red-800 transition hover:bg-red-100"
            >
              <RefreshCw className="h-3 w-3" />
              Retry
            </button>
          </div>
        ) : null}

        <div
          role="log"
          aria-live="polite"
          aria-label="Admin copilot messages"
          className="mt-4 max-h-96 space-y-3 overflow-y-auto rounded-xl border border-navy-900/10 bg-cream-50/70 p-4"
        >
          {loading ? (
            <div className="space-y-3 py-2" aria-busy="true">
              <div className="h-10 w-3/4 animate-pulse rounded-2xl bg-cream-200/70" />
              <div className="ml-auto h-10 w-1/2 animate-pulse rounded-2xl bg-navy-900/10" />
              <div className="h-14 w-4/5 animate-pulse rounded-2xl bg-cream-200/70" />
            </div>
          ) : messages.length === 0 ? (
            <div className="py-6 text-center text-sm text-navy-900/60">
              Ask about fleet occupancy, route performance, confirmed bookings, demo revenue/refunds, or AI quota health.
            </div>
          ) : (
            messages.map((msg) => {
              const isUser = msg.role === "user";
              return (
                <div key={msg.id} className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
                  <div
                    className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm shadow-sm ${
                      isUser
                        ? "bg-navy-950 text-white"
                        : "border border-navy-900/10 bg-white text-navy-950"
                    }`}
                  >
                    <p className="whitespace-pre-line leading-relaxed">
                      {renderFormattedAiText(msg.content)}
                    </p>
                    {!isUser ? (
                      <div className="mt-1.5 flex items-center gap-2 text-[11px] text-navy-900/55">
                        <ShieldCheck className="h-3 w-3" />
                        <span>{formatMessageProviderLabel(msg.provider)}</span>
                      </div>
                    ) : null}
                  </div>
                </div>
              );
            })
          )}
          {sending ? (
            <div className="flex justify-start">
              <div className="inline-flex items-center gap-2 rounded-2xl border border-navy-900/10 bg-white px-4 py-2.5 text-xs font-medium text-navy-900/70 shadow-sm">
                <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-500" />
                <span>Analyzing operational metrics...</span>
              </div>
            </div>
          ) : null}
        </div>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            submitPrompt(input);
          }}
          className="mt-4 flex gap-2"
        >
          <input
            type="text"
            value={input}
            maxLength={1000}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask an operational analytics question..."
            className="flex-1 rounded-xl border border-navy-900/15 bg-white px-4 py-2.5 text-sm text-navy-950 focus:border-emerald-500 focus:outline-none"
          />
          <button
            type="submit"
            disabled={sending || !input.trim()}
            className="inline-flex items-center gap-2 rounded-xl bg-navy-950 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-navy-800 disabled:opacity-50"
          >
            <Send className="h-4 w-4" />
            <span>{sending ? "Analyzing..." : "Ask Copilot"}</span>
          </button>
        </form>
      </div>
    </div>
  );
}
