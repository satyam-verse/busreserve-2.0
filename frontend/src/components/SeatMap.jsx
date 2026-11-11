import { Disc } from "lucide-react";

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

export default function SeatMap({ seats, selectedSeatNumber, onSelectSeat }) {
  const rows = groupSeatsByRow(seats);

  const renderSeatButton = (seat) => {
    if (!seat) {
      return <div className="h-12 w-12" />;
    }

    const isSelected = selectedSeatNumber === seat.seat_number;
    const isOccupied = !seat.is_available;

    let styleClass =
      "border-emerald-500 bg-emerald-50 text-emerald-900 hover:bg-emerald-100 hover:shadow-sm";
    if (isOccupied) {
      styleClass =
        "cursor-not-allowed border-rose-300 bg-rose-100 text-rose-700 opacity-85";
    } else if (isSelected) {
      styleClass =
        "border-blue-700 bg-blue-600 text-white shadow-md ring-2 ring-blue-300";
    }

    return (
      <button
        key={seat.id}
        type="button"
        disabled={isOccupied}
        onClick={() => onSelectSeat(seat)}
        title={`Seat ${seat.seat_number} (${seat.seat_type}) — ${
          isOccupied ? "Occupied" : "Available"
        }`}
        aria-label={`Seat ${seat.seat_number}, ${
          isOccupied ? "occupied" : isSelected ? "selected" : "available"
        }`}
        className={`flex h-12 w-12 flex-col items-center justify-center rounded-xl border-2 text-xs font-bold transition-all ${styleClass}`}
      >
        <span>{seat.seat_number}</span>
        <span className="text-[9px] font-medium opacity-80">
          {seat.seat_type === "WINDOW" ? "WIN" : "ASL"}
        </span>
      </button>
    );
  };

  return (
    <div className="rounded-2xl border border-cream-200 bg-white p-5 shadow-sm">
      <div className="mb-5 flex flex-wrap items-center justify-between gap-3 border-b border-cream-100 pb-4">
        <div>
          <h2 className="font-display text-lg font-bold text-navy-900">
            Coach Seat Map
          </h2>
          <p className="text-xs text-slate-500">
            2+2 Executive AC Coach • Click an available green seat to reserve
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3 text-xs font-medium">
          <span className="inline-flex items-center gap-1.5">
            <span className="h-4 w-4 rounded border-2 border-emerald-500 bg-emerald-50" />
            Available
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-4 w-4 rounded border-2 border-rose-300 bg-rose-100" />
            Occupied
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-4 w-4 rounded border-2 border-blue-700 bg-blue-600" />
            Selected
          </span>
        </div>
      </div>

      <div className="mx-auto max-w-xs rounded-2xl border-2 border-navy-900/15 bg-cream-50 p-4">
        <div className="mb-4 flex items-center justify-between border-b border-dashed border-cream-200 pb-3 text-xs font-semibold uppercase tracking-wider text-slate-400">
          <span>Front Entrance</span>
          <span className="inline-flex items-center gap-1 text-navy-800">
            <Disc className="h-4 w-4" /> Driver
          </span>
        </div>

        <div className="space-y-2.5">
          {rows.map(([rowNum, cols]) => (
            <div key={rowNum} className="flex items-center justify-between gap-2">
              <div className="flex gap-2">
                {renderSeatButton(cols.A)}
                {renderSeatButton(cols.B)}
              </div>
              <span className="w-6 text-center text-[11px] font-semibold text-slate-400">
                {rowNum}
              </span>
              <div className="flex gap-2">
                {renderSeatButton(cols.C)}
                {renderSeatButton(cols.D)}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
