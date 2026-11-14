import { useEffect } from "react";
import { BrowserRouter, Route, Routes, useLocation } from "react-router-dom";
import Footer from "./components/Footer";
import Navbar from "./components/Navbar";
import ProtectedRoute from "./components/ProtectedRoute";
import { AuthProvider } from "./context/AuthContext";
import AdminLoginPage from "./pages/AdminLoginPage";
import AdminOverviewPage from "./pages/AdminOverviewPage";
import AssistantPage from "./pages/AssistantPage";
import BookingConfirmationPage from "./pages/BookingConfirmationPage";
import ForgotPasswordPage from "./pages/ForgotPasswordPage";
import HomePage from "./pages/HomePage";
import NotFoundPage from "./pages/NotFoundPage";
import PaymentPage from "./pages/PaymentPage";
import ResetPasswordPage from "./pages/ResetPasswordPage";
import SearchResultsPage from "./pages/SearchResultsPage";
import SeatSelectionPage from "./pages/SeatSelectionPage";
import UserDashboardPage from "./pages/UserDashboardPage";
import UserLoginPage from "./pages/UserLoginPage";
import UserRegisterPage from "./pages/UserRegisterPage";
import VerifyEmailPage from "./pages/VerifyEmailPage";
import PublicJourneyTrackPage from "./pages/PublicJourneyTrackPage";
import DriverConsolePage from "./pages/DriverConsolePage";
import OperatorFleetDashboard from "./pages/OperatorFleetDashboard";

function PageTitleManager() {
  const location = useLocation();

  useEffect(() => {
    const path = location.pathname;
    let title = "BusReserve 2.0 | Smart Bus Booking";

    if (path === "/") {
      title = "BusReserve 2.0 | Smart Bus Booking";
    } else if (path === "/search" || path === "/trips") {
      title = "Search Buses | BusReserve";
    } else if (path.startsWith("/trips/") && path.includes("/seats")) {
      title = "Select Seats | BusReserve";
    } else if (path.startsWith("/payment") || path === "/checkout") {
      title = "Secure Payment | BusReserve";
    } else if (path === "/pnr" || path.startsWith("/bookings")) {
      title = "Track Booking | BusReserve";
    } else if (path.startsWith("/journey/track")) {
      title = "Live Journey Tracking | BusReserve";
    } else if (path === "/driver") {
      title = "Driver GPS Console | BusReserve";
    } else if (path === "/operator") {
      title = "Operator Fleet Dashboard | BusReserve";
    } else if (path === "/login") {
      title = "Passenger Login | BusReserve";
    } else if (path === "/register") {
      title = "Create Account | BusReserve";
    } else if (path === "/admin/login") {
      title = "Admin Portal | BusReserve";
    } else if (path.startsWith("/admin")) {
      title = "Admin Portal | BusReserve";
    } else if (path.startsWith("/dashboard") || path === "/profile") {
      title = "My Dashboard | BusReserve";
    } else if (path === "/assistant") {
      title = "AI Travel Concierge | BusReserve";
    } else if (path === "/forgot-password") {
      title = "Reset Password | BusReserve";
    } else if (path === "/reset-password") {
      title = "Set New Password | BusReserve";
    } else if (path === "/verify-email") {
      title = "Verify Email | BusReserve";
    } else {
      title = "Page Not Found | BusReserve";
    }

    document.title = title;
  }, [location]);

  return null;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <PageTitleManager />
        <div className="flex min-h-screen flex-col bg-cream-50">
          <Navbar />
          <main id="main-content" className="flex-1">
            <Routes>
              {/* Core Passenger Routes */}
              <Route path="/" element={<HomePage />} />
              <Route path="/search" element={<SearchResultsPage />} />
              <Route path="/trips" element={<SearchResultsPage />} />
              <Route path="/trips/:tripId/seats" element={<SeatSelectionPage />} />

              {/* Checkout & Payment Routes */}
              <Route path="/payment" element={<PaymentPage />} />
              <Route path="/checkout" element={<PaymentPage />} />
              <Route path="/payment/success" element={<PaymentPage />} />
              <Route path="/payment/failure" element={<PaymentPage />} />
              <Route path="/payment/failed" element={<PaymentPage />} />

              {/* PNR & Booking Tracking */}
              <Route path="/pnr" element={<BookingConfirmationPage />} />
              <Route path="/bookings" element={<BookingConfirmationPage />} />
              <Route path="/bookings/:pnr" element={<BookingConfirmationPage />} />
              <Route path="/journey/track/:token" element={<PublicJourneyTrackPage />} />

              {/* Authentication & Account Lifecycle */}
              <Route path="/login" element={<UserLoginPage />} />
              <Route path="/register" element={<UserRegisterPage />} />
              <Route path="/verify-email" element={<VerifyEmailPage />} />
              <Route path="/forgot-password" element={<ForgotPasswordPage />} />
              <Route path="/reset-password" element={<ResetPasswordPage />} />

              {/* Passenger Portal & AI Concierge */}
              <Route
                path="/dashboard"
                element={
                  <ProtectedRoute requiredRole="USER">
                    <UserDashboardPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/dashboard/:tab"
                element={
                  <ProtectedRoute requiredRole="USER">
                    <UserDashboardPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/profile"
                element={
                  <ProtectedRoute requiredRole="USER">
                    <UserDashboardPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/assistant"
                element={
                  <ProtectedRoute requiredRole="USER">
                    <AssistantPage />
                  </ProtectedRoute>
                }
              />

              {/* Driver & Operator Consoles */}
              <Route
                path="/driver"
                element={
                  <ProtectedRoute allowedRoles={["DRIVER", "ADMIN"]}>
                    <DriverConsolePage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/operator"
                element={
                  <ProtectedRoute allowedRoles={["OPERATOR", "ADMIN"]}>
                    <OperatorFleetDashboard />
                  </ProtectedRoute>
                }
              />

              {/* Admin Portal & Sub-Modules */}
              <Route path="/admin/login" element={<AdminLoginPage />} />
              <Route
                path="/admin"
                element={
                  <ProtectedRoute requiredRole="ADMIN">
                    <AdminOverviewPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="/admin/:tab"
                element={
                  <ProtectedRoute requiredRole="ADMIN">
                    <AdminOverviewPage />
                  </ProtectedRoute>
                }
              />

              {/* Wildcard 404 Route */}
              <Route path="*" element={<NotFoundPage />} />
            </Routes>
          </main>
          <Footer />
        </div>
      </BrowserRouter>
    </AuthProvider>
  );
}
