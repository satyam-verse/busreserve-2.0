import { ArrowUpRight, Sparkles } from "lucide-react";

const FEATURED_NODES = [
  { id: "del", name: "Delhi", code: "DEL", x: 112, y: 74, badge: "North Hub" },
  { id: "jai", name: "Jaipur", code: "JAI", x: 76, y: 146, badge: "PinkCity" },
  { id: "vns", name: "Varanasi", code: "VNS", x: 196, y: 152, badge: "Purvanchal", align: "start" },
  { id: "pat", name: "Patna", code: "PAT", x: 298, y: 106, badge: "ISBT Hub", primary: true, align: "end" },
  { id: "ixr", name: "Ranchi", code: "IXR", x: 306, y: 196, badge: "Express", primary: true, align: "end" },
  { id: "pun", name: "Pune", code: "PNQ", x: 118, y: 248, badge: "West" },
  { id: "hyd", name: "Hyderabad", code: "HYD", x: 218, y: 266, badge: "Deccan" },
  { id: "blr", name: "Bengaluru", code: "BLR", x: 184, y: 332, badge: "South Hub" },
];

const HIGHLIGHT_CORRIDORS = [
  { from: "Patna", to: "Ranchi", label: "Patna → Ranchi", meta: "Express • Direct & Via Gaya" },
  { from: "Delhi", to: "Jaipur", label: "Delhi → Jaipur", meta: "NH-48 PinkCity Line" },
  { from: "Pune", to: "Bengaluru", label: "Pune → Bengaluru", meta: "Deccan Overnight" },
];

export default function CorridorMapIllustration({ onSelectCorridor }) {
  return (
    <div className="relative overflow-hidden rounded-3xl border border-white/15 bg-navy-900/80 p-5 shadow-editorial backdrop-blur-md">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <p className="font-mono text-[10px] font-semibold uppercase tracking-[0.2em] text-emerald-300">
            Live Topology • IST Network
          </p>
          <h2 className="mt-0.5 font-display text-sm font-bold text-white">
            Intercity Trunk Corridors
          </h2>
        </div>
        <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-400/30 bg-emerald-500/15 px-2.5 py-1 text-[11px] font-semibold text-emerald-300">
          <span className="relative flex h-2 w-2">
            <span className="animate-pulse-ring absolute inline-flex h-full w-full rounded-full bg-emerald-400" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
          </span>
          Live Seat Lock
        </span>
      </div>

      <div className="relative rounded-2xl border border-white/10 bg-navy-950/85 p-3">
        <svg
          viewBox="0 0 380 370"
          className="h-64 w-full sm:h-72"
          role="img"
          aria-label="Animated BusReserve intercity transit network map connecting Indian cities"
        >
          <defs>
            <linearGradient id="br-arc-emerald" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#10B981" stopOpacity="0.95" />
              <stop offset="100%" stopColor="#DDA13C" stopOpacity="0.85" />
            </linearGradient>
            <linearGradient id="br-arc-subtle" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#60A5FA" stopOpacity="0.45" />
              <stop offset="100%" stopColor="#10B981" stopOpacity="0.45" />
            </linearGradient>
          </defs>

          {/* Subtle Latitude/Longitude Reference Lines */}
          {[75, 150, 225, 300].map((y) => (
            <line
              key={`h-${y}`}
              x1="14"
              y1={y}
              x2="366"
              y2={y}
              stroke="rgba(255,255,255,0.04)"
              strokeWidth="1"
            />
          ))}
          {[95, 190, 285].map((x) => (
            <line
              key={`v-${x}`}
              x1={x}
              y1="14"
              x2={x}
              y2="356"
              stroke="rgba(255,255,255,0.04)"
              strokeWidth="1"
            />
          ))}

          {/* Base Static Edges */}
          <path
            d="M 112 74 Q 82 110 76 146"
            fill="none"
            stroke="url(#br-arc-subtle)"
            strokeWidth="2"
          />
          <path
            d="M 112 74 Q 158 104 196 152"
            fill="none"
            stroke="url(#br-arc-subtle)"
            strokeWidth="1.75"
          />
          <path
            d="M 196 152 Q 250 120 298 106"
            fill="none"
            stroke="url(#br-arc-subtle)"
            strokeWidth="2"
          />
          <path
            d="M 76 146 Q 90 198 118 248"
            fill="none"
            stroke="url(#br-arc-subtle)"
            strokeWidth="1.75"
          />
          <path
            d="M 118 248 Q 168 250 218 266"
            fill="none"
            stroke="url(#br-arc-subtle)"
            strokeWidth="1.75"
          />
          <path
            d="M 218 266 Q 205 304 184 332"
            fill="none"
            stroke="url(#br-arc-subtle)"
            strokeWidth="2"
          />
          <path
            d="M 118 248 Q 134 298 184 332"
            fill="none"
            stroke="url(#br-arc-emerald)"
            strokeWidth="2.2"
          />

          {/* Animated High-Demand Trunk Flows */}
          <path
            d="M 298 106 Q 322 152 306 196"
            fill="none"
            stroke="url(#br-arc-emerald)"
            strokeWidth="2.6"
            className="animate-dash-flow"
          />
          <path
            d="M 112 74 Q 82 110 76 146"
            fill="none"
            stroke="#34D399"
            strokeWidth="2.2"
            className="animate-dash-flow"
          />
          <path
            d="M 118 248 Q 134 298 184 332"
            fill="none"
            stroke="#DDA13C"
            strokeWidth="2.2"
            className="animate-dash-flow"
          />

          {/* City Hub Nodes */}
          {FEATURED_NODES.map((node) => {
            const alignEnd = node.align === "end";
            return (
              <g key={node.id} transform={`translate(${node.x}, ${node.y})`}>
                {node.primary ? (
                  <circle r="11" fill="rgba(16, 185, 129, 0.16)" className="animate-pulse-ring" />
                ) : null}
                <circle
                  r={node.primary ? 5.5 : 4.5}
                  fill={node.primary ? "#10B981" : "#FAF8F3"}
                  stroke="#06101E"
                  strokeWidth="2"
                />
                <text
                  x={alignEnd ? -10 : 10}
                  y="4"
                  textAnchor={alignEnd ? "end" : "start"}
                  fill="#FAF8F3"
                  fontSize="11"
                  fontWeight="700"
                  fontFamily="Plus Jakarta Sans, sans-serif"
                >
                  {node.name}
                </text>
                <text
                  x={alignEnd ? -10 : 10}
                  y="15"
                  textAnchor={alignEnd ? "end" : "start"}
                  fill={node.primary ? "#6EE7B7" : "#94A3B8"}
                  fontSize="8.5"
                  fontFamily="JetBrains Mono, monospace"
                >
                  {node.code} • {node.badge}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Quick Clickable Corridor Pills */}
      <div className="mt-3 grid gap-2 sm:grid-cols-3">
        {HIGHLIGHT_CORRIDORS.map((corridor) => (
          <button
            key={corridor.label}
            type="button"
            onClick={() => onSelectCorridor?.(corridor.from, corridor.to)}
            className="group flex items-center justify-between rounded-xl border border-white/10 bg-white/5 px-3 py-2 text-left transition hover:border-emerald-400/50 hover:bg-emerald-500/15"
          >
            <div className="min-w-0">
              <p className="truncate text-xs font-bold text-white">{corridor.label}</p>
              <p className="truncate text-[10px] text-slate-300">{corridor.meta}</p>
            </div>
            <ArrowUpRight className="ml-1.5 h-3.5 w-3.5 shrink-0 text-emerald-300 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
          </button>
        ))}
      </div>

      <p className="mt-2.5 flex items-center gap-1.5 text-[11px] text-slate-300/80">
        <Sparkles className="h-3.5 w-3.5 text-brass-400" />
        Click a highlighted corridor to prefill origin &amp; destination or enter any Indian city.
      </p>
    </div>
  );
}
