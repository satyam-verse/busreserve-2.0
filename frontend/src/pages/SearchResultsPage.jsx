import { Calendar, Filter, Search, SlidersHorizontal } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import CityAutocompleteInput from "../components/CityAutocompleteInput";
import InteractiveBookingCalendar from "../components/InteractiveBookingCalendar";
import TripCard from "../components/TripCard";
import { busApi } from "../services/api";
import {
  addDaysIstIso,
  addDaysToIso,
  formatIsoShortDisplay,
  getTodayIstIso,
} from "../utils/dates";

export default function SearchResultsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [trips, setTrips] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [minDate, setMinDate] = useState(getTodayIstIso());
  const [maxDate, setMaxDate] = useState(addDaysIstIso(90));
  const [horizonDays, setHorizonDays] = useState(90);

  const [source, setSource] = useState(searchParams.get("source") || "");
  const [destination, setDestination] = useState(searchParams.get("destination") || "");
  const [travelDate, setTravelDate] = useState(searchParams.get("travel_date") || "");
  const [sortBy, setSortBy] = useState(searchParams.get("sort_by") || "departure_asc");
  const [minSeats, setMinSeats] = useState(searchParams.get("min_seats") || "");

  useEffect(() => {
    setSource(searchParams.get("source") || "");
    setDestination(searchParams.get("destination") || "");
    setTravelDate(searchParams.get("travel_date") || "");
    setSortBy(searchParams.get("sort_by") || "departure_asc");
    setMinSeats(searchParams.get("min_seats") || "");
  }, [searchParams]);

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
        if (resp.min_date) setMinDate(resp.min_date);
        if (resp.max_date) setMaxDate(resp.max_date);
        if (resp.booking_horizon_days) setHorizonDays(resp.booking_horizon_days);
      } catch (err) {
        if (active) {
          setTrips([]);
          setError(err.message || "Failed to search trips.");
        }
      } finally {
        if (active) setLoading(false);
      }
    }
    fetchTrips();
    return () => {
      active = false;
    };
  }, [searchParams]);

  const dateStrip = useMemo(() => {
    return [0, 1, 2, 3, 4].map((offset) => addDaysToIso(minDate, offset)).filter((d) => d <= maxDate);
  }, [minDate, maxDate]);

  const commitQuery = (overrides = {}) => {
    const nextSource = overrides.source !== undefined ? overrides.source : source;
    const nextDest = overrides.destination !== undefined ? overrides.destination : destination;
    const nextDate = overrides.travelDate !== undefined ? overrides.travelDate : travelDate;
    const nextSort = overrides.sortBy !== undefined ? overrides.sortBy : sortBy;
    const nextSeats = overrides.minSeats !== undefined ? overrides.minSeats : minSeats;

    const next = new URLSearchParams();
    if (nextSource.trim()) next.set("source", nextSource.trim());
    if (nextDest.trim()) next.set("destination", nextDest.trim());
    if (nextDate) next.set("travel_date", nextDate);
    if (nextSort) next.set("sort_by", nextSort);
    if (nextSeats) next.set("min_seats", nextSeats);
    setSearchParams(next);
  };

  const applyFilters = (e) => {
    e.preventDefault();
    commitQuery();
  };

  return (
    <div className="bg-transit-grid min-h-[calc(100vh-140px)]">
      <div className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6">
        <div className="rounded-3xl border border-cream-200 bg-white p-5 shadow-card sm:p-6">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
            <span className="inline-flex items-center gap-2 text-sm font-bold text-navy-950">
              <SlidersHorizontal className="h-4 w-4 text-emerald-600" />
              <span>Search &amp; Filter Bus Trips</span>
            </span>
            <span className="rounded-full bg-cream-100 px-3 py-1 font-mono text-[11px] font-medium text-slate-600">
              Booking horizon: {minDate} to {maxDate} ({horizonDays} days, IST)
            </span>
          </div>

          <form
            onSubmit={applyFilters}
            className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-6"
          >
            <CityAutocompleteInput
              value={source}
              onChange={setSource}
              placeholder="Source city (any)"
              inputClassName="w-full rounded-xl border border-cream-200 bg-cream-50 py-2.5 pl-3 pr-8 text-sm font-medium focus:border-emerald-500 focus:outline-none"
            />
            <CityAutocompleteInput
              value={destination}
              onChange={setDestination}
              placeholder="Destination city (any)"
              inputClassName="w-full rounded-xl border border-cream-200 bg-cream-50 py-2.5 pl-3 pr-8 text-sm font-medium focus:border-emerald-500 focus:outline-none"
            />
            <InteractiveBookingCalendar
              compact
              value={travelDate}
              onChange={setTravelDate}
              minDate={minDate}
              maxDate={maxDate}
              horizonDays={horizonDays}
            />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              aria-label="Sort trips"
              className="rounded-xl border border-cream-200 bg-cream-50 px-3 py-2.5 text-sm font-medium text-navy-900 focus:border-emerald-500 focus:outline-none"
            >
              <option value="departure_asc">Sort: Earliest Departure</option>
              <option value="fare_asc">Sort: Fare Low to High</option>
              <option value="fare_desc">Sort: Fare High to Low</option>
              <option value="seats_desc">Sort: Most Available Seats</option>
            </select>
            <select
              value={minSeats}
              onChange={(e) => setMinSeats(e.target.value)}
              aria-label="Minimum seats filter"
              className="rounded-xl border border-cream-200 bg-cream-50 px-3 py-2.5 text-sm font-medium text-navy-900 focus:border-emerald-500 focus:outline-none"
            >
              <option value="">Any Seats Left</option>
              <option value="1">At least 1 seat</option>
              <option value="5">At least 5 seats</option>
              <option value="15">At least 15 seats</option>
            </select>
            <button
              type="submit"
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-navy-950 px-4 py-2.5 text-sm font-bold text-white transition hover:bg-emerald-600"
            >
              <Search className="h-4 w-4" />
              <span>Apply</span>
            </button>
          </form>

          {/* IST Quick-Switch Date Strip */}
          <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-cream-200 pt-3.5">
            <span className="inline-flex items-center gap-1 text-xs font-semibold text-slate-500">
              <Calendar className="h-3.5 w-3.5 text-emerald-600" />
              IST Dates:
            </span>
            <button
              type="button"
              onClick={() => {
                setTravelDate("");
                commitQuery({ travelDate: "" });
              }}
              className={`rounded-lg px-2.5 py-1 text-xs font-semibold transition ${
                !travelDate
                  ? "bg-navy-950 text-white"
                  : "border border-cream-200 bg-cream-50 text-navy-900 hover:bg-emerald-50"
              }`}
            >
              All Horizon Dates
            </button>
            {dateStrip.map((iso) => {
              const active = travelDate === iso;
              return (
                <button
                  key={iso}
                  type="button"
                  onClick={() => {
                    setTravelDate(iso);
                    commitQuery({ travelDate: iso });
                  }}
                  className={`rounded-lg px-2.5 py-1 text-xs font-semibold transition ${
                    active
                      ? "bg-emerald-600 text-white shadow-sm"
                      : "border border-cream-200 bg-cream-50 text-navy-900 hover:border-emerald-400 hover:bg-emerald-50"
                  }`}
                >
                  {formatIsoShortDisplay(iso)}
                </button>
              );
            })}
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2">
          <h1 className="font-display text-2xl font-extrabold text-navy-950">
            Available Buses{" "}
            <span className="text-base font-semibold text-slate-500">({trips.length} found)</span>
          </h1>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-cream-200 bg-white px-3 py-1 text-xs font-semibold text-slate-600">
            <Filter className="h-3.5 w-3.5 text-emerald-600" />
            Live schedules &amp; real-time seat inventory
          </span>
        </div>

        {loading && (
          <div className="space-y-4" aria-busy="true" aria-label="Searching available trips">
            <div className="h-32 animate-pulse rounded-2xl border border-cream-200 bg-white" />
            <div className="h-32 animate-pulse rounded-2xl border border-cream-200 bg-white" />
          </div>
        )}

        {error && (
          <div role="alert" className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-800">
            {error}
          </div>
        )}

        {!loading && !error && trips.length === 0 && (
          <div className="rounded-3xl border border-cream-200 bg-white p-10 text-center shadow-card">
            <p className="font-display text-lg font-bold text-navy-950">No matching trips found</p>
            <p className="mt-1 text-sm text-slate-500">
              No scheduled services match that exact filter. Try clearing the travel date or
              searching another city corridor.
            </p>
          </div>
        )}

        <div className="space-y-4">
          {trips.map((trip) => (
            <TripCard key={trip.id} trip={trip} />
          ))}
        </div>
      </div>
    </div>
  );
}
