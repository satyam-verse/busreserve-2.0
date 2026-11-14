import { useCallback, useEffect, useState } from "react";
import { CheckCircle2, CreditCard, RefreshCw, Search, XCircle } from "lucide-react";
import { busApi } from "../../services/api";
import AdminPagination from "./AdminPagination";

export default function AdminPaymentTab({ onNotify }) {
  const [transactions, setTransactions] = useState([]);
  const [pagination, setPagination] = useState(null);
  const [loading, setLoading] = useState(true);

  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [gatewayFilter, setGatewayFilter] = useState("");
  const [page, setPage] = useState(1);

  const loadTransactions = useCallback(async () => {
    setLoading(true);
    try {
      const data = await busApi.getAdminPaymentTransactions({
        q: query,
        status: statusFilter,
        gateway: gatewayFilter,
        page,
        per_page: 15,
      });
      setTransactions(data.transactions || []);
      setPagination(data.pagination || null);
    } catch (err) {
      onNotify("error", err.message || "Failed to load payment transactions.");
    } finally {
      setLoading(false);
    }
  }, [query, statusFilter, gatewayFilter, page, onNotify]);

  useEffect(() => {
    loadTransactions();
  }, [loadTransactions]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    loadTransactions();
  };

  return (
    <div className="space-y-6">
      <div className="rounded-2xl border border-navy-900/10 bg-white p-6 shadow-sm">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="flex items-center gap-2 font-display text-xl font-bold text-navy-950">
              <CreditCard className="h-5 w-5 text-emerald-600" />
              Financial Transactions &amp; Gateway Logs
            </h2>
            <p className="mt-1 text-xs text-slate-500">
              Audit trail of sandbox transactions across Razorpay, Stripe, and Mock Gateway.
            </p>
          </div>

          <button
            type="button"
            onClick={loadTransactions}
            className="inline-flex items-center gap-2 rounded-xl border border-navy-900/10 bg-cream-50 px-3.5 py-2 text-xs font-semibold text-navy-900 transition hover:bg-cream-100"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh Feed</span>
          </button>
        </div>

        {/* Filters */}
        <form onSubmit={handleSearchSubmit} className="grid grid-cols-1 gap-3 sm:grid-cols-4">
          <div className="relative sm:col-span-2">
            <Search className="pointer-events-none absolute left-3.5 top-3 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search by Txn Ref, Order ID, or Payment ID..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full rounded-xl border border-navy-900/15 bg-cream-50/70 py-2.5 pl-10 pr-3.5 text-xs font-medium text-navy-950 placeholder:text-slate-400 focus:border-emerald-600 focus:bg-white focus:outline-none"
            />
          </div>

          <div>
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="w-full rounded-xl border border-navy-900/15 bg-cream-50/70 px-3 py-2.5 text-xs font-medium text-navy-950 focus:border-emerald-600 focus:bg-white focus:outline-none"
            >
              <option value="">All Statuses</option>
              <option value="SUCCESS">SUCCESS</option>
              <option value="INITIATED">INITIATED</option>
              <option value="FAILED">FAILED</option>
              <option value="REFUNDED">REFUNDED</option>
            </select>
          </div>

          <div>
            <select
              value={gatewayFilter}
              onChange={(e) => {
                setGatewayFilter(e.target.value);
                setPage(1);
              }}
              className="w-full rounded-xl border border-navy-900/15 bg-cream-50/70 px-3 py-2.5 text-xs font-medium text-navy-950 focus:border-emerald-600 focus:bg-white focus:outline-none"
            >
              <option value="">All Gateways</option>
              <option value="MOCK_SANDBOX">Mock Sandbox</option>
              <option value="RAZORPAY_SANDBOX">Razorpay Sandbox</option>
              <option value="STRIPE_SANDBOX">Stripe Sandbox</option>
            </select>
          </div>
        </form>
      </div>

      {/* Transactions Table */}
      <div className="overflow-hidden rounded-2xl border border-navy-900/10 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-navy-900/10 bg-cream-50/90 text-navy-900/70">
              <tr>
                <th className="px-5 py-3.5 font-bold uppercase tracking-wider">Transaction Ref</th>
                <th className="px-4 py-3.5 font-bold uppercase tracking-wider">Gateway</th>
                <th className="px-4 py-3.5 font-bold uppercase tracking-wider">Method</th>
                <th className="px-4 py-3.5 font-bold uppercase tracking-wider">Amount</th>
                <th className="px-4 py-3.5 font-bold uppercase tracking-wider">Status</th>
                <th className="px-4 py-3.5 font-bold uppercase tracking-wider">Gateway Order / Payment ID</th>
                <th className="px-5 py-3.5 font-bold uppercase tracking-wider">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-navy-900/5">
              {loading && transactions.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-5 py-10 text-center text-slate-500">
                    Loading transactions...
                  </td>
                </tr>
              ) : transactions.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-5 py-10 text-center text-slate-500">
                    No transactions found matching your criteria.
                  </td>
                </tr>
              ) : (
                transactions.map((tx) => (
                  <tr key={tx.id} className="transition hover:bg-cream-50/50">
                    <td className="px-5 py-3 font-mono font-bold text-navy-950">
                      {tx.transaction_ref}
                    </td>
                    <td className="px-4 py-3 font-medium text-slate-600">
                      <span className="rounded-md bg-slate-100 px-2 py-1 text-[11px] font-semibold text-slate-700">
                        {tx.gateway}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-semibold text-navy-900">
                      {tx.payment_method || "N/A"}
                    </td>
                    <td className="px-4 py-3 font-mono text-sm font-bold text-emerald-700">
                      ₹{tx.amount.toFixed(2)}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-bold ${
                          tx.status === "SUCCESS"
                            ? "bg-emerald-100 text-emerald-800"
                            : tx.status === "FAILED"
                            ? "bg-rose-100 text-rose-800"
                            : "bg-amber-100 text-amber-800"
                        }`}
                      >
                        {tx.status === "SUCCESS" ? (
                          <CheckCircle2 className="h-3 w-3" />
                        ) : tx.status === "FAILED" ? (
                          <XCircle className="h-3 w-3" />
                        ) : null}
                        {tx.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-[11px] text-slate-500">
                      <div>Order: {tx.gateway_order_id || "—"}</div>
                      {tx.gateway_payment_id && <div>Pay: {tx.gateway_payment_id}</div>}
                    </td>
                    <td className="px-5 py-3 text-slate-500">
                      {tx.created_at ? new Date(tx.created_at).toLocaleString() : "—"}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {pagination && pagination.pages > 1 && (
          <div className="border-t border-navy-900/10 p-4">
            <AdminPagination pagination={pagination} onPageChange={setPage} />
          </div>
        )}
      </div>
    </div>
  );
}
