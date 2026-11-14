import { useCallback, useEffect, useState } from "react";
import { MapPin, Plus, Pencil, Trash2, RefreshCw, Check, X } from "lucide-react";
import { busApi } from "../../services/api";
import AdminPagination from "./AdminPagination";

export default function AdminCitiesTab({ onNotify, onChanged }) {
  const [cities, setCities] = useState([]);
  const [states, setStates] = useState([]);
  const [pagination, setPagination] = useState(null);
  const [loading, setLoading] = useState(true);

  const [query, setQuery] = useState("");
  const [stateFilter, setStateFilter] = useState("");
  const [activeFilter, setActiveFilter] = useState("");
  const [page, setPage] = useState(1);

  const [createForm, setCreateForm] = useState({ name: "", state: "", aliases: "" });
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({ name: "", state: "", aliases: "", is_active: true });

  const loadCities = useCallback(async () => {
    setLoading(true);
    try {
      const data = await busApi.getAdminCities({
        q: query,
        state: stateFilter,
        is_active: activeFilter,
        page,
        per_page: 12,
      });
      setCities(data.cities || []);
      setStates(data.states || []);
      setPagination(data.pagination || null);
    } catch (err) {
      onNotify("error", err.message || "Failed to load cities.");
    } finally {
      setLoading(false);
    }
  }, [query, stateFilter, activeFilter, page, onNotify]);

  useEffect(() => {
    loadCities();
  }, [loadCities]);

  async function handleCreate(e) {
    e.preventDefault();
    try {
      const data = await busApi.createAdminCity({
        name: createForm.name.trim(),
        state: createForm.state.trim() || null,
        aliases: createForm.aliases.trim() || null,
      });
      setCreateForm({ name: "", state: "", aliases: "" });
      onNotify("success", `City "${data.city.name}" added.`);
      setPage(1);
      await loadCities();
      onChanged?.();
    } catch (err) {
      onNotify("error", err.message || "Could not create city.");
    }
  }

  function startEdit(city) {
    setEditingId(city.id);
    setEditForm({
      name: city.name,
      state: city.state || "",
      aliases: (city.aliases || []).join(", "),
      is_active: city.is_active,
    });
  }

  async function saveEdit(cityId) {
    try {
      const data = await busApi.updateAdminCity(cityId, {
        name: editForm.name.trim(),
        state: editForm.state.trim() || null,
        aliases: editForm.aliases.trim() || null,
        is_active: editForm.is_active,
      });
      setEditingId(null);
      onNotify("success", `City "${data.city.name}" updated.`);
      await loadCities();
      onChanged?.();
    } catch (err) {
      onNotify("error", err.message || "Could not update city.");
    }
  }

  async function handleDelete(city) {
    try {
      await busApi.deleteAdminCity(city.id);
      onNotify("success", `City "${city.name}" deleted.`);
      await loadCities();
      onChanged?.();
    } catch (err) {
      onNotify("error", err.message || "Could not delete city.");
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-12">
      <form
        onSubmit={handleCreate}
        className="h-fit rounded-2xl border border-navy-900/10 bg-white p-5 shadow-sm lg:col-span-4"
      >
        <div className="mb-3 flex items-center gap-2">
          <MapPin className="h-4 w-4 text-navy-950" />
          <h2 className="text-base font-bold text-navy-950">Add City</h2>
        </div>
        <p className="mb-4 text-xs text-navy-900/65">
          Add any Indian city or town. No hardcoded restrictions apply.
        </p>
        <div className="space-y-3">
          <div>
            <label htmlFor="city-name" className="block text-xs font-semibold text-navy-900/80">
              City Name
            </label>
            <input
              id="city-name"
              type="text"
              required
              placeholder="e.g. Kochi"
              value={createForm.name}
              onChange={(e) => setCreateForm((p) => ({ ...p, name: e.target.value }))}
              className="mt-1 w-full rounded-xl border border-navy-900/15 bg-cream-50/60 px-3 py-2 text-xs outline-none focus:border-navy-700 focus:bg-white"
            />
          </div>
          <div>
            <label htmlFor="city-state" className="block text-xs font-semibold text-navy-900/80">
              State / UT
            </label>
            <input
              id="city-state"
              type="text"
              placeholder="e.g. Kerala"
              value={createForm.state}
              onChange={(e) => setCreateForm((p) => ({ ...p, state: e.target.value }))}
              className="mt-1 w-full rounded-xl border border-navy-900/15 bg-cream-50/60 px-3 py-2 text-xs outline-none focus:border-navy-700 focus:bg-white"
            />
          </div>
          <div>
            <label
              htmlFor="city-aliases"
              className="block text-xs font-semibold text-navy-900/80"
            >
              Search Aliases (Comma-separated)
            </label>
            <input
              id="city-aliases"
              type="text"
              placeholder="e.g. Cochin, COK"
              value={createForm.aliases}
              onChange={(e) => setCreateForm((p) => ({ ...p, aliases: e.target.value }))}
              className="mt-1 w-full rounded-xl border border-navy-900/15 bg-cream-50/60 px-3 py-2 text-xs outline-none focus:border-navy-700 focus:bg-white"
            />
          </div>
          <button
            type="submit"
            className="inline-flex w-full items-center justify-center gap-1.5 rounded-xl bg-navy-950 px-3 py-2.5 text-xs font-semibold text-white hover:bg-navy-800"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Add Searchable City</span>
          </button>
        </div>
      </form>

      <div className="rounded-2xl border border-navy-900/10 bg-white p-6 shadow-sm lg:col-span-8">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-bold text-navy-950">Cities Directory</h2>
          <div className="flex flex-wrap gap-2">
            <input
              type="text"
              placeholder="Search city or alias..."
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setPage(1);
              }}
              className="rounded-xl border border-navy-900/15 bg-cream-50/60 px-3 py-2 text-xs outline-none focus:border-navy-700 focus:bg-white"
            />
            <select
              value={stateFilter}
              onChange={(e) => {
                setStateFilter(e.target.value);
                setPage(1);
              }}
              className="rounded-xl border border-navy-900/15 bg-cream-50/60 px-3 py-2 text-xs outline-none"
            >
              <option value="">All States</option>
              {states.map((st) => (
                <option key={st} value={st}>
                  {st}
                </option>
              ))}
            </select>
            <select
              value={activeFilter}
              onChange={(e) => {
                setActiveFilter(e.target.value);
                setPage(1);
              }}
              className="rounded-xl border border-navy-900/15 bg-cream-50/60 px-3 py-2 text-xs outline-none"
            >
              <option value="">All Status</option>
              <option value="true">Active</option>
              <option value="false">Paused</option>
            </select>
            <button
              type="button"
              onClick={loadCities}
              className="inline-flex items-center gap-1 rounded-xl bg-navy-950 px-3 py-2 text-xs font-semibold text-white"
            >
              <RefreshCw className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        {loading ? (
          <p className="text-sm text-navy-900/65">Loading cities...</p>
        ) : cities.length === 0 ? (
          <div className="rounded-xl border border-dashed border-navy-900/15 bg-cream-50/70 p-8 text-center text-xs text-navy-900/70">
            <p className="font-semibold text-navy-950">No cities found</p>
            <p className="mt-1">Try adjusting your search or filter criteria.</p>
            {query || stateFilter || activeFilter ? (
              <button
                type="button"
                onClick={() => {
                  setQuery("");
                  setStateFilter("");
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
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-navy-900/10 uppercase text-navy-900/55">
                    <th className="pb-2.5 pr-3">City / Aliases</th>
                    <th className="pb-2.5 pr-3">State</th>
                    <th className="pb-2.5 pr-3">Routes</th>
                    <th className="pb-2.5 pr-3">Status</th>
                    <th className="pb-2.5">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-navy-900/10">
                  {cities.map((c) => {
                    const isEdit = editingId === c.id;
                    return (
                      <tr key={c.id}>
                        <td className="py-2.5 pr-3">
                          {isEdit ? (
                            <div className="space-y-1">
                              <input
                                type="text"
                                value={editForm.name}
                                onChange={(e) =>
                                  setEditForm((p) => ({ ...p, name: e.target.value }))
                                }
                                className="w-full rounded-lg border border-navy-900/20 px-2 py-1 text-xs"
                              />
                              <input
                                type="text"
                                placeholder="Aliases"
                                value={editForm.aliases}
                                onChange={(e) =>
                                  setEditForm((p) => ({ ...p, aliases: e.target.value }))
                                }
                                className="w-full rounded-lg border border-navy-900/20 px-2 py-1 text-xs"
                              />
                            </div>
                          ) : (
                            <div>
                              <span className="font-semibold text-navy-950">{c.name}</span>
                              {c.aliases?.length ? (
                                <p className="text-[11px] text-navy-900/55">
                                  Aliases: {c.aliases.join(", ")}
                                </p>
                              ) : null}
                            </div>
                          )}
                        </td>
                        <td className="py-2.5 pr-3">
                          {isEdit ? (
                            <input
                              type="text"
                              value={editForm.state}
                              onChange={(e) =>
                                setEditForm((p) => ({ ...p, state: e.target.value }))
                              }
                              className="w-28 rounded-lg border border-navy-900/20 px-2 py-1 text-xs"
                            />
                          ) : (
                            c.state || "—"
                          )}
                        </td>
                        <td className="py-2.5 pr-3 font-semibold">{c.route_count ?? 0}</td>
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
                                c.is_active
                                  ? "bg-emerald-50 text-emerald-700"
                                  : "bg-red-50 text-red-700"
                              }`}
                            >
                              {c.is_active ? "Active" : "Paused"}
                            </span>
                          )}
                        </td>
                        <td className="py-2.5">
                          {isEdit ? (
                            <div className="flex gap-1.5">
                              <button
                                type="button"
                                onClick={() => saveEdit(c.id)}
                                className="inline-flex items-center gap-1 rounded-lg bg-emerald-700 px-2 py-1 font-semibold text-white"
                              >
                                <Check className="h-3 w-3" />
                                <span>Save</span>
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
                                onClick={() => startEdit(c)}
                                title="Edit city"
                                className="text-navy-800 hover:text-navy-950"
                              >
                                <Pencil className="h-3.5 w-3.5" />
                              </button>
                              <button
                                type="button"
                                onClick={() => handleDelete(c)}
                                title="Delete unreferenced city"
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
