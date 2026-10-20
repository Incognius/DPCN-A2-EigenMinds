export const fmt = (n: number | null | undefined, digits = 0) =>
  n == null || Number.isNaN(n) ? "–" : n.toLocaleString("en-IN", { maximumFractionDigits: digits, minimumFractionDigits: digits });

export const compact = (n: number | null | undefined) =>
  n == null ? "–" : Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 }).format(n);

export const pct = (x: number | null | undefined, digits = 1) =>
  x == null || Number.isNaN(x) ? "–" : `${(x * 100).toFixed(digits)}%`;

export const signedPct = (x: number | null | undefined, digits = 1) =>
  x == null ? "–" : `${x >= 0 ? "+" : ""}${(x * 100).toFixed(digits)}%`;

export const pval = (p: number | null | undefined) =>
  p == null ? "–" : p < 0.001 ? "p < 0.001" : `p = ${p.toFixed(3)}`;

export const initials = (name: string) =>
  name.split(/\s+/).filter((t) => t.length > 1).slice(0, 2).map((t) => t[0]).join("").toUpperCase();

export const doiUrl = (doi?: string | null, id?: string) =>
  doi ? doi : id ? `https://openalex.org/${id}` : undefined;
