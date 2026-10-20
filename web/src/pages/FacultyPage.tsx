import { useMemo, useState } from "react";
import { createColumnHelper } from "@tanstack/react-table";
import { Search } from "lucide-react";
import Chart from "../components/Chart";
import DataTable from "../components/DataTable";
import { Avatar, Card, CardHead, Loading, Note, Pills } from "../components/ui";
import { useData } from "../lib/data";
import { fmt, pct } from "../lib/format";
import { useStore } from "../lib/store";
import { INK, INST_COLOR, INST_ORDER, INST_SHORT, axisX, axisY } from "../lib/theme";
import type { Faculty, Institutes } from "../lib/types";

const ch = createColumnHelper<Faculty>();
const columns = [
  ch.accessor("name", {
    header: "Faculty", cell: (c) => (
      <span className="flex items-center gap-2.5"><Avatar name={c.getValue()} inst={c.row.original.institution} size={30} />
        <span><span className="block text-ink">{c.getValue()}</span>
          <span className="block text-[11.5px] text-ink-faint">{c.row.original.designation}</span></span></span>),
  }),
  ch.accessor("department", { header: "Department", cell: (c) => <span className="text-ink-2">{c.getValue()}</span> }),
  ch.accessor("institution", { header: "Inst.", cell: (c) => <span style={{ color: INST_COLOR[c.getValue()] }}>{INST_SHORT[c.getValue()]}</span> }),
  ch.accessor("papers", { header: "Papers" }),
  ch.accessor("citations", { header: "Citations", cell: (c) => fmt(c.getValue()) }),
  ch.accessor("h_index_career", { header: "h (career)", cell: (c) => c.getValue() ?? "–", sortUndefined: "last" }),
  ch.accessor("h_index_window", { header: "h (16–26)" }),
  ch.accessor("q1_share", { header: "Q1", cell: (c) => pct(c.getValue(), 0), sortUndefined: "last" }),
  ch.accessor("median_fwci", { header: "FWCI", cell: (c) => fmt(c.getValue(), 2), sortUndefined: "last" }),
  ch.accessor("degree", { header: "Co-fac.", cell: (c) => c.getValue() ?? 0 }),
  ch.accessor("top_journal", { header: "Top venue", cell: (c) => <span className="block max-w-[220px] truncate" title={c.getValue() ?? ""}>{c.getValue() ?? "–"}</span> }),
];

export default function FacultyPage() {
  const { scope, openFaculty } = useStore();
  const { data } = useData<Faculty[]>("faculty.json");
  const { data: inst } = useData<Institutes>("institutes.json");
  const [q, setQ] = useState("");
  const [dept, setDept] = useState("all");
  const [hKind, setHKind] = useState<"career" | "window">("career");

  const pool = useMemo(() => (data ?? []).filter((f) => scope === "ALL" || f.institution === scope), [data, scope]);
  const depts = useMemo(() => ["all", ...Array.from(new Set(pool.map((f) => f.department))).sort()], [pool]);
  const rows = useMemo(() => pool.filter((f) =>
    (dept === "all" || f.department === dept) &&
    (!q || f.name.toLowerCase().includes(q.toLowerCase()) || f.department.toLowerCase().includes(q.toLowerCase()))), [pool, dept, q]);

  if (!data || !inst) return <Loading h={600} />;

  const bins = Array.from({ length: 20 }, (_, i) => i * 5);
  const hist = (k: (typeof INST_ORDER)[number]) => {
    const vals = data.filter((f) => f.institution === k).map((f) => (hKind === "career" ? f.h_index_career : f.h_index_window)).filter((v): v is number => v != null);
    return bins.map((b) => vals.filter((v) => v >= b && v < b + 5).length);
  };
  const shown = scope === "ALL" ? INST_ORDER : [scope];
  const med = (k: (typeof INST_ORDER)[number]) => {
    const v = data.filter((f) => f.institution === k).map((f) => f.h_index_career).filter((x): x is number => x != null).sort((a, b) => a - b);
    return v.length ? v[Math.floor(v.length / 2)] : null;
  };

  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHead title="h-index distribution" sub="Faculty counts per 5-point h-index bin"
            info="Career h-index is OpenAlex's lifetime value for the faculty member's profile. The window h-index uses only 2016–2026 papers and their citations to date."
            right={<Pills small value={hKind} onChange={setHKind} options={[{ value: "career", label: "Career" }, { value: "window", label: "2016–26 window" }]} />} />
          <Chart height={300} option={{
            legend: shown.length > 1 ? { top: 0, right: 0 } : { show: false }, grid: { top: 36 },
            tooltip: { trigger: "axis" },
            xAxis: axisX({ type: "category", data: bins.map((b) => `${b}–${b + 4}`), name: "h-index", nameLocation: "middle", nameGap: 28, nameTextStyle: { color: INK.faint } }),
            yAxis: axisY({ type: "value", name: "faculty", nameTextStyle: { color: INK.faint } }),
            series: shown.map((k) => ({ name: INST_SHORT[k], type: "bar" as const, data: hist(k), barGap: "8%",
              itemStyle: { color: INST_COLOR[k], borderRadius: [4, 4, 0, 0] } })),
          }} />
        </Card>
        <Card>
          <CardHead title="Medians" sub="Career h-index of current faculty" />
          <ul className="flex flex-col gap-4">
            {INST_ORDER.map((k) => (
              <li key={k} className="flex items-center justify-between">
                <span className="flex items-center gap-2 text-[15px]"><span className="h-2.5 w-2.5 rounded-full" style={{ background: INST_COLOR[k] }} />IISER {INST_SHORT[k]}</span>
                <span className="text-[22px] font-bold">{med(k) ?? "–"}</span>
              </li>
            ))}
          </ul>
          <Note>Kruskal–Wallis across institutes: H = {fmt(inst.tests.h_index_kruskal.H, 2)}, p = {inst.tests.h_index_kruskal.p < 0.001 ? "< 0.001" : fmt(inst.tests.h_index_kruskal.p, 3)}. Career h-index rewards seniority, so it partly measures how long faculty have been publishing.</Note>
        </Card>
      </div>

      <Card>
        <CardHead title="Faculty performance" sub={`${rows.length} faculty · click a row for the profile`}
          right={<div className="flex flex-wrap items-center gap-2">
            <label className="flex h-9 items-center gap-2 rounded-full border border-white/10 bg-[#0d0a0c] px-3">
              <Search size={14} className="text-ink-muted" />
              <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Filter by name" aria-label="Filter faculty"
                className="w-40 bg-transparent text-[13px] focus:outline-none" />
            </label>
            <select value={dept} onChange={(e) => setDept(e.target.value)} aria-label="Department"
              className="h-9 rounded-full border border-white/10 bg-[#0d0a0c] px-3 text-[13px] text-ink-2 focus:outline-none">
              {depts.map((d) => <option key={d} value={d}>{d === "all" ? "All departments" : d}</option>)}
            </select>
          </div>} />
        <DataTable data={rows} columns={columns} initialSort={[{ id: "citations", desc: true }]} pageSize={15} onRow={(f) => openFaculty(f.key)} />
      </Card>
    </div>
  );
}
