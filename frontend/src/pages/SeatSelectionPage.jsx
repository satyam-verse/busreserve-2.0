import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  Building2,
  CheckCircle2,
  CreditCard,
  Loader2,
  MapPin,
  QrCode,
  ShieldCheck,
  User,
  Zap,
  Sparkles,
  Star,
  Tag,
  Filter,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import SeatMap from "../components/SeatMap";
import { useAuth } from "../context/AuthContext";
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
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user } = useAuth();

  const [tripData, setTripData] = useState(null);
  const [cheapestData, setCheapestData] = useState(null);
  const [highlightTier, setHighlightTier] = useState("ALL");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");

  const [selectedSeat, setSelectedSeat] = useState(null);
  const [boardingStopId, setBoardingStopId] = useState("");
  const [dropStopId, setDropStopId] = useState("");
  const [passengerName, setPassengerName] = useState("");
  const [passengerEmail, setPassengerEmail] = useState("");
  const [passengerPhone, setPassengerPhone] = useState("");

  const [paymentMethod, setPaymentMethod] = useState("UPI");
  const [paymentGateway, setPaymentGateway] = useState("MOCK_SANDBOX");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");

  const loadSeatMap = useCallback(async () => {
    try {
      setLoading(true);
      setLoadError("");
      const [seatRes, cheapRes] = await Promise.all([
        busApi.getTripSeats(tripId),
        busApi.getCheapestSeats(tripId).catch(() => null),
      ]);
      setTripData(seatRes);
      if (cheapRes) setCheapestData(cheapRes);

      const stops = seatRes.stops || [];
      if (stops.length >= 2) {
        const stopIds = new Set(stops.map((s) => String(s.id)));
        const preferredBoard = searchParams.get("boarding_stop_id");
        const preferredDrop = searchParams.get("drop_stop_id");
        setBoardingStopId(
          (prev) =>
            prev ||
            (preferredBoard && stopIds.has(preferredBoard) ? preferredBoard : String(stops[0].id))
        );
        setDropStopId(
          (prev) =>
            prev ||
            (preferredDrop && stopIds.has(preferredDrop)
              ? preferredDrop
              : String(stops[stops.length - 1].id))
        );
      }
    } catch (err) {
      setLoadError(err.message || "Could not load trip seat map.");
    } finally {
      setLoading(false);
    }
  }, [tripId, searchParams]);

  const handleSelectCheapest = (seatNumber) => {
    if (!tripData?.seats || !seatNumber) return;
    const found = tripData.seats.find((s) => s.seat_number === seatNumber);
    if (found && found.is_available) {
      setSelectedSeat(found);
      setSubmitError("");
    }
  };

  useEffect(() => {
    loadSeatMap();
  }, [loadSeatMap]);

  useEffect(() => {
    if (user && user.role === "USER") {
      setPassengerName((prev) => prev || user.full_name || "");
      setPassengerEmail((prev) => prev || user.email || "");
      setPassengerPhone((prev) => prev || user.phone || "");
    }
  }, [user]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedSeat) {
      setSubmitError("Please select an available seat from the coach diagram.");
      return;
    }

    try {
      setSubmitting(true);
      setSubmitError("");

      const bookingPayload = {
        trip_id: Number(tripId),
        seat_number: selectedSeat.seat_number,
        boarding_stop_id: Number(boardingStopId),
        drop_stop_id: Number(dropStopId),
        passenger_name: passengerName.trim(),
        passenger_email: passengerEmail.trim(),
        passenger_phone: passengerPhone.trim(),
      };

      const idempotencyKey = `p7_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;

      // Step 1: Initialize payment order in chosen gateway sandbox
      const orderResp = await busApi.createPaymentOrder({
        ...bookingPayload,
        gateway: paymentGateway,
        payment_method: paymentMethod,
        idempotency_key: idempotencyKey,
      });

      const tx = orderResp.transaction || orderResp.order;
      const checkout = orderResp.checkout || {};
      if (!tx || !tx.transaction_ref) {
        throw new Error("Unable to initialize payment transaction.");
      }

      // Step 2: Assemble session payload and navigate to dedicated Payment Page
      const sessionData = {
        transaction_ref: tx.transaction_ref,
        gateway_order_id: tx.gateway_order_id,
        amount: tx.amount || selectedSeat.fare,
        currency: tx.currency || "INR",
        gateway: tx.gateway || paymentGateway,
        payment_method: paymentMethod,
        bookingPayload,
        trip: {
          id: tripData.id,
          bus_operator: tripData.bus_operator,
          bus_number: tripData.bus_number,
          bus_type: tripData.bus_type,
          origin: tripData.origin,
          destination: tripData.destination,
          departure_time: tripData.departure_time,
          arrival_time: tripData.arrival_time,
          boarding_stop:
            tripData.stops?.find((s) => String(s.id) === String(boardingStopId))?.stop_name ||
            tripData.origin,
          drop_stop:
            tripData.stops?.find((s) => String(s.id) === String(dropStopId))?.stop_name ||
            tripData.destination,
        },
        seat: selectedSeat,
        checkout,
      };

      try {
        sessionStorage.setItem("busreserve_payment_session", JSON.stringify(sessionData));
      } catch {
        // ignore storage error
      }

      navigate(`/payment?txn=${encodeURIComponent(tx.transaction_ref)}`, {
        state: sessionData,
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
      <div className="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6" aria-busy="true">
        <div className="space-y-2">
          <div className="h-4 w-28 animate-pulse rounded bg-cream-200" />
          <div className="h-8 w-72 animate-pulse rounded-lg bg-cream-200" />
          <div className="h-4 w-80 animate-pulse rounded bg-cream-200/80" />
        </div>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
          <div className="h-96 animate-pulse rounded-2xl border border-cream-200 bg-white lg:col-span-6" />
          <div className="h-96 animate-pulse rounded-2xl border border-cream-200 bg-white lg:col-span-6" />
        </div>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12">
        <div role="alert" className="rounded-2xl border border-rose-200 bg-rose-50 p-6 text-rose-900">
          <p className="font-bold">{loadError}</p>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={loadSeatMap}
              className="rounded-xl bg-navy-950 px-4 py-2 text-xs font-semibold text-white transition hover:bg-navy-800"
            >
              Retry Seat Map
            </button>
            <Link to="/search" className="text-sm font-semibold text-rose-900 underline">
              ← Back to search results
            </Link>
          </div>
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

      {/* Find Cheapest Seats Discovery Widget */}
      {cheapestData && (
        <div className="rounded-2xl border border-amber-300/80 bg-gradient-to-r from-amber-50 via-cream-50 to-emerald-50/60 p-4 shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-amber-400 text-navy-950 shadow-sm">
                <Sparkles className="h-4 w-4" />
              </div>
              <div>
                <h3 className="text-xs font-bold uppercase tracking-wider text-amber-950">
                  Find Cheapest Seats
                </h3>
                <p className="text-xs text-navy-900/70">
                  {cheapestData.overall_cheapest_seat ? (
                    <>
                      Lowest available fare starts at{" "}
                      <span className="font-bold text-emerald-700">
                        ₹{Number(cheapestData.overall_cheapest_seat.fare).toFixed(0)}
                      </span>{" "}
                      (Seat {cheapestData.overall_cheapest_seat.seat_number} • {cheapestData.overall_cheapest_seat.seat_tier})
                    </>
                  ) : (
                    "Instant seat pricing across categories"
                  )}
                </p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              {cheapestData.tiers?.STANDARD?.best_seat && (
                <button
                  type="button"
                  onClick={() => handleSelectCheapest(cheapestData.tiers.STANDARD.best_seat.seat_number)}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-emerald-300 bg-white px-3 py-1.5 text-xs font-bold text-emerald-800 shadow-sm transition hover:bg-emerald-50"
                >
                  <span>Standard: ₹{Number(cheapestData.tiers.STANDARD.lowest_fare).toFixed(0)}</span>
                </button>
              )}
              {cheapestData.tiers?.PREMIUM?.best_seat && (
                <button
                  type="button"
                  onClick={() => handleSelectCheapest(cheapestData.tiers.PREMIUM.best_seat.seat_number)}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-amber-300 bg-amber-100/70 px-3 py-1.5 text-xs font-bold text-amber-900 shadow-sm transition hover:bg-amber-100"
                >
                  <Star className="h-3 w-3 fill-amber-500 text-amber-500" />
                  <span>Premium: ₹{Number(cheapestData.tiers.PREMIUM.lowest_fare).toFixed(0)}</span>
                </button>
              )}
              {cheapestData.tiers?.SLEEPER?.best_seat && (
                <button
                  type="button"
                  onClick={() => handleSelectCheapest(cheapestData.tiers.SLEEPER.best_seat.seat_number)}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-indigo-300 bg-indigo-50 px-3 py-1.5 text-xs font-bold text-indigo-900 shadow-sm transition hover:bg-indigo-100"
                >
                  <span>Sleeper: ₹{Number(cheapestData.tiers.SLEEPER.lowest_fare).toFixed(0)}</span>
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12">
        <div className="lg:col-span-6 space-y-3">
          {/* Tier Filter Tabs */}
          <div className="flex flex-wrap items-center gap-1.5 text-xs font-semibold">
            <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mr-1 flex items-center gap-1">
              <Filter className="h-3 w-3" /> Filter Tier:
            </span>
            {["ALL", "STANDARD", "PREMIUM", "SLEEPER"].map((tier) => (
              <button
                key={tier}
                type="button"
                onClick={() => setHighlightTier(tier)}
                className={`rounded-lg px-2.5 py-1 transition ${
                  highlightTier === tier
                    ? "bg-navy-950 text-white"
                    : "bg-cream-100 text-slate-700 hover:bg-cream-200"
                }`}
              >
                {tier === "ALL" ? "All Seats" : tier === "PREMIUM" ? "Premium ★" : tier}
              </button>
            ))}
          </div>

          <SeatMap
            seats={seats}
            seatLayout={trip.seat_layout || "2+2"}
            busType={trip.bus_type || ""}
            highlightTier={highlightTier}
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
              <div className="mt-3 rounded-xl border border-brass-400/50 bg-brass-50 p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-base text-navy-950">
                        Seat {selectedSeat.seat_number}
                      </span>
                      <span
                        className={`rounded-md px-2 py-0.5 text-xs font-bold ${
                          selectedSeat.seat_tier === "PREMIUM"
                            ? "bg-amber-400 text-navy-950"
                            : selectedSeat.seat_tier === "SLEEPER"
                            ? "bg-indigo-600 text-white"
                            : "bg-emerald-600 text-white"
                        }`}
                      >
                        {selectedSeat.seat_tier || "STANDARD"}
                        {selectedSeat.seat_tier === "PREMIUM" && " ★"}
                      </span>
                      <span className="text-xs text-slate-500 font-medium">
                        ({selectedSeat.seat_type?.replace(/_/g, " ")})
                      </span>
                    </div>
                    <p className="text-xs text-slate-600">
                      {trip.source} to {trip.destination} • {trip.travel_date}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="font-display text-2xl font-extrabold text-navy-950">
                      ₹{Number(selectedSeat.fare).toFixed(0)}
                    </p>
                    <p className="text-[10px] text-slate-400 font-medium">Final Authoritative Fare</p>
                  </div>
                </div>

                {/* Amenities Badges */}
                {selectedSeat.amenities && selectedSeat.amenities.length > 0 && (
                  <div className="border-t border-brass-200/60 pt-2 flex flex-wrap gap-1.5">
                    <span className="text-[11px] font-semibold text-slate-500 mr-1">Amenities:</span>
                    {selectedSeat.amenities.map((am, i) => (
                      <span
                        key={i}
                        className="rounded-md bg-white px-2 py-0.5 text-[11px] font-medium text-amber-900 border border-amber-200 shadow-2xs"
                      >
                        ✓ {am}
                      </span>
                    ))}
                  </div>
                )}

                <div className="border-t border-brass-200/60 pt-2 text-[11px] text-slate-500 flex items-center justify-between">
                  <span>Base fare: ₹{Number(trip.base_fare).toFixed(0)}</span>
                  {Number(selectedSeat.fare) > Number(trip.base_fare) && (
                    <span className="text-amber-800 font-semibold">
                      Tier adjustment: +₹{Number(selectedSeat.fare - trip.base_fare).toFixed(0)}
                    </span>
                  )}
                  <span className="text-emerald-700 font-semibold">Backend Price Verified</span>
                </div>
              </div>
            ) : (
              <p className="mt-2 rounded-xl border border-dashed border-cream-200 bg-cream-50 p-4 text-sm text-slate-500">
                No seat selected yet. Choose any available seat on the coach map or use the cheapest seat finder above.
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
              <label
                htmlFor="passenger-full-name"
                className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-navy-900/65"
              >
                Passenger Full Name
              </label>
              <input
                id="passenger-full-name"
                type="text"
                required
                placeholder="e.g. Ananya Singh"
                value={passengerName}
                onChange={(e) => setPassengerName(e.target.value)}
                className="w-full rounded-xl border border-navy-900/15 bg-cream-50/70 px-3.5 py-2.5 text-sm font-medium text-navy-950 transition focus:border-emerald-600 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-600/20"
              />
            </div>

            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div>
                <label
                  htmlFor="passenger-email"
                  className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-navy-900/65"
                >
                  Email Address
                </label>
                <input
                  id="passenger-email"
                  type="email"
                  required
                  placeholder="ananya@example.com"
                  value={passengerEmail}
                  onChange={(e) => setPassengerEmail(e.target.value)}
                  className="w-full rounded-xl border border-navy-900/15 bg-cream-50/70 px-3.5 py-2.5 text-sm font-medium text-navy-950 transition focus:border-emerald-600 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-600/20"
                />
              </div>

              <div>
                <label
                  htmlFor="passenger-phone"
                  className="mb-1.5 block text-xs font-bold uppercase tracking-wider text-navy-900/65"
                >
                  Mobile Number
                </label>
                <input
                  id="passenger-phone"
                  type="tel"
                  required
                  placeholder="9876543210"
                  value={passengerPhone}
                  onChange={(e) => setPassengerPhone(e.target.value)}
                  className="w-full rounded-xl border border-navy-900/15 bg-cream-50/70 px-3.5 py-2.5 text-sm font-medium text-navy-950 transition focus:border-emerald-600 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-600/20"
                />
              </div>
            </div>

            <div className="space-y-3 border-t border-cream-200/80 pt-4">
              <div className="flex items-center justify-between">
                <label className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-navy-900/70">
                  <CreditCard className="h-4 w-4 text-emerald-600" />
                  Select Payment Method
                </label>
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-800">
                  <ShieldCheck className="h-3 w-3" /> Sandbox Mode
                </span>
              </div>

              <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-3">
                {[
                  {
                    id: "UPI",
                    title: "UPI / QR",
                    desc: "Instant simulated scan",
                    icon: QrCode,
                  },
                  {
                    id: "CARD",
                    title: "Cards",
                    desc: "Visa, Mastercard, RuPay",
                    icon: CreditCard,
                  },
                  {
                    id: "NETBANKING",
                    title: "NetBanking",
                    desc: "All major banks",
                    icon: Building2,
                  },
                ].map((m) => {
                  const Icon = m.icon;
                  const isSelected = paymentMethod === m.id;
                  return (
                    <button
                      key={m.id}
                      type="button"
                      onClick={() => setPaymentMethod(m.id)}
                      className={`flex flex-col items-start rounded-xl border p-3 text-left transition ${
                        isSelected
                          ? "border-emerald-600 bg-emerald-50/60 shadow-sm"
                          : "border-cream-200 bg-cream-50/50 hover:border-navy-900/30 hover:bg-cream-100/50"
                      }`}
                    >
                      <div className="flex w-full items-center justify-between">
                        <Icon
                          className={`h-4 w-4 ${
                            isSelected ? "text-emerald-700" : "text-slate-500"
                          }`}
                        />
                        <span
                          className={`h-2.5 w-2.5 rounded-full ${
                            isSelected ? "bg-emerald-600" : "border border-slate-300"
                          }`}
                        />
                      </div>
                      <p className="mt-2 text-xs font-bold text-navy-950">{m.title}</p>
                      <p className="text-[11px] text-slate-500">{m.desc}</p>
                    </button>
                  );
                })}
              </div>

              <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-cream-200 bg-cream-50/40 px-3 py-2 text-xs">
                <span className="text-slate-600">Simulated Gateway:</span>
                <div className="flex gap-1.5">
                  {[
                    { id: "MOCK_SANDBOX", label: "Mock Sandbox" },
                    { id: "RAZORPAY_SANDBOX", label: "Razorpay Sandbox" },
                    { id: "STRIPE_SANDBOX", label: "Stripe Sandbox" },
                  ].map((gw) => (
                    <button
                      key={gw.id}
                      type="button"
                      onClick={() => setPaymentGateway(gw.id)}
                      className={`rounded-lg px-2 py-0.5 text-[11px] font-semibold transition ${
                        paymentGateway === gw.id
                          ? "bg-navy-950 text-white"
                          : "bg-white text-slate-600 border border-cream-200 hover:bg-cream-100"
                      }`}
                    >
                      {gw.label}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {selectedSeat && (
              <div className="space-y-1.5 rounded-xl border border-navy-900/10 bg-cream-50/90 p-3.5 text-xs">
                <p className="font-bold text-navy-950">Fare Summary</p>
                <div className="flex justify-between text-slate-600">
                  <span>Base Seat Fare ({selectedSeat.seat_number})</span>
                  <span className="font-mono font-semibold text-navy-900">
                    ₹{Number(selectedSeat.fare).toFixed(2)}
                  </span>
                </div>
                <div className="flex justify-between text-slate-600">
                  <span>Booking &amp; Platform Fee</span>
                  <span className="font-mono text-emerald-700 font-semibold">₹0.00 (Free)</span>
                </div>
                <div className="flex justify-between text-slate-600">
                  <span>Applicable GST / Taxes</span>
                  <span className="font-mono font-semibold text-navy-900">₹0.00</span>
                </div>
                <div className="flex justify-between border-t border-dashed border-navy-900/15 pt-2 text-sm font-bold text-navy-950">
                  <span>Total Amount Payable</span>
                  <span className="font-display font-extrabold text-emerald-700">
                    ₹{Number(selectedSeat.fare).toFixed(2)}
                  </span>
                </div>
              </div>
            )}

            <div className="rounded-xl border border-emerald-200/70 bg-emerald-50/60 px-3.5 py-2.5 text-xs text-emerald-900">
              <p className="flex items-center gap-1.5 font-semibold">
                <Zap className="h-3.5 w-3.5 text-emerald-600" />
                Atomic Reservation Lock &amp; Multi-Channel Notification Active
              </p>
              <p className="mt-0.5 text-[11px] text-emerald-800/80">
                Seat is held exclusively. Upon payment settlement, instant confirmation is dispatched via Email, SMS, and in-app alerts.
              </p>
            </div>

            <button
              type="submit"
              disabled={submitting || !selectedSeat}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-navy-950 px-5 py-3.5 text-sm font-bold text-white shadow-editorial transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:bg-slate-300"
            >
              {submitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Initiating Secure Payment Session...</span>
                </>
              ) : (
                <>
                  <ShieldCheck className="h-4 w-4 text-emerald-400" />
                  <span>
                    Review &amp; Proceed to Payment{" "}
                    {selectedSeat ? `• ₹${Number(selectedSeat.fare).toFixed(0)}` : ""}
                  </span>
                  <ArrowRight className="h-4 w-4 ml-0.5" />
                </>
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
