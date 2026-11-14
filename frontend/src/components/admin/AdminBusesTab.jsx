import { useCallback, useEffect, useState } from "react";
import { Bus, Plus, Pencil, Trash2, RefreshCw, Check, X } from "lucide-react";
import { busApi } from "../../services/api";
import AdminPagination from "./AdminPagination";

const BUS_TYPES = [
  "AC_SEATER",
  "NON_AC_SEATER",
  "AC_SLEEPER",
  "SEATER_SLEEPER",
  "VOLVO_MULTI_AXLE",
];

const SEAT_LAYOUTS = ["2+2", "2+1", "1+2"];

export default function AdminBusesTab({ onNotify, onChanged }) {
  const [buses, setBuses] = useState([]);
  const [pagination, setPagination] = useState(null);
  const [loading, setLoading] = useState(true);

  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [layoutFilter, setLayoutFilter] = useState("");
  const [page, setPage] = useState(1);

  const [form, setForm] = useState({
    operator_name: "",
    registration_number: "",
    bus_type: "AC_SEATER",
    seat_layout: "2+2",
    total_seats: "32",
    amenities: "AC, Charging Point, Live GPS",
  });

  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({
    operator_name: "",
    registration_number: "",
    bus_type: "AC_SEATER",
    seat_layout: "2+2",
    total_seats: "32",
    amenities: "",
    is_active: true,
  });

  const loadBuses = useCallback(async () => {
    setLoading(true);
    try {
      const data = await busApi.getAdminBuses({
        q: query,
        bus_type: typeFilter,
        seat_layout: layoutFilter,
        page,
        per_page: 10,
      });
      setBuses(data.buses || []);
      setPagination(data.pagination || null);
    } catch (err) {
      onNotify("error", err.message || "Failed to load bus fleet.");
    } finally {
      setLoading(false);
    }
  }, [query, typeFilter, layoutFilter, page, onNotify]);

  useEffect(() => {
    loadBuses();
  }, [loadBuses]);

  async function handleCreate(e) {
    e.preventDefault();
    try {
      const data = await busApi.createAdminBus({
        operator_name: form.operator_name.trim(),
        registration_number: form.registration_number.trim(),
        bus_type: form.bus_type,
        seat_layout: form.seat_layout,
        total_seats: Number(form.total_seats),
        amenities: form.amenities.trim() || null,
      });
      setForm((p) => ({ ...p, operator_name: "", registration_number: "" }));
      onNotify("success", `Bus "${data.bus.registration_number}" registered.`);
      setPage(1);
      await loadBuses();
      onChanged?.();
    } catch (err) {
      onNotify("error", err.message || "Could not create bus.");
    }
  }

  function startEdit(bus) {
    setEditingId(bus.id);
    setEditForm({
      operator_name: bus.operator_name,
      registration_number: bus.registration_number,
      bus_type: bus.bus_type,
      seat_layout: bus.seat_layout,
      total_seats: String(bus.total_seats),
      amenities: bus.amenities_text || "",
      is_active: bus.is_active,
    });
  }

  async function saveEdit(busId) {
    try {
      const data = await busApi.updateAdminBus(busId, {
        operator_name: editForm.operator_name.trim(),
        registration_number: editForm.registration_number.trim(),
        bus_type: editForm.bus_type,
        seat_layout: editForm.seat_layout,
        total_seats: Number(editForm.total_seats),
        amenities: editForm.amenities.trim() || null,
        is_active: editForm.is_active,
      });
      setEditingId(null);
      onNotify("success", `Bus "${data.bus.registration_number}" updated.`);
      await loadBuses();
      onChanged?.();
    } catch (err) {
      onNotify("error", err.message || "Could not update bus.");
    }
  }

  async function handleDelete(bus) {
    try {
      await busApi.deleteAdminBus(bus.id);
      onNotify("success", `Bus "${bus.registration_number}" removed.`);
      await loadBuses();
      onChanged?.();
    } catch (err) {
      onNotify("error", err.message || "Could not remove bus.");
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-12">
      <form
        onSubmit={handleCreate}
        className="h-fit rounded-2xl border border-navy-900/10 bg-white p-5 shadow-sm lg:col-span-4"
      >
        <div className="mb-3 flex items-center gap-2">
          <Bus className="h-4 w-4 text-navy-950" />
          <h2 className="text-base font-bold text-navy-950">Register Fleet Bus</h2>
        </div>
        <div className="space-y-3">
          <input
            type="text"
            required
            placeholder="Operator Name (e.g. Malabar Express)"
            value={form.operator_name}
            onChange={(e) => setForm((p) => ({ ...p, operator_name: e.target.value }))}
            className="w-full rounded-xl border border-navy-900/15 bg-cream-50/60 px-3 py-2 text-xs outline-none focus:border-navy-700 focus:bg-white"
          />
          <input
            type="text"
            required
            placeholder="Registration Number (e.g. KL-07-PA-7788)"
            value={form.registration_number}
            onChange={(e) => setForm((p) => ({ ...p, registration_number: e.target.value }))}
            className="w-full rounded-xl border border-navy-900/15 bg-cream-50/60 px-3 py-2 text-xs uppercase outline-none focus:border-navy-700 focus:bg-white"
          />
          <div className="grid grid-cols-2 gap-2">
            <select
              value={form.bus_type}
              onChange={(e) => setForm((p) => ({ ...p, bus_type: e.target.value }))}
              className="rounded-xl border border-navy-900/15 bg-cream-50/60 px-2.5 py-2 text-xs outline-none"
            >
              {BUS_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
            <select
              value={form.seat_layout}
              onChange={(e) => setForm((p) => ({ ...p, seat_layout: e.target.value }))}
              className="rounded-xl border border-navy-900/15 bg-cream-50/60 px-2.5 py-2 text-xs outline-none"
            >
              {SEAT_LAYOUTS.map((l) => (
                <option key={l} value={l}>
                  Layout {l}
                </option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-3 gap-2">
            <input
              type="number"
              min="4"
              max="80"
              required
              placeholder="Seats"
              value={form.total_seats}
              onChange={(e) => setForm((p) => ({ ...p, total_seats: e.target.value }))}
              className="rounded-xl border border-navy-900/15 bg-cream-50/60 px-3 py-2 text-xs outline-none"
            />
            <input
              type="text"
              placeholder="Amenities"
              value={form.amenities}
              onChange={(e) => setForm((p) => ({ ...p, amenities: e.target.value }))}
              className="col-span-2 rounded-xl border border-navy-900/15 bg-cream-50/60 px-3 py-2 text-xs outline-none"
            />
          </div>
          <button
            type="submit"
            className="inline-flex w-full items-center justify-center gap-1.5 rounded-xl bg-navy-950 px-3 py-2.5 text-xs font-semibold text-white hover:bg-navy-800"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Add Bus to Fleet</span>
          </button>
        </div>
      </form>

      <div className="rounded-2xl border border-navy-900/10 bg-white p-6 shadow-sm lg:col-span-8">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-bold text-navy-950">Bus Fleet</h2>
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
              value={typeFilter}
              onChange={(e) => {
                setTypeFilter(e.target.value);
                setPage(1);
              }}
              className="rounded-xl border border-navy-900/15 bg-cream-50/60 px-2.5 py-2 text-xs outline-none"
            >
              <option value="">All Types</option>
              {BUS_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
            <select
              value={layoutFilter}
              onChange={(e) => {
                setLayoutFilter(e.target.value);
                setPage(1);
              }}
              className="rounded-xl border border-navy-900/15 bg-cream-50/60 px-2.5 py-2 text-xs outline-none"
            >
              <option value="">All Layouts</option>
              {SEAT_LAYOUTS.map((l) => (
                <option key={l} value={l}>
                  {l}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={loadBuses}
              className="inline-flex items-center gap-1 rounded-xl bg-navy-950 px-3 py-2 text-xs font-semibold text-white"
            >
              <RefreshCw className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        {loading ? (
          <p className="text-sm text-navy-900/65">Loading fleet...</p>
        ) : buses.length === 0 ? (
          <div className="rounded-xl border border-dashed border-navy-900/15 bg-cream-50/70 p-8 text-center text-xs text-navy-900/70">
            <p className="font-semibold text-navy-950">No buses match your filters</p>
            <p className="mt-1">Clear filters or register a new vehicle on the left.</p>
            {query || typeFilter || layoutFilter ? (
              <button
                type="button"
                onClick={() => {
                  setQuery("");
                  setTypeFilter("");
                  setLayoutFilter("");
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
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-navy-900/10 uppercase text-navy-900/55">
                    <th className="pb-2.5 pr-3">Operator &amp; Reg #</th>
                    <th className="pb-2.5 pr-3">Type / Layout</th>
                    <th className="pb-2.5 pr-3">Seats</th>
                    <th className="pb-2.5 pr-3">Status</th>
                    <th className="pb-2.5">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-navy-900/10">
                  {buses.map((b) => {
                    const isEdit = editingId === b.id;
                    return (
                      <tr key={b.id}>
                        <td className="py-2.5 pr-3">
                          {isEdit ? (
                            <div className="space-y-1">
                              <input
                                type="text"
                                value={editForm.operator_name}
                                onChange={(e) =>
                                  setEditForm((p) => ({ ...p, operator_name: e.target.value }))
                                }
                                className="w-full rounded-lg border border-navy-900/20 px-2 py-1"
                              />
                              <input
                                type="text"
                                value={editForm.registration_number}
                                onChange={(e) =>
                                  setEditForm((p) => ({
                                    ...p,
                                    registration_number: e.target.value,
                                  }))
                                }
                                className="w-full rounded-lg border border-navy-900/20 px-2 py-1 font-mono uppercase"
                              />
                            </div>
                          ) : (
                            <div>
                              <p className="font-semibold text-navy-950">{b.operator_name}</p>
                              <p className="font-mono text-[11px] text-navy-900/70">
                                {b.registration_number} ({b.schedule_count ?? 0} sched)
                              </p>
                            </div>
                          )}
                        </td>
                        <td className="py-2.5 pr-3">
                          {isEdit ? (
                            <div className="flex gap-1">
                              <select
                                value={editForm.bus_type}
                                onChange={(e) =>
                                  setEditForm((p) => ({ ...p, bus_type: e.target.value }))
                                }
                                className="rounded-lg border border-navy-900/20 px-1.5 py-1"
                              >
                                {BUS_TYPES.map((t) => (
                                  <option key={t} value={t}>
                                    {t}
                                  </option>
                                ))}
                              </select>
                              <select
                                value={editForm.seat_layout}
                                onChange={(e) =>
                                  setEditForm((p) => ({ ...p, seat_layout: e.target.value }))
                                }
                                className="rounded-lg border border-navy-900/20 px-1.5 py-1"
                              >
                                {SEAT_LAYOUTS.map((l) => (
                                  <option key={l} value={l}>
                                    {l}
                                  </option>
                                ))}
                              </select>
                            </div>
                          ) : (
                            <span>
                              {b.bus_type} • <strong>{b.seat_layout}</strong>
                            </span>
                          )}
                        </td>
                        <td className="py-2.5 pr-3">
                          {isEdit ? (
                            <input
                              type="number"
                              min="4"
                              max="80"
                              value={editForm.total_seats}
                              onChange={(e) =>
                                setEditForm((p) => ({ ...p, total_seats: e.target.value }))
                              }
                              className="w-16 rounded-lg border border-navy-900/20 px-2 py-1"
                            />
                          ) : (
                            <span className="font-semibold">{b.total_seats}</span>
                          )}
                        </td>
                        <td className="py-2.5 pr-3">
                          {isEdit ? (
                            <label className="inline-flex items-center gap-1">
                              <input
                                type="checkbox"
                                checked={editForm.is_active}
                                onChange={(e) =>
                                  setEditForm((p) => ({ ...p, is_active: e.target.checked }))
                                }
                              />
                              <span>Active</span>
                            </label>
                          ) : (
                            <span
                              className={`rounded-full px-2 py-0.5 font-semibold ${
                                b.is_active
                                  ? "bg-emerald-50 text-emerald-700"
                                  : "bg-red-50 text-red-700"
                              }`}
                            >
                              {b.is_active ? "Active" : "Inactive"}
                            </span>
                          )}
                        </td>
                        <td className="py-2.5">
                          {isEdit ? (
                            <div className="flex gap-1.5">
                              <button
                                type="button"
                                onClick={() => saveEdit(b.id)}
                                className="inline-flex items-center gap-1 rounded-lg bg-emerald-700 px-2 py-1 font-semibold text-white"
                              >
                                <Check className="h-3 w-3" />
                              </button>
                              <button
                                type="button"
                                onClick={() => setEditingId(null)}
                                className="inline-flex items-center gap-1 rounded-lg border border-navy-900/15 px-2 py-1"
                              >
                                <X className="h-3 w-3" />
                              </button>
                            </div>
                          ) : (
                            <div className="flex gap-2">
                              <button
                                type="button"
                                onClick={() => startEdit(b)}
                                className="text-navy-800 hover:text-navy-950"
                              >
                                <Pencil className="h-3.5 w-3.5" />
                              </button>
                              <button
                                type="button"
                                onClick={() => handleDelete(b)}
                                className="text-red-600 hover:text-red-800"
                              >
                                <Trash2 className="h-3.5 w-3.5" />
                              </button>
                            </div>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <AdminPagination pagination={pagination} onPageChange={setPage} />
          </>
        )}
      </div>
    </div>
  );
}
