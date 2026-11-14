import { ChevronLeft, ChevronRight } from "lucide-react";

export default function AdminPagination({ pagination, onPageChange }) {
  if (!pagination || pagination.total === 0) return null;
  const { page, pages, total } = pagination;
  return (
    <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-navy-900/10 pt-4 text-xs text-navy-900/70">
      <span>
        Page <strong className="text-navy-950">{page}</strong> of{" "}
        <strong className="text-navy-950">{pages}</strong> ({total} total records)
      </span>
      <div className="flex items-center gap-2">
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
          className="inline-flex items-center gap-1 rounded-lg border border-navy-900/15 bg-white px-2.5 py-1.5 font-semibold text-navy-950 hover:bg-cream-50 disabled:opacity-40"
        >
          <ChevronLeft className="h-3.5 w-3.5" />
          <span>Prev</span>
        </button>
        <button
          type="button"
          disabled={page >= pages}
          onClick={() => onPageChange(page + 1)}
          className="inline-flex items-center gap-1 rounded-lg border border-navy-900/15 bg-white px-2.5 py-1.5 font-semibold text-navy-950 hover:bg-cream-50 disabled:opacity-40"
        >
          <span>Next</span>
          <ChevronRight className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}
