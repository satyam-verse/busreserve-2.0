import assert from "node:assert/strict";
import test from "node:test";
import { addDaysIstIso, addDaysToIso, formatIstDate, getTodayIstIso } from "./dates.js";

test("formats UTC timestamps in Asia/Kolkata across 00:00-05:30 IST boundary", () => {
  // 2026-11-11 18:29:59 UTC == 2026-11-11 23:59:59 IST
  const beforeMidnightIst = new Date("2026-11-11T18:29:59Z");
  assert.equal(formatIstDate(beforeMidnightIst), "2026-11-11");

  // 2026-11-11 18:30:00 UTC == 2026-11-12 00:00:00 IST (still Nov 11 in UTC!)
  const atMidnightIst = new Date("2026-11-11T18:30:00Z");
  assert.equal(getTodayIstIso(atMidnightIst), "2026-11-12");
  assert.equal(addDaysIstIso(1, atMidnightIst), "2026-11-13");
  assert.equal(addDaysIstIso(90, atMidnightIst), "2027-02-10");

  // 2026-11-11 23:59:59 UTC == 2026-11-12 05:29:59 IST (still Nov 11 in UTC!)
  const at0529Ist = new Date("2026-11-11T23:59:59Z");
  assert.equal(getTodayIstIso(at0529Ist), "2026-11-12");
});

test("calendar arithmetic preserves exact YYYY-MM-DD strings without UTC shifting", () => {
  assert.equal(addDaysToIso("2026-11-12", 0), "2026-11-12");
  assert.equal(addDaysToIso("2026-11-12", 90), "2027-02-10");
  assert.equal(addDaysToIso("2026-11-12", -1), "2026-11-11");
});
