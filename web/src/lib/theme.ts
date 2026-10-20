import type { InstKey, Scope } from "./types";

// Institute identity colours -- validated with the dataviz palette checker on the #141114 surface
// (lightness band, chroma floor, CVD separation >= 8, contrast >= 3:1).
export const INST_COLOR: Record<InstKey, string> = {
  IISERB: "#c266b8",
  IISERM: "#c9802a",
  IISERTVM: "#3a93d6",
};
export const INST_SHORT: Record<InstKey, string> = { IISERB: "Bhopal", IISERM: "Mohali", IISERTVM: "TVM" };
export const INST_ORDER: InstKey[] = ["IISERB", "IISERM", "IISERTVM"];
export const SCOPES: Scope[] = ["ALL", ...INST_ORDER];
export const scopeLabel = (s: Scope) => (s === "ALL" ? "All IISERs" : INST_SHORT[s]);

// Categorical slots for communities etc. (6 validated; anything past slot 6 folds into OTHER)
export const CAT = ["#c266b8", "#c9802a", "#3a93d6", "#199e70", "#9085e9", "#d9546a"];
export const OTHER = "#5d5560";

// Quartiles: one plum hue, dark -> light (sequential magnitude of journal rank)
export const QUARTILE = { Q1: "#e2b3d6", Q2: "#c27fb2", Q3: "#8e4f80", Q4: "#5a3053" } as const;
export const CORE_COLOR: Record<string, string> = { "A*": "#e2b3d6", A: "#c27fb2", B: "#8e4f80", C: "#5a3053", Unranked: "#3a3238" };

export const INK = { text: "#f4eef3", text2: "#cfc4cc", muted: "#a39aa1", faint: "#71666e", grid: "rgba(255,255,255,0.06)" };
export const POS = "#4ade80";
export const NEG = "#f87171";

/** Shared ECharts base: recessive axes and grid, dark tooltip card like the reference. */
export const baseOption = {
  backgroundColor: "transparent",
  textStyle: { fontFamily: "Urbanist, system-ui, sans-serif", color: INK.muted },
  animationDuration: 600,
  grid: { left: 8, right: 12, top: 28, bottom: 8, containLabel: true },
  tooltip: {
    backgroundColor: "rgba(16,12,15,0.96)",
    borderColor: "rgba(255,255,255,0.08)",
    borderWidth: 1,
    padding: [10, 14],
    textStyle: { color: INK.text, fontFamily: "Urbanist, system-ui, sans-serif", fontSize: 13 },
    extraCssText: "border-radius:14px;box-shadow:0 18px 40px -12px rgba(0,0,0,.7);",
  },
  legend: { textStyle: { color: INK.text2, fontSize: 12 }, icon: "roundRect", itemWidth: 10, itemHeight: 10, itemGap: 16 },
};

export const axisX = (extra: object = {}) => ({
  axisLine: { lineStyle: { color: "rgba(255,255,255,0.12)" } },
  axisTick: { show: false },
  axisLabel: { color: INK.muted, fontSize: 12 },
  splitLine: { show: false },
  ...extra,
});
export const axisY = (extra: object = {}) => ({
  axisLine: { show: false },
  axisTick: { show: false },
  axisLabel: { color: INK.faint, fontSize: 11.5 },
  splitLine: { lineStyle: { color: INK.grid, type: "dashed" as const } },
  ...extra,
});
