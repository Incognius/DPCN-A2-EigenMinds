import { useState } from "react";
import { ExternalLink } from "lucide-react";
import Chart from "../components/Chart";
import { Badge, Card, CardHead, Loading, Note, Pills } from "../components/ui";
import { useData } from "../lib/data";
import { fmt, pct } from "../lib/format";
import { useStore } from "../lib/store";
import { CORE_COLOR, INST_COLOR, INST_ORDER, INST_SHORT, QUARTILE, axisX, axisY, scopeLabel } from "../lib/theme";
import type { Institutes, PaperCard } from "../lib/types";

const QS = ["Q1", "Q2", "Q3", "Q4"] as const;
const YEARS = Array.from({ length: 11 }, (_, i) => String(2016 + i));

export default function Journals() {
  const { scope } = useStore();
  const { data } = useData<Institutes>("institutes.json");
  const [mode, setMode] = useState<"share" | "count">("share");
  const [excl, setExcl] = useState<"all" | "core">("all");
  if (!data) return <Loading h={600} />;
  const s = data.institutes[scope];
  const qTot = QS.reduce((a, q) => a + s.quartiles[q], 0);
  const byYear = (q: (typeof QS)[number]) => YEARS.map((y) => {
    const r = s.q_by_year[y] ?? {};
    const tot = QS.reduce((a, k) => a + (r[k] ?? 0), 0);
    return mode === "share" ? (tot ? +(100 * (r[q] ?? 0) / tot).toFixed(1) : 0) : (r[q] ?? 0);
  });
  const coreKeys = ["A*", "A", "B", "C", "Unranked"].filter((k) => (s.core[k] ?? 0) > 0);
  const top: PaperCard[] = excl === "all" ? s.top_cited : s.top_cited_excl_hyper;

  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        <Card>
          <CardHead title="Journal quartiles" sub={`${scopeLabel(scope)} · SCImago best quartile, matched on ISSN and year`} />
          <Chart height={270} option={{
            tooltip: { trigger: "item", formatter: "{b}: {c} papers ({d}%)" },
            legend: { bottom: 0, left: "center" },
            series: [{
              type: "pie", radius: ["58%", "82%"], center: ["50%", "44%"], padAngle: 1.5,
              itemStyle: { borderRadius: 6, borderColor: "#141114", borderWidth: 2 },
              label: { show: true, position: "center", formatter: () => `{a|${pct(s.q1_share, 0)}}\n{b|in Q1}`,
                rich: { a: { fontSize: 30, fontWeight: 700, color: "#f4eef3" }, b: { fontSize: 12, color: "#a39aa1", padding: [4, 0, 0, 0] } } },
              labelLine: { show: false },
              data: QS.map((q) => ({ name: q, value: s.quartiles[q], itemStyle: { color: QUARTILE[q] } })),
            }],
          }} />
          <Note>{fmt(qTot)} of {fmt(s.journal_papers)} journal papers have a quartile ({pct(s.quartile_coverage, 0)} coverage).</Note>
        </Card>
        <Card className="xl:col-span-2">
          <CardHead title="Quartile mix over time" sub="Is the share of Q1 papers rising?"
            right={<Pills small value={mode} onChange={setMode} options={[{ value: "share", label: "Share" }, { value: "count", label: "Count" }]} />} />
          <Chart height={300} option={{
            legend: { top: 0, right: 0 }, grid: { top: 36 },
            tooltip: { trigger: "axis", valueFormatter: (v) => (mode === "share" ? `${v}%` : String(v)) },
            xAxis: axisX({ type: "category", data: YEARS }),
            yAxis: axisY({ type: "value", max: mode === "share" ? 100 : undefined }),
            series: QS.map((q) => ({ name: q, type: "bar" as const, stack: "q", data: byYear(q), barWidth: "58%",
              itemStyle: { color: QUARTILE[q], borderColor: "#141114", borderWidth: 1.5, borderRadius: q === "Q4" ? [4, 4, 0, 0] : 0 } })),
          }} />
        </Card>
      </div>

      <Card>
        <CardHead title="Top 5 journals per institute" sub="By number of unique affiliated papers" />
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          {INST_ORDER.map((k) => (
            <div key={k} className="rounded-[18px] border border-white/[0.06] bg-[#0f0b0e] p-4">
              <div className="mb-3 flex items-center gap-2 text-[14px] font-semibold"><span className="h-2.5 w-2.5 rounded-full" style={{ background: INST_COLOR[k] }} />IISER {INST_SHORT[k]}</div>
              <ol className="flex flex-col gap-2.5">
                {data.institutes[k].top_journals.slice(0, 5).map((j, i) => {
                  const max = data.institutes[k].top_journals[0].papers;
                  return (
                    <li key={j.source_name}>
                      <div className="flex items-baseline justify-between gap-2 text-[13px]">
                        <span className="truncate text-ink" title={j.source_name}><span className="mr-1.5 text-ink-faint">{i + 1}</span>{j.source_name}</span>
                        <span className="shrink-0 text-ink-2">{j.papers}{j.quartile && <span className="ml-1.5 text-[11px]" style={{ color: QUARTILE[j.quartile as "Q1"] ?? "#a39aa1" }}>{j.quartile}</span>}</span>
                      </div>
                      <div className="mt-1 h-1.5 rounded-full bg-white/[0.05]"><div className="h-1.5 rounded-full" style={{ width: `${(100 * j.papers) / max}%`, background: INST_COLOR[k] }} /></div>
                    </li>
                  );
                })}
              </ol>
            </div>
          ))}
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        <Card>
          <CardHead title="Conference ranks" sub="CORE 2023, for conference papers" />
          {coreKeys.length ? (
            <Chart height={240} option={{
              tooltip: { trigger: "axis" }, grid: { left: 8, right: 16 },
              xAxis: axisX({ type: "category", data: coreKeys }),
              yAxis: axisY({ type: "value", minInterval: 1 }),
              series: [{ type: "bar", barWidth: "52%", data: coreKeys.map((k) => ({ value: s.core[k], itemStyle: { color: CORE_COLOR[k], borderRadius: [4, 4, 0, 0] } })),
                label: { show: true, position: "top", color: "#cfc4cc", fontSize: 12 } }],
            }} />
          ) : <p className="text-ink-muted">No conference papers.</p>}
          <Note>{fmt(s.conference_papers)} conference papers ({pct(s.conference_papers / Math.max(s.papers, 1))} of output). IISERs publish mainly in journals; most conference venues here (physics and chemistry meetings) are outside CORE's computing-focused list, so "Unranked" dominates.</Note>
        </Card>
        <Card className="xl:col-span-2">
          <CardHead title="Most-cited papers" sub={`${scopeLabel(scope)} · top 10 by citations to date`}
            right={<Pills small value={excl} onChange={setExcl} options={[{ value: "all", label: "All papers" }, { value: "core", label: "≤ 50 authors" }]} />} />
          <ol className="flex flex-col divide-y divide-white/[0.05]">
            {top.map((p, i) => (
              <li key={p.work_id} className="flex items-start gap-3 py-2.5">
                <span className="mt-0.5 w-5 shrink-0 text-right text-[13px] font-semibold text-ink-faint">{i + 1}</span>
                <div className="min-w-0 flex-1">
                  <a href={p.doi ?? `https://openalex.org/${p.work_id}`} target="_blank" rel="noreferrer" className="group block text-[14px] leading-snug text-ink hover:text-plum-200">
                    {p.title} <ExternalLink size={11} className="inline opacity-0 transition group-hover:opacity-100" />
                  </a>
                  <div className="mt-0.5 flex flex-wrap items-center gap-2 text-[12px] text-ink-muted">
                    <span>{p.source_name}</span><span>· {p.year}</span>
                    {p.n_authors != null && <span>· {p.n_authors} authors</span>}
                    {p.hyperauthored && <Badge tone="muted">large collaboration</Badge>}
                  </div>
                </div>
                <span className="shrink-0 text-[15px] font-semibold">{fmt(p.cited_by_count)}</span>
              </li>
            ))}
          </ol>
        </Card>
      </div>
    </div>
  );
}
