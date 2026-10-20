import Chart from "../components/Chart";
import { Card, CardHead, Loading, Note } from "../components/ui";
import { useData } from "../lib/data";
import { fmt } from "../lib/format";
import { useStore } from "../lib/store";
import { INK, INST_COLOR, INST_ORDER, INST_SHORT, axisX, axisY, scopeLabel } from "../lib/theme";
import type { Institutes } from "../lib/types";

// one plum ramp, dark -> light, for the four OpenAlex domains (identity is also labelled in-cell)
const DOMAIN = { "Physical Sciences": "#8e4f80", "Life Sciences": "#b56fa3", "Health Sciences": "#d79bc7", "Social Sciences": "#5a3053" } as Record<string, string>;

export default function Areas() {
  const { scope } = useStore();
  const { data } = useData<Institutes>("institutes.json");
  const { data: sim } = useData<{ pairs: { a: string; b: string; ruzicka: number; jaccard: number }[] }>("areas.json");
  if (!data) return <Loading h={600} />;
  const s = data.institutes[scope];

  const tree: Record<string, Record<string, { name: string; value: number }[]>> = {};
  for (const r of s.subfields) {
    ((tree[r.domain] ??= {})[r.field] ??= []).push({ name: r.subfield, value: r.n });
  }
  const treeData = Object.entries(tree).map(([d, fields]) => ({
    name: d, itemStyle: { color: DOMAIN[d] ?? "#6d4a66" },
    children: Object.entries(fields).map(([f, subs]) => ({ name: f, children: subs })),
  }));

  const fields = Object.entries(data.institutes.ALL.fields).filter(([f]) => f !== "Unknown").slice(0, 10).map(([f]) => f);
  const share = (k: (typeof INST_ORDER)[number], f: string) => {
    const tot = Object.values(data.institutes[k].fields).reduce((a, b) => a + b, 0);
    return +((100 * (data.institutes[k].fields[f] ?? 0)) / tot).toFixed(1);
  };

  return (
    <div className="flex flex-col gap-5">
      <Card>
        <CardHead title="Research landscape" sub={`${scopeLabel(scope)} · OpenAlex primary topic of each paper, domain → field → subfield (top 60 subfields)`}
          info="Every OpenAlex work gets a primary topic; topics roll up into ~250 subfields, 26 fields and 4 domains. Area = number of unique affiliated papers." />
        <Chart height={460} option={{
          tooltip: { formatter: (p: unknown) => { const q = p as { name: string; value: number; treePathInfo: { name: string }[] }; return `${q.treePathInfo.map((t) => t.name).filter(Boolean).join(" › ")}<br/><b>${fmt(q.value)}</b> papers`; } },
          series: [{
            type: "treemap", roam: false, nodeClick: "zoomToNode", width: "100%", height: "92%", top: 0,
            breadcrumb: { show: true, bottom: 0, itemStyle: { color: "#1b141a", borderColor: "rgba(255,255,255,.1)", textStyle: { color: INK.text2 } } },
            itemStyle: { borderColor: "#141114", borderWidth: 2, gapWidth: 2, borderRadius: 6 },
            upperLabel: { show: true, height: 22, color: INK.text, fontWeight: 600 },
            label: { color: "#fff", fontSize: 12, overflow: "truncate" },
            levels: [
              { itemStyle: { borderWidth: 0, gapWidth: 4 }, upperLabel: { show: false } },
              { itemStyle: { gapWidth: 2, borderColor: "#141114", borderWidth: 3 }, colorSaturation: [0.35, 0.6] },
              { colorSaturation: [0.3, 0.55], itemStyle: { borderColorSaturation: 0.5, gapWidth: 1 } },
            ],
            data: treeData,
          }],
        }} />
      </Card>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHead title="Field mix by institute" sub="Share of each institute's papers in the ten largest fields" />
          <Chart height={380} option={{
            legend: { top: 0, right: 0 }, grid: { top: 36, left: 8 },
            tooltip: { trigger: "axis", axisPointer: { type: "shadow" }, valueFormatter: (v) => `${v}%` },
            yAxis: axisX({ type: "category", data: [...fields].reverse(), axisLabel: { color: INK.text2, fontSize: 12, width: 190, overflow: "truncate", interval: 0 } }),
            xAxis: axisY({ type: "value", axisLabel: { formatter: "{value}%" } }),
            series: INST_ORDER.map((k) => ({ name: INST_SHORT[k], type: "bar" as const, data: [...fields].reverse().map((f) => share(k, f)), barGap: "12%",
              itemStyle: { color: INST_COLOR[k], borderRadius: [0, 4, 4, 0] } })),
          }} />
        </Card>
        <Card>
          <CardHead title="Portfolio similarity" sub="How alike are the institutes' research mixes?"
            info="Ruzicka (weighted Jaccard) similarity of subfield distributions, and plain Jaccard of their top-50 topics. 1 = identical portfolios." />
          {sim ? (
            <ul className="flex flex-col gap-5">
              {sim.pairs.map((p) => (
                <li key={p.a + p.b}>
                  <div className="flex items-center justify-between text-[14px]">
                    <span className="flex items-center gap-1.5">
                      <span className="h-2 w-2 rounded-full" style={{ background: INST_COLOR[p.a as "IISERB"] }} />{INST_SHORT[p.a as "IISERB"]}
                      <span className="text-ink-faint">↔</span>
                      <span className="h-2 w-2 rounded-full" style={{ background: INST_COLOR[p.b as "IISERB"] }} />{INST_SHORT[p.b as "IISERB"]}
                    </span>
                    <span className="text-[20px] font-bold">{fmt(p.ruzicka, 2)}</span>
                  </div>
                  <div className="mt-1.5 h-1.5 rounded-full bg-white/[0.05]"><div className="h-1.5 rounded-full bg-plum-300" style={{ width: `${p.ruzicka * 100}%` }} /></div>
                  <div className="mt-1 text-[12px] text-ink-muted">top-50 topic Jaccard {fmt(p.jaccard, 2)}</div>
                </li>
              ))}
            </ul>
          ) : <Loading h={200} />}
          <Note>Similar portfolios plus few joint papers would mean untapped collaboration potential; see the Collaboration page.</Note>
        </Card>
      </div>
    </div>
  );
}
