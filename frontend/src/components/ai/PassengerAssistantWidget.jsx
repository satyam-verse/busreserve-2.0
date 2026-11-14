import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Sparkles,
  Send,
  Trash2,
  Bus,
  Clock,
  ArrowRight,
  AlertCircle,
  ShieldCheck,
  SlidersHorizontal,
  RefreshCw,
} from "lucide-react";
import { busApi } from "../../services/api";
import { renderFormattedAiText } from "../../utils/formatAiText";
import {
  formatAiIntentLabel,
  formatMessageProviderLabel,
  getPassengerAiPresentation,
} from "../../utils/aiStatusDisplay";

const SUGGESTED_PROMPTS = [
  "Cheapest AC bus from Patna to Ranchi tomorrow",
  "Find overnight sleeper buses under ₹900",
  "Show my bookings and recent PNR status",
  "How does the 90-day IST booking window and cancellation work?",
];

export default function PassengerAssistantWidget() {
  const [messages, setMessages] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [status, setStatus] = useState(null);
  const [input, setInput] = useState("");
  const [preference, setPreference] = useState("balanced");
  const [maxBudget, setMaxBudget] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [error, setError] = useState("");

  const loadInitialState = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [statusPayload, historyPayload] = await Promise.all([
        busApi.getAiStatus(),
        busApi.getAiHistory(20),
      ]);
      setStatus(statusPayload);
      setMessages(historyPayload.messages || []);
    } catch (err) {
      setError(err.message || "Unable to initialize AI Travel Assistant.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadInitialState();
  }, [loadInitialState]);

  async function submitPrompt(promptText) {
    const trimmed = promptText.trim();
    if (!trimmed || sending) return;
    setError("");
    setSending(true);
    setInput("");

    const optimisticUser = {
      id: `tmp-u-${Date.now()}`,
      role: "user",
      content: trimmed,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, optimisticUser]);

    try {
      const payload = { message: trimmed };
      if (preference && preference !== "balanced") {
        payload.preference = preference;
      }
      if (maxBudget && Number(maxBudget) > 0) {
        payload.max_budget = Number(maxBudget);
      }

      const res = await busApi.aiChat(payload);
      setStatus((prev) => ({
        ...(prev || {}),
        provider: res.provider,
        mode: res.mode,
        model: res.model,
        fallback_used: res.fallback_used,
      }));
      setRecommendations(res.data?.recommendations || []);

      const assistantMsg = {
        id: `tmp-a-${Date.now()}`,
        role: "assistant",
        content: res.message,
        provider: res.provider,
        mode: res.mode,
        intent: res.intent,
        fallback_used: res.fallback_used,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      setError(err.message || "AI assistant request failed. Please try again.");
      setMessages((prev) => prev.filter((m) => m.id !== optimisticUser.id));
    } finally {
      setSending(false);
    }
  }

  async function handleSmartRecommend() {
    if (sending) return;
    setError("");
    setSending(true);
    try {
      const res = await busApi.aiRecommendations({
        query: input.trim(),
        preference,
        max_budget: maxBudget ? Number(maxBudget) : undefined,
        limit: 5,
      });
      setRecommendations(res.data?.recommendations || []);
      setStatus((prev) => ({
        ...(prev || {}),
        provider: res.provider,
        mode: res.mode,
        model: res.model,
        fallback_used: res.fallback_used,
      }));
      setMessages((prev) => [
        ...prev,
        {
          id: `tmp-r-${Date.now()}`,
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
      setError(err.message || "Could not load smart recommendations.");
    } finally {
      setSending(false);
    }
  }

  async function handleClearHistory() {
    setClearing(true);
    setError("");
    try {
      await busApi.clearAiHistory();
      setMessages([]);
      setRecommendations([]);
    } catch (err) {
      setError(err.message || "Failed to clear conversation history.");
    } finally {
      setClearing(false);
    }
  }

  const aiDisplay = getPassengerAiPresentation(status);

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-navy-900/10 bg-white p-5 shadow-card">
        <div className="flex flex-col justify-between gap-4 border-b border-navy-900/10 pb-4 sm:flex-row sm:items-center">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-full bg-navy-950 px-3 py-1 text-xs font-semibold text-white">
                <Sparkles className="h-3.5 w-3.5 text-emerald-400" />
                <span>BusReserve AI Travel Concierge</span>
              </span>
              <span
                data-testid="ai-provider-badge"
                title={aiDisplay.statusNotice}
                className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${
                  aiDisplay.badgeTone === "emerald"
                    ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                    : "bg-brass-50 text-brass-600 border border-brass-400/40"
                }`}
              >
                <ShieldCheck className="h-3.5 w-3.5" />
                <span>{aiDisplay.badgeLabel}</span>
              </span>
            </div>
            <p className="mt-2 text-xs text-navy-900/70 sm:text-sm">
              {aiDisplay.statusNotice}
            </p>
          </div>

          <button
            type="button"
            onClick={handleClearHistory}
            disabled={clearing || messages.length === 0}
            className="inline-flex items-center gap-1.5 self-start rounded-xl border border-navy-900/15 bg-cream-50 px-3.5 py-2 text-xs font-semibold text-navy-900 transition hover:bg-cream-100 disabled:opacity-50"
          >
            <Trash2 className="h-3.5 w-3.5" />
            <span>{clearing ? "Clearing..." : "Clear History"}</span>
          </button>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-1 text-xs font-semibold text-navy-900/70">
            <SlidersHorizontal className="h-3.5 w-3.5" />
            Smart Filters:
          </span>
          <select
            aria-label="Recommendation priority"
            value={preference}
            onChange={(e) => setPreference(e.target.value)}
            className="rounded-lg border border-navy-900/15 bg-cream-50 px-2.5 py-1.5 text-xs font-medium text-navy-950"
          >
            <option value="balanced">Balanced Score</option>
            <option value="cheapest">Cheapest Fare</option>
            <option value="earliest">Earliest Departure</option>
            <option value="overnight">Overnight Priority</option>
            <option value="shortest">Shortest Duration</option>
            <option value="most_seats">Most Available Seats</option>
          </select>
          <input
            type="number"
            min="100"
            max="50000"
            placeholder="Max budget ₹"
            value={maxBudget}
            onChange={(e) => setMaxBudget(e.target.value)}
            className="w-32 rounded-lg border border-navy-900/15 bg-cream-50 px-2.5 py-1.5 text-xs text-navy-950 placeholder:text-navy-900/45"
          />
          <button
            type="button"
            onClick={handleSmartRecommend}
            disabled={sending}
            className="rounded-lg border border-emerald-600/30 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-800 transition hover:bg-emerald-100 disabled:opacity-50"
          >
            Find Smart Recommendations
          </button>
        </div>

        <div className="mt-3 flex flex-wrap gap-2">
          {SUGGESTED_PROMPTS.map((q) => (
            <button
              key={q}
              type="button"
              onClick={() => submitPrompt(q)}
              disabled={sending}
              className="rounded-full border border-navy-900/10 bg-cream-50 px-3 py-1 text-xs font-medium text-navy-900/80 transition hover:border-emerald-500/40 hover:bg-emerald-50"
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
              onClick={loadInitialState}
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
          aria-label="Travel concierge messages"
          className="mt-4 max-h-96 space-y-3 overflow-y-auto rounded-xl border border-navy-900/10 bg-cream-50/70 p-4"
        >
          {loading ? (
            <div className="space-y-3 py-2" aria-busy="true">
              <div className="h-10 w-3/4 animate-pulse rounded-2xl bg-cream-200/70" />
              <div className="ml-auto h-10 w-2/3 animate-pulse rounded-2xl bg-navy-900/10" />
              <div className="h-14 w-4/5 animate-pulse rounded-2xl bg-cream-200/70" />
            </div>
          ) : messages.length === 0 ? (
            <div className="py-6 text-center text-sm text-navy-900/65">
              Ask about routes, cheapest fares, overnight sleepers, seat preferences, booking steps, or your own PNR status.
            </div>
          ) : (
            messages.map((msg) => {
              const isUser = msg.role === "user";
              return (
                <div
                  key={msg.id}
                  className={`flex ${isUser ? "justify-end" : "justify-start"}`}
                >
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
                    {!isUser && (msg.provider || msg.intent) ? (
                      <div className="mt-1.5 flex flex-wrap items-center gap-2 text-[11px] text-navy-900/55">
                        <span>{formatMessageProviderLabel(msg.provider)}</span>
                        {msg.intent ? <span>• {formatAiIntentLabel(msg.intent)}</span> : null}
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
                <span>Checking live schedules &amp; seats...</span>
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
            placeholder="Ask e.g. 'Cheapest bus from Patna to Ranchi tomorrow under ₹800'"
            className="flex-1 rounded-xl border border-navy-900/15 bg-white px-4 py-2.5 text-sm text-navy-950 focus:border-emerald-500 focus:outline-none"
          />
          <button
            type="submit"
            disabled={sending || !input.trim()}
            className="inline-flex items-center gap-2 rounded-xl bg-navy-950 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-navy-800 disabled:opacity-50"
          >
            <Send className="h-4 w-4" />
            <span>{sending ? "Thinking..." : "Send"}</span>
          </button>
        </form>
      </div>

      {recommendations.length > 0 ? (
        <div className="rounded-2xl border border-navy-900/10 bg-white p-5 shadow-sm">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-base font-bold text-navy-950">
              Recommended Live Schedules ({recommendations.length})
            </h2>
            <span className="text-xs font-medium text-emerald-700">Live IST Schedule &amp; Availability</span>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            {recommendations.map((trip) => (
              <div
                key={trip.id}
                className="flex flex-col justify-between rounded-xl border border-navy-900/10 bg-cream-50/70 p-4"
              >
                <div>
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="text-sm font-bold text-navy-950">{trip.route_name}</p>
                      <p className="text-xs text-navy-900/65">
                        {trip.operator_name} • {trip.bus_type?.replace(/_/g, " ")} ({trip.seat_layout})
                      </p>
                    </div>
                    <span className="rounded-lg bg-emerald-50 px-2.5 py-1 text-sm font-bold text-emerald-700">
                      ₹{Number(trip.base_fare).toFixed(0)}
                    </span>
                  </div>
                  <div className="mt-2.5 flex flex-wrap items-center gap-3 text-xs text-navy-900/75">
                    <span className="inline-flex items-center gap-1">
                      <Clock className="h-3.5 w-3.5 text-emerald-600" />
                      {trip.travel_date} • {trip.departure_time} → {trip.arrival_time} ({trip.duration_display})
                    </span>
                    <span className="inline-flex items-center gap-1 font-semibold text-navy-950">
                      <Bus className="h-3.5 w-3.5 text-navy-700" />
                      {trip.available_seats} seats open
                    </span>
                  </div>
                  {trip.reasons?.length ? (
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {trip.reasons.map((r) => (
                        <span
                          key={r}
                          className="rounded-full bg-white px-2.5 py-0.5 text-[11px] font-medium text-navy-900/80 border border-navy-900/10"
                        >
                          {r}
                        </span>
                      ))}
                    </div>
                  ) : null}
                </div>

                <div className="mt-3 pt-3 border-t border-navy-900/10 flex justify-end">
                  <Link
                    to={(() => {
                      const qs = new URLSearchParams();
                      if (trip.matched_boarding_stop_id) {
                        qs.set("boarding_stop_id", String(trip.matched_boarding_stop_id));
                      }
                      if (trip.matched_drop_stop_id) {
                        qs.set("drop_stop_id", String(trip.matched_drop_stop_id));
                      }
                      const q = qs.toString();
                      return `/trips/${trip.id}/seats${q ? `?${q}` : ""}`;
                    })()}
                    className="inline-flex items-center gap-1.5 rounded-lg bg-navy-950 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-navy-800"
                  >
                    <span>Select Seats</span>
                    <ArrowRight className="h-3.5 w-3.5" />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  );
}
