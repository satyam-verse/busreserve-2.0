import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  Ticket,
  User,
  KeyRound,
  Shield,
  LogOut,
  XCircle,
  CheckCircle2,
  AlertCircle,
  Calendar,
  MapPin,
  Clock,
  Bus,
  Sparkles,
  Bell,
  Download,
  CreditCard,
  Check,
  Mail,
  Navigation,
  Share2,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { busApi } from "../services/api";
import LiveTrackingModal from "../components/LiveTrackingModal";
import ShareJourneyModal from "../components/ShareJourneyModal";

export default function UserDashboardPage() {
  const { user, setUser, logout, logoutAll } = useAuth();
  const { tab: paramTab } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const validTabs = new Set(["bookings", "profile", "security", "notifications"]);
  const resolveTab = () => {
    if (paramTab && validTabs.has(paramTab)) return paramTab;
    const queryTab = searchParams.get("tab");
    if (queryTab && validTabs.has(queryTab)) return queryTab;
    return "bookings";
  };

  const [activeTab, setActiveTabState] = useState(resolveTab);

  useEffect(() => {
    setActiveTabState(resolveTab());
  }, [paramTab, searchParams]);

  const handleTabChange = (newTab) => {
    setActiveTabState(newTab);
    setBanner({ type: "", text: "" });
    navigate(`/dashboard/${newTab}`);
  };

  const [bookings, setBookings] = useState([]);
  const [bookingFilter, setBookingFilter] = useState("");
  const [bookingsLoading, setBookingsLoading] = useState(true);
  const [cancellingPnr, setCancellingPnr] = useState("");
  const [confirmCancelPnr, setConfirmCancelPnr] = useState("");
  const [trackingBooking, setTrackingBooking] = useState(null);
  const [shareBooking, setShareBooking] = useState(null);

  const [profileForm, setProfileForm] = useState({
    full_name: user?.full_name || "",
    phone: user?.phone || "",
  });
  const [profileSaving, setProfileSaving] = useState(false);

  const [passwordForm, setPasswordForm] = useState({
    current_password: "",
    new_password: "",
    confirm_password: "",
  });
  const [passwordSaving, setPasswordSaving] = useState(false);

  const [sessions, setSessions] = useState([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);

  const [notifications, setNotifications] = useState([]);
  const [notificationsLoading, setNotificationsLoading] = useState(false);
  const [markingReadId, setMarkingReadId] = useState(null);

  const [banner, setBanner] = useState({ type: "", text: "" });

  useEffect(() => {
    setProfileForm({
      full_name: user?.full_name || "",
      phone: user?.phone || "",
    });
  }, [user]);

  const loadNotifications = useCallback(async () => {
    setNotificationsLoading(true);
    try {
      const data = await busApi.getUserNotifications();
      setNotifications(data.notifications || []);
    } catch {
      // Non-blocking notification loading
    } finally {
      setNotificationsLoading(false);
    }
  }, []);

  const loadBookings = useCallback(async (statusFilter = bookingFilter) => {
    setBookingsLoading(true);
    try {
      const data = await busApi.getUserBookings(statusFilter);
      setBookings(data.bookings || []);
    } catch (err) {
      setBanner({ type: "error", text: err.message || "Failed to load your bookings." });
    } finally {
      setBookingsLoading(false);
    }
  }, [bookingFilter]);

  const loadSessions = useCallback(async () => {
    setSessionsLoading(true);
    try {
      const data = await busApi.getUserSessions();
      setSessions(data.sessions || []);
    } catch (err) {
      setBanner({ type: "error", text: err.message || "Failed to load active sessions." });
    } finally {
      setSessionsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadBookings(bookingFilter);
  }, [bookingFilter, loadBookings]);

  useEffect(() => {
    if (activeTab === "security") {
      loadSessions();
    } else if (activeTab === "notifications") {
      loadNotifications();
    }
  }, [activeTab, loadSessions, loadNotifications]);

  async function handleMarkRead(id) {
    setMarkingReadId(id);
    try {
      await busApi.markNotificationRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
    } catch {
      // Ignore
    } finally {
      setMarkingReadId(null);
    }
  }

  async function handleCancelBooking(pnr) {
    setBanner({ type: "", text: "" });
    setCancellingPnr(pnr);
    try {
      const data = await busApi.cancelUserBooking(pnr);
      setBanner({ type: "success", text: data.message || `Booking ${pnr} cancelled.` });
      await loadBookings(bookingFilter);
    } catch (err) {
      setBanner({ type: "error", text: err.message || "Unable to cancel reservation." });
    } finally {
      setCancellingPnr("");
    }
  }

  async function handleProfileSubmit(e) {
    e.preventDefault();
    setBanner({ type: "", text: "" });
    setProfileSaving(true);
    try {
      const data = await busApi.updateUserProfile({
        full_name: profileForm.full_name.trim(),
        phone: profileForm.phone.trim() || null,
      });
      setUser(data.user);
      setBanner({ type: "success", text: data.message || "Profile updated." });
    } catch (err) {
      setBanner({ type: "error", text: err.message || "Could not update profile." });
    } finally {
      setProfileSaving(false);
    }
  }

  async function handlePasswordSubmit(e) {
    e.preventDefault();
    setBanner({ type: "", text: "" });
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setBanner({ type: "error", text: "New passwords do not match." });
      return;
    }
    setPasswordSaving(true);
    try {
      const data = await busApi.changeUserPassword({
        current_password: passwordForm.current_password,
        new_password: passwordForm.new_password,
      });
      setPasswordForm({ current_password: "", new_password: "", confirm_password: "" });
      setBanner({ type: "success", text: data.message || "Password updated." });
      await loadSessions();
    } catch (err) {
      setBanner({ type: "error", text: err.message || "Failed to update password." });
    } finally {
      setPasswordSaving(false);
    }
  }

  return (
    <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mb-6 flex flex-col justify-between gap-4 rounded-2xl border border-navy-900/10 bg-white p-6 shadow-sm sm:flex-row sm:items-center">
        <div>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700">
            <CheckCircle2 className="h-3.5 w-3.5" />
            Verified Passenger Account
          </span>
          <h1 className="mt-2 text-2xl font-bold text-navy-950">Welcome, {user?.full_name}</h1>
          <p className="text-sm text-navy-900/65">
            {user?.email} {user?.phone ? `• ${user.phone}` : ""}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <Link
            to="/assistant"
            className="inline-flex items-center gap-2 rounded-xl border border-emerald-600/30 bg-emerald-50 px-4 py-2.5 text-sm font-semibold text-emerald-800 transition hover:bg-emerald-100"
          >
            <Sparkles className="h-4 w-4" />
            <span>AI Assistant</span>
          </Link>
          <Link
            to="/search"
            className="inline-flex items-center gap-2 rounded-xl bg-navy-950 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-navy-800"
          >
            <Bus className="h-4 w-4" />
            <span>Book a Trip</span>
          </Link>
          <button
            type="button"
            onClick={logout}
            className="inline-flex items-center gap-2 rounded-xl border border-navy-900/15 bg-cream-50 px-4 py-2.5 text-sm font-semibold text-navy-950 transition hover:bg-cream-100"
          >
            <LogOut className="h-4 w-4" />
            <span>Sign Out</span>
          </button>
        </div>
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
        aria-label="Passenger dashboard sections"
        className="mb-6 flex gap-2 overflow-x-auto border-b border-navy-900/10 pb-3"
      >
        {[
          { id: "bookings", label: "My Bookings", icon: Ticket },
          {
            id: "notifications",
            label: "Notifications & Alerts",
            icon: Bell,
            badge: notifications.filter((n) => !n.is_read).length,
          },
          { id: "profile", label: "Profile Details", icon: User },
          { id: "security", label: "Password & Sessions", icon: Shield },
        ].map((tab) => {
          const Icon = tab.icon;
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => handleTabChange(tab.id)}
              className={`inline-flex shrink-0 items-center gap-2 whitespace-nowrap rounded-xl px-4 py-2 text-sm font-semibold transition ${
                active
                  ? "bg-navy-950 text-white shadow-sm"
                  : "bg-white text-navy-900/75 hover:bg-navy-900/5"
              }`}
            >
              <Icon className="h-4 w-4" />
              <span>{tab.label}</span>
              {tab.badge > 0 ? (
                <span className="rounded-full bg-emerald-500 px-1.5 py-0.2 text-[10px] font-bold text-white">
                  {tab.badge}
                </span>
              ) : null}
            </button>
          );
        })}
      </div>

      {activeTab === "bookings" ? (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-lg font-bold text-navy-950">Reservation History</h2>
            <div className="flex gap-2">
              {[
                { label: "All", val: "" },
                { label: "Confirmed", val: "CONFIRMED" },
                { label: "Cancelled", val: "CANCELLED" },
              ].map((item) => (
                <button
                  key={item.label}
                  type="button"
                  onClick={() => setBookingFilter(item.val)}
                  className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                    bookingFilter === item.val
                      ? "bg-navy-950 text-white"
                      : "border border-navy-900/15 bg-white text-navy-900/75 hover:bg-cream-100"
                  }`}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>

          {bookingsLoading ? (
            <div className="space-y-4" aria-busy="true">
              <div className="h-32 animate-pulse rounded-2xl border border-navy-900/10 bg-white" />
              <div className="h-32 animate-pulse rounded-2xl border border-navy-900/10 bg-white" />
            </div>
          ) : bookings.length === 0 ? (
            <div className="rounded-2xl border border-navy-900/10 bg-white p-10 text-center">
              <Ticket className="mx-auto mb-3 h-10 w-10 text-navy-900/30" />
              <h3 className="text-base font-bold text-navy-950">No reservations found</h3>
              <p className="mt-1 text-sm text-navy-900/65">
                Trips booked while signed in appear automatically in your account history.
              </p>
              <Link
                to="/search"
                className="mt-4 inline-flex items-center gap-2 rounded-xl bg-navy-950 px-4 py-2 text-sm font-semibold text-white hover:bg-navy-800"
              >
                Explore Buses
              </Link>
            </div>
          ) : (
            <div className="grid gap-4">
              {bookings.map((b) => {
                const isConfirmed = b.status === "CONFIRMED";
                return (
                  <div
                    key={b.pnr}
                    className="rounded-2xl border border-navy-900/10 bg-white p-5 shadow-sm"
                  >
                    <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
                      <div className="space-y-2">
                        <div className="flex flex-wrap items-center gap-2.5">
                          <span className="rounded-lg bg-navy-950 px-2.5 py-1 font-mono text-xs font-bold text-white">
                            PNR: {b.pnr}
                          </span>
                          <span
                            className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                              isConfirmed
                                ? "bg-emerald-50 text-emerald-700"
                                : "bg-red-50 text-red-700"
                            }`}
                          >
                            {b.status}
                          </span>
                          <span className="rounded-full bg-cream-100 px-2.5 py-0.5 text-xs font-semibold text-navy-900">
                            Seat {b.seat_number} ({b.seat_type})
                          </span>
                        </div>

                        <h3 className="text-base font-bold text-navy-950">
                          {b.trip?.route?.name || `${b.boarding_stop?.stop_name} → ${b.drop_stop?.stop_name}`}
                        </h3>

                        <div className="flex flex-wrap gap-x-5 gap-y-1 text-xs text-navy-900/70">
                          <span className="inline-flex items-center gap-1">
                            <Calendar className="h-3.5 w-3.5" />
                            {b.trip?.travel_date || "Scheduled"}
                          </span>
                          <span className="inline-flex items-center gap-1">
                            <Clock className="h-3.5 w-3.5" />
                            {b.trip?.departure_time} → {b.trip?.arrival_time}
                          </span>
                          <span className="inline-flex items-center gap-1">
                            <MapPin className="h-3.5 w-3.5" />
                            {b.boarding_stop?.stop_name} → {b.drop_stop?.stop_name}
                          </span>
                        </div>
                      </div>

                      <div className="flex flex-col items-start gap-2 sm:items-end">
                        <div className="text-lg font-bold text-navy-950">
                          ₹{Number(b.total_fare).toFixed(0)}
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <Link
                            to={`/bookings/${b.pnr}`}
                            className="rounded-lg border border-navy-900/15 px-3 py-1.5 text-xs font-semibold text-navy-950 hover:bg-cream-50"
                          >
                            View Ticket
                          </Link>
                          {isConfirmed ? (
                            <>
                              <button
                                type="button"
                                onClick={() => setTrackingBooking(b)}
                                className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-600/30 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-800 hover:bg-emerald-100"
                              >
                                <Navigation className="h-3.5 w-3.5" />
                                <span>Track Bus</span>
                              </button>
                              <button
                                type="button"
                                onClick={() => setShareBooking(b)}
                                className="inline-flex items-center gap-1.5 rounded-lg border border-navy-900/15 bg-white px-3 py-1.5 text-xs font-semibold text-navy-950 hover:bg-cream-50"
                              >
                                <Share2 className="h-3.5 w-3.5" />
                                <span>Share</span>
                              </button>
                              <a
                                href={busApi.getTicketPdfUrl(b.pnr)}
                                download={`BoardingPass-${b.pnr}.pdf`}
                                className="inline-flex items-center gap-1 rounded-lg border border-emerald-600/30 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-800 hover:bg-emerald-100"
                              >
                                <Download className="h-3.5 w-3.5" />
                                <span>PDF Pass</span>
                              </a>
                            </>
                          ) : null}
                          {isConfirmed ? (
                            confirmCancelPnr === b.pnr ? (
                              <div className="inline-flex flex-wrap items-center gap-1.5 rounded-lg border border-red-200 bg-red-50 px-2 py-1">
                                <span className="text-[11px] font-semibold text-red-800">
                                  Cancel PNR?
                                </span>
                                <button
                                  type="button"
                                  onClick={async () => {
                                    setConfirmCancelPnr("");
                                    await handleCancelBooking(b.pnr);
                                  }}
                                  disabled={cancellingPnr === b.pnr}
                                  className="rounded-md bg-red-700 px-2.5 py-1 text-[11px] font-bold text-white hover:bg-red-800 disabled:opacity-50"
                                >
                                  {cancellingPnr === b.pnr ? "Cancelling..." : "Confirm Cancel"}
                                </button>
                                <button
                                  type="button"
                                  onClick={() => setConfirmCancelPnr("")}
                                  className="rounded-md border border-navy-900/15 bg-white px-2 py-1 text-[11px] font-semibold text-navy-900 hover:bg-cream-50"
                                >
                                  Keep
                                </button>
                              </div>
                            ) : (
                              <button
                                type="button"
                                onClick={() => setConfirmCancelPnr(b.pnr)}
                                disabled={cancellingPnr === b.pnr}
                                className="inline-flex items-center gap-1 rounded-lg border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-semibold text-red-700 hover:bg-red-100 disabled:opacity-50"
                              >
                                <XCircle className="h-3.5 w-3.5" />
                                <span>
                                  {cancellingPnr === b.pnr ? "Cancelling..." : "Cancel Booking"}
                                </span>
                              </button>
                            )
                          ) : null}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      ) : null}

      {activeTab === "notifications" ? (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-bold text-navy-950">Notifications &amp; Alerts</h2>
              <p className="text-xs text-navy-900/65">
                Real-time booking confirmations, payment receipts, and travel alerts.
              </p>
            </div>
            <button
              type="button"
              onClick={loadNotifications}
              disabled={notificationsLoading}
              className="rounded-lg border border-navy-900/15 bg-white px-3 py-1.5 text-xs font-semibold text-navy-900 hover:bg-cream-100 disabled:opacity-50"
            >
              {notificationsLoading ? "Refreshing..." : "Refresh Alerts"}
            </button>
          </div>

          {notificationsLoading && notifications.length === 0 ? (
            <div className="rounded-2xl border border-navy-900/10 bg-white p-8 text-center text-sm text-slate-500">
              Loading your alerts...
            </div>
          ) : notifications.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-navy-900/15 bg-white p-10 text-center">
              <Bell className="mx-auto h-8 w-8 text-navy-900/35" />
              <p className="mt-2 text-sm font-bold text-navy-950">No notifications yet</p>
              <p className="text-xs text-navy-900/65">
                Your booking confirmations, payment receipts, and schedule updates will appear here.
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {notifications.map((n) => {
                const isBooking = n.event_type.includes("BOOKING");
                const isPayment = n.event_type.includes("PAYMENT") || n.event_type.includes("REFUND");
                const Icon = isPayment ? CreditCard : isBooking ? Ticket : Mail;
                return (
                  <div
                    key={n.id}
                    className={`rounded-2xl border p-4 transition ${
                      n.is_read
                        ? "border-navy-900/10 bg-white"
                        : "border-emerald-300/80 bg-emerald-50/40 shadow-sm"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex items-start gap-3">
                        <div
                          className={`mt-0.5 rounded-xl p-2 ${
                            n.is_read
                              ? "bg-cream-100 text-slate-600"
                              : "bg-emerald-600 text-white"
                          }`}
                        >
                          <Icon className="h-4 w-4" />
                        </div>
                        <div>
                          <div className="flex flex-wrap items-center gap-2">
                            <h3 className="text-sm font-bold text-navy-950">{n.title}</h3>
                            {!n.is_read && (
                              <span className="rounded-full bg-emerald-500 px-2 py-0.2 text-[10px] font-bold text-white">
                                New
                              </span>
                            )}
                            <span className="rounded-full bg-cream-100 px-2 py-0.2 text-[10px] font-mono font-medium text-slate-600">
                              {n.event_type}
                            </span>
                            {n.status && (
                              <span
                                className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${
                                  n.status === "SENT"
                                    ? "bg-emerald-100 text-emerald-800"
                                    : n.status === "MOCK"
                                    ? "bg-amber-100 text-amber-800"
                                    : n.status === "FAILED"
                                    ? "bg-red-100 text-red-800"
                                    : "bg-slate-100 text-slate-700"
                                }`}
                              >
                                {n.status}
                              </span>
                            )}
                          </div>
                          <p className="mt-1 text-xs text-navy-900/75">{n.content}</p>
                          <p className="mt-2 text-[11px] text-slate-400">
                            {new Date(n.created_at).toLocaleString("en-IN", {
                              dateStyle: "medium",
                              timeStyle: "short",
                            })}{" "}
                            • Channel: {n.channel}
                          </p>
                        </div>
                      </div>

                      {!n.is_read ? (
                        <button
                          type="button"
                          onClick={() => handleMarkRead(n.id)}
                          disabled={markingReadId === n.id}
                          className="shrink-0 rounded-lg border border-navy-900/15 bg-white px-2.5 py-1 text-[11px] font-semibold text-navy-900 transition hover:bg-cream-100 disabled:opacity-50"
                        >
                          {markingReadId === n.id ? "Marking..." : "Mark Read"}
                        </button>
                      ) : (
                        <span className="inline-flex shrink-0 items-center gap-1 text-[11px] text-slate-400">
                          <Check className="h-3 w-3 text-emerald-600" /> Read
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      ) : null}

      {activeTab === "profile" ? (
        <div className="max-w-xl rounded-3xl border border-navy-900/10 bg-white p-6 shadow-card sm:p-8">
          <h2 className="font-serif text-2xl font-normal tracking-tight text-navy-950">
            Account Information
          </h2>
          <p className="mt-1 text-xs text-navy-900/65">
            These details are used to prefill passenger information during seat checkout.
          </p>

          <form onSubmit={handleProfileSubmit} className="mt-6 space-y-4">
            <div>
              <label
                htmlFor="prof-email"
                className="block text-xs font-bold uppercase tracking-wider text-navy-900/65"
              >
                Email Address (Verified)
              </label>
              <input
                id="prof-email"
                type="email"
                disabled
                value={user?.email || ""}
                className="mt-1.5 w-full rounded-xl border border-navy-900/10 bg-cream-100/80 px-3.5 py-2.5 text-sm text-navy-900/65"
              />
            </div>

            <div>
              <label
                htmlFor="prof-name"
                className="block text-xs font-bold uppercase tracking-wider text-navy-900/65"
              >
                Full Name
              </label>
              <input
                id="prof-name"
                type="text"
                required
                value={profileForm.full_name}
                onChange={(e) =>
                  setProfileForm((prev) => ({ ...prev, full_name: e.target.value }))
                }
                className="mt-1.5 w-full rounded-xl border border-navy-900/15 bg-cream-50/70 px-3.5 py-2.5 text-sm text-navy-950 outline-none transition focus:border-emerald-600 focus:bg-white focus:ring-2 focus:ring-emerald-600/20"
              />
            </div>

            <div>
              <label
                htmlFor="prof-phone"
                className="block text-xs font-bold uppercase tracking-wider text-navy-900/65"
              >
                Mobile Number
              </label>
              <input
                id="prof-phone"
                type="tel"
                value={profileForm.phone}
                onChange={(e) => setProfileForm((prev) => ({ ...prev, phone: e.target.value }))}
                placeholder="9876543210"
                className="mt-1.5 w-full rounded-xl border border-navy-900/15 bg-cream-50/70 px-3.5 py-2.5 text-sm text-navy-950 outline-none transition focus:border-emerald-600 focus:bg-white focus:ring-2 focus:ring-emerald-600/20"
              />
            </div>

            <button
              type="submit"
              disabled={profileSaving}
              className="rounded-xl bg-navy-950 px-5 py-2.5 text-sm font-bold text-white shadow-editorial transition hover:bg-emerald-700 disabled:opacity-60"
            >
              {profileSaving ? "Saving..." : "Save Changes"}
            </button>
          </form>
        </div>
      ) : null}

      {activeTab === "security" ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-3xl border border-navy-900/10 bg-white p-6 shadow-card">
            <div className="mb-4 flex items-center gap-2">
              <div className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-cream-100 text-navy-950">
                <KeyRound className="h-4 w-4 text-emerald-700" />
              </div>
              <h2 className="font-serif text-2xl font-normal tracking-tight text-navy-950">
                Change Password
              </h2>
            </div>

            <form onSubmit={handlePasswordSubmit} className="space-y-4">
              <div>
                <label
                  htmlFor="sec-curr-pw"
                  className="block text-xs font-bold uppercase tracking-wider text-navy-900/65"
                >
                  Current Password
                </label>
                <input
                  id="sec-curr-pw"
                  type="password"
                  required
                  value={passwordForm.current_password}
                  onChange={(e) =>
                    setPasswordForm((prev) => ({ ...prev, current_password: e.target.value }))
                  }
                  className="mt-1.5 w-full rounded-xl border border-navy-900/15 bg-cream-50/70 px-3.5 py-2.5 text-sm outline-none transition focus:border-emerald-600 focus:bg-white focus:ring-2 focus:ring-emerald-600/20"
                />
              </div>
              <div>
                <label
                  htmlFor="sec-new-pw"
                  className="block text-xs font-bold uppercase tracking-wider text-navy-900/65"
                >
                  New Password
                </label>
                <input
                  id="sec-new-pw"
                  type="password"
                  required
                  value={passwordForm.new_password}
                  onChange={(e) =>
                    setPasswordForm((prev) => ({ ...prev, new_password: e.target.value }))
                  }
                  className="mt-1.5 w-full rounded-xl border border-navy-900/15 bg-cream-50/70 px-3.5 py-2.5 text-sm outline-none transition focus:border-emerald-600 focus:bg-white focus:ring-2 focus:ring-emerald-600/20"
                />
              </div>
              <div>
                <label
                  htmlFor="sec-confirm-pw"
                  className="block text-xs font-bold uppercase tracking-wider text-navy-900/65"
                >
                  Confirm New Password
                </label>
                <input
                  id="sec-confirm-pw"
                  type="password"
                  required
                  value={passwordForm.confirm_password}
                  onChange={(e) =>
                    setPasswordForm((prev) => ({ ...prev, confirm_password: e.target.value }))
                  }
                  className="mt-1.5 w-full rounded-xl border border-navy-900/15 bg-cream-50/70 px-3.5 py-2.5 text-sm outline-none transition focus:border-emerald-600 focus:bg-white focus:ring-2 focus:ring-emerald-600/20"
                />
              </div>
              <button
                type="submit"
                disabled={passwordSaving}
                className="rounded-xl bg-navy-950 px-5 py-2.5 text-sm font-bold text-white shadow-editorial transition hover:bg-emerald-700 disabled:opacity-60"
              >
                {passwordSaving ? "Updating..." : "Update Password"}
              </button>
            </form>
          </div>

          <div className="rounded-3xl border border-navy-900/10 bg-white p-6 shadow-card">
            <div className="mb-4 flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <div className="inline-flex h-9 w-9 items-center justify-center rounded-xl bg-cream-100 text-navy-950">
                  <Shield className="h-4 w-4 text-emerald-700" />
                </div>
                <h2 className="font-serif text-2xl font-normal tracking-tight text-navy-950">
                  Active Sessions
                </h2>
              </div>
              <button
                type="button"
                onClick={logoutAll}
                className="rounded-xl border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-semibold text-red-700 transition hover:bg-red-100"
              >
                Sign out all devices
              </button>
            </div>

            {sessionsLoading ? (
              <p className="text-sm text-navy-900/65">Loading session history...</p>
            ) : (
              <div className="space-y-3">
                {sessions.map((s) => (
                  <div
                    key={s.id}
                    className="rounded-xl border border-navy-900/10 bg-cream-50/80 p-3.5 text-xs"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono font-semibold text-navy-950">
                        {s.ip_address || "Local Client"}
                        {s.is_current ? (
                          <span className="ml-2 rounded-full bg-emerald-100 px-2 py-0.5 font-sans text-[10px] font-bold text-emerald-800">
                            CURRENT
                          </span>
                        ) : null}
                      </span>
                      <span
                        className={`font-semibold ${
                          s.is_active ? "text-emerald-700" : "text-navy-900/45"
                        }`}
                      >
                        {s.is_active ? "ACTIVE" : "REVOKED / EXPIRED"}
                      </span>
                    </div>
                    <p className="mt-1 truncate text-navy-900/60">
                      {s.user_agent || "Browser session"}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      ) : null}

      {trackingBooking ? (
        <LiveTrackingModal
          isOpen={Boolean(trackingBooking)}
          tripId={trackingBooking.trip_id}
          pnr={trackingBooking.pnr}
          tripInfo={{
            origin:
              trackingBooking.boarding_stop?.stop_name ||
              trackingBooking.trip?.route?.origin_city?.name,
            destination:
              trackingBooking.drop_stop?.stop_name ||
              trackingBooking.trip?.route?.destination_city?.name,
            departure_time: trackingBooking.trip?.departure_time,
            arrival_time: trackingBooking.trip?.arrival_time,
            travel_date: trackingBooking.trip?.travel_date,
          }}
          onClose={() => setTrackingBooking(null)}
        />
      ) : null}

      {shareBooking ? (
        <ShareJourneyModal
          isOpen={Boolean(shareBooking)}
          booking={shareBooking}
          onClose={() => setShareBooking(null)}
        />
      ) : null}
    </div>
  );
}
