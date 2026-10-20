import type { ReactNode } from "react";
import { ArrowDownRight, ArrowUpRight, Info } from "lucide-react";
import { INST_COLOR, INST_SHORT } from "../lib/theme";
import type { InstKey } from "../lib/types";

export function Card({ children, className = "", glow = false }: { children: ReactNode; className?: string; glow?: boolean }) {
  return <section className={`${glow ? "card-glow" : "card"} ${className}`}>{children}</section>;
}

export function CardHead({ title, sub, right, info }: { title: ReactNode; sub?: ReactNode; right?: ReactNode; info?: string }) {
  return (
    <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0">
        <h3 className="card-title flex items-center gap-2">
          {title}
          {info && (
            <span className="group relative">
              <Info size={14} className="text-ink-faint" />
              <span className="pointer-events-none absolute left-1/2 top-6 z-30 w-64 -translate-x-1/2 rounded-xl border border-white/10 bg-[#100c0f] p-3 text-[12px] font-normal leading-relaxed text-ink-2 opacity-0 shadow-2xl transition group-hover:opacity-100">
                {info}
              </span>
            </span>
          )}
        </h3>
        {sub && <p className="card-sub mt-0.5">{sub}</p>}
      </div>
      {right}
    </div>
  );
}

export function Pills<T extends string>({ options, value, onChange, label, small = false }: {
  options: { value: T; label: ReactNode }[]; value: T; onChange: (v: T) => void; label?: (v: T) => string; small?: boolean;
}) {
  return (
    <div className="flex flex-wrap items-center gap-1.5" role="tablist">
      {options.map((o) => (
        <button key={o.value} role="tab" aria-selected={o.value === value} title={label?.(o.value)}
          className={`pill ${small ? "pill-sm" : ""} ${o.value === value ? "pill-active" : ""}`}
          onClick={() => onChange(o.value)}>
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function Delta({ value, suffix = "%", digits = 1 }: { value: number | null | undefined; suffix?: string; digits?: number }) {
  if (value == null || Number.isNaN(value)) return <span className="text-ink-faint">–</span>;
  const up = value >= 0;
  const Icon = up ? ArrowUpRight : ArrowDownRight;
  return (
    <span className={`inline-flex items-center gap-0.5 text-[12.5px] font-semibold ${up ? "text-pos" : "text-neg"}`}>
      <Icon size={13} strokeWidth={2.6} />
      {up ? "+" : ""}{(value * (suffix === "%" ? 100 : 1)).toFixed(digits)}{suffix}
    </span>
  );
}

export function Stat({ label, value, sub, accent }: { label: string; value: ReactNode; sub?: ReactNode; accent?: string }) {
  return (
    <div className="min-w-0">
      <div className="stat-label">{label}</div>
      <div className="mt-1 truncate text-[24px] font-bold tracking-tight text-ink" style={accent ? { color: accent } : undefined}>{value}</div>
      {sub && <div className="mt-0.5 text-[12.5px] text-ink-muted">{sub}</div>}
    </div>
  );
}

export function InstDot({ inst, label = false }: { inst: InstKey; label?: boolean }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="inline-block h-2.5 w-2.5 rounded-full ring-2 ring-[#141114]" style={{ background: INST_COLOR[inst] }} />
      {label && <span>{INST_SHORT[inst]}</span>}
    </span>
  );
}

export function Avatar({ name, inst, size = 38 }: { name: string; inst: InstKey; size?: number }) {
  const ini = name.split(/\s+/).filter((t) => t.length > 1).slice(0, 2).map((t) => t[0]).join("").toUpperCase();
  return (
    <span className="grid shrink-0 place-items-center rounded-full text-[12px] font-bold text-white"
      style={{ width: size, height: size, background: `radial-gradient(circle at 30% 25%, ${INST_COLOR[inst]}, #2a1a27 85%)`, boxShadow: "inset 0 1px 0 rgba(255,255,255,.2)" }}>
      {ini}
    </span>
  );
}

export function Loading({ h = 240 }: { h?: number }) {
  return <div className="animate-pulse rounded-2xl bg-white/[0.03]" style={{ height: h }} />;
}

export function Note({ children }: { children: ReactNode }) {
  return <p className="mt-3 text-[12.5px] leading-relaxed text-ink-muted">{children}</p>;
}

export function Badge({ children, tone = "plum" }: { children: ReactNode; tone?: "plum" | "pos" | "neg" | "muted" }) {
  const cls = {
    plum: "bg-plum-500/15 text-plum-200 border-plum-400/25",
    pos: "bg-pos/10 text-pos border-pos/25",
    neg: "bg-neg/10 text-neg border-neg/25",
    muted: "bg-white/5 text-ink-muted border-white/10",
  }[tone];
  return <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] font-semibold ${cls}`}>{children}</span>;
}
