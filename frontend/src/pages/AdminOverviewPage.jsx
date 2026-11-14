import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  LayoutDashboard,
  MapPin,
  Route as RouteIcon,
  Bus,
  CalendarClock,
  Ticket,
  CreditCard,
  Users,
  LogOut,
  AlertCircle,
  CheckCircle2,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { busApi } from "../services/api";
import AdminAnalyticsPanel from "../components/admin/AdminAnalyticsPanel";
import AdminCitiesTab from "../components/admin/AdminCitiesTab";
import AdminRoutesTab from "../components/admin/AdminRoutesTab";
import AdminBusesTab from "../components/admin/AdminBusesTab";
import AdminSchedulesTab from "../components/admin/AdminSchedulesTab";
import AdminBookingsTab from "../components/admin/AdminBookingsTab";
import AdminPaymentTab from "../components/admin/AdminPaymentTab";
import AdminUsersTab from "../components/admin/AdminUsersTab";
import AdminAiTab from "../components/admin/AdminAiTab";

const ADMIN_TABS = [
  { id: "analytics", label: "Analytics & Overview", icon: LayoutDashboard },
  { id: "cities", label: "Cities", icon: MapPin },
  { id: "routes", label: "Routes", icon: RouteIcon },
  { id: "buses", label: "Buses", icon: Bus },
  { id: "schedules", label: "Schedules", icon: CalendarClock },
  { id: "bookings", label: "Bookings & Refunds", icon: Ticket },
  { id: "payments", label: "Payments & Financials", icon: CreditCard },
  { id: "users", label: "Users & Roles", icon: Users },
  { id: "ai_copilot", label: "AI Copilot", icon: Sparkles },
];

export default function AdminOverviewPage() {
  const { user, logout } = useAuth();
  const { tab: paramTab } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const validTabIds = new Set(ADMIN_TABS.map((t) => t.id));
  const resolveTab = () => {
    if (paramTab && validTabIds.has(paramTab)) return paramTab;
    const queryTab = searchParams.get("tab");
    if (queryTab && validTabIds.has(queryTab)) return queryTab;
    return "analytics";
  };

  const [activeTab, setActiveTabState] = useState(resolveTab);
  const [banner, setBanner] = useState({ type: "", text: "" });
  const [overview, setOverview] = useState(null);
  const [overviewLoading, setOverviewLoading] = useState(true);

  useEffect(() => {
    const target = resolveTab();
    setActiveTabState(target);
  }, [paramTab, searchParams]);

  const handleTabChange = (newTab) => {
    setActiveTabState(newTab);
    setBanner({ type: "", text: "" });
    navigate(`/admin/${newTab}`);
  };

  const notify = useCallback((type, text) => {
    setBanner({ type, text });
  }, []);

  const loadOverview = useCallback(async () => {
    setOverviewLoading(true);
    try {
      const data = await busApi.getAdminAnalytics();
      setOverview(data);
    } catch (err) {
      setBanner({ type: "error", text: err.message || "Failed to load analytics." });
    } finally {
      setOverviewLoading(false);
    }
  }, []);

  useEffect(() => {
    loadOverview();
  }, [loadOverview]);

  async function handleCancelTrip(tripId) {
    setBanner({ type: "", text: "" });
    try {
      const data = await busApi.cancelAdminTrip(tripId);
      setBanner({ type: "success", text: data.message || `Trip #${tripId} cancelled.` });
      await loadOverview();
    } catch (err) {
      setBanner({ type: "error", text: err.message || "Could not cancel trip." });
    }
  }

  return (
    <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6 flex flex-col justify-between gap-4 rounded-2xl border border-navy-900/10 bg-navy-950 p-6 text-white shadow-sm sm:flex-row sm:items-center">
        <div>
          <div className="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/20 px-3 py-1 text-xs font-semibold text-emerald-300">
            <ShieldCheck className="h-3.5 w-3.5" />
            <span>BusReserve Admin Control Centre • RBAC Enforced</span>
          </div>
          <h1 className="mt-2 text-2xl font-bold">Fleet, Network &amp; Operations Console</h1>
          <p className="text-sm text-cream-200/80">
            Signed in as {user?.full_name} ({user?.email})
          </p>
        </div>

        <button
          type="button"
          onClick={logout}
          className="inline-flex items-center gap-2 self-start rounded-xl border border-white/20 bg-white/10 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-white/20 sm:self-auto"
        >
          <LogOut className="h-4 w-4" />
          <span>Admin Logout</span>
        </button>
      </div>

      {banner.text ? (
        <div
          className={`mb-6 flex items-start gap-2.5 rounded-xl border px-4 py-3 text-sm ${
            banner.type === "error"
              ? "border-red-200 bg-red-50 text-red-800"
              : "border-emerald-200 bg-emerald-50 text-emerald-900"
          }`}
        >
          {banner.type === "error" ? (
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          ) : (
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
          )}
          <span>{banner.text}</span>
        </div>
      ) : null}

      <div
        role="tablist"
        aria-label="Admin console sections"
        className="mb-6 flex gap-2 overflow-x-auto border-b border-navy-900/10 pb-3"
      >
        {ADMIN_TABS.map((tab) => {
          const Icon = tab.icon;
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => handleTabChange(tab.id)}
              className={`inline-flex shrink-0 items-center gap-2 whitespace-nowrap rounded-xl px-3.5 py-2 text-xs font-semibold transition sm:text-sm ${
                active
                  ? "bg-navy-950 text-white shadow-sm"
                  : "bg-white text-navy-900/75 hover:bg-navy-900/5"
              }`}
            >
              <Icon className="h-4 w-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {activeTab === "analytics" ? (
        <AdminAnalyticsPanel
          overview={overview}
          loading={overviewLoading}
          onCancelTrip={handleCancelTrip}
        />
      ) : null}

      {activeTab === "cities" ? (
        <AdminCitiesTab onNotify={notify} onChanged={loadOverview} />
      ) : null}

      {activeTab === "routes" ? (
        <AdminRoutesTab onNotify={notify} onChanged={loadOverview} />
      ) : null}

      {activeTab === "buses" ? (
        <AdminBusesTab onNotify={notify} onChanged={loadOverview} />
      ) : null}

      {activeTab === "schedules" ? (
        <AdminSchedulesTab
          horizonDays={overview?.summary?.booking_horizon_days || 90}
          onNotify={notify}
          onChanged={loadOverview}
        />
      ) : null}

      {activeTab === "bookings" ? (
        <AdminBookingsTab onNotify={notify} onChanged={loadOverview} />
      ) : null}

      {activeTab === "payments" ? (
        <AdminPaymentTab onNotify={notify} />
      ) : null}

      {activeTab === "users" ? (
        <AdminUsersTab onNotify={notify} onChanged={loadOverview} />
      ) : null}

      {activeTab === "ai_copilot" ? <AdminAiTab onNotify={notify} /> : null}
    </div>
  );
}
