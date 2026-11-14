import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  ArrowRight,
  Bell,
  Check,
  CheckCheck,
  Clock,
  CreditCard,
  Mail,
  MapPin,
  Navigation,
  RefreshCw,
  Ticket,
  X,
  XCircle,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";
import { busApi } from "../services/api";

function getNotificationIcon(eventType) {
  const type = (eventType || "").toUpperCase();
  if (type.includes("DEPART") || type.includes("LIVE") || type.includes("TRACK")) {
    return <Navigation className="h-4 w-4 text-emerald-400" />;
  }
  if (type.includes("ARRIV")) {
    return <MapPin className="h-4 w-4 text-teal-400" />;
  }
  if (type.includes("PAYMENT") || type.includes("REFUND")) {
    return <CreditCard className="h-4 w-4 text-amber-400" />;
  }
  if (type.includes("CANCEL") || type.includes("FAIL")) {
    return <XCircle className="h-4 w-4 text-rose-400" />;
  }
  if (type.includes("DELAY")) {
    return <AlertTriangle className="h-4 w-4 text-orange-400" />;
  }
  return <Ticket className="h-4 w-4 text-emerald-400" />;
}

function getStatusBadge(status) {
  switch (status) {
    case "SENT":
      return {
        label: "Delivered",
        classes: "bg-emerald-100 text-emerald-800 border-emerald-300",
      };
    case "MOCK":
      return {
        label: "Mock Sandbox",
        classes: "bg-amber-100 text-amber-800 border-amber-300",
      };
    case "FAILED":
      return {
        label: "Delivery Failed",
        classes: "bg-rose-100 text-rose-800 border-rose-300",
      };
    default:
      return {
        label: "In-App (No Provider)",
        classes: "bg-slate-100 text-slate-700 border-slate-300",
      };
  }
}

export default function NotificationBell() {
  const { user } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(false);
  const [markingId, setMarkingId] = useState(null);

  const dropdownRef = useRef(null);

  const loadNotifications = async () => {
    if (!user) return;
    try {
      setLoading(true);
      const res = await busApi.getNotifications();
      setNotifications(res.notifications || []);
    } catch {
      // Non-blocking notification fetch
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (user) {
      loadNotifications();
      const timer = setInterval(loadNotifications, 30000); // 30s background poll
      return () => clearInterval(timer);
    } else {
      setNotifications([]);
    }
  }, [user]);

  // Click outside listener
  useEffect(() => {
    function handleClickOutside(e) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  if (!user) return null;

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  const handleMarkRead = async (id, e) => {
    e.stopPropagation();
    try {
      setMarkingId(id);
      await busApi.markNotificationRead(id);
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, is_read: true } : n))
      );
    } catch {
      // ignore
    } finally {
      setMarkingId(null);
    }
  };

  const handleMarkAllRead = async () => {
    const unread = notifications.filter((n) => !n.is_read);
    for (const n of unread) {
      try {
        await busApi.markNotificationRead(n.id);
      } catch {
        // ignore
      }
    }
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell Trigger Button */}
      <button
        type="button"
        aria-label={`Notifications, ${unreadCount} unread`}
        aria-expanded={isOpen}
        onClick={() => setIsOpen((prev) => !prev)}
        className="relative inline-flex h-9 w-9 items-center justify-center rounded-xl border border-white/15 bg-white/5 text-white transition hover:bg-white/15 focus:outline-none focus:ring-2 focus:ring-emerald-400"
      >
        <Bell className="h-4 w-4" />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 flex h-4.5 min-w-4.5 items-center justify-center rounded-full bg-emerald-500 px-1 font-mono text-[10px] font-bold text-navy-950 shadow-sm animate-pulse">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown Panel */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 rounded-2xl border border-slate-200 bg-white shadow-2xl z-50 overflow-hidden text-slate-900 animate-fade-in">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-slate-100 bg-navy-950 px-4 py-3 text-white">
            <div className="flex items-center gap-2">
              <Bell className="h-4 w-4 text-emerald-400" />
              <h3 className="font-display text-sm font-bold text-white">
                Notifications
              </h3>
              {unreadCount > 0 && (
                <span className="rounded-full bg-emerald-500/20 px-2 py-0.5 text-[10px] font-bold text-emerald-300">
                  {unreadCount} new
                </span>
              )}
            </div>

            <div className="flex items-center gap-2">
              {unreadCount > 0 && (
                <button
                  type="button"
                  onClick={handleMarkAllRead}
                  className="text-[11px] font-semibold text-emerald-300 hover:text-emerald-200 hover:underline"
                >
                  Mark all read
                </button>
              )}
              <button
                type="button"
                onClick={loadNotifications}
                disabled={loading}
                className="rounded-lg p-1 text-slate-300 hover:bg-white/10 hover:text-white"
                title="Refresh notifications"
              >
                <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
              </button>
            </div>
          </div>

          {/* Feed List */}
          <div className="max-h-96 overflow-y-auto divide-y divide-slate-100">
            {notifications.length === 0 ? (
              <div className="p-8 text-center text-slate-500">
                <Bell className="mx-auto h-8 w-8 text-slate-300 mb-2" />
                <p className="text-xs font-bold text-slate-700">No notifications yet</p>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  Real-time booking, departure, and travel updates will appear here.
                </p>
              </div>
            ) : (
              notifications.slice(0, 10).map((n) => {
                const badge = getStatusBadge(n.status);
                return (
                  <div
                    key={n.id}
                    className={`p-3.5 transition flex items-start gap-3 ${
                      n.is_read ? "bg-white opacity-85" : "bg-emerald-50/40"
                    }`}
                  >
                    <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-xl bg-navy-950 text-white">
                      {getNotificationIcon(n.event_type)}
                    </div>

                    <div className="flex-1 min-w-0 space-y-1">
                      <div className="flex items-center justify-between gap-1">
                        <h4 className="font-bold text-xs text-navy-950 truncate">
                          {n.title || n.event_type}
                        </h4>
                        {!n.is_read && (
                          <span className="h-2 w-2 rounded-full bg-emerald-500 shrink-0" />
                        )}
                      </div>

                      <p className="text-xs text-slate-600 line-clamp-2">
                        {n.content}
                      </p>

                      <div className="flex flex-wrap items-center justify-between gap-2 pt-1 text-[10px]">
                        <div className="flex items-center gap-1.5 text-slate-400">
                          <Clock className="h-3 w-3" />
                          <span>
                            {new Date(n.created_at).toLocaleTimeString([], {
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </span>
                          <span>•</span>
                          <span
                            className={`rounded px-1.5 py-0.2 font-bold border ${badge.classes}`}
                          >
                            {badge.label}
                          </span>
                        </div>

                        {!n.is_read && (
                          <button
                            type="button"
                            onClick={(e) => handleMarkRead(n.id, e)}
                            disabled={markingId === n.id}
                            className="font-semibold text-emerald-700 hover:text-emerald-800 hover:underline"
                          >
                            {markingId === n.id ? "..." : "Mark read"}
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Footer */}
          <div className="border-t border-slate-100 bg-slate-50 px-4 py-2.5 text-center">
            <Link
              to="/dashboard/notifications"
              onClick={() => setIsOpen(false)}
              className="inline-flex items-center gap-1 text-xs font-bold text-navy-950 hover:text-emerald-700"
            >
              <span>View all in Notification Centre</span>
              <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
