import { AlertCircle, ArrowLeft, CheckCircle2, Loader2, MapPin, User } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import SeatMap from "../components/SeatMap";
import { busApi } from "../services/api";

function formatApiError(err) {
  if (!err?.details || typeof err.details !== "object") {
    return err?.message || "Booking failed.";
  }
  const parts = Object.entries(err.details).flatMap(([field, msgs]) =>
    Array.isArray(msgs) ? msgs.map((m) => `${field}: ${m}`) : [`${field}: ${String(msgs)}`]
  );
  return parts.length ? parts.join(" • ") : err.message;
}

export default function SeatSelectionPage() {
  const { tripId } = useParams();
  const navigate = useNavigate();

  const [tripData, setTripData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");

  const [selectedSeat, setSelectedSeat] = useState(null);
  const [boardingStopId, setBoardingStopId] = useState("");
  const [dropStopId, setDropStopId] = useState("");
  const [passengerName, setPassengerName] = useState("");
  const [passengerEmail, setPassengerEmail] = useState("");
  const [passengerPhone, setPassengerPhone] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");

  const loadSeatMap = useCallback(async () => {
    try {
      setLoading(true);
      setLoadError("");
      const data = await busApi.getTripSeats(tripId);
      setTripData(data);
      const stops = data.stops || [];
      if (stops.length >= 2) {
        setBoardingStopId((prev) => prev || String(stops[0].id));
        setDropStopId((prev) => prev || String(stops[stops.length - 1].id));
      }
    } catch (err) {
      setLoadError(err.message || "Could not load trip seat map.");
    } finally {
      setLoading(false);
    }
  }, [tripId]);

  useEffect(() => {
    loadSeatMap();
  }, [loadSeatMap]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedSeat) {
      setSubmitError("Please select an available seat from the coach diagram.");
      return;
    }

    try {
      setSubmitting(true);
      setSubmitError("");
      const resp = await busApi.createBooking({
        trip_id: Number(tripId),
        seat_number: selectedSeat.seat_number,
        boarding_stop_id: Number(boardingStopId),
        drop_stop_id: Number(dropStopId),
        passenger_name: passengerName,
        passenger_email: passengerEmail,
        passenger_phone: passengerPhone,
      });
      navigate(`/bookings/${resp.booking.pnr}`, {
        state: { booking: resp.booking, justCreated: true },
      });
    } catch (err) {
      setSubmitError(formatApiError(err));
      if (err.status === 409) {
        setSelectedSeat(null);
        await loadSeatMap();
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (loading && !tripData) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-12 text-center text-sm text-slate-500">
        Loading coach seat availability...
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12">
        <div className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-rose-800">
          <p className="font-bold">{loadError}</p>
          <Link to="/search" className="mt-3 inline-block text-sm font-semibold underline">
            ← Back to search results
          </Link>
        </div>
      </div>
    );
  }

  const { trip, stops = [], seats = [] } = tripData;

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <Link
            to="/search"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-navy-900"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to buses
          </Link>
          <h1 className="mt-1 font-display text-2xl font-bold text-navy-900">
            {trip.source} → {trip.destination}
          </h1>
          <p className="text-sm text-slate-600">
            {trip.operator_name} ({trip.bus_number}) • {trip.travel_date} •{" "}
            {trip.departure_time} – {trip.arrival_time} ({trip.duration_display})
          </p>
        </div>
        <div className="rounded-xl bg-navy-900 px-4 py-2.5 text-right text-white">
          <p className="text-[11px] uppercase tracking-wider text-slate-300">Available</p>
          <p className="font-display text-lg font-bold text-emerald-400">
            {trip.available_seats} / {trip.total_seats} seats
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <div className="lg:col-span-6">
          <SeatMap
            seats={seats}
            selectedSeatNumber={selectedSeat?.seat_number || null}
            onSelectSeat={(seat) => {
              setSelectedSeat(seat);
              setSubmitError("");
            }}
          />
        </div>

        <div className="space-y-5 lg:col-span-6">
          <div className="rounded-2xl border border-cream-200 bg-white p-5 shadow-sm">
            <h2 className="font-display text-lg font-bold text-navy-900">
              Selected Seat Summary
            </h2>
            {selectedSeat ? (
              <div className="mt-3 flex items-center justify-between rounded-xl border border-blue-200 bg-blue-50 p-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wider text-blue-700">
                    Seat {selectedSeat.seat_number} • {selectedSeat.seat_type}
                  </p>
                  <p className="mt-0.5 text-sm text-navy-900">
                    {trip.source} to {trip.destination} ({trip.travel_date})
                  </p>
                </div>
                <p className="font-display text-2xl font-extrabold text-navy-900">
                  ₹{Number(selectedSeat.fare).toFixed(0)}
                </p>
              </div>
            ) : (
              <p className="mt-2 rounded-xl border border-dashed border-cream-200 bg-cream-50 p-4 text-sm text-slate-500">
                No seat selected yet. Choose any green seat on the left.
              </p>
            )}
          </div>

          <form
            onSubmit={handleSubmit}
            className="space-y-4 rounded-2xl border border-cream-200 bg-white p-5 shadow-sm"
          >
            <h2 className="flex items-center gap-2 font-display text-lg font-bold text-navy-900">
              <User className="h-5 w-5 text-emerald-600" />
              Passenger &amp; Boarding Details
            </h2>

            {submitError && (
              <div className="flex items-start gap-2.5 rounded-xl border border-rose-200 bg-rose-50 p-3.5 text-xs font-medium text-rose-800">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{submitError}</span>
              </div>
            )}

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label className="mb-1 flex items-center gap-1 text-xs font-semibold text-slate-600">
                  <MapPin className="h-3.5 w-3.5 text-emerald-600" />
                  Boarding Stop
                </label>
                <select
                  required
                  value={boardingStopId}
                  onChange={(e) => setBoardingStopId(e.target.value)}
                  className="w-full rounded-xl border border-cream-200 bg-cream-50 px-3 py-2.5 text-sm focus:border-emerald-500 focus:outline-none"
                >
                  {stops.map((stop) => (
                    <option key={stop.id} value={stop.id}>
                      {stop.stop_order}. {stop.stop_name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="mb-1 flex items-center gap-1 text-xs font-semibold text-slate-600">
                  <MapPin className="h-3.5 w-3.5 text-navy-700" />
                  Drop Stop
                </label>
                <select
                  required
                  value={dropStopId}
                  onChange={(e) => setDropStopId(e.target.value)}
                  className="w-full rounded-xl border border-cream-200 bg-cream-50 px-3 py-2.5 text-sm focus:border-emerald-500 focus:outline-none"
                >
                  {stops.map((stop) => (
                    <option key={stop.id} value={stop.id}>
                      {stop.stop_order}. {stop.stop_name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="mb-1 block text-xs font-semibold text-slate-600">
                Passenger Full Name
              </label>
              <input
                type="text"
                required
                placeholder="e.g. Ananya Singh"
                value={passengerName}
                onChange={(e) => setPassengerName(e.target.value)}
                className="w-full rounded-xl border border-cream-200 bg-cream-50 px-3.5 py-2.5 text-sm focus:border-emerald-500 focus:outline-none"
              />
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label className="mb-1 block text-xs font-semibold text-slate-600">
                  Email Address
                </label>
                <input
                  type="email"
                  required
                  placeholder="ananya@example.com"
                  value={passengerEmail}
                  onChange={(e) => setPassengerEmail(e.target.value)}
                  className="w-full rounded-xl border border-cream-200 bg-cream-50 px-3.5 py-2.5 text-sm focus:border-emerald-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="mb-1 block text-xs font-semibold text-slate-600">
                  Mobile Number
                </label>
                <input
                  type="tel"
                  required
                  placeholder="9876543210"
                  value={passengerPhone}
                  onChange={(e) => setPassengerPhone(e.target.value)}
                  className="w-full rounded-xl border border-cream-200 bg-cream-50 px-3.5 py-2.5 text-sm focus:border-emerald-500 focus:outline-none"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={submitting || !selectedSeat}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-600 px-5 py-3 text-sm font-bold text-white shadow-md transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              {submitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Reserving Seat Atomically...</span>
                </>
              ) : (
                <>
                  <CheckCircle2 className="h-4 w-4" />
                  <span>
                    Confirm Booking{" "}
                    {selectedSeat ? `• ₹${Number(selectedSeat.fare).toFixed(0)}` : ""}
                  </span>
                </>
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
