import ReactECharts from "echarts-for-react";
import type { EChartsOption } from "echarts";
import { baseOption } from "../lib/theme";

function merge(a: Record<string, unknown>, b: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = { ...a };
  for (const [k, v] of Object.entries(b)) {
    const av = out[k];
    out[k] = av && typeof av === "object" && !Array.isArray(av) && v && typeof v === "object" && !Array.isArray(v)
      ? merge(av as Record<string, unknown>, v as Record<string, unknown>)
      : v;
  }
  return out;
}

/** ECharts with the shared dark theme merged underneath the caller's option. */
export default function Chart({ option, height = 280, onClick }: {
  option: EChartsOption; height?: number; onClick?: (p: { name?: string; data?: unknown; seriesName?: string }) => void;
}) {
  return (
    <ReactECharts
      option={merge(baseOption as Record<string, unknown>, option as Record<string, unknown>)}
      style={{ height, width: "100%" }}
      notMerge
      lazyUpdate
      opts={{ renderer: "canvas" }}
      onEvents={onClick ? { click: onClick } : undefined}
    />
  );
}
