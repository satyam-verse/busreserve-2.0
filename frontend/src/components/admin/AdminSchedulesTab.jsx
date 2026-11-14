import { useCallback, useEffect, useState } from "react";
import { CalendarClock, Plus, Pencil, Trash2, RefreshCw, Check, X } from "lucide-react";
import { busApi } from "../../services/api";
import AdminPagination from "./AdminPagination";

export default function AdminSchedulesTab({ horizonDays = 90, onNotify, onChanged }) {
  const [schedules, setSchedules] = useState([]);
  const [routes, setRoutes] = useState([]);
  const [buses, setBuses] = useState([]);
  const [pagination, setPagination] = useState(null);
  const [loading, setLoading] = useState(true);

  const [query, setQuery] = useState("");
  const [routeFilter, setRouteFilter] = useState("");
  const [activeFilter, setActiveFilter] = useState("");
  const [page, setPage] = useState(1);

  const [form, setForm] = useState({
    route_id: "",
    bus_id: "",
    departure_time: "08:00",
    arrival_time: "14:00",
    base_fare: "590",
    horizon_days: String(horizonDays),
  });

  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({
    departure_time: "08:00",
    arrival_time: "14:00",
    base_fare: "590",
    is_active: true,
    apply_to_future_trips: true,
  });

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [sData, rData, bData] = await Promise.all([
        busApi.getAdminSchedules({
          q: query,
          route_id: routeFilter,
          is_active: activeFilter,
          page,
          per_page: 10,
        }),
        busApi.getAdminRoutes({ per_page: 100 }),
        busApi.getAdminBuses({ is_active: true, per_page: 100 }),
      ]);
      setSchedules(sData.schedules || []);
      setPagination(sData.pagination || null);
      const rRows = rData.routes || [];
      const bRows = bData.buses || [];
      setRoutes(rRows);
      setBuses(bRows);
      setForm((prev) => ({
        ...prev,
        route_id: prev.route_id || (rRows[0] ? String(rRows[0].id) : ""),
        bus_id: prev.bus_id || (bRows[0] ? String(bRows[0].id) : ""),
      }));
    } catch (err) {
      onNotify("error", err.message || "Failed to load schedules.");
    } finally {
      setLoading(false);
    }
  }, [query, routeFilter, activeFilter, page, onNotify]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  async function handleCreate(e) {
    e.preventDefault();
    try {
      const data = await busApi.createAdminSchedule({
        route_id: Number(form.route_id),
        bus_id: Number(form.bus_id),
        departure_time: form.departure_time,
        arrival_time: form.arrival_time,
        base_fare: Number(form.base_fare),
        horizon_days: form.horizon_days ? Number(form.horizon_days) : undefined,
      });
      onNotify(
        "success",
        `Schedule "${data.schedule.bus_number}" launched with ${data.generated?.trips_created ?? 0} trips.`
      );
      setPage(1);
      await loadData();
      onChanged?.();
    } catch (err) {
      onNotify("error", err.message || "Could not create schedule.");
    }
  }

  function startEdit(s) {
    setEditingId(s.id);
    setEditForm({
      departure_time: s.departure_time,
      arrival_time: s.arrival_time,
      base_fare: String(s.base_fare),
      is_active: s.is_active,
      apply_to_future_trips: true,
    });
  }

  async function saveEdit(scheduleId) {
    try {
      const data = await busApi.updateAdminSchedule(scheduleId, {
        departure_time: editForm.departure_time,
        arrival_time: editForm.arrival_time,
        base_fare: Number(editForm.base_fare),
        is_active: editForm.is_active,
        apply_to_future_trips: editForm.apply_to_future_trips,
      });
      setEditingId(null);
      onNotify("success", `Schedule ${data.schedule.bus_number} updated.`);
      await loadData();
      onChanged?.();
    } catch (err) {
      onNotify("error", err.message || "Could not update schedule.");
    }
  }

  async function handleToggle(sched) {
    try {
      await busApi.toggleAdminSchedule(sched.id, !sched.is_active);
      onNotify(
        "success",
        `Schedule ${sched.bus_number} ${!sched.is_active ? "activated" : "paused"}.`
      );
      await loadData();
      onChanged?.();
    } catch (err) {
      onNotify("error", err.message || "Could not toggle schedule.");
    }
  }

  async function handleDelete(sched) {
    try {
      await busApi.deleteAdminSchedule(sched.id);
      onNotify("success", `Schedule ${sched.bus_number} deleted.`);
      await loadData();
      onChanged?.();
    } catch (err) {
      onNotify("error", err.message || "Could not delete schedule.");
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-12">
      <form
        onSubmit={handleCreate}
        className="h-fit rounded-2xl border border-navy-900/10 bg-white p-5 shadow-sm lg:col-span-4"
      >
        <div className="mb-3 flex items-center gap-2">
          <CalendarClock className="h-4 w-4 text-navy-950" />
          <h2 className="text-base font-bold text-navy-950">Create Schedule</h2>
        </div>
        <div className="space-y-3">
          <div>
            <label htmlFor="sched-route" className="block text-xs font-semibold text-navy-900/80">
              Route
            </label>
            <select
              id="sched-route"
              required
              value={form.route_id}
              onChange={(e) => setForm((p) => ({ ...p, route_id: e.target.value }))}
              className="mt-1 w-full rounded-xl border border-navy-900/15 bg-cream-50/60 px-3 py-2 text-xs outline-none"
            >
              {routes.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="sched-bus" className="block text-xs font-semibold text-navy-900/80">
              Assigned Fleet Bus
            </label>
            <select
              id="sched-bus"
              required
              value={form.bus_id}
              onChange={(e) => setForm((p) => ({ ...p, bus_id: e.target.value }))}
              className="mt-1 w-full rounded-xl border border-navy-900/15 bg-cream-50/60 px-3 py-2 text-xs outline-none"
            >
              {buses.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.registration_number} — {b.operator_name} ({b.seat_layout}, {b.total_seats}{" "}
                  seats)
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label htmlFor="sched-dep" className="block text-[11px] font-semibold text-navy-900/75">
                Departure (IST)
              </label>
              <input
                id="sched-dep"
                type="time"
                required
                value={form.departure_time}
                onChange={(e) => setForm((p) => ({ ...p, departure_time: e.target.value }))}
                className="mt-1 w-full rounded-xl border border-navy-900/15 bg-cream-50/60 px-2.5 py-2 text-xs outline-none"
              />
            </div>
            <div>
              <label htmlFor="sched-arr" className="block text-[11px] font-semibold text-navy-900/75">
                Arrival (IST)
              </label>
              <input
                id="sched-arr"
                type="time"
                required
                value={form.arrival_time}
                onChange={(e) => setForm((p) => ({ ...p, arrival_time: e.target.value }))}
                className="mt-1 w-full rounded-xl border border-navy-900/15 bg-cream-50/60 px-2.5 py-2 text-xs outline-none"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div>
              <label htmlFor="sched-fare" className="block text-[11px] font-semibold text-navy-900/75">
                Base Fare (₹)
              </label>
              <input
                id="sched-fare"
                type="number"
                min="1"
                required
                value={form.base_fare}
                onChange={(e) => setForm((p) => ({ ...p, base_fare: e.target.value }))}
                className="mt-1 w-full rounded-xl border border-navy-900/15 bg-cream-50/60 px-3 py-2 text-xs outline-none"
              />
            </div>
            <div>
              <label
                htmlFor="sched-horizon"
                className="block text-[11px] font-semibold text-navy-900/75"
              >
                Window (Days)
              </label>
              <input
                id="sched-horizon"
                type="number"
                min="1"
                max="365"
                value={form.horizon_days}
                onChange={(e) => setForm((p) => ({ ...p, horizon_days: e.target.value }))}
                className="mt-1 w-full rounded-xl border border-navy-900/15 bg-cream-50/60 px-3 py-2 text-xs outline-none"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={routes.length === 0 || buses.length === 0}
            className="inline-flex w-full items-center justify-center gap-1.5 rounded-xl bg-navy-950 px-3 py-2.5 text-xs font-semibold text-white hover:bg-navy-800 disabled:opacity-50"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Launch Schedule</span>
          </button>
        </div>
      </form>

      <div className="rounded-2xl border border-navy-900/10 bg-white p-6 shadow-sm lg:col-span-8">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-bold text-navy-950">Travel Schedules</h2>
          <div className="flex flex-wrap gap-2">
            <input
              type="text"
              placeholder="Search operator or reg..."
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setPage(1);
              }}
              className="rounded-xl border border-navy-900/15 bg-cream-50/60 px-3 py-2 text-xs outline-none"
            />
            <select
              value={routeFilter}
              onChange={(e) => {
                setRouteFilter(e.target.value);
                setPage(1);
              }}
              className="rounded-xl border border-navy-900/15 bg-cream-50/60 px-2.5 py-2 text-xs outline-none"
            >
              <option value="">All Routes</option>
              {routes.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </select>
            <select
              value={activeFilter}
              onChange={(e) => {
                setActiveFilter(e.target.value);
                setPage(1);
              }}
              className="rounded-xl border border-navy-900/15 bg-cream-50/60 px-2.5 py-2 text-xs outline-none"
            >
              <option value="">All Status</option>
              <option value="true">Active</option>
              <option value="false">Paused</option>
            </select>
            <button
              type="button"
              onClick={loadData}
              className="inline-flex items-center gap-1 rounded-xl bg-navy-950 px-3 py-2 text-xs font-semibold text-white"
            >
              <RefreshCw className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        {loading ? (
          <p className="text-sm text-navy-900/65">Loading schedules...</p>
        ) : schedules.length === 0 ? (
          <div className="rounded-xl border border-dashed border-navy-900/15 bg-cream-50/70 p-8 text-center text-xs text-navy-900/70">
            <p className="font-semibold text-navy-950">No travel schedules found</p>
            <p className="mt-1">Clear filters or launch a schedule for an active bus.</p>
            {query || routeFilter || activeFilter ? (
              <button
                type="button"
                onClick={() => {
                  setQuery("");
                  setRouteFilter("");
                  setActiveFilter("");
                  setPage(1);
                }}
                className="mt-3 rounded-lg border border-navy-900/15 bg-white px-3 py-1.5 font-semibold text-navy-950 hover:bg-cream-100"
              >
                Clear Filters
              </button>
            ) : null}
          </div>
        ) : (
          <>
            <div className="space-y-2.5">
              {schedules.map((s) => {
                const isEdit = editingId === s.id;
                return (
                  <div
                    key={s.id}
                    className="rounded-xl border border-navy-900/10 bg-cream-50/60 p-3.5 text-xs"
                  >
                    {isEdit ? (
                      <div className="space-y-2">
                        <p className="font-semibold text-navy-950">
                          {s.route_name} • {s.bus_number}
                        </p>
                        <div className="grid grid-cols-3 gap-2">
                          <input
                            type="time"
                            value={editForm.departure_time}
                            onChange={(e) =>
                              setEditForm((p) => ({ ...p, departure_time: e.target.value }))
                            }
                            className="rounded-lg border border-navy-900/20 bg-white px-2 py-1"
                          />
                          <input
                            type="time"
                            value={editForm.arrival_time}
                            onChange={(e) =>
                              setEditForm((p) => ({ ...p, arrival_time: e.target.value }))
                            }
                            className="rounded-lg border border-navy-900/20 bg-white px-2 py-1"
                          />
                          <input
                            type="number"
                            min="1"
                            value={editForm.base_fare}
                            onChange={(e) =>
                              setEditForm((p) => ({ ...p, base_fare: e.target.value }))
                            }
                            className="rounded-lg border border-navy-900/20 bg-white px-2 py-1"
                          />
                        </div>
                        <div className="flex flex-wrap items-center gap-4">
                          <label className="inline-flex items-center gap-1.5">
                            <input
                              type="checkbox"
                              checked={editForm.apply_to_future_trips}
                              onChange={(e) =>
                                setEditForm((p) => ({
                                  ...p,
                                  apply_to_future_trips: e.target.checked,
                                }))
                              }
                            />
                            <span>Update future scheduled trips</span>
                          </label>
                          <div className="flex gap-2">
                            <button
                              type="button"
                              onClick={() => saveEdit(s.id)}
                              className="inline-flex items-center gap-1 rounded-lg bg-emerald-700 px-3 py-1 font-semibold text-white"
                            >
                              <Check className="h-3 w-3" />
                              <span>Save</span>
                            </button>
                            <button
                              type="button"
                              onClick={() => setEditingId(null)}
                              className="inline-flex items-center gap-1 rounded-lg border border-navy-900/15 bg-white px-2.5 py-1"
                            >
                              <X className="h-3 w-3" />
                            </button>
                          </div>
                        </div>
                      </div>
                    ) : (
                      <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-center">
                        <div>
                          <p className="font-semibold text-navy-950">
                            {s.route_name} • <span className="font-mono">{s.bus_number}</span>
                          </p>
                          <p className="text-navy-900/70">
                            {s.operator_name} ({s.bus_type} • {s.seat_layout}) • {s.departure_time}–
                            {s.arrival_time} • ₹{s.base_fare} • {s.upcoming_trips_count ?? 0}{" "}
                            upcoming trips
                          </p>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                          <button
                            type="button"
                            onClick={() => handleToggle(s)}
                            className={`rounded-md px-2.5 py-1 font-semibold ${
                              s.is_active
                                ? "bg-emerald-50 text-emerald-700"
                                : "bg-amber-50 text-amber-800"
                            }`}
                          >
                            {s.is_active ? "Active" : "Paused"}
                          </button>
                          <button
                            type="button"
                            onClick={() => startEdit(s)}
                            className="rounded-lg border border-navy-900/15 bg-white p-1.5 text-navy-900 hover:bg-cream-100"
                          >
                            <Pencil className="h-3 w-3" />
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDelete(s)}
                            className="rounded-lg border border-red-200 bg-red-50 p-1.5 text-red-700 hover:bg-red-100"
                          >
                            <Trash2 className="h-3 w-3" />
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
            <AdminPagination pagination={pagination} onPageChange={setPage} />
          </>
        )}
      </div>
    </div>
  );
}
