import { Download } from "lucide-react";
import { Card, CardHead, Loading, Stat } from "../components/ui";
import { useData } from "../lib/data";
import { fmt, pct } from "../lib/format";
import type { Meta } from "../lib/types";

const STEPS = [
  ["Faculty roster", "Scraped each IISER's own faculty pages (Bhopal: 10 department sites; Mohali: /people; TVM: 7 school pages). Current regular faculty only: Assistant, Associate and full Professors. Visiting, adjunct, emeritus, INSPIRE/Ramanujan fellows and former faculty are excluded so the three institutes are counted alike."],
  ["Name → OpenAlex author", "Every author OpenAlex has ever affiliated with each IISER (~7.7k) was pulled and fuzzy-matched locally. Surname and given name must agree, a namesake whose field doesn't fit the department loses to one that does, and split profiles are merged only when they share an ORCID or exact name and field."],
  ["Publications", "All 2016–2026 works of the matched authors, kept if they are articles, reviews, letters or conference papers in a journal or conference venue. Lists returned by OpenAlex cut authors at 100, so the 583 larger papers were re-fetched one by one with full author lists."],
  ["Venue quality", "Journal quartile = SCImago best quartile matched on ISSN and year (2026 uses 2025), read from the open sjrdata mirror because scimagojr.com blocks scripts. Conference rank = CORE 2023 by acronym or fuzzy name."],
  ["Indian links", "Every referenced work (≈385k) was fetched to see whether it has another Indian institution (cites_indian_inst, out-flow). Every work by an Indian-affiliated author citing a corpus paper was fetched (cited_by_indian_inst, in-flow)."],
  ["Networks", "Citation graph: corpus papers citing corpus papers (directed), PageRank, HITS, power-law fit. Co-authorship graph: faculty as nodes, joint papers as weights, Leiden/Louvain communities, betweenness, small-world test against configuration-model nulls, link prediction with a 2022 train/test split."],
] as const;

const CAVEATS = [
  "Only current faculty are listed, so papers by people who left before 2026 are missing; institute totals undercount the full institutional output.",
  "Institute statistics count a paper only if one of that institute's faculty lists the institute on it (affiliated). Pre-joining papers stay in the dataset with affiliated = FALSE.",
  "Papers with more than 50 authors (Planck, pulsar-timing arrays, collider experiments) dominate raw citation totals; they are kept but excluded from the co-authorship graph and shown separately.",
  "OpenAlex author disambiguation is imperfect; 14 of 410 faculty could not be matched and common names were resolved with a field-plausibility rule (match confidence is in the data).",
  "Citation counts are as of October 2026; recent papers have had less time to be cited, so use FWCI for fair comparisons across years and fields.",
];

export default function Methods() {
  const { data: m } = useData<Meta>("meta.json");
  if (!m) return <Loading h={600} />;
  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-2 gap-5 md:grid-cols-4">
        <Card><Stat label="Faculty matched" value={`${m.counts.faculty_matched}/${m.counts.faculty_listed}`} sub={pct(m.coverage.faculty_match)} /></Card>
        <Card><Stat label="Unique papers" value={fmt(m.counts.papers)} sub={`${fmt(m.counts.rows)} faculty-paper rows`} /></Card>
        <Card><Stat label="DOI coverage" value={pct(m.coverage.doi)} /></Card>
        <Card><Stat label="Quartile coverage" value={pct(m.coverage.quartile)} sub="journal papers" /></Card>
      </div>

      <Card>
        <CardHead title="Data files" sub={m.links.drive
          ? "The raw dataset and network files are kept private; they are shared through Google Drive (access on request)"
          : "The submitted dataset and the three network files (CSV, UTF-8)"} />
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          {m.downloads.map((d) => (
            <a key={d.file} href={d.url} {...(m.links.drive ? { target: "_blank", rel: "noreferrer" } : { download: true })}
              className="flex items-start gap-3 rounded-[16px] border border-white/[0.07] bg-[#0f0b0e] p-4 transition hover:border-white/20">
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-plum-500/15 text-plum-200"><Download size={17} /></span>
              <span><span className="block text-[14.5px] font-semibold">{d.file}</span>
                <span className="block text-[12.5px] text-ink-muted">{fmt(d.rows)} rows · {d.desc}</span></span>
            </a>
          ))}
        </div>
      </Card>

      <Card>
        <CardHead title="How the data was built" />
        <ol className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {STEPS.map(([t, d], i) => (
            <li key={t} className="flex gap-3">
              <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-plum-500/20 text-[12px] font-bold text-plum-200">{i + 1}</span>
              <div><div className="text-[14.5px] font-semibold">{t}</div><p className="mt-0.5 text-[13px] leading-relaxed text-ink-muted">{d}</p></div>
            </li>
          ))}
        </ol>
      </Card>

      <Card>
        <CardHead title="Read the numbers with these limits in mind" />
        <ul className="flex list-disc flex-col gap-2 pl-5 text-[13.5px] leading-relaxed text-ink-2">
          {CAVEATS.map((c) => <li key={c}>{c}</li>)}
        </ul>
        <p className="mt-4 text-[12.5px] text-ink-muted">Generated {m.generated}. Source code and pipeline: <a className="link" href={m.links.repo} target="_blank" rel="noreferrer">{m.links.repo}</a></p>
      </Card>
    </div>
  );
}
