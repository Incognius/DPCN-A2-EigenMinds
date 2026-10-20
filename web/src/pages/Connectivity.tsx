import { useEffect, useState } from "react";
import * as echarts from "echarts";
import Chart from "../components/Chart";
import { Badge, Card, CardHead, Loading, Note, Pills, Stat } from "../components/ui";
import { loadJSON, useData } from "../lib/data";
import { fmt, pct } from "../lib/format";
import { useStore } from "../lib/store";
import { INK, INST_COLOR, INST_ORDER, INST_SHORT, axisX, axisY } from "../lib/theme";
import type { Connections, InstKey, Meta, Partner } from "../lib/types";

const YEARS = Array.from({ length: 11 }, (_, i) => String(2016 + i));
const CLUSTER_ORDER = ["University", "IIT", "DST/DBT Autonomous", "DAE", "CSIR", "IISER", "Govt S&T", "NIT", "IISc", "Agricultural", "Medical", "IIIT", "IIM/Other national", "Industry", "Other"];

export default function Connectivity() {
  const { scope } = useStore();
  const { data } = useData<Connections>("connections.json");
  const { data: meta } = useData<Meta>("meta.json");
  const [local, setLocal] = useState<InstKey>("IISERB");
  const [mapReady, setMapReady] = useState(false);
  const k: InstKey = scope === "ALL" ? local : scope;

  useEffect(() => {
    loadJSON<object>("india.json").then((geo) => { echarts.registerMap("india", geo as never); setMapReady(true); }).catch(() => setMapReady(false));
  }, []);

  if (!data || !meta) return <Loading h={700} />;
  const c = data[k];
  const home = meta.institutes.find((i) => i.key === k)!;
  const partners = c.top_partners.filter((p) => p.lat != null && p.lon != null) as (Partner & { lat: number; lon: number })[];
  const maxShared = Math.max(...partners.map((p) => p.shared_papers), 1);
  const clusters = CLUSTER_ORDER.filter((cl) => (c.by_cluster[cl] ?? 0) > 0);

  return (
    <div className="flex flex-col gap-5">
      {scope === "ALL" && (
        <div className="flex items-center gap-3 text-[13px] text-ink-muted">Showing
          <Pills small value={local} onChange={setLocal} options={INST_ORDER.map((i) => ({ value: i, label: INST_SHORT[i] }))} />
        </div>
      )}
      <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
        {INST_ORDER.map((i) => (
          <Card key={i} className={i === k ? "!border-white/20" : ""}>
            <div className="mb-3 flex items-center gap-2 text-[14px] font-semibold"><span className="h-2.5 w-2.5 rounded-full" style={{ background: INST_COLOR[i] }} />IISER {INST_SHORT[i]}</div>
            <div className="grid grid-cols-3 gap-3">
              <Stat label="Cites in" value={fmt(data[i].citations_in)} />
              <Stat label="Cites out" value={fmt(data[i].citations_out)} />
              <Stat label="In / out" value={fmt(data[i].impact_ratio, 2)} accent={(data[i].impact_ratio ?? 0) >= 1 ? "#4ade80" : undefined} />
            </div>
            <div className="mt-3 text-[12px] text-ink-muted">{fmt(data[i].partners)} co-author partner institutes · cited by {fmt(data[i].citing_institutes)} Indian institutes</div>
          </Card>
        ))}
      </div>
      <Note>Citations "in" = (citing paper, cited paper) pairs where the citing paper has an author at another Indian institute; "out" = references from our papers to papers with another Indian institute. A ratio above 1 means the institute is cited by Indian science more than it cites it.</Note>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-5">
        <Card className="xl:col-span-3">
          <CardHead title={`Partner map · IISER ${INST_SHORT[k]}`} sub="Top co-author partner institutes in India · bubble = shared papers" />
          {mapReady ? (
            <Chart height={470} option={{
              tooltip: { trigger: "item", formatter: (p: unknown) => { const d = (p as { data: { name: string; value: number[] } }).data; return d ? `${d.name}<br/><b>${d.value[2]}</b> shared papers` : ""; } },
              geo: { map: "india", roam: true, zoom: 1.15, center: [80, 22], itemStyle: { areaColor: "#1a1319", borderColor: "rgba(255,255,255,0.14)" },
                emphasis: { disabled: true }, label: { show: false } },
              series: [
                { type: "lines", coordinateSystem: "geo", zlevel: 1, silent: true,
                  lineStyle: { color: INST_COLOR[k], width: 1, opacity: 0.35, curveness: 0.25 },
                  data: partners.map((p) => ({ coords: [[home.lon, home.lat], [p.lon, p.lat]] })) },
                { type: "scatter", coordinateSystem: "geo", zlevel: 2,
                  symbolSize: (v: number[]) => 6 + 26 * Math.sqrt(v[2] / maxShared),
                  itemStyle: { color: "#d79bc7", borderColor: "#141114", borderWidth: 1.5, opacity: 0.9 },
                  data: partners.map((p) => ({ name: p.partner_inst, value: [p.lon, p.lat, p.shared_papers] })) },
                { type: "effectScatter", coordinateSystem: "geo", zlevel: 3, symbolSize: 14, rippleEffect: { scale: 3, brushType: "stroke" },
                  itemStyle: { color: INST_COLOR[k] }, data: [{ name: `IISER ${INST_SHORT[k]}`, value: [home.lon, home.lat, 0] }] },
              ],
            }} />
          ) : <Loading h={470} />}
        </Card>
        <div className="flex flex-col gap-5 xl:col-span-2">
          <Card>
            <CardHead title="Year-wise citation flow" sub="Citing / cited papers per publication year" />
            <Chart height={220} option={{
              legend: { top: 0, right: 0 }, grid: { top: 34 }, tooltip: { trigger: "axis" },
              xAxis: axisX({ type: "category", data: YEARS }),
              yAxis: axisY({ type: "value" }),
              series: [
                { name: "In (cited by India)", type: "line", smooth: true, data: YEARS.map((y) => c.in_by_year[y] ?? 0), lineStyle: { width: 2, color: "#d79bc7" }, itemStyle: { color: "#d79bc7" }, symbolSize: 6 },
                { name: "Out (citing India)", type: "line", smooth: true, data: YEARS.map((y) => c.out_by_year[y] ?? 0), lineStyle: { width: 2, color: "#3a93d6" }, itemStyle: { color: "#3a93d6" }, symbolSize: 6 },
              ],
            }} />
          </Card>
          <Card>
            <CardHead title="Partners by cluster" sub="Shared papers with each kind of institute" />
            <Chart height={Math.max(210, 22 * clusters.length + 30)} option={{
              tooltip: { trigger: "axis", axisPointer: { type: "shadow" } }, grid: { left: 8, right: 30, top: 4 },
              yAxis: axisX({ type: "category", data: [...clusters].reverse(), axisLabel: { color: INK.text2, interval: 0 } }),
              xAxis: axisY({ type: "value" }),
              series: [{ type: "bar", data: [...clusters].reverse().map((cl) => c.by_cluster[cl]), barWidth: 12,
                itemStyle: { color: "#c27fb2", borderRadius: [0, 4, 4, 0] }, label: { show: true, position: "right", color: INK.text2, fontSize: 11 } }],
            }} />
          </Card>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-5">
        <Card className="xl:col-span-2">
          <CardHead title="Top 10 Indian institutes citing us" sub={`IISER ${INST_SHORT[k]} · citing-cited pairs`} />
          <Chart height={360} option={{
            tooltip: { trigger: "axis", axisPointer: { type: "shadow" } }, grid: { left: 8, right: 40, top: 4 },
            yAxis: axisX({ type: "category", data: c.top_citing.map((t) => t.partner_inst).reverse(), axisLabel: { color: INK.text2, width: 200, overflow: "truncate", interval: 0 } }),
            xAxis: axisY({ type: "value" }),
            series: [{ type: "bar", barWidth: 14, data: c.top_citing.map((t) => t.citations_in).reverse(),
              itemStyle: { color: INST_COLOR[k], borderRadius: [0, 4, 4, 0] }, label: { show: true, position: "right", color: INK.text2, fontSize: 11 } }],
          }} />
        </Card>
        <Card className="xl:col-span-3">
          <CardHead title="Co-authorship partners" sub="Ranked by shared papers · topic overlap vs this IISER"
            info="Jaccard = overlap of the two institutes' top-50 OpenAlex topics (2016–26). Subfield overlap = weighted Jaccard of their subfield mix. Cross-cluster links (e.g. IISER ↔ IIT, IISER ↔ CSIR) are flagged by cluster." />
          <div className="scroll-thin max-h-[380px] overflow-auto rounded-2xl border border-white/[0.05]">
            <table className="dt w-full">
              <thead><tr><th>Institute</th><th>Cluster</th><th>Shared</th><th>In</th><th>Out</th><th>Jaccard</th><th>Subfield</th></tr></thead>
              <tbody>
                {c.top_partners.map((p) => (
                  <tr key={p.partner_inst}>
                    <td className="max-w-[260px] truncate text-ink" title={p.partner_inst}>{p.partner_inst}</td>
                    <td><Badge tone={p.partner_cluster === "IISER" ? "muted" : "plum"}>{p.partner_cluster}</Badge></td>
                    <td className="font-semibold text-ink">{p.shared_papers}</td>
                    <td>{fmt(p.citations_in)}</td><td>{fmt(p.citations_out)}</td>
                    <td>{fmt(p.topic_jaccard, 2)}</td><td>{pct(p.subfield_overlap, 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </div>
  );
}
