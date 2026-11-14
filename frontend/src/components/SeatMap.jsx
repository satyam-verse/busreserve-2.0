import { useState } from "react";
import { Disc, Sparkles, Star, Zap } from "lucide-react";

function groupSeatsByRow(seats) {
  const rows = new Map();
  seats.forEach((seat) => {
    const match = seat.seat_number.match(/^(\d+)([A-Z]+)$/);
    const rowNum = match ? Number(match[1]) : 0;
    const col = match ? match[2] : seat.seat_number;
    if (!rows.has(rowNum)) {
      rows.set(rowNum, {});
    }
    rows.get(rowNum)[col] = seat;
  });
  return Array.from(rows.entries()).sort((a, b) => a[0] - b[0]);
}

const SEAT_SHORT_LABEL = {
  WINDOW: "WIN",
  AISLE: "ASL",
  SLEEPER_LOWER: "SL-L",
  SLEEPER_UPPER: "SL-U",
};

export default function SeatMap({
  seats,
  selectedSeatNumber,
  onSelectSeat,
  seatLayout = "2+2",
  busType = "",
  highlightTier = "ALL",
}) {
  const rows = groupSeatsByRow(seats);
  const [hoveredSeat, setHoveredSeat] = useState(null);

  const renderSeatButton = (seat) => {
    if (!seat) {
      return <div className="h-12 w-12" />;
    }

    const isSelected = selectedSeatNumber === seat.seat_number;
    const isOccupied = !seat.is_available;
    const tier = seat.seat_tier || "STANDARD";
    const isDimmed =
      highlightTier !== "ALL" && tier !== highlightTier && !isSelected && !isOccupied;

    let styleClass = "";
    if (isOccupied) {
      styleClass =
        "cursor-not-allowed border-rose-300 bg-rose-100 text-rose-700 opacity-75";
    } else if (isSelected) {
      styleClass =
        "border-amber-400 bg-navy-950 text-white shadow-lg ring-2 ring-amber-400 scale-105 z-10";
    } else if (tier === "PREMIUM") {
      styleClass =
        "border-amber-400 bg-gradient-to-br from-amber-50 to-amber-100/70 text-amber-950 hover:bg-amber-100 hover:shadow-md ring-1 ring-amber-300/60";
    } else if (tier === "SLEEPER") {
      styleClass =
        "border-indigo-400 bg-gradient-to-br from-indigo-50 to-indigo-100/70 text-indigo-950 hover:bg-indigo-100 hover:shadow-md ring-1 ring-indigo-300/60";
    } else {
      // STANDARD
      styleClass =
        "border-emerald-500 bg-emerald-50 text-emerald-950 hover:bg-emerald-100 hover:shadow-sm";
    }

    if (isDimmed) {
      styleClass += " opacity-40 grayscale-[40%]";
    }

    return (
      <div key={seat.id} className="relative group">
        <button
          type="button"
          disabled={isOccupied}
          onClick={() => onSelectSeat(seat)}
          onMouseEnter={() => setHoveredSeat(seat)}
          onMouseLeave={() => setHoveredSeat(null)}
          onFocus={() => setHoveredSeat(seat)}
          onBlur={() => setHoveredSeat(null)}
          title={`Seat ${seat.seat_number} (${tier} • ${seat.seat_type}) — ${
            isOccupied ? "Occupied" : `₹${seat.fare != null ? Number(seat.fare).toFixed(0) : "--"}`
          }`}
          aria-pressed={isSelected}
          aria-label={`Seat ${seat.seat_number}, ${tier} tier, ${
            isOccupied ? "occupied" : isSelected ? "selected" : "available"
          }`}
          className={`flex h-12 w-12 flex-col items-center justify-center rounded-xl border-2 text-xs font-bold transition-all ${styleClass}`}
        >
          <div className="flex items-center gap-0.5">
            <span>{seat.seat_number}</span>
            {tier === "PREMIUM" && !isSelected && (
              <Star className="h-2.5 w-2.5 fill-amber-500 text-amber-500" />
            )}
          </div>
          <span className="text-[9px] font-medium opacity-85">
            {seat.fare != null ? `₹${Number(seat.fare).toFixed(0)}` : SEAT_SHORT_LABEL[seat.seat_type] || "ST"}
          </span>
        </button>

        {/* Hover Tooltip Card */}
        {hoveredSeat?.id === seat.id && (
          <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 rounded-xl bg-navy-950 p-2.5 text-white shadow-xl z-30 pointer-events-none text-[11px] animate-fade-in">
            <div className="flex items-center justify-between border-b border-white/10 pb-1.5 mb-1.5">
              <span className="font-bold text-white">Seat {seat.seat_number}</span>
              <span
                className={`rounded px-1.5 py-0.5 text-[9px] font-bold ${
                  tier === "PREMIUM"
                    ? "bg-amber-400 text-navy-950"
                    : tier === "SLEEPER"
                    ? "bg-indigo-400 text-navy-950"
                    : "bg-emerald-400 text-navy-950"
                }`}
              >
                {tier}
              </span>
            </div>
            <div className="space-y-1 text-slate-300">
              <div className="flex justify-between">
                <span>Fare:</span>
                <span className="font-bold text-emerald-400">
                  ₹{seat.fare != null ? Number(seat.fare).toFixed(0) : "--"}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Type:</span>
                <span className="font-medium text-white">{seat.seat_type?.replace(/_/g, " ")}</span>
              </div>
              {seat.position_type && (
                <div className="flex justify-between">
                  <span>Position:</span>
                  <span className="text-white">{seat.position_type}</span>
                </div>
              )}
              {seat.amenities && seat.amenities.length > 0 && (
                <div className="pt-1 border-t border-white/10 flex flex-wrap gap-1">
                  {seat.amenities.slice(0, 3).map((am, i) => (
                    <span key={i} className="rounded bg-white/10 px-1 text-[9px] text-amber-200">
                      {am}
                    </span>
                  ))}
                </div>
              )}
            </div>
            {/* Tooltip caret */}
            <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-1 border-4 border-transparent border-t-navy-950" />
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="rounded-2xl border border-cream-200 bg-white p-5 shadow-sm space-y-4">
      {/* Header and Legend */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-cream-100 pb-4">
        <div>
          <h2 className="font-display text-lg font-bold text-navy-900">
            Coach Seat Map
          </h2>
          <p className="text-xs text-slate-500">
            {seatLayout} {busType ? busType.replace(/_/g, " ") : "Coach"} • Hover seat for amenities &amp; exact fare
          </p>
        </div>

        {/* Tier Badges & Legend */}
        <div className="flex flex-wrap items-center gap-2.5 text-xs font-medium">
          <span className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-50 px-2 py-1 border border-emerald-300 text-emerald-900 text-[11px] font-semibold">
            <span className="h-3 w-3 rounded bg-emerald-500" />
            Standard
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-lg bg-amber-50 px-2 py-1 border border-amber-300 text-amber-900 text-[11px] font-semibold">
            <Star className="h-3 w-3 fill-amber-500 text-amber-500" />
            Premium
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-lg bg-indigo-50 px-2 py-1 border border-indigo-300 text-indigo-900 text-[11px] font-semibold">
            <span className="h-3 w-3 rounded bg-indigo-500" />
            Sleeper
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-lg bg-rose-50 px-2 py-1 border border-rose-300 text-rose-700 text-[11px]">
            <span className="h-3 w-3 rounded bg-rose-300" />
            Booked
          </span>
        </div>
      </div>

      {/* Bus Graphic Container */}
      <div className="relative mx-auto max-w-[340px] rounded-[28px] border-2 border-navy-900/20 bg-gradient-to-b from-white via-cream-50 to-cream-100/70 p-4 shadow-card">
        {/* Coach Windshield Cap */}
        <div
          aria-hidden="true"
          className="mx-auto -mt-1.5 mb-3 h-1.5 w-24 rounded-full bg-navy-900/20"
        />

        <div className="mb-4 flex items-center justify-between border-b border-dashed border-navy-900/15 pb-3 text-[11px] font-bold uppercase tracking-wider text-navy-900/60">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-cream-100 px-2.5 py-1 text-navy-800">
            Front Door
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-navy-900/15 bg-navy-950 px-2.5 py-1 text-cream-50">
            <Disc className="h-3.5 w-3.5 text-amber-400" /> Captain
          </span>
        </div>

        <div className="space-y-2.5">
          {rows.map(([rowNum, cols]) => (
            <div key={rowNum} className="flex items-center justify-between gap-2">
              <div className="flex gap-2">
                {renderSeatButton(cols.A)}
                {renderSeatButton(cols.B)}
              </div>
              <div className="flex w-7 flex-col items-center justify-center">
                <span className="rounded-md bg-navy-900/5 px-1.5 py-0.5 font-mono text-[10px] font-bold text-navy-900/50">
                  R{rowNum}
                </span>
              </div>
              <div className="flex gap-2">
                {renderSeatButton(cols.C)}
                {renderSeatButton(cols.D)}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-4 flex items-center justify-center border-t border-dashed border-navy-900/15 pt-2.5 text-[10px] font-bold uppercase tracking-[0.2em] text-navy-900/45">
          Rear Bulkhead &amp; Luggage Bay
        </div>
      </div>
    </div>
  );
}
