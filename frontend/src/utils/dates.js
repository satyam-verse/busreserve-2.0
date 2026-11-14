export const APP_TIMEZONE = "Asia/Kolkata";

/**
 * Format an instant (`Date` or epoch ms) as a `YYYY-MM-DD` calendar date in Asia/Kolkata (IST).
 * Never uses `Date.prototype.toISOString()`, preventing UTC-vs-IST day shifts between 00:00 and 05:30 IST.
 */
export function formatIstDate(dateInput = new Date()) {
  const instant = dateInput instanceof Date ? dateInput : new Date(dateInput);
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: APP_TIMEZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(instant);

  const map = {};
  parts.forEach((p) => {
    if (p.type !== "literal") map[p.type] = p.value;
  });
  return `${map.year}-${map.month}-${map.day}`;
}

/**
 * Add calendar days to an opaque `YYYY-MM-DD` string using UTC calendar arithmetic
 * so browser timezone/DST never shifts the resulting calendar day.
 */
export function addDaysToIso(isoDate, days) {
  const [year, month, day] = isoDate.split("-").map(Number);
  const utc = new Date(Date.UTC(year, month - 1, day + days));
  const y = utc.getUTCFullYear();
  const m = String(utc.getUTCMonth() + 1).padStart(2, "0");
  const d = String(utc.getUTCDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export function getTodayIstIso(now = new Date()) {
  return formatIstDate(now);
}

export function addDaysIstIso(days, now = new Date()) {
  return addDaysToIso(formatIstDate(now), days);
}

const SHORT_MONTHS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

const SHORT_DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

/**
 * Format an opaque `YYYY-MM-DD` string using UTC calendar fields so client TZ never shifts it.
 */
export function formatIsoShortDisplay(isoDate) {
  if (!isoDate || !/^\d{4}-\d{2}-\d{2}$/.test(isoDate)) return isoDate || "";
  const [y, m, d] = isoDate.split("-").map(Number);
  const utc = new Date(Date.UTC(y, m - 1, d));
  return `${SHORT_DAYS[utc.getUTCDay()]}, ${String(d).padStart(2, "0")} ${SHORT_MONTHS[m - 1]}`;
}

export function getMonthLabel(year, month1Indexed) {
  return `${SHORT_MONTHS[(month1Indexed - 1 + 12) % 12]} ${year}`;
}

/**
 * Return leading empty cell count (0=Sun..6=Sat) and day count for a given year/month.
 */
export function getCalendarMonthMeta(year, month1Indexed) {
  const firstDow = new Date(Date.UTC(year, month1Indexed - 1, 1)).getUTCDay();
  const daysInMonth = new Date(Date.UTC(year, month1Indexed, 0)).getUTCDate();
  return { firstDow, daysInMonth };
}

export function getIstClockLabel(now = new Date()) {
  return new Intl.DateTimeFormat("en-IN", {
    timeZone: APP_TIMEZONE,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(now);
}
