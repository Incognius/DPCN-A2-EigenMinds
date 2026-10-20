import { createColumnHelper } from "@tanstack/react-table";
import Chart from "../components/Chart";
import DataTable from "../components/DataTable";
import { Card, CardHead, InstDot, Loading, Note } from "../components/ui";
import { useData } from "../lib/data";
import { fmt, pct, pval, signedPct } from "../lib/format";
import { useStore } from "../lib/store";
import { INK, INST_COLOR, INST_ORDER, INST_SHORT, axisX, axisY } from "../lib/theme";
import type { Department, Institutes as I } from "../lib/types";

const ch = createColumnHelper<Department>();
const deptCols = [
  ch.accessor("department", { header: "Department", cell: (c) => <span className="text-ink">{c.getValue()}</span> }),
  ch.accessor("institution", { header: "Institute", cell: (c) => <InstDot inst={c.getValue()} label /> }),
  ch.accessor("faculty", { header: "Faculty" }),
  ch.accessor("papers", { header: "Papers", cell: (c) => fmt(c.getValue()) }),
  ch.accessor("papers_per_faculty", { header: "Papers / fac.", cell: (c) => fmt(c.getValue(), 1) }),
  ch.accessor("citations", { header: "Citations", cell: (c) => fmt(c.getValue()) }),
  ch.accessor("q1_share", { header: "Q1 share", cell: (c) => pct(c.getValue(), 0) }),
  ch.accessor("median_h_career", { header: "Median h", cell: (c) => fmt(c.getValue(), 1) }),
];

export default function Institutes() {
  const { scope } = useStore();
  const { data } = useData<I>("institutes.json");
  if (!data) return <Loading h={600} />;
  const B = data.institutes;
  const rows: [string, (k: (typeof INST_ORDER)[number]) => string, string?][] = [
    ["Papers (affiliated, unique)", (k) => fmt(B[k].papers)],
    ["Citations to date", (k) => fmt(B[k].citations)],
    ["… excluding >50-author papers", (k) => fmt(B[k].citations_excl_hyper), "Large collaborations (Planck, LHC, pulsar timing) carry a big share of citations"],
    ["Median citations / paper", (k) => fmt(B[k].median_citations, 0)],
    ["Median FWCI", (k) => fmt(B[k].median_fwci, 2), "Field-weighted citation impact; 1.0 = world average for the same field, year and type"],
    ["Top-10% cited share", (k) => pct(B[k].top10pct_share)],
    ["Q1 share (SCImago)", (k) => pct(B[k].q1_share)],
    ["International co-authorship", (k) => pct(B[k].intl_share)],
    ["Open access", (k) => pct(B[k].oa_share)],
    ["CAGR 2016→2025", (k) => pct(B[k].cagr)],
    ["NB-GLM annual growth", (k) => `${signedPct(B[k].trend_nb.annual_growth)} (${pval(B[k].trend_nb.growth_p)})`, "Negative-binomial regression of yearly paper counts on year, with a COVID (2020–21) indicator"],
    ["COVID-years effect", (k) => `${signedPct(B[k].trend_nb.covid_effect)} (${pval(B[k].trend_nb.covid_p)})`],
    ["Mann–Kendall trend", (k) => `${B[k].mann_kendall.trend}, τ=${fmt(B[k].mann_kendall.tau, 2)}`],
    ["Citation Gini", (k) => fmt(B[k].gini_citations, 2), "Inequality of citations across papers: 0 = equal, 1 = all citations in one paper"],
  ];
  const T = data.tests;
  const depts = scope === "ALL" ? data.departments : data.departments.filter((d) => d.institution === scope);
  return (
    <div className="flex flex-col gap-5">
      <Card>
        <CardHead title="Head to head" sub="All numbers count each paper once and only where the faculty member lists the institute" />
        <div className="scroll-thin overflow-x-auto">
          <table className="dt w-full min-w-[640px]">
            <thead><tr><th className="!cursor-default">Metric</th>{INST_ORDER.map((k) => <th key={k} className="!cursor-default"><InstDot inst={k} label /></th>)}</tr></thead>
            <tbody>
              {rows.map(([label, f, tip]) => (
                <tr key={label}>
                  <td className="text-ink" title={tip}>{label}{tip && <span className="ml-1 text-ink-faint">ⓘ</span>}</td>
                  {INST_ORDER.map((k) => <td key={k} className={scope === k ? "font-semibold text-ink" : ""}>{f(k)}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
        <Card>
          <CardHead title="Citation concentration" sub="Lorenz curves: share of citations held by the least-cited x% of papers"
            info="The further a curve bows below the diagonal, the more citations are concentrated in a few papers. Gini is twice the area between the curve and the diagonal." />
          <Chart height={300} option={{
            legend: { top: 0, right: 0 }, grid: { top: 36 },
            tooltip: { trigger: "axis", valueFormatter: (v) => `${(Number(v) * 100).toFixed(1)}%` },
            xAxis: axisX({ type: "value", min: 0, max: 1, axisLabel: { formatter: (v: number) => `${v * 100}%`, color: INK.muted } }),
            yAxis: axisY({ type: "value", min: 0, max: 1, axisLabel: { formatter: (v: number) => `${v * 100}%` } }),
            series: [
              { name: "Equality", type: "line", data: [[0, 0], [1, 1]], symbol: "none", lineStyle: { color: "rgba(255,255,255,.25)", type: "dashed", width: 1 }, tooltip: { show: false } },
              ...INST_ORDER.map((k) => ({ name: INST_SHORT[k], type: "line" as const, symbol: "none", smooth: true, data: B[k].lorenz,
                lineStyle: { width: 2, color: INST_COLOR[k] }, itemStyle: { color: INST_COLOR[k] } })),
            ],
          }} />
        </Card>
        <Card>
          <CardHead title="Do the institutes differ?" sub="Non-parametric tests on faculty and paper-level distributions" />
          <ul className="flex flex-col gap-4 text-[14px]">
            <li><div className="text-ink">Faculty career h-index · Kruskal–Wallis</div>
              <div className="text-ink-muted">H = {fmt(T.h_index_kruskal.H, 2)}, {pval(T.h_index_kruskal.p)}. Dunn–Holm pairs: {Object.entries(T.h_index_kruskal.dunn_holm).map(([k, v]) => `${k.replace(/IISER/g, "")} ${pval(v)}`).join(" · ")}</div></li>
            <li><div className="text-ink">Journal quartile mix · χ² test</div>
              <div className="text-ink-muted">χ² = {fmt(T.quartile_chi2.chi2, 1)} (df {T.quartile_chi2.dof}), {pval(T.quartile_chi2.p)}, Cramér's V = {fmt(T.quartile_chi2.cramers_v, 3)}</div></li>
            <li><div className="text-ink">Field-weighted impact (FWCI) · Kruskal–Wallis</div>
              <div className="text-ink-muted">H = {fmt(T.fwci_kruskal.H, 2)}, {pval(T.fwci_kruskal.p)}</div></li>
            <li><div className="text-ink">Team size vs citations · Spearman</div>
              <div className="text-ink-muted">ρ = {fmt(T.teamsize_citation_spearman.rho, 3)}, {pval(T.teamsize_citation_spearman.p)}</div></li>
          </ul>
          <Note>A significant test with a tiny effect size (e.g. Cramér's V below 0.1) means the difference is real but small; with thousands of papers almost everything is "significant".</Note>
        </Card>
      </div>

      <Card>
        <CardHead title="Departments" sub="Click a header to sort · papers are unique affiliated papers of the department's current faculty" />
        <DataTable data={depts} columns={deptCols} initialSort={[{ id: "papers", desc: true }]} pageSize={14} />
      </Card>
    </div>
  );
}
