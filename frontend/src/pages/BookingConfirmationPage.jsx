import {
  AlertTriangle,
  ArrowRight,
  Bus,
  CheckCircle2,
  Copy,
  CreditCard,
  Download,
  Mail,
  Navigation,
  Receipt,
  Search,
  Share2,
  ShieldCheck,
  Ticket,
  XCircle,
} from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";
import { busApi } from "../services/api";
import LiveTrackingModal from "../components/LiveTrackingModal";
import ShareJourneyModal from "../components/ShareJourneyModal";

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
  const [trackingOpen, setTrackingOpen] = useState(false);
  const [shareOpen, setShareOpen] = useState(false);

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
      let cancelPayload = {};
      if (booking.is_masked) {
        const inputEmail = window.prompt(
          "To cancel this guest reservation, please confirm the passenger email address:"
        );
        if (!inputEmail) {
          setCancelling(false);
          return;
        }
        cancelPayload = { passenger_email: inputEmail.trim() };
      } else if (booking.passenger_email) {
        cancelPayload = { passenger_email: booking.passenger_email };
      }
      const resp = await busApi.cancelBooking(booking.pnr, cancelPayload);
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
              <h2 className="flex items-center gap-2 font-display text-xs font-bold uppercase tracking-[0.18em] text-navy-900/55">
                <Bus className="h-4 w-4 text-emerald-700" />
                Journey Details
              </h2>
              <div className="space-y-3 rounded-2xl border border-navy-900/10 bg-cream-50/90 p-5 text-sm">
                <p className="font-serif text-2xl font-normal tracking-tight text-navy-950">
                  {booking.trip?.source}{" "}
                  <ArrowRight className="mx-1 inline h-4 w-4 text-emerald-700" />{" "}
                  {booking.trip?.destination}
                </p>
                <p className="text-slate-600">
                  {booking.trip?.operator_name} •{" "}
                  <span className="font-mono text-xs font-semibold text-navy-900">
                    {booking.trip?.bus_number}
                  </span>
                </p>
                <p className="text-slate-600">
                  Date:{" "}
                  <span className="font-mono font-semibold text-navy-950">
                    {booking.trip?.travel_date}
                  </span>{" "}
                  •{" "}
                  <span className="font-mono font-semibold text-navy-950">
                    {booking.trip?.departure_time} – {booking.trip?.arrival_time} IST
                  </span>
                </p>
                <div className="space-y-1 border-t border-dashed border-navy-900/15 pt-3 text-xs text-slate-600">
                  <p>
                    Boarding:{" "}
                    <span className="font-semibold text-navy-950">
                      {booking.boarding_stop?.stop_name}
                    </span>
                  </p>
                  <p>
                    Drop:{" "}
                    <span className="font-semibold text-navy-950">
                      {booking.drop_stop?.stop_name}
                    </span>
                  </p>
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <h2 className="font-display text-xs font-bold uppercase tracking-[0.18em] text-navy-900/55">
                Passenger &amp; Seat
              </h2>
              <div className="space-y-2.5 rounded-2xl border border-navy-900/10 bg-cream-50/90 p-5 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Passenger</span>
                  <span className="font-bold text-navy-950">{booking.passenger_name}</span>
                </div>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-slate-500">Email</span>
                  <span className="truncate font-medium text-navy-900">
                    {booking.passenger_email}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Phone</span>
                  <span className="font-mono text-xs font-medium text-navy-900">
                    {booking.passenger_phone}
                  </span>
                </div>
                <div className="flex items-center justify-between border-t border-dashed border-navy-900/15 pt-3">
                  <span className="text-slate-500">Seat</span>
                  <span className="rounded-lg bg-navy-950 px-3 py-1 font-mono text-xs font-bold text-cream-50">
                    {booking.seat_number} ({booking.seat_type})
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-slate-500">Total Fare</span>
                  <span className="font-display text-2xl font-extrabold text-emerald-700">
                    ₹{Number(booking.total_fare).toFixed(0)}
                  </span>
                </div>
              </div>
            </div>
          </div>

          {/* Payment & Transaction Receipt Card */}
          <div className="border-t border-dashed border-navy-900/15 bg-white p-6">
            <h2 className="flex items-center gap-2 font-display text-xs font-bold uppercase tracking-[0.18em] text-navy-900/70">
              <Receipt className="h-4 w-4 text-emerald-600" />
              Verified Payment &amp; Transaction Receipt
            </h2>
            <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 md:grid-cols-4">
              <div className="rounded-xl border border-cream-200 bg-cream-50/60 p-3">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                  Payment Status
                </p>
                <div className="mt-1 flex items-center gap-1.5">
                  <span className="h-2 w-2 rounded-full bg-emerald-500" />
                  <p className="font-bold text-emerald-800">
                    {location.state?.payment?.status ||
                      booking.payment_summary?.status ||
                      (booking.status === "CONFIRMED" ? "SETTLED (SUCCESS)" : "REFUNDED")}
                  </p>
                </div>
              </div>

              <div className="rounded-xl border border-cream-200 bg-cream-50/60 p-3">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                  Transaction Ref
                </p>
                <p className="mt-1 font-mono text-xs font-bold text-navy-950 truncate">
                  {location.state?.payment?.transaction_ref ||
                    booking.payment_summary?.transaction_ref ||
                    `TXN-${booking.pnr}`}
                </p>
              </div>

              <div className="rounded-xl border border-cream-200 bg-cream-50/60 p-3">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                  Gateway &amp; Method
                </p>
                <p className="mt-1 text-xs font-bold text-navy-900">
                  {location.state?.payment?.gateway ||
                    booking.payment_summary?.gateway ||
                    "MOCK_SANDBOX"}{" "}
                  •{" "}
                  {location.state?.payment?.payment_method ||
                    booking.payment_summary?.payment_method ||
                    "UPI"}
                </p>
              </div>

              <div className="rounded-xl border border-cream-200 bg-cream-50/60 p-3">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-500">
                  Amount Settled
                </p>
                <p className="mt-1 font-display text-sm font-extrabold text-navy-950">
                  ₹{Number(booking.total_fare).toFixed(2)} INR
                </p>
              </div>
            </div>

            <div className="mt-3 flex items-center justify-between rounded-xl border border-emerald-200 bg-emerald-50/50 p-3 text-xs text-emerald-900">
              <div className="flex items-center gap-2">
                <Mail className="h-4 w-4 text-emerald-700 shrink-0" />
                <span>
                  Booking confirmation &amp; digital tax invoice dispatched to{" "}
                  <strong className="font-semibold">{booking.passenger_email}</strong> and SMS to{" "}
                  <strong className="font-semibold">{booking.passenger_phone}</strong>.
                </span>
              </div>
              <span className="hidden sm:inline-flex items-center gap-1 font-medium text-emerald-800">
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" /> 256-bit Secured
              </span>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-dashed border-navy-900/15 bg-cream-50/80 px-6 py-4 print:hidden">
            <Link
              to="/search"
              className="text-sm font-semibold text-navy-800 hover:text-emerald-700"
            >
              ← Search more buses
            </Link>

            <div className="flex flex-wrap items-center gap-2.5">
              {booking.status === "CONFIRMED" && (
                <>
                  <button
                    type="button"
                    onClick={() => setTrackingOpen(true)}
                    className="inline-flex items-center gap-2 rounded-xl bg-navy-950 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-navy-900"
                  >
                    <Navigation className="h-4 w-4 text-emerald-400" />
                    <span>Track Live Bus</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => setShareOpen(true)}
                    className="inline-flex items-center gap-2 rounded-xl border border-emerald-600/40 bg-emerald-50 px-4 py-2 text-sm font-semibold text-emerald-800 shadow-sm transition hover:bg-emerald-100"
                  >
                    <Share2 className="h-4 w-4 text-emerald-700" />
                    <span>Share Journey</span>
                  </button>
                </>
              )}

              <a
                href={busApi.getTicketPdfUrl(booking.pnr)}
                download={`BoardingPass-${booking.pnr}.pdf`}
                className="inline-flex items-center gap-2 rounded-xl bg-emerald-700 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-800"
              >
                <Download className="h-4 w-4" />
                <span>Download Boarding Pass (PDF)</span>
              </a>

              <button
                type="button"
                onClick={() => window.print()}
                className="inline-flex items-center gap-2 rounded-xl border border-navy-900/15 bg-white px-4 py-2 text-sm font-semibold text-navy-900 transition hover:bg-cream-100"
              >
                <svg
                  aria-hidden="true"
                  className="h-4 w-4 text-navy-800"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M6 9V2h12v7M6 18H4a2 2 0 01-2-2v-5a2 2 0 012-2h16a2 2 0 012 2v5a2 2 0 01-2 2h-2M6 14h12v8H6v-8z"
                  />
                </svg>
                <span>Print Boarding Pass</span>
              </button>

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
        </div>
      )}

      {/* Live Tracking Modal */}
      {booking?.trip_id && (
        <LiveTrackingModal
          isOpen={trackingOpen}
          onClose={() => setTrackingOpen(false)}
          tripId={booking.trip_id}
          tripInfo={{
            source: booking.trip?.source,
            destination: booking.trip?.destination,
            busNumber: booking.trip?.bus_number,
          }}
        />
      )}

      {/* Share Journey Modal */}
      {booking && (
        <ShareJourneyModal
          isOpen={shareOpen}
          onClose={() => setShareOpen(false)}
          booking={booking}
        />
      )}
    </div>
  );
}
