import { Download, Info, Menu, Search } from "lucide-react";
import Fuse from "fuse.js";
import { useEffect, useMemo, useRef, useState } from "react";
import { useData } from "../lib/data";
import { useStore } from "../lib/store";
import { INST_COLOR, INST_SHORT, SCOPES, scopeLabel } from "../lib/theme";
import type { SearchItem } from "../lib/types";
import { Pills } from "./ui";

const TITLES: Record<string, [string, string]> = {
  overview: ["Research Atlas", "Publication, citation and collaboration overview of the three IISERs"],
  institutes: ["Institutes", "Head-to-head comparison, growth models and departments"],
  faculty: ["Faculty", "Every current regular faculty member, sortable and searchable"],
  journals: ["Journals & Impact", "Quartiles, venues, conference ranks and the most-cited papers"],
  areas: ["Research Areas", "What the institutes work on, from domains down to subfields"],
  citation: ["Citation Network", "Papers citing papers inside the three institutes"],
  collaboration: ["Collaboration Network", "Who co-authors with whom, communities and bridges"],
  connectivity: ["Indian Connectivity", "Citation flow and co-authorship with the rest of Indian science"],
  methods: ["Methods & Data", "How the data was built, its limits, and the downloads"],
};

export default function Header({ onMenu }: { onMenu: () => void }) {
  const { page, scope, setScope, setPage, openFaculty } = useStore();
  const [t, sub] = TITLES[page];
  return (
    <header className="flex flex-col gap-5">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <button className="icon-btn lg:hidden" onClick={onMenu} aria-label="Open menu"><Menu size={18} /></button>
          <div>
            <h1 className="text-[30px] font-semibold leading-tight tracking-tight sm:text-[34px]">
              {page === "overview" ? <>IISER <span className="text-plum-300">Research Atlas</span></> : t}
            </h1>
            <p className="mt-1 text-[14px] text-ink-muted">{sub}</p>
          </div>
        </div>
        <div className="hidden items-center gap-2 md:flex">
          <button className="icon-btn" title="Download the datasets" onClick={() => setPage("methods")}><Download size={18} /></button>
          <button className="icon-btn" title="About the data" onClick={() => setPage("methods")}><Info size={18} /></button>
          <div className="ml-2 flex items-center gap-3 rounded-full border border-white/10 bg-[#0d0a0c] py-1.5 pl-1.5 pr-4">
            <span className="grid h-9 w-9 place-items-center rounded-full text-[13px] font-bold"
              style={{ background: "linear-gradient(135deg,#c78fb8,#5a2f51)" }}>20</span>
            <div className="leading-tight">
              <div className="text-[14px] font-semibold">EigenMinds</div>
              <div className="text-[12px] text-ink-muted">Group 20 · DPCN 2026</div>
            </div>
          </div>
        </div>
      </div>
      <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
        <Pills options={SCOPES.map((s) => ({
          value: s,
          label: s === "ALL" ? "All IISERs" : (<><span className="h-2 w-2 rounded-full" style={{ background: INST_COLOR[s] }} />{INST_SHORT[s]}</>),
        }))} value={scope} onChange={setScope} label={scopeLabel} />
        <GlobalSearch onFaculty={(k) => { openFaculty(k); }} />
      </div>
    </header>
  );
}

function GlobalSearch({ onFaculty }: { onFaculty: (key: string) => void }) {
  const { data } = useData<SearchItem[]>("search.json");
  const { setPage } = useStore();
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  const fuse = useMemo(() => (data ? new Fuse(data, { keys: ["label", "sub"], threshold: 0.32, ignoreLocation: true }) : null), [data]);
  const hits = useMemo(() => (fuse && q.length > 1 ? fuse.search(q, { limit: 9 }).map((r) => r.item) : []), [fuse, q]);
  useEffect(() => {
    const off = (e: MouseEvent) => { if (box.current && !box.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", off);
    return () => document.removeEventListener("mousedown", off);
  }, []);
  const pick = (h: SearchItem) => {
    setOpen(false); setQ("");
    if (h.k === "f") onFaculty(h.id);
    else if (h.k === "j") setPage("journals");
    else window.open(h.id.startsWith("http") ? h.id : `https://openalex.org/${h.id}`, "_blank", "noopener");
  };
  return (
    <div ref={box} className="relative w-full xl:w-[420px]">
      <div className="flex h-12 items-center gap-3 rounded-full border border-white/10 bg-[#0d0a0c] px-5 focus-within:border-plum-300/50">
        <Search size={17} className="text-ink-muted" />
        <input value={q} onChange={(e) => { setQ(e.target.value); setOpen(true); }} onFocus={() => setOpen(true)}
          placeholder="Search faculty, papers, journals…" aria-label="Search"
          className="h-full w-full bg-transparent text-[15px] text-ink placeholder:text-ink-muted focus:outline-none" />
      </div>
      {open && hits.length > 0 && (
        <div className="absolute right-0 top-14 z-40 w-full overflow-hidden rounded-2xl border border-white/10 bg-[#120d11] p-1.5 shadow-2xl">
          {hits.map((h) => (
            <button key={h.k + h.id} onClick={() => pick(h)} className="flex w-full items-start gap-3 rounded-xl px-3 py-2 text-left hover:bg-white/[0.05]">
              <span className="mt-0.5 rounded-md bg-white/5 px-1.5 py-0.5 text-[10px] font-bold uppercase text-ink-muted">
                {{ f: "Faculty", p: "Paper", j: "Journal" }[h.k]}
              </span>
              <span className="min-w-0">
                <span className="block truncate text-[14px] text-ink">{h.label}</span>
                <span className="block truncate text-[12px] text-ink-muted">{h.sub}</span>
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
