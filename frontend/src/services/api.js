const API_BASE = import.meta.env.VITE_API_BASE_URL || "/api";

export class ApiError extends Error {
  constructor(message, status, code, details = null, requestId = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
    this.requestId = requestId;
  }
}

async function request(path, options = {}) {
  const url = path.startsWith("/health") ? path : `${API_BASE}${path}`;
  const response = await fetch(url, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const err = payload.error || {};
    throw new ApiError(
      err.message || `Request failed with status ${response.status}`,
      response.status,
      err.code || "request_failed",
      err.details || null,
      payload.request_id || response.headers.get("X-Request-ID")
    );
  }
  return payload;
}

export const busApi = {
  getHealthReady: () => request("/health/ready"),
  getCities: (q = "", limit = 15) => {
    const qs = new URLSearchParams();
    if (q && q.trim()) qs.set("q", q.trim());
    if (limit) qs.set("limit", String(limit));
    const query = qs.toString();
    return request(`/cities${query ? `?${query}` : ""}`);
  },
  getRoutes: () => request("/routes"),
  searchTrips: (params = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined && val !== null && val !== "") {
        qs.set(key, String(val));
      }
    });
    const query = qs.toString();
    return request(`/trips${query ? `?${query}` : ""}`);
  },
  getTripSeats: (tripId, params = {}) => {
    const qs = new URLSearchParams();
    if (params.tier) qs.set("tier", params.tier);
    if (params.position) qs.set("position", params.position);
    if (params.max_fare) qs.set("max_fare", String(params.max_fare));
    if (params.available_only) qs.set("available_only", "true");
    const query = qs.toString();
    return request(`/trips/${tripId}/seats${query ? `?${query}` : ""}`);
  },
  getCheapestSeats: (tripId) => request(`/trips/${tripId}/cheapest-seats`),
  createBooking: (data) =>
    request("/bookings", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getBooking: (pnr) => request(`/bookings/${encodeURIComponent(pnr.trim())}`),
  cancelBooking: (pnr, payload = {}) =>
    request(`/bookings/${encodeURIComponent(pnr.trim())}/cancel`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getTicketPdfUrl: (pnr) => `/api/bookings/${encodeURIComponent(pnr.trim())}/pdf`,

  // Phase 7: Payment gateway sandbox & notifications
  createPaymentOrder: (payload) =>
    request("/payments/order", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getPaymentOrder: (transactionRef) =>
    request(`/payments/order/${encodeURIComponent(transactionRef)}`),
  verifyPayment: (payload) =>
    request("/payments/verify", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  cancelPayment: (payload) =>
    request("/payments/cancel", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  failPayment: (payload) =>
    request("/payments/fail", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  retryPayment: (payload) =>
    request("/payments/retry", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  getUserNotifications: () => request("/payments/notifications"),
  markNotificationRead: (id) =>
    request(`/payments/notifications/${id}/read`, {
      method: "POST",
    }),
  getAdminPaymentTransactions: (params = {}) => {
    const qs = new URLSearchParams();
    if (params.page) qs.set("page", params.page);
    if (params.per_page) qs.set("per_page", params.per_page);
    if (params.status) qs.set("status", params.status);
    if (params.gateway) qs.set("gateway", params.gateway);
    if (params.q) qs.set("q", params.q);
    const qStr = qs.toString();
    return request(`/payments/admin/transactions${qStr ? `?${qStr}` : ""}`);
  },

  // Authentication & session endpoints
  register: (data) =>
    request("/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  verifyEmail: (token) =>
    request("/auth/verify-email", {
      method: "POST",
      body: JSON.stringify({ token }),
    }),
  resendVerification: (email) =>
    request("/auth/resend-verification", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  loginUser: (data) =>
    request("/auth/login", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  loginAdmin: (data) =>
    request("/auth/admin/login", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  forgotPassword: (email) =>
    request("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),
  resetPassword: (data) =>
    request("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getMe: () => request("/auth/me"),
  logout: () => request("/auth/logout", { method: "POST" }),
  logoutAll: () => request("/auth/logout-all", { method: "POST" }),

  // Protected User module endpoints
  getUserProfile: () => request("/user/profile"),
  updateUserProfile: (data) =>
    request("/user/profile", {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  changeUserPassword: (data) =>
    request("/user/change-password", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getUserSessions: () => request("/user/sessions"),
  getUserBookings: (status = "") => {
    const qs = status ? `?status=${encodeURIComponent(status)}` : "";
    return request(`/user/bookings${qs}`);
  },
  cancelUserBooking: (pnr) =>
    request(`/user/bookings/${encodeURIComponent(pnr.trim())}/cancel`, {
      method: "POST",
    }),

  // Protected Admin Control Centre endpoints
  getAdminOverview: () => request("/admin/overview"),
  getAdminAnalytics: () => request("/admin/analytics"),

  getAdminUsers: (params = {}) => {
    const qs = new URLSearchParams();
    if (params.q) qs.set("q", params.q.trim());
    if (params.role) qs.set("role", params.role);
    if (params.is_active !== undefined && params.is_active !== "") {
      qs.set("is_active", String(params.is_active));
    }
    if (params.email_verified !== undefined && params.email_verified !== "") {
      qs.set("email_verified", String(params.email_verified));
    }
    if (params.page) qs.set("page", String(params.page));
    if (params.per_page) qs.set("per_page", String(params.per_page));
    const query = qs.toString();
    return request(`/admin/users${query ? `?${query}` : ""}`);
  },
  updateAdminUser: (userId, data) =>
    request(`/admin/users/${userId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  getAdminBookings: (params = {}) => {
    const qs = new URLSearchParams();
    if (params.status) qs.set("status", params.status);
    if (params.refund_status) qs.set("refund_status", params.refund_status);
    if (params.travel_date) qs.set("travel_date", params.travel_date);
    if (params.q) qs.set("q", params.q.trim());
    if (params.page) qs.set("page", String(params.page));
    if (params.per_page) qs.set("per_page", String(params.per_page));
    const query = qs.toString();
    return request(`/admin/bookings${query ? `?${query}` : ""}`);
  },
  getAdminBookingDetail: (pnr) =>
    request(`/admin/bookings/${encodeURIComponent(pnr.trim())}`),
  cancelAdminBooking: (pnr, data = {}) =>
    request(`/admin/bookings/${encodeURIComponent(pnr.trim())}/cancel`, {
      method: "POST",
      body: JSON.stringify(data),
    }),
  refundAdminBooking: (pnr, data = {}) =>
    request(`/admin/bookings/${encodeURIComponent(pnr.trim())}/refund`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  getAdminCities: (params = {}) => {
    const qs = new URLSearchParams();
    if (params.q) qs.set("q", params.q.trim());
    if (params.state) qs.set("state", params.state.trim());
    if (params.is_active !== undefined && params.is_active !== "") {
      qs.set("is_active", String(params.is_active));
    }
    if (params.page) qs.set("page", String(params.page));
    if (params.per_page) qs.set("per_page", String(params.per_page));
    const query = qs.toString();
    return request(`/admin/cities${query ? `?${query}` : ""}`);
  },
  createAdminCity: (data) =>
    request("/admin/cities", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateAdminCity: (cityId, data) =>
    request(`/admin/cities/${cityId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  deleteAdminCity: (cityId) =>
    request(`/admin/cities/${cityId}`, {
      method: "DELETE",
    }),

  getAdminRoutes: (params = {}) => {
    const qs = new URLSearchParams();
    if (params.q) qs.set("q", params.q.trim());
    if (params.source) qs.set("source", params.source.trim());
    if (params.destination) qs.set("destination", params.destination.trim());
    if (params.page) qs.set("page", String(params.page));
    if (params.per_page) qs.set("per_page", String(params.per_page));
    const query = qs.toString();
    return request(`/admin/routes${query ? `?${query}` : ""}`);
  },
  createAdminRoute: (data) =>
    request("/admin/routes", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateAdminRoute: (routeId, data) =>
    request(`/admin/routes/${routeId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  deleteAdminRoute: (routeId) =>
    request(`/admin/routes/${routeId}`, {
      method: "DELETE",
    }),

  getAdminBuses: (params = {}) => {
    const qs = new URLSearchParams();
    if (params.q) qs.set("q", params.q.trim());
    if (params.bus_type) qs.set("bus_type", params.bus_type);
    if (params.seat_layout) qs.set("seat_layout", params.seat_layout);
    if (params.is_active !== undefined && params.is_active !== "") {
      qs.set("is_active", String(params.is_active));
    }
    if (params.page) qs.set("page", String(params.page));
    if (params.per_page) qs.set("per_page", String(params.per_page));
    const query = qs.toString();
    return request(`/admin/buses${query ? `?${query}` : ""}`);
  },
  createAdminBus: (data) =>
    request("/admin/buses", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateAdminBus: (busId, data) =>
    request(`/admin/buses/${busId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  deleteAdminBus: (busId) =>
    request(`/admin/buses/${busId}`, {
      method: "DELETE",
    }),

  getAdminSchedules: (params = {}) => {
    const qs = new URLSearchParams();
    if (params.q) qs.set("q", params.q.trim());
    if (params.route_id) qs.set("route_id", String(params.route_id));
    if (params.bus_id) qs.set("bus_id", String(params.bus_id));
    if (params.is_active !== undefined && params.is_active !== "") {
      qs.set("is_active", String(params.is_active));
    }
    if (params.page) qs.set("page", String(params.page));
    if (params.per_page) qs.set("per_page", String(params.per_page));
    const query = qs.toString();
    return request(`/admin/schedules${query ? `?${query}` : ""}`);
  },
  createAdminSchedule: (data) =>
    request("/admin/schedules", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  updateAdminSchedule: (scheduleId, data) =>
    request(`/admin/schedules/${scheduleId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),
  toggleAdminSchedule: (scheduleId, isActive) =>
    request(`/admin/schedules/${scheduleId}`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: isActive }),
    }),
  deleteAdminSchedule: (scheduleId) =>
    request(`/admin/schedules/${scheduleId}`, {
      method: "DELETE",
    }),
  cancelAdminTrip: (tripId) =>
    request(`/admin/trips/${tripId}/cancel`, {
      method: "POST",
    }),

  // Phase 4: AI Passenger Assistant, Recommendations & Admin Copilot
  aiChat: (data) =>
    request("/ai/chat", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  aiTravelAssistant: (data) =>
    request("/ai/travel-assistant", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  aiRecommendations: (data = {}) =>
    request("/ai/recommendations", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getAiStatus: () => request("/ai/status"),
  getAiHistory: (limit = 20) =>
    request(`/ai/history${limit ? `?limit=${encodeURIComponent(limit)}` : ""}`),
  clearAiHistory: () =>
    request("/ai/history", {
      method: "DELETE",
    }),

  adminAiChat: (data) =>
    request("/admin/ai/chat", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getAdminAiStatus: () => request("/admin/ai/status"),
  getAdminAiHistory: (limit = 20) =>
    request(`/admin/ai/history${limit ? `?limit=${encodeURIComponent(limit)}` : ""}`),
  clearAdminAiHistory: () =>
    request("/admin/ai/history", {
      method: "DELETE",
    }),

  // Phase 3: Live GPS Tracking & Journey Sharing
  getTripTracking: (tripId) => request(`/tracking/trip/${tripId}`),
  createJourneyShare: (data) =>
    request("/tracking/share", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  revokeJourneyShare: (token) =>
    request(`/tracking/share/${encodeURIComponent(token)}`, {
      method: "DELETE",
    }),
  getSharedJourney: (token) =>
    request(`/tracking/shared/${encodeURIComponent(token)}`),
  sendDriverLocation: (data) =>
    request("/tracking/driver/location", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  sendOperatorLocation: (data) =>
    request("/tracking/operator/location", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Phase 3: Driver Dispatch
  getDriverTrips: () => request("/driver/trips"),
  markTripDeparted: (tripId) =>
    request(`/driver/trip/${tripId}/depart`, {
      method: "POST",
    }),
  markTripArrived: (tripId) =>
    request(`/driver/trip/${tripId}/arrive`, {
      method: "POST",
    }),

  // Phase 3: Operator Fleet Management
  getOperatorFleet: () => request("/operator/fleet"),
  getOperatorTrips: () => request("/operator/trips"),
  assignDriverToTrip: (data) =>
    request("/operator/assign-driver", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  // Phase 3: In-App Notifications Feed
  getNotifications: () => request("/payments/notifications"),
  markNotificationRead: (notificationId) =>
    request(`/payments/notifications/${notificationId}/read`, {
      method: "POST",
    }),
};
