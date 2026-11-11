import {
  AlertTriangle,
  ArrowRight,
  Bus,
  CheckCircle2,
  Copy,
  Search,
  Ticket,
  XCircle,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { busApi } from "../services/api";

export default function BookingConfirmationPage() {
  const { pnr } = useParams();
  const location = useLocation();
  const navigate = useNavigate();

  const [lookupInput, setLookupInput] = useState(pnr || "");
  const [booking, setBooking] = useState(location.state?.booking || null);
  const [loading, setLoading] = useState(Boolean(pnr && !location.state?.booking));
  const [error, setError] = useState("");
  const [cancelling, setCancelling] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!pnr) {
      setBooking(null);
      setLoading(false);
      return;
    }
    let active = true;
    async function loadPnr() {
      try {
        setLoading(true);
        setError("");
        const resp = await busApi.getBooking(pnr);
        if (active) setBooking(resp.booking);
      } catch (err) {
        if (active) {
          setBooking(null);
          setError(err.message || "Booking not found.");
        }
      } finally {
        if (active) setLoading(false);
      }
    }
    loadPnr();
    return () => {
      active = false;
    };
  }, [pnr]);

  const handleLookup = (e) => {
    e.preventDefault();
    const cleaned = lookupInput.trim().toUpperCase();
    if (!cleaned) return;
    navigate(`/bookings/${encodeURIComponent(cleaned)}`);
  };

  const handleCancel = async () => {
    if (!booking) return;
    try {
      setCancelling(true);
      setError("");
      const resp = await busApi.cancelBooking(booking.pnr);
      setBooking(resp.booking);
    } catch (err) {
      setError(err.message || "Could not cancel booking.");
    } finally {
      setCancelling(false);
    }
  };

  const handleCopy = () => {
    if (!booking?.pnr || !navigator.clipboard) return;
    navigator.clipboard.writeText(booking.pnr);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  return (
    <div className="mx-auto max-w-4xl space-y-6 px-4 py-8 sm:px-6">
      <div className="rounded-2xl border border-cream-200 bg-white p-5 shadow-sm">
        <h1 className="flex items-center gap-2 font-display text-xl font-bold text-navy-900">
          <Ticket className="h-5 w-5 text-emerald-600" />
          Manage Reservation by PNR
        </h1>
        <form onSubmit={handleLookup} className="mt-3 flex flex-col gap-3 sm:flex-row">
          <input
            type="text"
            placeholder="Enter PNR (e.g. BRSEED0001)"
            value={lookupInput}
            onChange={(e) => setLookupInput(e.target.value.toUpperCase())}
            className="flex-1 rounded-xl border border-cream-200 bg-cream-50 px-4 py-2.5 font-mono text-sm uppercase focus:border-emerald-500 focus:outline-none"
          />
          <button
            type="submit"
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-navy-900 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-navy-800"
          >
            <Search className="h-4 w-4" />
            <span>Retrieve Ticket</span>
          </button>
        </form>
      </div>

      {loading && (
        <div className="rounded-2xl border border-cream-200 bg-white p-10 text-center text-sm text-slate-500">
          Fetching reservation details...
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2.5 rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm font-medium text-rose-800">
          <AlertTriangle className="h-5 w-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {booking && (
        <div className="overflow-hidden rounded-2xl border border-cream-200 bg-white shadow-md">
          <div
            className={`flex flex-wrap items-center justify-between gap-4 px-6 py-5 text-white ${
              booking.status === "CONFIRMED"
                ? "bg-gradient-to-r from-navy-900 to-emerald-800"
                : "bg-gradient-to-r from-navy-900 to-rose-900"
            }`}
          >
            <div className="flex items-center gap-3">
              {booking.status === "CONFIRMED" ? (
                <CheckCircle2 className="h-8 w-8 text-emerald-300" />
              ) : (
                <XCircle className="h-8 w-8 text-rose-300" />
              )}
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-slate-200">
                  {booking.status === "CONFIRMED"
                    ? "Reservation Confirmed"
                    : "Reservation Cancelled"}
                </p>
                <div className="mt-0.5 flex items-center gap-2">
                  <span className="font-mono text-2xl font-extrabold tracking-wide">
                    {booking.pnr}
                  </span>
                  <button
                    type="button"
                    onClick={handleCopy}
                    title="Copy PNR"
                    className="rounded-lg bg-white/15 px-2 py-1 text-xs font-medium hover:bg-white/25"
                  >
                    <Copy className="inline h-3.5 w-3.5" /> {copied ? "Copied" : "Copy"}
                  </button>
                </div>
              </div>
            </div>

            <span
              className={`rounded-full px-3.5 py-1 text-xs font-bold tracking-wider ${
                booking.status === "CONFIRMED"
                  ? "bg-emerald-400/20 text-emerald-200"
                  : "bg-rose-400/20 text-rose-200"
              }`}
            >
              {booking.status}
            </span>
          </div>

          <div className="grid grid-cols-1 gap-6 p-6 md:grid-cols-2">
            <div className="space-y-4">
              <h2 className="flex items-center gap-2 font-display text-sm font-bold uppercase tracking-wider text-slate-400">
                <Bus className="h-4 w-4 text-emerald-600" />
                Journey Details
              </h2>
              <div className="rounded-xl bg-cream-50 p-4 space-y-2 text-sm">
                <p className="font-display text-lg font-bold text-navy-900">
                  {booking.trip?.source} <ArrowRight className="inline h-4 w-4" />{" "}
                  {booking.trip?.destination}
                </p>
                <p className="text-slate-600">
                  {booking.trip?.operator_name} •{" "}
                  <span className="font-semibold">{booking.trip?.bus_number}</span>
                </p>
                <p className="text-slate-600">
                  Date: <span className="font-semibold">{booking.trip?.travel_date}</span> •{" "}
                  {booking.trip?.departure_time} – {booking.trip?.arrival_time}
                </p>
                <div className="border-t border-cream-200 pt-2 text-xs text-slate-600">
                  <p>
                    Boarding:{" "}
                    <span className="font-semibold text-navy-900">
                      {booking.boarding_stop?.stop_name}
                    </span>
                  </p>
                  <p>
                    Drop:{" "}
                    <span className="font-semibold text-navy-900">
                      {booking.drop_stop?.stop_name}
                    </span>
                  </p>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <h2 className="font-display text-sm font-bold uppercase tracking-wider text-slate-400">
                Passenger &amp; Seat
              </h2>
              <div className="rounded-xl bg-cream-50 p-4 space-y-2 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Passenger</span>
                  <span className="font-bold text-navy-900">{booking.passenger_name}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Email</span>
                  <span className="font-medium text-navy-900">{booking.passenger_email}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Phone</span>
                  <span className="font-medium text-navy-900">{booking.passenger_phone}</span>
                </div>
                <div className="flex items-center justify-between border-t border-cream-200 pt-2">
                  <span className="text-slate-500">Seat</span>
                  <span className="rounded-lg bg-navy-900 px-2.5 py-0.5 font-mono text-xs font-bold text-white">
                    {booking.seat_number} ({booking.seat_type})
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Total Fare</span>
                  <span className="font-display text-xl font-extrabold text-emerald-700">
                    ₹{Number(booking.total_fare).toFixed(0)}
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-cream-100 bg-cream-50/70 px-6 py-4">
            <Link
              to="/search"
              className="text-sm font-semibold text-navy-800 hover:text-emerald-700"
            >
              ← Search more buses
            </Link>

            {booking.status === "CONFIRMED" && (
              <button
                type="button"
                disabled={cancelling}
                onClick={handleCancel}
                className="inline-flex items-center gap-2 rounded-xl border border-rose-300 bg-white px-4 py-2 text-sm font-semibold text-rose-700 transition hover:bg-rose-50 disabled:opacity-50"
              >
                <XCircle className="h-4 w-4" />
                <span>{cancelling ? "Cancelling..." : "Cancel Reservation"}</span>
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
