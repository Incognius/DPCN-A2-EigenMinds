import { useMemo, useState } from "react";
import { ExternalLink, X } from "lucide-react";
import Chart from "../components/Chart";
import GraphView, { type GEdge, type GNode } from "../components/GraphView";
import { Badge, Card, CardHead, Loading, Note, Pills, Stat } from "../components/ui";
import { useData } from "../lib/data";
import { fmt, pct, pval } from "../lib/format";
import { useStore } from "../lib/store";
import { INK, INST_COLOR, INST_ORDER, INST_SHORT, axisX, axisY } from "../lib/theme";
import type { CitationGraph, CitationStats, PaperCard } from "../lib/types";

// sequential plum ramp for publication year (light = old, saturated = recent)
const yearColor = (y: number) => {
  const t = Math.min(Math.max((y - 2016) / 10, 0), 1);
  const a = [0x4a, 0x2a, 0x45], b = [0xf0, 0xb8, 0xe0];
  return `rgb(${a.map((v, i) => Math.round(v + (b[i] - v) * t)).join(",")})`;
};

export default function CitationNet() {
  const { scope } = useStore();
  const { data: g } = useData<CitationGraph>("citation_graph.json");
  const { data: st } = useData<CitationStats>("citation.json");
  const [color, setColor] = useState<"inst" | "year">("inst");
  const [hyper, setHyper] = useState<"show" | "hide">("show");
  const [prMode, setPrMode] = useState<"all" | "core">("all");
  const [sel, setSel] = useState<string | null>(null);

  const { nodes, edges } = useMemo(() => {
    if (!g) return { nodes: [] as GNode[], edges: [] as GEdge[] };
    const keep = g.nodes.filter((n) => hyper === "show" || !n.h);
    const maxPr = Math.max(...keep.map((n) => n.pr));
    const nodes: GNode[] = keep.map((n) => ({
      id: n.id, x: n.x, y: n.y, label: n.t.length > 60 ? n.t.slice(0, 58) + "…" : n.t,
      size: 1.2 + 8 * Math.sqrt(n.pr / maxPr),
      color: color === "inst" ? INST_COLOR[n.inst] ?? "#888" : yearColor(n.year),
      muted: scope !== "ALL" && n.inst !== scope,
    }));
    const ids = new Set(nodes.map((n) => n.id));
    return { nodes, edges: g.edges.filter(([a, b]) => ids.has(a) && ids.has(b)).map(([s, t]) => ({ s, t })) };
  }, [g, color, hyper, scope]);

  if (!g || !st) return <Loading h={700} />;
  const node = sel ? g.nodes.find((n) => n.id === sel) : null;
  const pr: PaperCard[] = prMode === "all" ? st.pagerank_top : st.pagerank_top_excl_hyper;
  const indeg = Object.entries(st.indegree_dist).filter(([k]) => +k > 0).map(([k, v]) => [+k, v]);
  const flowMax = Math.max(...INST_ORDER.flatMap((a) => INST_ORDER.map((b) => st.flow_matrix[a]?.[b] ?? 0)));

  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-2 gap-5 md:grid-cols-3 xl:grid-cols-6">
        <Card><Stat label="Papers (nodes)" value={fmt(st.nodes)} sub={`${fmt(st.isolated)} not linked internally`} /></Card>
        <Card><Stat label="Citations (edges)" value={fmt(st.edges)} sub="paper → paper, inside the 3 IISERs" /></Card>
        <Card><Stat label="Giant component" value={pct(st.giant_wcc_share, 0)} sub={`${fmt(st.wcc_count)} weak components`} /></Card>
        <Card><Stat label="Self-institute share" value={pct(st.self_citation_share, 0)} sub="edges within one IISER" /></Card>
        <Card><Stat label="Median citation lag" value={`${fmt(st.median_lag, 0)} yr`} sub="citing − cited year" /></Card>
        <Card><Stat label="Best tail fit" value={st.powerlaw.vs_lognormal_R < 0 && st.powerlaw.vs_lognormal_p < 0.1 ? "log-normal" : "power law"} sub={`vs power law: R = ${fmt(st.powerlaw.vs_lognormal_R, 1)}`} /></Card>
      </div>

      <Card>
        <CardHead title="Citation graph" sub={`${fmt(nodes.length)} papers with at least one internal citation · size = PageRank · hover to trace, click for details`}
          right={<div className="flex flex-wrap gap-2">
            <Pills small value={color} onChange={setColor} options={[{ value: "inst", label: "By institute" }, { value: "year", label: "By year" }]} />
            <Pills small value={hyper} onChange={setHyper} options={[{ value: "show", label: "All papers" }, { value: "hide", label: "Hide >50 authors" }]} />
          </div>} />
        <div className="relative">
          <GraphView nodes={nodes} edges={edges} directed onNode={setSel} height={600} edgeColor="rgba(210,170,200,0.08)" labelThreshold={16} />
          <div className="pointer-events-none absolute left-3 top-3 flex flex-wrap gap-3 rounded-full border border-white/10 bg-[#120d11]/85 px-3 py-1.5 text-[12px] text-ink-2">
            {color === "inst" ? INST_ORDER.map((k) => <span key={k} className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full" style={{ background: INST_COLOR[k] }} />{INST_SHORT[k]}</span>)
              : <span className="flex items-center gap-2">2016 <span className="h-2 w-24 rounded-full" style={{ background: `linear-gradient(90deg, ${yearColor(2016)}, ${yearColor(2026)})` }} /> 2026</span>}
          </div>
          {node && (
            <div className="absolute bottom-3 right-3 w-[min(380px,calc(100%-24px))] rounded-2xl border border-white/10 bg-[#120d11]/95 p-4 shadow-2xl">
              <div className="flex items-start justify-between gap-2">
                <a href={node.doi ?? `https://openalex.org/${node.id}`} target="_blank" rel="noreferrer" className="text-[14px] font-semibold leading-snug hover:text-plum-200">{node.t} <ExternalLink size={11} className="inline" /></a>
                <button onClick={() => setSel(null)} aria-label="Close" className="text-ink-muted hover:text-white"><X size={15} /></button>
              </div>
              <div className="mt-1 text-[12px] text-ink-muted">{node.j} · {node.year} · <span style={{ color: INST_COLOR[node.inst] }}>{INST_SHORT[node.inst]}</span></div>
              <div className="mt-3 grid grid-cols-3 gap-2">
                <Stat label="Cited (all)" value={fmt(node.c)} />
                <Stat label="Internal in" value={node.indeg} />
                <Stat label="PageRank" value={fmt(node.pr, 2)} sub="× 10⁻⁴" />
              </div>
              {node.h && <div className="mt-2"><Badge tone="muted">large collaboration</Badge></div>}
            </div>
          )}
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <Card>
          <CardHead title="Most influential papers" sub="PageRank on the internal citation graph (α = 0.85)"
            info="PageRank rewards papers cited by papers that are themselves well cited inside the three IISERs, unlike raw citation counts which come mostly from outside."
            right={<Pills small value={prMode} onChange={setPrMode} options={[{ value: "all", label: "All" }, { value: "core", label: "≤ 50 authors" }]} />} />
          <ol className="flex flex-col divide-y divide-white/[0.05]">
            {pr.map((p, i) => (
              <li key={p.work_id} className="flex items-start gap-3 py-2.5">
                <span className="w-5 shrink-0 text-right text-[13px] font-semibold text-ink-faint">{i + 1}</span>
                <div className="min-w-0 flex-1">
                  <a href={p.doi ?? `https://openalex.org/${p.work_id}`} target="_blank" rel="noreferrer" className="block text-[13.5px] leading-snug text-ink hover:text-plum-200">{p.title}</a>
                  <div className="mt-0.5 flex flex-wrap gap-x-2 text-[12px] text-ink-muted">
                    <span>{p.journal} · {p.year}</span>
                    {(p.inst ?? []).map((k) => <span key={k} style={{ color: INST_COLOR[k] }}>{INST_SHORT[k]}</span>)}
                  </div>
                </div>
                <span className="shrink-0 text-right text-[12px] text-ink-muted"><span className="block text-[14px] font-semibold text-ink">{p.internal_in}</span>internal</span>
              </li>
            ))}
          </ol>
        </Card>
        <div className="flex flex-col gap-5">
          <Card>
            <CardHead title="In-degree distribution" sub="How many internal citations each paper receives (log–log)" />
            <Chart height={230} option={{
              tooltip: { trigger: "item", formatter: (p: unknown) => { const v = (p as { value: number[] }).value; return `${v[1]} papers cited ${v[0]}× internally`; } },
              xAxis: axisY({ type: "log", name: "internal citations", nameLocation: "middle", nameGap: 26, nameTextStyle: { color: INK.faint }, splitLine: { show: false } }),
              yAxis: axisY({ type: "log", name: "papers", nameTextStyle: { color: INK.faint } }),
              series: [{ type: "scatter", data: indeg, symbolSize: 8, itemStyle: { color: "#d79bc7", borderColor: "#141114", borderWidth: 1.5 } }],
            }} />
            <Note>
              Heavy-tailed, but {st.powerlaw.vs_lognormal_R < 0 && st.powerlaw.vs_lognormal_p < 0.1
                ? <>a <b>log-normal</b> fits significantly better than a power law (likelihood ratio R = {fmt(st.powerlaw.vs_lognormal_R, 2)}, {pval(st.powerlaw.vs_lognormal_p)}), the signature of cumulative advantage with ageing rather than pure preferential attachment.</>
                : <>a power law (α = {fmt(st.powerlaw.alpha, 2)}, x<sub>min</sub> = {fmt(st.powerlaw.xmin, 0)}) cannot be rejected against a log-normal (R = {fmt(st.powerlaw.vs_lognormal_R, 2)}, {pval(st.powerlaw.vs_lognormal_p)}).</>}
              {" "}Power-law fit for reference: α = {fmt(st.powerlaw.alpha, 2)} above x<sub>min</sub> = {fmt(st.powerlaw.xmin, 0)}.
            </Note>
          </Card>
          <div className="grid grid-cols-1 gap-5 md:grid-cols-2">
            <Card>
              <CardHead title="IISER → IISER flow" sub="row cites column" />
              <Chart height={220} option={{
                tooltip: { formatter: (p: unknown) => { const v = (p as { value: number[] }).value; return `${INST_SHORT[INST_ORDER[v[1]]]} cites ${INST_SHORT[INST_ORDER[v[0]]]}: <b>${fmt(v[2])}</b>`; } },
                grid: { left: 8, right: 8, top: 8, bottom: 8, containLabel: true },
                xAxis: axisX({ type: "category", data: INST_ORDER.map((k) => INST_SHORT[k]) }),
                yAxis: axisX({ type: "category", data: INST_ORDER.map((k) => INST_SHORT[k]), inverse: true }),
                visualMap: { show: false, min: 0, max: flowMax, inRange: { color: ["#24161f", "#d79bc7"] } },
                series: [{ type: "heatmap", data: INST_ORDER.flatMap((a, i) => INST_ORDER.map((b, j) => [j, i, st.flow_matrix[a]?.[b] ?? 0])),
                  label: { show: true, color: "#fff", fontSize: 12, formatter: (p: unknown) => fmt((p as { value: number[] }).value[2]) },
                  itemStyle: { borderColor: "#141114", borderWidth: 3, borderRadius: 6 } }],
              }} />
            </Card>
            <Card>
              <CardHead title="Citation lag" sub="years between cited and citing paper" />
              <Chart height={220} option={{
                tooltip: { trigger: "axis" }, grid: { top: 10 },
                xAxis: axisX({ type: "category", data: Object.keys(st.lag_hist).filter((k) => +k >= 0) }),
                yAxis: axisY({ type: "value" }),
                series: [{ type: "bar", data: Object.entries(st.lag_hist).filter(([k]) => +k >= 0).map(([, v]) => v), barWidth: "60%", itemStyle: { color: "#c27fb2", borderRadius: [4, 4, 0, 0] } }],
              }} />
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
