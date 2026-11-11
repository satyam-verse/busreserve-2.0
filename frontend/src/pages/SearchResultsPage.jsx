import { Filter, Search, SlidersHorizontal } from "lucide-react";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import TripCard from "../components/TripCard";
import { busApi } from "../services/api";

export default function SearchResultsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [trips, setTrips] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [source, setSource] = useState(searchParams.get("source") || "");
  const [destination, setDestination] = useState(searchParams.get("destination") || "");
  const [travelDate, setTravelDate] = useState(searchParams.get("travel_date") || "");
  const [sortBy, setSortBy] = useState(searchParams.get("sort_by") || "departure_asc");
  const [minSeats, setMinSeats] = useState(searchParams.get("min_seats") || "");

  useEffect(() => {
    let active = true;
    async function fetchTrips() {
      try {
        setLoading(true);
        setError("");
        const resp = await busApi.searchTrips({
          source: searchParams.get("source") || "",
          destination: searchParams.get("destination") || "",
          travel_date: searchParams.get("travel_date") || "",
          sort_by: searchParams.get("sort_by") || "departure_asc",
          min_seats: searchParams.get("min_seats") || "",
        });
        if (!active) return;
        setTrips(resp.trips || []);
      } catch (err) {
        if (active) setError(err.message || "Failed to search trips.");
      } finally {
        if (active) setLoading(false);
      }
    }
    fetchTrips();
    return () => {
      active = false;
    };
  }, [searchParams]);

  const applyFilters = (e) => {
    e.preventDefault();
    const next = new URLSearchParams();
    if (source.trim()) next.set("source", source.trim());
    if (destination.trim()) next.set("destination", destination.trim());
    if (travelDate) next.set("travel_date", travelDate);
    if (sortBy) next.set("sort_by", sortBy);
    if (minSeats) next.set("min_seats", minSeats);
    setSearchParams(next);
  };

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 py-8 sm:px-6">
      <div className="rounded-2xl border border-cream-200 bg-white p-5 shadow-sm">
        <div className="mb-4 flex items-center gap-2 text-sm font-bold text-navy-900">
          <SlidersHorizontal className="h-4 w-4 text-emerald-600" />
          <span>Search &amp; Filter Bus Trips</span>
        </div>
        <form onSubmit={applyFilters} className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-6">
          <input
            type="text"
            placeholder="Source city (e.g. Patna)"
            value={source}
            onChange={(e) => setSource(e.target.value)}
            className="rounded-xl border border-cream-200 bg-cream-50 px-3 py-2.5 text-sm focus:border-emerald-500 focus:outline-none"
          />
          <input
            type="text"
            placeholder="Destination city (e.g. Ranchi)"
            value={destination}
            onChange={(e) => setDestination(e.target.value)}
            className="rounded-xl border border-cream-200 bg-cream-50 px-3 py-2.5 text-sm focus:border-emerald-500 focus:outline-none"
          />
          <input
            type="date"
            value={travelDate}
            onChange={(e) => setTravelDate(e.target.value)}
            className="rounded-xl border border-cream-200 bg-cream-50 px-3 py-2.5 text-sm focus:border-emerald-500 focus:outline-none"
          />
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="rounded-xl border border-cream-200 bg-cream-50 px-3 py-2.5 text-sm focus:border-emerald-500 focus:outline-none"
          >
            <option value="departure_asc">Sort: Earliest Departure</option>
            <option value="fare_asc">Sort: Fare Low to High</option>
            <option value="fare_desc">Sort: Fare High to Low</option>
            <option value="seats_desc">Sort: Most Available Seats</option>
          </select>
          <select
            value={minSeats}
            onChange={(e) => setMinSeats(e.target.value)}
            className="rounded-xl border border-cream-200 bg-cream-50 px-3 py-2.5 text-sm focus:border-emerald-500 focus:outline-none"
          >
            <option value="">Any Seats Left</option>
            <option value="1">At least 1 seat</option>
            <option value="5">At least 5 seats</option>
            <option value="15">At least 15 seats</option>
          </select>
          <button
            type="submit"
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-navy-900 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-navy-800"
          >
            <Search className="h-4 w-4" />
            <span>Apply</span>
          </button>
        </form>
      </div>

      <div className="flex items-center justify-between">
        <h1 className="font-display text-2xl font-bold text-navy-900">
          Available Buses{" "}
          <span className="text-base font-medium text-slate-500">({trips.length} found)</span>
        </h1>
        <span className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-500">
          <Filter className="h-3.5 w-3.5" />
          Real-time inventory
        </span>
      </div>

      {loading && (
        <div className="rounded-2xl border border-cream-200 bg-white p-10 text-center text-sm text-slate-500">
          Searching trips...
        </div>
      )}

      {error && (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-800">
          {error}
        </div>
      )}

      {!loading && !error && trips.length === 0 && (
        <div className="rounded-2xl border border-cream-200 bg-white p-10 text-center">
          <p className="font-display text-lg font-bold text-navy-900">No matching trips found</p>
          <p className="mt-1 text-sm text-slate-500">
            Try clearing the travel date filter or searching another route.
          </p>
        </div>
      )}

      <div className="space-y-4">
        {trips.map((trip) => (
          <TripCard key={trip.id} trip={trip} />
        ))}
      </div>
    </div>
  );
}
