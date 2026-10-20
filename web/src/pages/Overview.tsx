import { useMemo, useState } from "react";
import { ArrowUpRight, ChevronDown, Sparkles } from "lucide-react";
import Chart from "../components/Chart";
import { Avatar, Card, CardHead, Delta, Loading, Pills, Stat } from "../components/ui";
import { useData } from "../lib/data";
import { compact, fmt, pct } from "../lib/format";
import { useStore } from "../lib/store";
import { INST_COLOR, INST_ORDER, INST_SHORT, axisX, axisY } from "../lib/theme";
import type { Connections, Faculty, InstKey, Institutes, Meta } from "../lib/types";

const ALL_YEARS = Array.from({ length: 11 }, (_, i) => 2016 + i);
type Range = "all" | "5y" | "3y";
type Board = "cited" | "h" | "collab";

export interface Insight { title: string; body: string; page: string }

export default function Overview() {
  const { scope, setPage, openFaculty } = useStore();
  const { data: inst } = useData<Institutes>("institutes.json");
  const { data: fac } = useData<Faculty[]>("faculty.json");
  const { data: meta } = useData<Meta>("meta.json");
  const { data: conn } = useData<Connections>("connections.json");
  const { data: insights } = useData<Insight[]>("insights.json");
  const [range, setRange] = useState<Range>("all");
  const [metric, setMetric] = useState<"papers" | "cites">("papers");
  const [board, setBoard] = useState<Board>("cited");
  const [ins, setIns] = useState(0);

  const s = inst?.institutes[scope];
  const years = range === "all" ? ALL_YEARS : range === "5y" ? ALL_YEARS.slice(-5) : ALL_YEARS.slice(-3);

  const leaders = useMemo(() => {
    if (!fac) return [];
    const pool = scope === "ALL" ? fac : fac.filter((f) => f.institution === scope);
    const key = { cited: (f: Faculty) => f.citations, h: (f: Faculty) => f.h_index_career ?? 0, collab: (f: Faculty) => f.degree ?? 0 }[board];
    return [...pool].sort((a, b) => key(b) - key(a)).slice(0, 5);
  }, [fac, scope, board]);

  if (!inst || !s || !meta) return <Loading h={640} />;

  const yoy = (k: InstKey | "ALL") => {
    const b = inst.institutes[k].by_year;
    return b["2025"] && b["2024"] ? b["2025"] / b["2024"] - 1 : null;
  };
  const trendSeries = (scope === "ALL" ? INST_ORDER : [scope]).map((k) => {
    const src = metric === "papers" ? inst.institutes[k].by_year : inst.institutes[k].cites_by_year;
    const c = INST_COLOR[k];
    return {
      name: INST_SHORT[k], type: "line" as const, smooth: 0.35, symbol: "circle", symbolSize: 8, showSymbol: false,
      lineStyle: { width: 2.2, color: c }, itemStyle: { color: c, borderColor: "#141114", borderWidth: 2 },
      areaStyle: { color: { type: "linear" as const, x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: c + "55" }, { offset: 1, color: c + "00" }] } },
      emphasis: { focus: "series" as const },
      data: years.map((y) => src[String(y)] ?? 0),
    };
  });
  const insight = insights?.[ins % (insights?.length || 1)];

  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2 2xl:grid-cols-12">
        {/* hero + insight */}
        <div className="flex flex-col gap-5 2xl:col-span-4">
          <Card glow>
            <div className="flex items-center justify-between">
              <h3 className="card-title">Total Papers</h3>
              <div className="flex items-center gap-1.5">
                <span className="pill pill-sm">2016–26</span>
                <button className="pill pill-sm !px-2" onClick={() => setPage("institutes")} aria-label="Compare institutes"><ChevronDown size={14} /></button>
              </div>
            </div>
            <div className="mt-6 text-[46px] font-bold leading-none tracking-tight">{fmt(s.papers)}</div>
            <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-[13px] text-ink-muted">
              <span>{compact(s.citations)} citations</span>
              <span>CAGR <span className="font-semibold text-pos">{pct(s.cagr)}</span> <span className="text-ink-faint">2016→25</span></span>
            </div>
          </Card>
          <Card glow className="flex min-h-[230px] flex-col items-center justify-between text-center">
            <div>
              <h3 className="flex items-center justify-center gap-2 text-[19px] font-semibold"><Sparkles size={16} className="text-plum-300" />{insight?.title ?? "Decisions powered by data"}</h3>
              <p className="mx-auto mt-3 max-w-[380px] text-[13.5px] leading-relaxed text-ink-2">{insight?.body}</p>
            </div>
            <div className="mt-4 flex flex-col items-center gap-3">
              <button className="pill pill-active !h-10 !px-6" onClick={() => setPage((insight?.page as never) ?? "citation")}>Explore the evidence</button>
              {insights && insights.length > 1 && (
                <div className="flex gap-1.5">{insights.map((_, i) => (
                  <button key={i} aria-label={`insight ${i + 1}`} onClick={() => setIns(i)}
                    className={`h-1.5 rounded-full transition-all ${i === ins % insights.length ? "w-5 bg-plum-300" : "w-1.5 bg-white/20"}`} />
                ))}</div>
              )}
            </div>
          </Card>
        </div>

        {/* watchlist-style leaderboard */}
        <Card className="2xl:col-span-4">
          <CardHead title="Top Faculty" />
          <Pills small value={board} onChange={setBoard} options={[
            { value: "cited", label: "Most cited" }, { value: "h", label: "h-index" }, { value: "collab", label: "Most collaborative" }]} />
          <ul className="mt-4 flex flex-col divide-y divide-white/[0.06]">
            {leaders.map((f) => (
              <li key={f.key}>
                <button className="flex w-full items-center gap-3 py-3 text-left" onClick={() => openFaculty(f.key)}>
                  <Avatar name={f.name} inst={f.institution} />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[15px] font-medium">{f.name}</span>
                    <span className="block truncate text-[12px] text-ink-muted">{f.department} · {INST_SHORT[f.institution]}</span>
                  </span>
                  <span className="text-right">
                    <span className="block text-[15px] font-semibold">
                      {board === "cited" ? fmt(f.citations) : board === "h" ? f.h_index_career : `${f.degree ?? 0} links`}
                    </span>
                    <span className="block text-[12px] text-pos">
                      {board === "cited" ? `${f.papers} papers` : board === "h" ? `${f.h_index_window} in window` : `${fmt((f.betweenness ?? 0) * 100, 1)} btw`}
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </Card>

        {/* portfolio-style institute grid */}
        <Card className="lg:col-span-2 2xl:col-span-4">
          <CardHead title="The Institutes" right={
            <div className="flex gap-1.5">
              <button className="pill pill-sm" onClick={() => setPage("institutes")}>Compare</button>
              <button className="pill pill-sm !px-2" onClick={() => setPage("institutes")} aria-label="Open institutes"><ArrowUpRight size={14} /></button>
            </div>} />
          <div className="grid grid-cols-2 gap-3">
            {INST_ORDER.map((k) => {
              const b = inst.institutes[k];
              const nf = fac?.filter((f) => f.institution === k).length ?? 0;
              return (
                <button key={k} onClick={() => setPage("institutes")}
                  className="rounded-[18px] border border-white/[0.07] bg-[#0f0b0e] p-4 text-left transition hover:border-white/20"
                  style={{ boxShadow: `inset 0 1px 0 rgba(255,255,255,.04), inset 0 -40px 60px -50px ${INST_COLOR[k]}` }}>
                  <div className="text-[20px] font-bold tracking-tight">{fmt(b.papers)}</div>
                  <div className="mt-0.5"><Delta value={yoy(k)} /> <span className="text-[11.5px] text-ink-faint">YoY</span></div>
                  <div className="mt-4 grid h-9 w-9 place-items-center rounded-xl text-[13px] font-extrabold" style={{ background: INST_COLOR[k] + "26", color: INST_COLOR[k] }}>
                    {INST_SHORT[k][0]}
                  </div>
                  <div className="mt-3 flex items-end justify-between text-[12px]">
                    <span className="font-semibold text-ink-2">{INST_SHORT[k]}</span>
                    <span className="text-ink-muted">Q1 <span className="font-semibold text-ink">{pct(b.q1_share, 0)}</span></span>
                  </div>
                  <div className="text-right text-[11.5px] text-ink-faint">{nf} faculty</div>
                </button>
              );
            })}
            <button onClick={() => setPage("connectivity")} className="rounded-[18px] border border-white/[0.07] bg-[#0f0b0e] p-4 text-left transition hover:border-white/20">
              <div className="text-[20px] font-bold tracking-tight">{conn ? compact(INST_ORDER.reduce((a, k) => a + conn[k].citations_in, 0)) : "–"}</div>
              <div className="mt-0.5 text-[12px] text-ink-muted">citations from other Indian institutes</div>
              <div className="mt-4 text-[12px] text-ink-2">{fmt(meta.counts.partners)} Indian co-author partner institutes</div>
              <div className="mt-3 text-right text-[11.5px] text-plum-300">Connectivity →</div>
            </button>
          </div>
        </Card>
      </div>

      {/* performance chart */}
      <Card>
        <CardHead title={metric === "papers" ? "Publication Performance" : "Citations by Publication Year"}
          sub={metric === "papers" ? "Unique affiliated papers per year · 2026 is partial (to October)" : "Citations received to date by papers published in each year"}
          right={<div className="flex flex-wrap gap-3">
            <Pills small value={metric} onChange={setMetric} options={[{ value: "papers", label: "Papers" }, { value: "cites", label: "Citations" }]} />
            <Pills small value={range} onChange={setRange} options={[{ value: "all", label: "2016–26" }, { value: "5y", label: "5Y" }, { value: "3y", label: "3Y" }]} />
          </div>} />
        <Chart height={330} option={{
          legend: scope === "ALL" ? { top: 0, right: 0 } : { show: false },
          grid: { top: 36 },
          tooltip: { trigger: "axis", axisPointer: { type: "line", lineStyle: { color: "rgba(244,238,243,.5)", type: "dashed" } } },
          xAxis: axisX({ type: "category", boundaryGap: false, data: years.map(String) }),
          yAxis: axisY({ type: "value" }),
          series: trendSeries,
        }} />
      </Card>

      <div className="grid grid-cols-2 gap-5 md:grid-cols-3 xl:grid-cols-6">
        {[
          ["Q1 share", pct(s.q1_share), `of ${fmt(s.journal_papers)} journal papers`],
          ["Median FWCI", fmt(s.median_fwci, 2), "1.0 = world average"],
          ["Top-10% cited", pct(s.top10pct_share), "share of papers"],
          ["International", pct(s.intl_share), "papers with a foreign co-author"],
          ["Open access", pct(s.oa_share), "papers freely readable"],
          ["Citation Gini", fmt(s.gini_citations, 2), "0 equal · 1 concentrated"],
        ].map(([l, v, sub]) => <Card key={l}><Stat label={l} value={v} sub={sub} /></Card>)}
      </div>
    </div>
  );
}
