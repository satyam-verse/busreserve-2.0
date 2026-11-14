/**
 * Translate backend AI status telemetry into understandable UI copy
 * without exposing internal model identifiers, API config flags, or raw error codes.
 */

const INTENT_LABELS = {
  trip_recommendation: "Trip Search & Advice",
  route_search: "Route Search",
  pnr_lookup: "Booking Status",
  booking_help: "Booking Guidance",
  seat_advice: "Seat Guidance",
  fare_comparison: "Fare Comparison",
  general_help: "Travel Support",
  operations_summary: "Operations Summary",
  revenue_analysis: "Revenue Insights",
  occupancy_analysis: "Occupancy Insights",
  fleet_analysis: "Fleet Overview",
  route_performance: "Route Performance",
  anomaly_check: "Booking Anomalies",
};

export function formatAiIntentLabel(intent) {
  if (!intent || typeof intent !== "string") return "";
  if (INTENT_LABELS[intent]) return INTENT_LABELS[intent];
  return intent
    .replaceAll("_", " ")
    .replace(/\b\w/g, (ch) => ch.toUpperCase());
}

export function getPassengerAiPresentation(statusPayload) {
  const telemetry = statusPayload?.status || {};
  const activeProvider = statusPayload?.provider || telemetry.active_provider || "local_fallback";
  const isGemini = activeProvider === "gemini";
  const usedBackupModel = Boolean(telemetry.last_model_failover);

  if (isGemini) {
    return {
      isLive: true,
      badgeLabel: "Smart AI Active",
      badgeTone: "emerald",
      statusNotice: usedBackupModel
        ? "Connected using backup AI capacity so your responses remain uninterrupted."
        : "Connected to live travel AI grounded in real-time schedules and seat availability.",
      messageSourceLabel: () => "Smart AI",
    };
  }

  return {
    isLive: false,
    badgeLabel: "Offline Schedule Mode",
    badgeTone: "amber",
    statusNotice:
      "Live AI capacity is temporarily busy. Answers are generated directly from verified route schedules, fares, and booking records.",
    messageSourceLabel: () => "Schedule Assistant",
  };
}

export function getAdminAiPresentation(statusPayload) {
  const telemetry = statusPayload?.status || {};
  const activeProvider = statusPayload?.provider || telemetry.active_provider || "local_fallback";
  const isGemini = activeProvider === "gemini";
  const isDegraded = Boolean(telemetry.degraded);
  const hasFailover = Boolean(telemetry.last_model_failover);

  let modeSummary = "Automatic failover enabled";
  if (telemetry.configured_provider === "local_fallback") {
    modeSummary = "Local schedule engine only";
  } else if (isGemini && hasFailover) {
    modeSummary = "Primary capacity throttled; backup cloud tier active";
  } else if (isGemini) {
    modeSummary = "Primary cloud AI active with automatic fallback";
  }

  let healthLabel = "Healthy";
  let healthTone = "emerald";
  if (!isGemini) {
    healthLabel = "Fallback Active";
    healthTone = "amber";
  } else if (isDegraded || hasFailover) {
    healthLabel = "Healthy (Backup Active)";
    healthTone = "amber";
  }

  let healthDetail = "All AI responses operating normally";
  const rawReason = String(telemetry.fallback_reason || telemetry.last_error_reason || "").toLowerCase();
  if (!isGemini) {
    if (rawReason.includes("rate") || rawReason.includes("429") || rawReason.includes("quota")) {
      healthDetail = "Daily or per-minute cloud quota reached; verified database fallback is handling requests";
    } else if (rawReason.includes("cooldown")) {
      healthDetail = "Temporary cloud cooldown active; automatically recovers once window resets";
    } else {
      healthDetail = "Database-grounded local assistant is serving responses without interruption";
    }
  } else if (hasFailover || rawReason.includes("rate_limited") || rawReason.includes("429")) {
    healthDetail = "Backup cloud tier engaged after primary rate limit";
  }

  return {
    isGemini,
    providerTitle: isGemini ? "Cloud AI Active" : "Local Fallback Active",
    modeSummary,
    healthLabel,
    healthTone,
    healthDetail,
  };
}

export function formatMessageProviderLabel(provider) {
  return provider === "gemini" ? "Smart AI" : "Schedule Assistant";
}
