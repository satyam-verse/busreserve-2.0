import { useCallback, useEffect, useState } from "react";
import { RefreshCw, ShieldAlert } from "lucide-react";
import { useAuth } from "../../context/AuthContext";
import { busApi } from "../../services/api";
import AdminPagination from "./AdminPagination";

export default function AdminUsersTab({ onNotify, onChanged }) {
  const { user: currentUser } = useAuth();
  const [usersList, setUsersList] = useState([]);
  const [pagination, setPagination] = useState(null);
  const [loading, setLoading] = useState(true);

  const [query, setQuery] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [activeFilter, setActiveFilter] = useState("");
  const [page, setPage] = useState(1);

  const loadUsers = useCallback(async () => {
    setLoading(true);
    try {
      const data = await busApi.getAdminUsers({
        q: query,
        role: roleFilter,
        is_active: activeFilter,
        page,
        per_page: 12,
      });
      setUsersList(data.users || []);
      setPagination(data.pagination || null);
    } catch (err) {
      onNotify("error", err.message || "Failed to load users.");
    } finally {
      setLoading(false);
    }
  }, [query, roleFilter, activeFilter, page, onNotify]);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  async function updateUserField(u, payload, msg) {
    try {
      await busApi.updateAdminUser(u.id, payload);
      onNotify("success", msg || `Updated ${u.email}.`);
      await loadUsers();
      onChanged?.();
    } catch (err) {
      onNotify("error", err.message || "Could not update user.");
    }
  }

  return (
    <div className="rounded-2xl border border-navy-900/10 bg-white p-6 shadow-sm">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-navy-950">Registered Accounts &amp; Roles</h2>
          <p className="inline-flex items-center gap-1.5 text-xs text-navy-900/65">
            <ShieldAlert className="h-3.5 w-3.5 text-amber-700" />
            <span>
              Administrators cannot suspend or demote themselves or remove the last active admin.
            </span>
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <input
            type="text"
            placeholder="Search name, email, phone..."
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setPage(1);
            }}
            className="rounded-xl border border-navy-900/15 bg-cream-50/60 px-3 py-2 text-xs outline-none"
          />
          <select
            value={roleFilter}
            onChange={(e) => {
              setRoleFilter(e.target.value);
              setPage(1);
            }}
            className="rounded-xl border border-navy-900/15 bg-cream-50/60 px-2.5 py-2 text-xs outline-none"
          >
            <option value="">All Roles</option>
            <option value="USER">USER</option>
            <option value="ADMIN">ADMIN</option>
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
            <option value="false">Suspended</option>
          </select>
          <button
            type="button"
            onClick={loadUsers}
            className="inline-flex items-center gap-1 rounded-xl bg-navy-950 px-3 py-2 text-xs font-semibold text-white"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {loading ? (
        <p className="text-sm text-navy-900/65">Loading users...</p>
      ) : usersList.length === 0 ? (
        <div className="rounded-xl border border-dashed border-navy-900/15 bg-cream-50/70 p-8 text-center text-xs text-navy-900/70">
          <p className="font-semibold text-navy-950">No user accounts match your filters</p>
          <p className="mt-1">Adjust your search term, role, or account status filter.</p>
          {query || roleFilter || activeFilter ? (
            <button
              type="button"
              onClick={() => {
                setQuery("");
                setRoleFilter("");
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
                  <th className="pb-3 pr-3">Account</th>
                  <th className="pb-3 pr-3">Role</th>
                  <th className="pb-3 pr-3">Verified</th>
                  <th className="pb-3 pr-3">Activity</th>
                  <th className="pb-3 pr-3">Status</th>
                  <th className="pb-3">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-navy-900/10">
                {usersList.map((u) => {
                  const isSelf = u.id === currentUser?.id;
                  return (
                    <tr key={u.id}>
                      <td className="py-3 pr-3">
                        <p className="font-semibold text-navy-950">{u.full_name}</p>
                        <p className="text-[11px] text-navy-900/65">{u.email}</p>
                      </td>
                      <td className="py-3 pr-3">
                        {isSelf ? (
                          <span className="rounded-md bg-navy-900/5 px-2 py-0.5 font-mono font-semibold text-navy-950">
                            {u.role}
                          </span>
                        ) : (
                          <select
                            aria-label={`Role for ${u.email}`}
                            value={u.role}
                            onChange={(e) =>
                              updateUserField(
                                u,
                                { role: e.target.value },
                                `Changed ${u.email} role to ${e.target.value}.`
                              )
                            }
                            className="rounded-lg border border-navy-900/15 bg-cream-50/70 px-2 py-1 font-mono text-xs"
                          >
                            <option value="USER">USER</option>
                            <option value="ADMIN">ADMIN</option>
                          </select>
                        )}
                      </td>
                      <td className="py-3 pr-3">
                        <span
                          className={`rounded-full px-2 py-0.5 font-semibold ${
                            u.email_verified
                              ? "bg-emerald-50 text-emerald-700"
                              : "bg-amber-50 text-amber-700"
                          }`}
                        >
                          {u.email_verified ? "Verified" : "Pending"}
                        </span>
                      </td>
                      <td className="py-3 pr-3">
                        <span className="font-semibold">{u.booking_count ?? 0}</span> bookings •{" "}
                        {u.active_sessions_count ?? 0} sessions
                      </td>
                      <td className="py-3 pr-3">
                        <span
                          className={`rounded-full px-2 py-0.5 font-semibold ${
                            u.is_active ? "bg-emerald-50 text-emerald-700" : "bg-red-50 text-red-700"
                          }`}
                        >
                          {u.is_active ? "Active" : "Suspended"}
                        </span>
                      </td>
                      <td className="py-3">
                        <div className="flex flex-wrap gap-2">
                          {isSelf ? (
                            <span className="rounded-lg bg-navy-900/5 px-2.5 py-1 font-semibold text-navy-900/65">
                              Current Session
                            </span>
                          ) : (
                            <button
                              type="button"
                              onClick={() =>
                                updateUserField(
                                  u,
                                  { is_active: !u.is_active },
                                  `${u.email} ${u.is_active ? "suspended" : "reactivated"}.`
                                )
                              }
                              className="rounded-lg border border-navy-900/15 px-2.5 py-1 font-semibold text-navy-950 hover:bg-cream-100"
                            >
                              {u.is_active ? "Suspend" : "Reactivate"}
                            </button>
                          )}
                          {!u.email_verified ? (
                            <button
                              type="button"
                              onClick={() =>
                                updateUserField(
                                  u,
                                  { email_verified: true },
                                  `Verified email for ${u.email}.`
                                )
                              }
                              className="rounded-lg border border-emerald-200 bg-emerald-50 px-2.5 py-1 font-semibold text-emerald-700 hover:bg-emerald-100"
                            >
                              Verify Email
                            </button>
                          ) : null}
                        </div>
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
  );
}
