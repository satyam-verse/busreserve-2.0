import { ShieldCheck } from "lucide-react";

export default function AuthShell({
  badge = "BusReserve 2.0",
  title,
  subtitle,
  highlights = [],
  variant = "passenger",
  children,
}) {
  const isAdmin = variant === "admin";

  return (
    <div
      className={`min-h-[calc(100vh-140px)] px-4 py-10 sm:px-6 lg:py-14 ${
        isAdmin ? "bg-navy-950 bg-navy-grid text-white" : "bg-transit-grid"
      }`}
    >
      <div className="mx-auto grid max-w-5xl overflow-hidden rounded-3xl border border-navy-900/10 bg-white shadow-editorial lg:grid-cols-12">
        {/* Left Editorial Brand & Trust Column */}
        <div
          className={`relative flex flex-col justify-between p-8 text-white lg:col-span-5 lg:p-10 ${
            isAdmin
              ? "bg-gradient-to-br from-navy-950 via-navy-900 to-navy-800"
              : "bg-gradient-to-br from-navy-950 via-navy-900 to-emerald-950"
          }`}
        >
          <div className="pointer-events-none absolute -right-16 -top-16 h-56 w-56 rounded-full bg-emerald-500/15 blur-3xl" />
          <div className="pointer-events-none absolute -bottom-20 -left-16 h-56 w-56 rounded-full bg-brass-500/15 blur-3xl" />

          <div className="relative space-y-5">
            <span className="inline-flex items-center gap-2 rounded-full border border-emerald-400/30 bg-emerald-500/10 px-3 py-1 text-xs font-semibold tracking-wide text-emerald-300">
              <ShieldCheck className="h-3.5 w-3.5" />
              <span>{badge}</span>
            </span>

            <h2 className="font-display text-2xl font-extrabold leading-tight tracking-tight sm:text-3xl">
              {title}
            </h2>
            <p className="text-sm leading-relaxed text-slate-300">{subtitle}</p>
          </div>

          {highlights.length > 0 ? (
            <ul className="relative mt-8 space-y-3 border-t border-white/10 pt-6">
              {highlights.map((item) => {
                const Icon = item.icon;
                return (
                  <li key={item.title} className="flex items-start gap-3">
                    {Icon ? (
                      <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-white/10 text-emerald-300">
                        <Icon className="h-3.5 w-3.5" />
                      </div>
                    ) : null}
                    <div>
                      <p className="text-xs font-bold text-white">{item.title}</p>
                      <p className="text-xs text-slate-300/85">{item.desc}</p>
                    </div>
                  </li>
                );
              })}
            </ul>
          ) : null}

          <div className="relative mt-8 flex items-center justify-between border-t border-white/10 pt-4 font-mono text-[11px] text-slate-300/75">
            <span>Asia/Kolkata (IST)</span>
            <span>Demo Platform • RBAC</span>
          </div>
        </div>

        {/* Right Form Panel */}
        <div className="animate-fade-up bg-white p-7 text-navy-950 sm:p-10 lg:col-span-7">
          {children}
        </div>
      </div>
    </div>
  );
}
