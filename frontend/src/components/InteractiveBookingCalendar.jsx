import { Calendar, ChevronLeft, ChevronRight } from "lucide-react";
import { useEffect, useId, useMemo, useRef, useState } from "react";
import {
  addDaysToIso,
  formatIsoShortDisplay,
  getCalendarMonthMeta,
  getMonthLabel,
  getTodayIstIso,
} from "../utils/dates";

const WEEKDAY_HEADERS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];

export default function InteractiveBookingCalendar({
  label = "Travel Date",
  value,
  onChange,
  minDate,
  maxDate,
  horizonDays = 90,
  compact = false,
}) {
  const inputId = useId();
  const containerRef = useRef(null);
  const [open, setOpen] = useState(false);

  const safeMin = minDate || getTodayIstIso();
  const safeMax = maxDate || addDaysToIso(safeMin, horizonDays);

  const initialAnchor = value && value >= safeMin && value <= safeMax ? value : safeMin;
  const [viewYear, setViewYear] = useState(() => Number(initialAnchor.slice(0, 4)));
  const [viewMonth, setViewMonth] = useState(() => Number(initialAnchor.slice(5, 7)));

  useEffect(() => {
    if (value && /^\d{4}-\d{2}-\d{2}$/.test(value)) {
      setViewYear(Number(value.slice(0, 4)));
      setViewMonth(Number(value.slice(5, 7)));
    }
  }, [value]);

  useEffect(() => {
    function handleOutside(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleOutside);
    return () => document.removeEventListener("mousedown", handleOutside);
  }, []);

  const quickDates = useMemo(
    () => [
      { label: "Today", iso: safeMin },
      { label: "Tomorrow", iso: addDaysToIso(safeMin, 1) },
      { label: "+2d", iso: addDaysToIso(safeMin, 2) },
    ],
    [safeMin]
  );

  const { firstDow, daysInMonth } = getCalendarMonthMeta(viewYear, viewMonth);

  const cells = useMemo(() => {
    const arr = [];
    for (let i = 0; i < firstDow; i += 1) {
      arr.push(null);
    }
    for (let day = 1; day <= daysInMonth; day += 1) {
      const iso = `${viewYear}-${String(viewMonth).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
      arr.push({ day, iso });
    }
    return arr;
  }, [firstDow, daysInMonth, viewYear, viewMonth]);

  const minYm = Number(safeMin.slice(0, 4)) * 12 + Number(safeMin.slice(5, 7));
  const maxYm = Number(safeMax.slice(0, 4)) * 12 + Number(safeMax.slice(5, 7));
  const curYm = viewYear * 12 + viewMonth;

  const canPrevMonth = curYm > minYm;
  const canNextMonth = curYm < maxYm;

  function stepMonth(delta) {
    const nextTotal = curYm + delta;
    if (delta < 0 && !canPrevMonth) return;
    if (delta > 0 && !canNextMonth) return;
    const ny = Math.floor((nextTotal - 1) / 12);
    const nm = ((nextTotal - 1) % 12) + 1;
    setViewYear(ny);
    setViewMonth(nm);
  }

  return (
    <div ref={containerRef} className="relative">
      {!compact && label ? (
        <label
          htmlFor={inputId}
          className="mb-1.5 flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-slate-500"
        >
          <span className="inline-flex items-center gap-1.5">
            <Calendar className="h-3.5 w-3.5 text-emerald-600" />
            {label}
          </span>
          <span className="text-[10px] font-medium normal-case text-slate-500">
            {horizonDays}d IST window
          </span>
        </label>
      ) : null}

      <div className="flex flex-col gap-1.5">
        <div className="flex items-center gap-1.5">
          <button
            id={inputId}
            type="button"
            aria-expanded={open}
            aria-haspopup="dialog"
            onClick={() => setOpen((prev) => !prev)}
            onKeyDown={(e) => {
              if (e.key === "Escape") setOpen(false);
            }}
            className={`flex flex-1 items-center justify-between gap-2 rounded-xl border border-cream-200 bg-cream-50 text-left font-semibold text-navy-950 transition hover:border-emerald-400 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-200 ${
              compact ? "px-3 py-2.5 text-sm" : "px-3.5 py-3 text-sm"
            }`}
          >
            <span className="flex items-center gap-2 truncate">
              <Calendar className="h-4 w-4 shrink-0 text-emerald-600" />
              <span className="truncate">
                {value ? formatIsoShortDisplay(value) : "Any open date"}
              </span>
            </span>
            {value ? (
              <span className="shrink-0 font-mono text-[11px] font-medium text-slate-500">
                {value}
              </span>
            ) : null}
          </button>

          {/* Accessible synced native date input for screen readers / quick keyboard entry */}
          <input
            type="date"
            aria-label={`${label} native picker`}
            min={safeMin}
            max={safeMax}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            className="sr-only"
          />
        </div>

        {/* Quick IST Pills */}
        {!compact ? (
          <div className="flex flex-wrap items-center gap-1.5">
            {quickDates.map((qd) => {
              const disabled = qd.iso < safeMin || qd.iso > safeMax;
              const active = value === qd.iso;
              return (
                <button
                  key={qd.label}
                  type="button"
                  disabled={disabled}
                  onClick={() => {
                    onChange(qd.iso);
                    setOpen(false);
                  }}
                  className={`rounded-lg px-2 py-0.5 text-[11px] font-semibold transition ${
                    active
                      ? "bg-navy-950 text-white"
                      : "border border-cream-200 bg-cream-50 text-navy-800 hover:border-emerald-400 hover:bg-emerald-50"
                  } disabled:opacity-40`}
                >
                  {qd.label}
                </button>
              );
            })}
            {value ? (
              <button
                type="button"
                onClick={() => onChange("")}
                className="ml-auto text-[11px] font-medium text-slate-500 underline-offset-2 hover:text-navy-900 hover:underline"
              >
                All dates
              </button>
            ) : null}
          </div>
        ) : null}
      </div>

      {open ? (
        <div
          role="dialog"
          tabIndex={-1}
          onKeyDown={(e) => {
            if (e.key === "Escape") {
              setOpen(false);
            }
          }}
          aria-label="IST 90-day booking calendar"
          className="absolute left-0 z-50 mt-2 w-72 max-w-[calc(100vw-2rem)] rounded-2xl border border-cream-200 bg-white p-4 shadow-editorial sm:w-80"
        >
          <div className="mb-3 flex items-center justify-between">
            <button
              type="button"
              onClick={() => stepMonth(-1)}
              disabled={!canPrevMonth}
              aria-label="Previous month"
              className="rounded-lg border border-cream-200 p-1.5 text-navy-900 transition hover:bg-cream-50 disabled:cursor-not-allowed disabled:opacity-35"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <div className="text-center">
              <p className="font-display text-sm font-bold text-navy-950">
                {getMonthLabel(viewYear, viewMonth)}
              </p>
              <p className="font-mono text-[10px] text-slate-500">Asia/Kolkata (IST)</p>
            </div>
            <button
              type="button"
              onClick={() => stepMonth(1)}
              disabled={!canNextMonth}
              aria-label="Next month"
              className="rounded-lg border border-cream-200 p-1.5 text-navy-900 transition hover:bg-cream-50 disabled:cursor-not-allowed disabled:opacity-35"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>

          <div className="grid grid-cols-7 gap-1 text-center">
            {WEEKDAY_HEADERS.map((wd) => (
              <span
                key={wd}
                className="py-1 font-mono text-[10px] font-semibold uppercase text-slate-400"
              >
                {wd}
              </span>
            ))}

            {cells.map((cell, idx) => {
              if (!cell) {
                return <div key={`empty-${idx}`} />;
              }
              const inWindow = cell.iso >= safeMin && cell.iso <= safeMax;
              const isSelected = value === cell.iso;
              const isToday = cell.iso === safeMin;

              return (
                <button
                  key={cell.iso}
                  type="button"
                  disabled={!inWindow}
                  onClick={() => {
                    onChange(cell.iso);
                    setOpen(false);
                  }}
                  aria-label={`Select ${cell.iso}`}
                  aria-current={isToday ? "date" : undefined}
                  aria-pressed={isSelected}
                  className={`relative flex h-9 items-center justify-center rounded-lg text-xs font-semibold transition ${
                    isSelected
                      ? "bg-emerald-600 text-white shadow-sm"
                      : inWindow
                        ? "text-navy-950 hover:bg-emerald-50 hover:text-emerald-800"
                        : "cursor-not-allowed text-slate-300"
                  }`}
                >
                  <span>{cell.day}</span>
                  {isToday && !isSelected ? (
                    <span className="absolute bottom-1 h-1 w-1 rounded-full bg-brass-500" />
                  ) : null}
                </button>
              );
            })}
          </div>

          <div className="mt-3 flex items-center justify-between border-t border-cream-200 pt-2.5 text-[11px] text-slate-500">
            <span>
              Valid: {safeMin} → {safeMax}
            </span>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="font-semibold text-navy-900 hover:underline"
            >
              Close
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
