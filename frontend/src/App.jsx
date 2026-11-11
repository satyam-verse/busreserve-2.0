import { BrowserRouter, Route, Routes } from "react-router-dom";
import Footer from "./components/Footer";
import Navbar from "./components/Navbar";
import AdminOverviewPage from "./pages/AdminOverviewPage";
import BookingConfirmationPage from "./pages/BookingConfirmationPage";
import HomePage from "./pages/HomePage";
import SearchResultsPage from "./pages/SearchResultsPage";
import SeatSelectionPage from "./pages/SeatSelectionPage";

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen flex-col bg-cream-50">
        <Navbar />
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/search" element={<SearchResultsPage />} />
            <Route path="/trips/:tripId/seats" element={<SeatSelectionPage />} />
            <Route path="/pnr" element={<BookingConfirmationPage />} />
            <Route path="/bookings/:pnr" element={<BookingConfirmationPage />} />
            <Route path="/admin" element={<AdminOverviewPage />} />
          </Routes>
        </main>
        <Footer />
      </div>
    </BrowserRouter>
  );
}
