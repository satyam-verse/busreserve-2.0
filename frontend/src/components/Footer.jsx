import { Bus } from "lucide-react";

export default function Footer() {
  return (
    <footer className="mt-auto border-t border-cream-200 bg-white">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-4 py-6 text-xs text-slate-500 sm:flex-row sm:px-6">
        <div className="flex items-center gap-2 font-medium text-navy-900">
          <Bus className="h-4 w-4 text-emerald-600" />
          <span>BusReserve Platform</span>
          <span className="text-slate-300">•</span>
          <span className="text-slate-500">PostgreSQL Transactional Seat Inventory</span>
        </div>
        <p className="text-center text-slate-500">
          Demo showcase for Cloud Deployment &amp; CI/CD Assessment — No real payments processed.
        </p>
      </div>
    </footer>
  );
}
