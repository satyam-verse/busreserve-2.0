import { Link } from "react-router-dom";
import { ArrowLeft, Sparkles } from "lucide-react";
import PassengerAssistantWidget from "../components/ai/PassengerAssistantWidget";

export default function AssistantPage() {
  return (
    <div className="bg-transit-grid min-h-[calc(100vh-140px)]">
      <div className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-6 flex flex-wrap items-end justify-between gap-4 rounded-3xl border border-navy-900/10 bg-white/95 p-6 shadow-card">
          <div>
            <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-emerald-700/20 bg-emerald-50 px-3 py-1 text-[11px] font-bold uppercase tracking-[0.16em] text-emerald-800">
              <Sparkles className="h-3.5 w-3.5" />
              <span>AI Travel Concierge • Read-Only Grounding</span>
            </div>
            <h1 className="font-serif text-3xl font-normal tracking-tight text-navy-950 sm:text-4xl">
              AI Travel Concierge
            </h1>
            <p className="mt-1 text-sm text-navy-900/65">
              Find optimal routes, compare real-time fares and overnight sleepers, or check your
              reservations within the 90-day IST window.
            </p>
          </div>
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-1.5 rounded-xl border border-navy-900/15 bg-cream-50 px-4 py-2.5 text-xs font-bold text-navy-950 transition hover:bg-navy-950 hover:text-white"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>Back to My Dashboard</span>
          </Link>
        </div>

        <PassengerAssistantWidget />
      </div>
    </div>
  );
}
