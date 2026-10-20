import { ExternalLink, X } from "lucide-react";
import { useEffect } from "react";
import { useData } from "../lib/data";
import { fmt, pct } from "../lib/format";
import { useStore } from "../lib/store";
import { INST_COLOR, INST_SHORT, axisX, axisY } from "../lib/theme";
import type { Faculty } from "../lib/types";
import Chart from "./Chart";
import { Avatar, Badge, Stat } from "./ui";

const YEARS = Array.from({ length: 11 }, (_, i) => 2016 + i);

export default function FacultyDrawer() {
  const { facultyKey, openFaculty } = useStore();
  const { data } = useData<Faculty[]>("faculty.json");
  const f = data?.find((x) => x.key === facultyKey);
  useEffect(() => {
    const k = (e: KeyboardEvent) => e.key === "Escape" && openFaculty(null);
    window.addEventListener("keydown", k);
    return () => window.removeEventListener("keydown", k);
  }, [openFaculty]);
  const open = Boolean(f);
  return (
    <>
      <div className={`fixed inset-0 z-50 bg-black/55 backdrop-blur-[2px] transition ${open ? "opacity-100" : "pointer-events-none opacity-0"}`} onClick={() => openFaculty(null)} />
      <aside role="dialog" aria-label="Faculty profile"
        className={`scroll-thin fixed inset-y-0 right-0 z-50 w-full max-w-[460px] overflow-y-auto border-l border-white/10 p-6 transition-transform duration-300 ${open ? "translate-x-0" : "translate-x-full"}`}
        style={{ background: "linear-gradient(180deg,#1a1219 0%,#0e0a0d 100%)" }}>
        {f && (
          <>
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-3">
                <Avatar name={f.name} inst={f.institution} size={52} />
                <div>
                  <h2 className="text-[21px] font-bold leading-tight">{f.name}</h2>
                  <div className="text-[13px] text-ink-muted">{f.designation || "Faculty"} · {f.department}</div>
                  <div className="mt-1 flex items-center gap-1.5 text-[12.5px]" style={{ color: INST_COLOR[f.institution] }}>
                    <span className="h-2 w-2 rounded-full" style={{ background: INST_COLOR[f.institution] }} />IISER {INST_SHORT[f.institution]}
                  </div>
                </div>
              </div>
              <button className="icon-btn !h-9 !w-9" onClick={() => openFaculty(null)} aria-label="Close"><X size={16} /></button>
            </div>

            <div className="mt-6 grid grid-cols-3 gap-4">
              <Stat label="Papers 16–26" value={fmt(f.papers)} sub={`${fmt(f.papers_affiliated)} at IISER`} />
              <Stat label="Citations" value={fmt(f.citations)} />
              <Stat label="h-index" value={f.h_index_career ?? "–"} sub={`${f.h_index_window} in window`} />
              <Stat label="Q1 share" value={pct(f.q1_share, 0)} />
              <Stat label="Median FWCI" value={fmt(f.median_fwci, 2)} />
              <Stat label="1st-author" value={pct(f.first_author_share, 0)} />
            </div>

            <div className="mt-6">
              <div className="stat-label mb-1">Papers per year</div>
              <Chart height={150} option={{
                grid: { top: 10, left: 4, right: 4, bottom: 4 },
                tooltip: { trigger: "axis" },
                xAxis: axisX({ type: "category", data: YEARS.map(String), axisLabel: { color: "#71666e", fontSize: 10, interval: 1 } }),
                yAxis: axisY({ type: "value", minInterval: 1 }),
                series: [{ type: "bar", data: YEARS.map((y) => f.by_year[String(y)] ?? 0), barWidth: "56%",
                  itemStyle: { color: INST_COLOR[f.institution], borderRadius: [4, 4, 0, 0] } }],
              }} />
            </div>

            {f.degree != null && (
              <div className="mt-5 rounded-2xl border border-white/[0.06] bg-white/[0.02] p-4">
                <div className="stat-label mb-3">In the collaboration network</div>
                <div className="grid grid-cols-3 gap-3">
                  <Stat label="Co-faculty" value={f.degree} />
                  <Stat label="Betweenness" value={fmt((f.betweenness ?? 0) * 100, 2)} sub="× 10⁻²" />
                  <Stat label="Community" value={`#${(f.community ?? 0) + 1}`} />
                </div>
              </div>
            )}

            {f.coauthors && f.coauthors.length > 0 && (
              <div className="mt-5">
                <div className="stat-label mb-2">Frequent co-authors</div>
                <ul className="flex flex-col divide-y divide-white/[0.05]">
                  {f.coauthors.slice(0, 10).map((c) => (
                    <li key={c.name + c.inst} className="flex items-center justify-between gap-3 py-2 text-[13.5px]">
                      <span className="min-w-0"><span className="block truncate text-ink">{c.name}</span>
                        <span className="block truncate text-[12px] text-ink-muted">{c.inst ?? "—"}</span></span>
                      <span className="shrink-0 text-ink-2">{c.papers} papers</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="mt-5 flex flex-wrap items-center gap-2 text-[12.5px] text-ink-muted">
              {f.top_journal && <span>Most frequent venue: <span className="text-ink-2">{f.top_journal}</span></span>}
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <Badge tone={f.match_confidence === "high" ? "pos" : "muted"}>match: {f.match_confidence}</Badge>
              {f.hyperauthored_papers > 0 && <Badge>{f.hyperauthored_papers} large-collaboration papers</Badge>}
              {f.openalex_ids.split(";").filter(Boolean).map((id) => (
                <a key={id} className="pill pill-sm" href={`https://openalex.org/${id}`} target="_blank" rel="noreferrer">
                  OpenAlex {id} <ExternalLink size={12} />
                </a>
              ))}
            </div>
          </>
        )}
      </aside>
    </>
  );
}
