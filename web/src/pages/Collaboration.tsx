import { useMemo, useState } from "react";
import { Check } from "lucide-react";
import Chart from "../components/Chart";
import GraphView, { type GEdge, type GNode } from "../components/GraphView";
import { Card, CardHead, Loading, Note, Pills, Stat } from "../components/ui";
import { useData } from "../lib/data";
import { fmt, pct } from "../lib/format";
import { useStore } from "../lib/store";
import { CAT, INK, INST_COLOR, INST_ORDER, INST_SHORT, OTHER, axisX, axisY } from "../lib/theme";
import type { CoauthorGraph, CoauthorStats, Ranked } from "../lib/types";

type ColorBy = "community" | "inst" | "dept";

export default function Collaboration() {
  const { scope, openFaculty } = useStore();
  const { data: g } = useData<CoauthorGraph>("coauthor_graph.json");
  const { data: st } = useData<CoauthorStats>("coauthor.json");
  const [colorBy, setColorBy] = useState<ColorBy>("community");
  const [rank, setRank] = useState<"degree" | "betweenness" | "eigenvector">("betweenness");

  // communities ranked by size; the 6 largest get validated categorical slots, the rest fold to grey
  const commColor = useMemo(() => {
    const m = new Map<number, string>();
    st?.communities.slice(0, 6).forEach((c, i) => m.set(c.community, CAT[i]));
    return m;
  }, [st]);
  const deptColor = useMemo(() => {
    const counts = new Map<string, number>();
    g?.nodes.forEach((n) => counts.set(n.dept, (counts.get(n.dept) ?? 0) + 1));
    const top = [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 6).map(([d]) => d);
    return new Map(top.map((d, i) => [d, CAT[i]]));
  }, [g]);

  const { nodes, edges } = useMemo(() => {
    if (!g) return { nodes: [] as GNode[], edges: [] as GEdge[] };
    const maxS = Math.max(...g.nodes.map((n) => n.strength));
    const nodes: GNode[] = g.nodes.map((n) => ({
      id: n.id, x: n.x, y: n.y, label: n.name, size: 3 + 13 * Math.sqrt(n.strength / maxS),
      color: colorBy === "inst" ? INST_COLOR[n.inst] : colorBy === "community" ? commColor.get(n.community) ?? OTHER : deptColor.get(n.dept) ?? OTHER,
      muted: scope !== "ALL" && n.inst !== scope,
    }));
    const edges: GEdge[] = g.edges.map(([s, t, w, cross]) => ({
      s, t, size: Math.min(0.5 + w * 0.35, 4), color: cross ? "rgba(255,214,150,0.55)" : "rgba(210,170,200,0.16)",
    }));
    return { nodes, edges };
  }, [g, colorBy, scope, commColor, deptColor]);

  if (!g || !st) return <Loading h={700} />;
  const ranked: Ranked[] = { degree: st.top_degree, betweenness: st.top_betweenness, eigenvector: st.top_eigenvector }[rank];
  const legend = colorBy === "inst"
    ? INST_ORDER.map((k) => [INST_SHORT[k], INST_COLOR[k]] as const)
    : colorBy === "community"
      ? st.communities.slice(0, 6).map((c, i) => [`#${c.community + 1} · ${c.top_groups[0][0].split(" · ")[1]}`, CAT[i]] as const)
      : [...deptColor.entries()].map(([d, c]) => [d, c] as const);
  const lp = st.link_prediction;
  const sw = st.small_world;

  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-2 gap-5 md:grid-cols-3 xl:grid-cols-6">
        <Card><Stat label="Connected faculty" value={`${st.connected}/${st.nodes}`} sub={`${st.isolates} with no co-faculty paper`} /></Card>
        <Card><Stat label="Co-authorship ties" value={fmt(st.edges)} sub={`mean degree ${fmt(st.mean_degree, 1)}`} /></Card>
        <Card><Stat label="Leiden communities" value={st.leiden_communities} sub={`modularity Q = ${fmt(st.leiden_modularity, 2)}`} /></Card>
        <Card><Stat label="Community ≈ department?" value={`NMI ${fmt(st.nmi_department, 2)}`} sub={`ARI ${fmt(st.ari_department, 2)}`} /></Card>
        <Card><Stat label="Small-world σ" value={fmt(sw.sigma, 1)} sub={sw.sigma_p05 != null ? `90% of nulls: ${fmt(sw.sigma_p05, 1)}–${fmt(sw.sigma_p95, 1)}` : `C ${fmt(sw.C, 2)} vs ${fmt(sw.C_null, 2)} null`} /></Card>
        <Card><Stat label="Cross-IISER ties" value={st.cross_institute_edges} sub="faculty pairs across institutes" /></Card>
      </div>

      <Card>
        <CardHead title="Faculty collaboration network" sub={`Nodes = faculty, edges = joint papers (≤ 50 authors) · size = weighted degree · gold edges cross institutes`}
          right={<Pills small value={colorBy} onChange={setColorBy} options={[{ value: "community", label: "Communities" }, { value: "dept", label: "Departments" }, { value: "inst", label: "Institutes" }]} />} />
        <div className="relative">
          <GraphView nodes={nodes} edges={edges} height={620} onNode={(id) => openFaculty(id)} />
          <div className="pointer-events-none absolute left-3 top-3 flex max-w-[75%] flex-wrap gap-x-3 gap-y-1 rounded-2xl border border-white/10 bg-[#120d11]/85 px-3 py-2 text-[12px] text-ink-2">
            {legend.map(([l, c]) => <span key={l} className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full" style={{ background: c }} />{l}</span>)}
            {colorBy !== "inst" && <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full" style={{ background: OTHER }} />other</span>}
          </div>
        </div>
        <Note>Department-community agreement (NMI {fmt(st.nmi_department, 2)}, department assortativity {fmt(st.assortativity_department, 2)}) shows how strongly collaboration follows department lines. {st.with_hyperauthored.edges === st.edges
            ? "Papers with more than 50 authors add no extra ties here: no two of these faculty share one, so the cap changes nothing for this graph."
            : `With hyper-authored papers included the graph would have ${fmt(st.with_hyperauthored.edges)} ties instead of ${fmt(st.edges)}.`}</Note>
      </Card>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        <Card>
          <CardHead title="Central faculty" sub="Click a name for the profile"
            info="Degree = number of co-faculty. Betweenness = how often a person lies on shortest paths between others (weighted by 1/joint papers), i.e. brokers between groups. Eigenvector = connected to well-connected people."
            right={<Pills small value={rank} onChange={setRank} options={[{ value: "betweenness", label: "Bridge" }, { value: "degree", label: "Degree" }, { value: "eigenvector", label: "Eigen" }]} />} />
          <ol className="flex flex-col divide-y divide-white/[0.05]">
            {ranked.map((r, i) => (
              <li key={r.name + r.inst}>
                <button className="flex w-full items-center gap-3 py-2 text-left" onClick={() => openFaculty(`${r.inst}|${r.name}`)}>
                  <span className="w-4 text-right text-[12px] text-ink-faint">{i + 1}</span>
                  <span className="min-w-0 flex-1"><span className="block truncate text-[14px]">{r.name}</span>
                    <span className="block truncate text-[12px] text-ink-muted">{r.dept} · <span style={{ color: INST_COLOR[r.inst] }}>{INST_SHORT[r.inst]}</span></span></span>
                  <span className="text-[13px] font-semibold">{rank === "degree" ? r.value : fmt(r.value, 3)}</span>
                </button>
              </li>
            ))}
          </ol>
        </Card>
        <Card>
          <CardHead title="Communities" sub="Leiden, largest first: dominant department and purity" />
          <ul className="flex flex-col gap-3">
            {st.communities.slice(0, 8).map((c, i) => (
              <li key={c.community} className="rounded-xl border border-white/[0.05] bg-white/[0.015] p-3">
                <div className="flex items-center justify-between text-[13.5px]">
                  <span className="flex items-center gap-2"><span className="h-2.5 w-2.5 rounded-full" style={{ background: CAT[i] ?? OTHER }} />#{c.community + 1} · {c.size} faculty</span>
                  <span className="text-ink-muted">purity {pct(c.purity, 0)}</span>
                </div>
                <div className="mt-1 truncate text-[12px] text-ink-muted">{c.top_groups.map(([n, k]) => `${n} (${k})`).join(" · ")}</div>
              </li>
            ))}
          </ul>
        </Card>
        <Card>
          <CardHead title="Structure tests" sub="Against randomised (configuration-model) networks" />
          <ul className="flex flex-col gap-3 text-[13.5px]">
            <li className="flex justify-between"><span className="text-ink-2">Clustering C / C<sub>null</sub></span><b>{fmt(sw.C, 3)} / {fmt(sw.C_null, 3)}</b></li>
            <li className="flex justify-between"><span className="text-ink-2">Path length L / L<sub>null</sub></span><b>{fmt(sw.L, 2)} / {fmt(sw.L_null, 2)}</b></li>
            <li className="flex justify-between"><span className="text-ink-2">Small-world σ</span><b>{fmt(sw.sigma, 2)}</b></li>
            <li className="flex justify-between"><span className="text-ink-2">Degree assortativity</span><b>{fmt(st.degree_assortativity, 3)}</b></li>
            <li className="flex justify-between"><span className="text-ink-2">Institute assortativity</span><b>{fmt(st.assortativity_institute, 3)}</b></li>
            <li className="flex justify-between"><span className="text-ink-2">Louvain Q (check)</span><b>{fmt(st.louvain_modularity, 3)}</b></li>
            <li className="flex justify-between"><span className="text-ink-2">Max k-core</span><b>{st.max_kcore}</b></li>
          </ul>
          <Note>σ &gt; 1: far more clustered than chance at similar path lengths, i.e. tight research groups joined by a few long-range ties.</Note>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <Card>
          <CardHead title="How the network grew" sub="Cumulative faculty network at the end of each year" />
          <Chart height={280} option={{
            legend: { top: 0, right: 0 }, grid: { top: 36 },
            tooltip: { trigger: "axis" },
            xAxis: axisX({ type: "category", data: st.temporal.map((t) => String(t.year)) }),
            yAxis: [axisY({ type: "value", name: "", min: 0, max: 1, axisLabel: { formatter: (v: number) => `${Math.round(v * 100)}%` } })],
            series: [
              { name: "Giant component share", type: "line", smooth: true, data: st.temporal.map((t) => +t.giant_share.toFixed(3)), lineStyle: { width: 2, color: "#d79bc7" }, itemStyle: { color: "#d79bc7" }, symbolSize: 7 },
              { name: "Modularity", type: "line", smooth: true, data: st.temporal.map((t) => +t.modularity.toFixed(3)), lineStyle: { width: 2, color: "#3a93d6" }, itemStyle: { color: "#3a93d6" }, symbolSize: 7 },
            ],
          }} />
          <Note>Both on a 0–1 scale. A rising giant component with steady modularity means the network is joining up while groups keep their identity.</Note>
        </Card>
        <Card>
          <CardHead title="Predicting new collaborations" sub={`Trained on ties up to ${lp.split_year}, tested on ${lp.positives} pairs that first co-authored afterwards`}
            info="Each unconnected pair of active faculty is scored by a link-prediction index computed on the pre-split network; AUC is the chance a future pair outranks a pair that never collaborates." />
          <Chart height={180} option={{
            grid: { left: 8, right: 30, top: 4, bottom: 4 },
            tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
            yAxis: axisX({ type: "category", data: Object.keys(lp.auc).map((k) => k.replace(/_/g, " ")), axisLabel: { color: INK.text2 } }),
            xAxis: axisY({ type: "value", min: 0.5, max: 1 }),
            series: [{ type: "bar", data: Object.values(lp.auc).map((v) => +(v ?? 0).toFixed(3)), barWidth: 14,
              itemStyle: { color: "#c27fb2", borderRadius: [0, 4, 4, 0] }, label: { show: true, position: "right", color: INK.text2, fontSize: 11 } }],
          }} />
          <div className="mt-3 stat-label">Top predicted pairs (Adamic–Adar)</div>
          <ul className="mt-1 grid grid-cols-1 gap-x-4 sm:grid-cols-2">
            {lp.top_predictions.slice(0, 8).map((p) => (
              <li key={p.a + p.b} className="flex items-center justify-between gap-2 border-b border-white/[0.04] py-1.5 text-[12.5px]">
                <span className="truncate text-ink-2">{p.a} – {p.b}</span>
                {p.realised ? <span className="flex items-center gap-1 text-pos"><Check size={12} />happened</span> : <span className="text-ink-faint">{fmt(p.score, 2)}</span>}
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card>
        <CardHead title="Bridges between groups" sub="Faculty whose co-faculty span the most other departments" />
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {st.bridges.slice(0, 8).map((b) => (
            <button key={b.name + b.inst} onClick={() => openFaculty(`${b.inst}|${b.name}`)}
              className="rounded-[16px] border border-white/[0.06] bg-[#0f0b0e] p-3 text-left transition hover:border-white/20">
              <div className="truncate text-[14px] font-medium">{b.name}</div>
              <div className="truncate text-[12px] text-ink-muted">{b.dept} · <span style={{ color: INST_COLOR[b.inst] }}>{INST_SHORT[b.inst]}</span></div>
              <div className="mt-2 text-[12px] text-ink-2">links into <b>{b.other_depts}</b> other dept{b.other_depts === 1 ? "" : "s"}{b.other_insts ? <> · <b>{b.other_insts}</b> other IISER</> : null}</div>
            </button>
          ))}
        </div>
      </Card>
    </div>
  );
}
