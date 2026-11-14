import { useCallback, useEffect, useState } from "react";
import { RefreshCw, XCircle, Eye, RotateCcw } from "lucide-react";
import { busApi } from "../../services/api";
import AdminPagination from "./AdminPagination";

export default function AdminBookingsTab({ onNotify, onChanged }) {
  const [bookings, setBookings] = useState([]);
  const [pagination, setPagination] = useState(null);
  const [loading, setLoading] = useState(true);

  const [query, setQuery] = useState("");
  const [travelDate, setTravelDate] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [refundFilter, setRefundFilter] = useState("");
  const [page, setPage] = useState(1);

  const [selectedDetail, setSelectedDetail] = useState(null);

  const loadBookings = useCallback(async () => {
    setLoading(true);
    try {
      const data = await busApi.getAdminBookings({
        q: query,
        travel_date: travelDate,
        status: statusFilter,
        refund_status: refundFilter,
        page,
        per_page: 12,
      });
      setBookings(data.bookings || []);
      setPagination(data.pagination || null);
    } catch (err) {
      onNotify("error", err.message || "Failed to load bookings.");
    } finally {
      setLoading(false);
    }
  }, [query, travelDate, statusFilter, refundFilter, page, onNotify]);

  useEffect(() => {
    loadBookings();
  }, [loadBookings]);

  async function handleInspect(pnr) {
    try {
      const data = await busApi.getAdminBookingDetail(pnr);
      setSelectedDetail(data.booking);
    } catch (err) {
      onNotify("error", err.message || "Could not load booking details.");
    }
  }

  async function handleCancel(pnr) {
    try {
      const data = await busApi.cancelAdminBooking(pnr, {
        reason: "Cancelled by administrator",
        process_refund: true,
      });
      onNotify("success", data.message || `Booking ${pnr} cancelled and demo refund recorded.`);
      if (selectedDetail?.pnr === pnr) setSelectedDetail(data.booking);
      await loadBookings();
      onChanged?.();
    } catch (err) {
      onNotify("error", err.message || "Failed to cancel booking.");
    }
  }

  async function handleRefund(b) {
    try {
      const data = await busApi.refundAdminBooking(b.pnr, {
        amount: b.total_fare,
        note: "Demo refund approved via Admin Control Centre",
      });
      onNotify("success", data.message || `Demo refund processed for ${b.pnr}.`);
      if (selectedDetail?.pnr === b.pnr) setSelectedDetail(data.booking);
      await loadBookings();
      onChanged?.();
    } catch (err) {
      onNotify("error", err.message || "Could not process demo refund.");
    }
  }

  return (
    <div className="space-y-5">
      <div className="rounded-2xl border border-navy-900/10 bg-white p-6 shadow-sm">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold text-navy-950">Platform Bookings &amp; Demo Refunds</h2>
            <p className="text-xs text-navy-900/60">
              Cancellations atomically release locked seats; refund actions track demo workflow
              state only.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <input
              type="text"
              placeholder="PNR, passenger, email, phone..."
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setPage(1);
              }}
              className="rounded-xl border border-navy-900/15 bg-cream-50/60 px-3 py-2 text-xs outline-none"
            />
            <input
              type="date"
              value={travelDate}
              onChange={(e) => {
                setTravelDate(e.target.value);
                setPage(1);
              }}
              className="rounded-xl border border-navy-900/15 bg-cream-50/60 px-2.5 py-2 text-xs outline-none"
            />
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="rounded-xl border border-navy-900/15 bg-cream-50/60 px-2.5 py-2 text-xs outline-none"
            >
              <option value="">All Status</option>
              <option value="CONFIRMED">CONFIRMED</option>
              <option value="CANCELLED">CANCELLED</option>
            </select>
            <select
              value={refundFilter}
              onChange={(e) => {
                setRefundFilter(e.target.value);
                setPage(1);
              }}
              className="rounded-xl border border-navy-900/15 bg-cream-50/60 px-2.5 py-2 text-xs outline-none"
            >
              <option value="">All Refunds</option>
              <option value="PENDING">Refund Pending</option>
              <option value="PROCESSED">Refund Processed</option>
              <option value="NONE">No Refund</option>
            </select>
            <button
              type="button"
              onClick={loadBookings}
              className="inline-flex items-center gap-1 rounded-xl bg-navy-950 px-3 py-2 text-xs font-semibold text-white"
            >
              <RefreshCw className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        {loading ? (
          <p className="text-sm text-navy-900/65">Loading bookings...</p>
        ) : bookings.length === 0 ? (
          <div className="rounded-xl border border-dashed border-navy-900/15 bg-cream-50/70 p-8 text-center text-xs text-navy-900/70">
            <p className="font-semibold text-navy-950">No matching reservations found</p>
            <p className="mt-1">Check the PNR, travel date, or status filter.</p>
            {query || travelDate || statusFilter || refundFilter ? (
              <button
                type="button"
                onClick={() => {
                  setQuery("");
                  setTravelDate("");
                  setStatusFilter("");
                  setRefundFilter("");
                  setPage(1);
                }}
                className="mt-3 rounded-lg border border-navy-900/15 bg-white px-3 py-1.5 font-semibold text-navy-950 hover:bg-cream-100"
              >
                Reset Filters
              </button>
            ) : null}
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-navy-900/10 uppercase text-navy-900/55">
                    <th className="pb-3 pr-3">PNR</th>
                    <th className="pb-3 pr-3">Passenger</th>
                    <th className="pb-3 pr-3">Route &amp; Date</th>
                    <th className="pb-3 pr-3">Seat / Demo Fare</th>
                    <th className="pb-3 pr-3">Status &amp; Demo Refund</th>
                    <th className="pb-3">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-navy-900/10">
                  {bookings.map((b) => (
                    <tr key={b.pnr}>
                      <td className="py-3 pr-3 font-mono font-bold text-navy-950">{b.pnr}</td>
                      <td className="py-3 pr-3">
                        <p className="font-semibold text-navy-950">{b.passenger_name}</p>
                        <p className="text-[11px] text-navy-900/65">
                          {b.passenger_email} • {b.passenger_phone}
                        </p>
                      </td>
                      <td className="py-3 pr-3">
                        <p className="font-medium text-navy-950">
                          {b.boarding_stop?.stop_name} → {b.drop_stop?.stop_name}
                        </p>
                        <p className="text-navy-900/60">
                          {b.trip?.travel_date} ({b.trip?.departure_time})
                        </p>
                      </td>
                      <td className="py-3 pr-3">
                        <span className="font-semibold">{b.seat_number}</span> • ₹
                        {Number(b.total_fare).toFixed(0)}
                      </td>
                      <td className="py-3 pr-3">
                        <div className="flex flex-wrap gap-1">
                          <span
                            className={`rounded-full px-2 py-0.5 font-semibold ${
                              b.status === "CONFIRMED"
                                ? "bg-emerald-50 text-emerald-700"
                                : "bg-red-50 text-red-700"
                            }`}
                          >
                            {b.status}
                          </span>
                          {b.refund_status && b.refund_status !== "NONE" ? (
                            <span
                              className={`rounded-full px-2 py-0.5 font-semibold ${
                                b.refund_status === "PROCESSED"
                                  ? "bg-emerald-50 text-emerald-700"
                                  : "bg-brass-50 text-brass-600"
                              }`}
                            >
                              {b.refund_status}
                            </span>
                          ) : null}
                        </div>
                      </td>
                      <td className="py-3">
                        <div className="flex flex-wrap gap-1.5">
                          <button
                            type="button"
                            onClick={() => handleInspect(b.pnr)}
                            className="inline-flex items-center gap-1 rounded-lg border border-navy-900/15 px-2 py-1 font-semibold text-navy-950 hover:bg-cream-50"
                          >
                            <Eye className="h-3 w-3" />
                            <span>Details</span>
                          </button>
                          {b.status === "CONFIRMED" ? (
                            <button
                              type="button"
                              onClick={() => handleCancel(b.pnr)}
                              className="inline-flex items-center gap-1 rounded-lg border border-red-200 bg-red-50 px-2 py-1 font-semibold text-red-700 hover:bg-red-100"
                            >
                              <XCircle className="h-3 w-3" />
                              <span>Cancel</span>
                            </button>
                          ) : b.refund_status !== "PROCESSED" ? (
                            <button
                              type="button"
                              onClick={() => handleRefund(b)}
                              className="inline-flex items-center gap-1 rounded-lg border border-brass-500/40 bg-brass-50 px-2 py-1 font-semibold text-brass-600 hover:bg-brass-100"
                            >
                              <RotateCcw className="h-3 w-3" />
                              <span>Process Demo Refund</span>
                            </button>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <AdminPagination pagination={pagination} onPageChange={setPage} />
          </>
        )}
      </div>

      {selectedDetail ? (
        <div className="rounded-2xl border border-navy-900/15 bg-cream-50 p-5 text-xs shadow-sm">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="text-sm font-bold text-navy-950">
                Reservation Detail: <span className="font-mono">{selectedDetail.pnr}</span>
              </h3>
              <p className="mt-0.5 text-navy-900/70">
                Demo Payment Flag: {String(selectedDetail.is_demo_payment)} • Trip Bus:{" "}
                {selectedDetail.trip?.operator_name} ({selectedDetail.trip?.bus_number})
              </p>
            </div>
            <button
              type="button"
              onClick={() => setSelectedDetail(null)}
              className="rounded-lg border border-navy-900/15 bg-white px-2.5 py-1 font-semibold"
            >
              Close
            </button>
          </div>
          <div className="mt-3 grid gap-3 sm:grid-cols-3">
            <div>
              <p className="font-semibold text-navy-900/60">Passenger</p>
              <p className="text-navy-950">{selectedDetail.passenger_name}</p>
              <p>{selectedDetail.passenger_email}</p>
              <p>{selectedDetail.passenger_phone}</p>
            </div>
            <div>
              <p className="font-semibold text-navy-900/60">Journey &amp; Stops</p>
              <p>
                {selectedDetail.boarding_stop?.stop_name} → {selectedDetail.drop_stop?.stop_name}
              </p>
              <p>
                {selectedDetail.trip?.travel_date} • {selectedDetail.trip?.departure_time}
              </p>
            </div>
            <div>
              <p className="font-semibold text-navy-900/60">Demo Refund Status</p>
              <p>Status: {selectedDetail.refund_status}</p>
              <p>
                Amount:{" "}
                {selectedDetail.refund_amount != null
                  ? `₹${Number(selectedDetail.refund_amount).toFixed(2)}`
                  : "—"}
              </p>
              {selectedDetail.cancellation_reason ? (
                <p>Note: {selectedDetail.cancellation_reason}</p>
              ) : null}
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
