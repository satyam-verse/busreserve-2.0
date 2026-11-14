import { MapPin, X } from "lucide-react";
import { useEffect, useId, useRef, useState } from "react";
import { busApi } from "../services/api";

export default function CityAutocompleteInput({
  label,
  value,
  onChange,
  placeholder = "Enter any Indian city",
  iconTone = "text-emerald-600",
  inputClassName = "",
}) {
  const inputId = useId();
  const containerRef = useRef(null);
  const [open, setOpen] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);

  useEffect(() => {
    function handleOutsideClick(event) {
      if (containerRef.current && !containerRef.current.contains(event.target)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleOutsideClick);
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, []);

  useEffect(() => {
    if (!open) return;
    let active = true;
    const timer = setTimeout(async () => {
      try {
        setLoading(true);
        const resp = await busApi.getCities(value, 12);
        if (!active) return;
        setSuggestions(resp.cities || []);
        setActiveIndex(-1);
      } catch {
        if (active) setSuggestions([]);
      } finally {
        if (active) setLoading(false);
      }
    }, 150);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [value, open]);

  const selectCity = (cityName) => {
    onChange(cityName);
    setOpen(false);
    setActiveIndex(-1);
  };

  const handleKeyDown = (e) => {
    if (!open || suggestions.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((prev) => (prev + 1) % suggestions.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((prev) => (prev <= 0 ? suggestions.length - 1 : prev - 1));
    } else if (e.key === "Enter" && activeIndex >= 0) {
      e.preventDefault();
      selectCity(suggestions[activeIndex].name);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  return (
    <div ref={containerRef} className="relative">
      {label && (
        <label
          htmlFor={inputId}
          className="mb-1.5 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-slate-500"
        >
          <MapPin className={`h-3.5 w-3.5 ${iconTone}`} />
          {label}
        </label>
      )}
      <div className="relative">
        <input
          id={inputId}
          type="text"
          autoComplete="off"
          value={value}
          placeholder={placeholder}
          onFocus={() => setOpen(true)}
          onChange={(e) => {
            onChange(e.target.value);
            setOpen(true);
          }}
          onKeyDown={handleKeyDown}
          className={
            inputClassName ||
            "w-full rounded-xl border border-cream-200 bg-cream-50 py-3 pl-3.5 pr-8 text-sm font-semibold text-navy-900 placeholder:font-normal placeholder:text-slate-400 focus:border-emerald-500 focus:outline-none focus:ring-2 focus:ring-emerald-200"
          }
        />
        {value && (
          <button
            type="button"
            onClick={() => {
              onChange("");
              setOpen(true);
            }}
            aria-label={`Clear ${label || "city"}`}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded p-0.5 text-slate-400 hover:text-navy-900"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      {open && (
        <div className="absolute left-0 right-0 z-40 mt-1.5 max-h-64 overflow-y-auto rounded-xl border border-cream-200 bg-white py-1 shadow-xl">
          {loading && suggestions.length === 0 && (
            <div className="px-3.5 py-2.5 text-xs text-slate-500">Searching Indian cities...</div>
          )}

          {!loading && suggestions.length === 0 && (
            <div className="px-3.5 py-2.5 text-xs text-slate-500">
              No directory match for &ldquo;{value}&rdquo; — press Search to query anyway.
            </div>
          )}

          {suggestions.map((city, idx) => (
            <button
              key={`${city.name}-${idx}`}
              type="button"
              onMouseDown={(e) => {
                e.preventDefault();
                selectCity(city.name);
              }}
              className={`flex w-full items-center justify-between gap-2 px-3.5 py-2 text-left text-sm transition-colors ${
                idx === activeIndex
                  ? "bg-emerald-50 text-navy-900"
                  : "text-navy-900 hover:bg-cream-50"
              }`}
            >
              <div>
                <span className="font-semibold">{city.name}</span>
                {city.state && (
                  <span className="ml-1.5 text-xs text-slate-500">({city.state})</span>
                )}
                {city.matched_alias && (
                  <span className="ml-2 text-[11px] font-medium text-emerald-700">
                    alias: {city.matched_alias}
                  </span>
                )}
              </div>
              <span
                className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                  city.has_routes
                    ? "bg-emerald-50 text-emerald-700"
                    : "bg-slate-100 text-slate-500"
                }`}
              >
                {city.has_routes ? "Routes active" : "City"}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
