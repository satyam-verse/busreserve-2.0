import { useCallback, useEffect, useState } from "react";
import { Route as RouteIcon, Plus, Pencil, Trash2, RefreshCw, Check, X } from "lucide-react";
import { busApi } from "../../services/api";
import AdminPagination from "./AdminPagination";

export default function AdminRoutesTab({ onNotify, onChanged }) {
  const [routes, setRoutes] = useState([]);
  const [pagination, setPagination] = useState(null);
  const [loading, setLoading] = useState(true);

  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);

  const [form, setForm] = useState({
    name: "",
    source: "",
    destination: "",
    distance_km: "",
    estimated_duration_minutes: "",
    stopsText: "",
  });

  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({
    name: "",
    source: "",
    destination: "",
    distance_km: "",
    estimated_duration_minutes: "",
    stopsText: "",
  });

  const loadRoutes = useCallback(async () => {
    setLoading(true);
    try {
      const data = await busApi.getAdminRoutes({ q: query, page, per_page: 10 });
      setRoutes(data.routes || []);
      setPagination(data.pagination || null);
    } catch (err) {
      onNotify("error", err.message || "Failed to load routes.");
    } finally {
      setLoading(false);
    }
  }, [query, page, onNotify]);

  useEffect(() => {
    loadRoutes();
  }, [loadRoutes]);

  async function handleCreate(e) {
    e.preventDefault();
    const stops = form.stopsText
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    try {
      const data = await busApi.createAdminRoute({
        name: form.name.trim(),
        source: form.source.trim(),
        destination: form.destination.trim(),
        distance_km: form.distance_km ? Number(form.distance_km) : null,
        estimated_duration_minutes: form.estimated_duration_minutes
          ? Number(form.estimated_duration_minutes)
          : null,
        stops,
      });
      setForm({
        name: "",
        source: "",
        destination: "",
        distance_km: "",
        estimated_duration_minutes: "",
        stopsText: "",
      });
      onNotify("success", `Route "${data.route.name}" created.`);
      setPage(1);
      await loadRoutes();
      onChanged?.();
    } catch (err) {
      onNotify("error", err.message || "Could not create route.");
    }
  }

  function startEdit(route) {
    setEditingId(route.id);
    setEditForm({
      name: route.name,
      source: route.source,
      destination: route.destination,
      distance_km: route.distance_km ?? "",
      estimated_duration_minutes: route.estimated_duration_minutes ?? "",
      stopsText: (route.stops || []).map((s) => s.stop_name).join(", "),
    });
  }

  async function saveEdit(routeId) {
    const stops = editForm.stopsText
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    try {
      const data = await busApi.updateAdminRoute(routeId, {
        name: editForm.name.trim(),
        source: editForm.source.trim(),
        destination: editForm.destination.trim(),
        distance_km: editForm.distance_km ? Number(editForm.distance_km) : null,
        estimated_duration_minutes: editForm.estimated_duration_minutes
          ? Number(editForm.estimated_duration_minutes)
          : null,
        stops,
      });
      setEditingId(null);
      onNotify("success", `Route "${data.route.name}" updated.`);
      await loadRoutes();
      onChanged?.();
    } catch (err) {
      onNotify("error", err.message || "Could not update route.");
    }
  }

  async function handleDelete(route) {
    try {
      await busApi.deleteAdminRoute(route.id);
      onNotify("success", `Route "${route.name}" deleted.`);
      await loadRoutes();
      onChanged?.();
    } catch (err) {
      onNotify("error", err.message || "Could not delete route.");
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-12">
      <form
        onSubmit={handleCreate}
        className="h-fit rounded-2xl border border-navy-900/10 bg-white p-5 shadow-sm lg:col-span-4"
      >
        <div className="mb-3 flex items-center gap-2">
          <RouteIcon className="h-4 w-4 text-navy-950" />
          <h2 className="text-base font-bold text-navy-950">Create Route</h2>
        </div>
        <div className="space-y-3">
          <input
            type="text"
            required
            placeholder="Route Name (e.g. Kochi to Munnar Express)"
            value={form.name}
            onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
            className="w-full rounded-xl border border-navy-900/15 bg-cream-50/60 px-3 py-2 text-xs outline-none focus:border-navy-700 focus:bg-white"
          />
          <div className="grid grid-cols-2 gap-2">
            <input
              type="text"
              required
              placeholder="Source City"
              value={form.source}
              onChange={(e) => setForm((p) => ({ ...p, source: e.target.value }))}
              className="rounded-xl border border-navy-900/15 bg-cream-50/60 px-3 py-2 text-xs outline-none focus:border-navy-700 focus:bg-white"
            />
            <input
              type="text"
              required
              placeholder="Destination City"
              value={form.destination}
              onChange={(e) => setForm((p) => ({ ...p, destination: e.target.value }))}
              className="rounded-xl border border-navy-900/15 bg-cream-50/60 px-3 py-2 text-xs outline-none focus:border-navy-700 focus:bg-white"
            />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <input
              type="number"
              min="1"
              placeholder="Distance (km)"
              value={form.distance_km}
              onChange={(e) => setForm((p) => ({ ...p, distance_km: e.target.value }))}
              className="rounded-xl border border-navy-900/15 bg-cream-50/60 px-3 py-2 text-xs outline-none focus:border-navy-700 focus:bg-white"
            />
            <input
              type="number"
              min="10"
              placeholder="Duration (mins)"
              value={form.estimated_duration_minutes}
              onChange={(e) =>
                setForm((p) => ({ ...p, estimated_duration_minutes: e.target.value }))
              }
              className="rounded-xl border border-navy-900/15 bg-cream-50/60 px-3 py-2 text-xs outline-none focus:border-navy-700 focus:bg-white"
            />
          </div>
          <textarea
            rows={2}
            required
            placeholder="Ordered stops comma-separated (min 2)"
            value={form.stopsText}
            onChange={(e) => setForm((p) => ({ ...p, stopsText: e.target.value }))}
            className="w-full rounded-xl border border-navy-900/15 bg-cream-50/60 px-3 py-2 text-xs outline-none focus:border-navy-700 focus:bg-white"
          />
          <button
            type="submit"
            className="inline-flex w-full items-center justify-center gap-1.5 rounded-xl bg-navy-950 px-3 py-2.5 text-xs font-semibold text-white hover:bg-navy-800"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Create Route</span>
          </button>
        </div>
      </form>

      <div className="rounded-2xl border border-navy-900/10 bg-white p-6 shadow-sm lg:col-span-8">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-bold text-navy-950">Corridors &amp; Stops</h2>
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Search route, source, dest..."
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setPage(1);
              }}
              className="rounded-xl border border-navy-900/15 bg-cream-50/60 px-3 py-2 text-xs outline-none focus:border-navy-700 focus:bg-white"
            />
            <button
              type="button"
              onClick={loadRoutes}
              className="inline-flex items-center gap-1 rounded-xl bg-navy-950 px-3 py-2 text-xs font-semibold text-white"
            >
              <RefreshCw className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        {loading ? (
          <p className="text-sm text-navy-900/65">Loading routes...</p>
        ) : routes.length === 0 ? (
          <div className="rounded-xl border border-dashed border-navy-900/15 bg-cream-50/70 p-8 text-center text-xs text-navy-900/70">
            <p className="font-semibold text-navy-950">No routes found</p>
            <p className="mt-1">Try adjusting your route search or add a new corridor.</p>
            {query ? (
              <button
                type="button"
                onClick={() => {
                  setQuery("");
                  setPage(1);
                }}
                className="mt-3 rounded-lg border border-navy-900/15 bg-white px-3 py-1.5 font-semibold text-navy-950 hover:bg-cream-100"
              >
                Clear Search
              </button>
            ) : null}
          </div>
        ) : (
          <>
            <div className="space-y-3">
              {routes.map((r) => {
                const isEdit = editingId === r.id;
                return (
                  <div
                    key={r.id}
                    className="rounded-xl border border-navy-900/10 bg-cream-50/60 p-4 text-xs"
                  >
                    {isEdit ? (
                      <div className="space-y-2">
                        <input
                          type="text"
                          value={editForm.name}
                          onChange={(e) => setEditForm((p) => ({ ...p, name: e.target.value }))}
                          className="w-full rounded-lg border border-navy-900/20 bg-white px-2.5 py-1.5"
                        />
                        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                          <input
                            type="text"
                            placeholder="Source"
                            value={editForm.source}
                            onChange={(e) => setEditForm((p) => ({ ...p, source: e.target.value }))}
                            className="rounded-lg border border-navy-900/20 bg-white px-2 py-1"
                          />
                          <input
                            type="text"
                            placeholder="Destination"
                            value={editForm.destination}
                            onChange={(e) =>
                              setEditForm((p) => ({ ...p, destination: e.target.value }))
                            }
                            className="rounded-lg border border-navy-900/20 bg-white px-2 py-1"
                          />
                          <input
                            type="number"
                            placeholder="Distance km"
                            value={editForm.distance_km}
                            onChange={(e) =>
                              setEditForm((p) => ({ ...p, distance_km: e.target.value }))
                            }
                            className="rounded-lg border border-navy-900/20 bg-white px-2 py-1"
                          />
                          <input
                            type="number"
                            placeholder="Duration mins"
                            value={editForm.estimated_duration_minutes}
                            onChange={(e) =>
                              setEditForm((p) => ({
                                ...p,
                                estimated_duration_minutes: e.target.value,
                              }))
                            }
                            className="rounded-lg border border-navy-900/20 bg-white px-2 py-1"
                          />
                        </div>
                        <input
                          type="text"
                          value={editForm.stopsText}
                          onChange={(e) =>
                            setEditForm((p) => ({ ...p, stopsText: e.target.value }))
                          }
                          className="w-full rounded-lg border border-navy-900/20 bg-white px-2.5 py-1.5"
                        />
                        <div className="flex gap-2">
                          <button
                            type="button"
                            onClick={() => saveEdit(r.id)}
                            className="inline-flex items-center gap-1 rounded-lg bg-emerald-700 px-3 py-1 font-semibold text-white"
                          >
                            <Check className="h-3 w-3" />
                            <span>Save Route</span>
                          </button>
                          <button
                            type="button"
                            onClick={() => setEditingId(null)}
                            className="inline-flex items-center gap-1 rounded-lg border border-navy-900/15 bg-white px-3 py-1"
                          >
                            <X className="h-3 w-3" />
                            <span>Cancel</span>
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-start">
                        <div>
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="text-sm font-bold text-navy-950">{r.name}</span>
                            <span className="rounded-full bg-white px-2 py-0.5 font-mono text-[11px] font-semibold text-navy-800">
                              {r.source} → {r.destination}
                            </span>
                            {r.distance_km ? (
                              <span className="text-navy-900/65">{r.distance_km} km</span>
                            ) : null}
                            {r.estimated_duration_minutes ? (
                              <span className="text-navy-900/65">
                                {Math.floor(r.estimated_duration_minutes / 60)}h{" "}
                                {String(r.estimated_duration_minutes % 60).padStart(2, "0")}m
                              </span>
                            ) : null}
                          </div>
                          <p className="mt-1 text-[11px] text-navy-900/70">
                            Stops: {(r.stops || []).map((s) => s.stop_name).join(" • ")}
                          </p>
                          <p className="mt-1 text-[11px] text-navy-900/55">
                            {r.schedule_count ?? 0} schedule(s) • {r.trip_count ?? 0} trip(s)
                          </p>
                        </div>
                        <div className="flex gap-2">
                          <button
                            type="button"
                            onClick={() => startEdit(r)}
                            className="inline-flex items-center gap-1 rounded-lg border border-navy-900/15 bg-white px-2.5 py-1 font-semibold text-navy-950 hover:bg-cream-100"
                          >
                            <Pencil className="h-3 w-3" />
                            <span>Edit</span>
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDelete(r)}
                            className="inline-flex items-center gap-1 rounded-lg border border-red-200 bg-red-50 px-2.5 py-1 font-semibold text-red-700 hover:bg-red-100"
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
