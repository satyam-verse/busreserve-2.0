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
  getTripSeats: (tripId) => request(`/trips/${tripId}/seats`),
  createBooking: (data) =>
    request("/bookings", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  getBooking: (pnr) => request(`/bookings/${encodeURIComponent(pnr.trim())}`),
  cancelBooking: (pnr) =>
    request(`/bookings/${encodeURIComponent(pnr.trim())}/cancel`, {
      method: "POST",
    }),
  getAdminOverview: () => request("/admin/overview"),
};
