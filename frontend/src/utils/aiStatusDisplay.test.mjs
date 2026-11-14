import assert from "node:assert/strict";
import test from "node:test";
import {
  formatAiIntentLabel,
  formatMessageProviderLabel,
  getAdminAiPresentation,
  getPassengerAiPresentation,
} from "./aiStatusDisplay.js";

test("passenger AI presentation hides internal model names and fallback codes", () => {
  const live = getPassengerAiPresentation({
    provider: "gemini",
    model: "gemini-3.8-flash",
    status: {
      active_provider: "gemini",
      last_model_failover: true,
      fallback_reason: "alternative_model:gemini-3.5-flash-lite:rate_limited",
    },
  });
  assert.equal(live.isLive, true);
  assert.equal(live.badgeLabel, "Smart AI Active");
  assert.ok(!live.badgeLabel.includes("gemini"));
  assert.ok(!live.statusNotice.includes("3.5"));
  assert.ok(!live.statusNotice.includes("rate_limited"));

  const fallback = getPassengerAiPresentation({
    provider: "local_fallback",
    status: { active_provider: "local_fallback", fallback_reason: "http_429_quota" },
  });
  assert.equal(fallback.isLive, false);
  assert.equal(fallback.badgeLabel, "Offline Schedule Mode");
  assert.ok(!fallback.statusNotice.toLowerCase().includes("postgresql"));
  assert.ok(!fallback.statusNotice.includes("429"));
});

test("admin AI presentation translates telemetry into readable operational summaries", () => {
  const failover = getAdminAiPresentation({
    provider: "gemini",
    status: {
      configured_provider: "auto",
      last_model_failover: true,
      degraded: true,
      fallback_reason: "alternative_model:gemini-3.5-flash-lite:rate_limited",
    },
  });
  assert.equal(failover.providerTitle, "Cloud AI Active");
  assert.equal(failover.healthLabel, "Healthy (Backup Active)");
  assert.ok(!failover.modeSummary.includes("auto"));
  assert.ok(!failover.healthDetail.includes("alternative_model"));
});

test("intent and message provider labels format cleanly", () => {
  assert.equal(formatAiIntentLabel("trip_recommendation"), "Trip Search & Advice");
  assert.equal(formatAiIntentLabel("custom_topic_name"), "Custom Topic Name");
  assert.equal(formatMessageProviderLabel("gemini"), "Smart AI");
  assert.equal(formatMessageProviderLabel("local_fallback"), "Schedule Assistant");
});
