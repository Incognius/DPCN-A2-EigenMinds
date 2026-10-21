"""Fetch every 2016-2026 publication of the matched faculty from OpenAlex.

Scope: journal and conference outputs only, as the spec's `type` column allows (journal|conference):
work types article / review / letter / conference paper whose venue is a journal or conference.
Preprints, book chapters, datasets, peer reviews and errata are dropped.

Cleaning, because OpenAlex types much more than research papers as `article`:
  - front matter (covers, frontispieces) and notices (errata, publisher's notes, addenda) are dropped,
    including errata that only show up as "<DOI of the paper>e" (Planck 2018);
  - "journal" venues without an ISSN (telegrams, data catalogues, meeting-abstract books) are dropped,
    after filling ISSNs OpenAlex lacks for real journals from SCImago titles;
  - one paper under two records is counted once: Angewandte's German edition (ange.*) twin of the
    International Edition (anie.*), and same-type, same-title records within a year sharing an author
    (version and provisional DOIs, repository copies, journal-supplement abstracts of a paper). The
    best-cited record is kept; references to the duplicate are redirected to it.

Outputs (data/interim):
  papers.parquet       one row per work
  authorships.parquet  one row per (work, author position) with that author's institutions
  refs.parquet         one row per (work, referenced work)
  faculty_papers.parquet  one row per (faculty, work) with the `affiliated` flag
"""
from __future__ import annotations

import json
import re

import pandas as pd
from rapidfuzz import fuzz, process

from . import openalex as oa
from .config import INTERIM, YEAR_MAX, YEAR_MIN, cfg, inst_by_key
from .enrich import sjr

SELECT = ("id,doi,title,publication_year,publication_date,type,primary_location,authorships,"
          "cited_by_count,referenced_works,primary_topic,fwci,open_access,counts_by_year,"
          "citation_normalized_percentile,is_retracted,language")
KEEP_TYPES = {"article", "review", "letter", "conference-paper", "proceedings-article"}
KEEP_SOURCES = {"journal", "conference"}

NON_PAPER = re.compile(
    r"^\s*(frontispi(z|ece)|titelbild|innentitel|r[üu]cktitelbild"
    r"|((inside |back |front )*cover (picture|feature|image|art|profile))\b"
    r"|erratum|errata\b|corrigendum|corrections?( to)?\s*[:\"“‘']|publisher['’]s note|addendum to"
    r"|retraction( note| notice)?\s*[:\"“‘']|expression of concern)", re.I)
ANGEW_DE, ANGEW_INT = "10.1002/ange.", "10.1002/anie."
ANGEW_DE_ISSN = "0044-8249"
ANGEW_INT_VENUE = {"source_name": "Angewandte Chemie International Edition", "issn_l": "1433-7851",
                   "issns": "1433-7851;1521-3773"}
MIN_TITLE = 25          # shorter titles ("ALICE Collaboration", "Planck 2018 results") are too generic to match on


def fetch_works(author_ids: list[str]) -> list[dict]:
    works: dict[str, dict] = {}
    for batch in oa.batched(sorted(set(author_ids)), 50):
        flt = f"author.id:{'|'.join(batch)},publication_year:{YEAR_MIN}-{YEAR_MAX}"
        for w in oa.paginate("/works", {"filter": flt, "select": SELECT}):
            works[oa.short_id(w["id"])] = w
    # list responses truncate authorships at 100; single-record GETs are complete (and free)
    truncated = [wid for wid, w in works.items() if len(w.get("authorships") or []) >= 100]
    for wid in truncated:
        works[wid] = oa.get(f"/works/{wid}", {"select": SELECT})
    print(f"re-fetched {len(truncated)} hyper-authored works with full author lists")
    return list(works.values())


def flatten(works: list[dict]):
    papers, auths, refs = [], [], []
    for w in works:
        wid = oa.short_id(w["id"])
        loc = w.get("primary_location") or {}
        src = loc.get("source") or {}
        topic = w.get("primary_topic") or {}
        oa_ = w.get("open_access") or {}
        pct = w.get("citation_normalized_percentile") or {}
        papers.append(dict(
            work_id=wid,
            doi=w.get("doi"),
            title=(w.get("title") or "").strip(),
            year=w.get("publication_year"),
            date=w.get("publication_date"),
            work_type=w.get("type"),
            source_id=oa.short_id(src.get("id")),
            source_name=src.get("display_name"),
            source_type=src.get("type"),
            issn_l=src.get("issn_l"),
            issns=";".join(src.get("issn") or []),
            cited_by_count=w.get("cited_by_count", 0),
            fwci=w.get("fwci"),
            citation_pct=pct.get("value"),
            top_10pct=pct.get("is_in_top_10_percent"),
            is_oa=oa_.get("is_oa"),
            oa_status=oa_.get("oa_status"),
            topic=(topic.get("display_name")),
            subfield=(topic.get("subfield") or {}).get("display_name"),
            field=(topic.get("field") or {}).get("display_name"),
            domain=(topic.get("domain") or {}).get("display_name"),
            n_authors=len(w.get("authorships") or []),
            n_refs=len(w.get("referenced_works") or []),
            counts_by_year=json.dumps(w.get("counts_by_year") or []),
            is_retracted=w.get("is_retracted"),
        ))
        for pos, a in enumerate(w.get("authorships") or []):
            insts = a.get("institutions") or []
            auths.append(dict(
                work_id=wid, position=pos,
                author_id=oa.short_id((a.get("author") or {}).get("id")),
                author_name=(a.get("author") or {}).get("display_name"),
                inst_ids=[oa.short_id(i.get("id")) for i in insts],
                inst_names=[i.get("display_name") for i in insts],
                inst_countries=[i.get("country_code") for i in insts],
                inst_types=[i.get("type") for i in insts],
                is_corresponding=a.get("is_corresponding"),
            ))
        for r in w.get("referenced_works") or []:
            refs.append(dict(work_id=wid, ref_id=oa.short_id(r)))
    return pd.DataFrame(papers), pd.DataFrame(auths), pd.DataFrame(refs)


def norm_title(t) -> str:
    return re.sub(r"[\W_]", "", str(t or "").lower())


def fix_venues(papers: pd.DataFrame) -> pd.DataFrame:
    """Angewandte's German edition -> International Edition; fill ISSNs OpenAlex lacks for real journals
    ('Chemistry. Asian Journal') from a close SCImago title match, renaming the venue to that title."""
    p = papers.copy()
    p["issn_l"] = p.issn_l.fillna(p.issns.fillna("").str.split(";").str[0].replace("", None))
    de = p.doi.fillna("").str.contains(ANGEW_DE, regex=False) | p.issn_l.eq(ANGEW_DE_ISSN)
    intl = p.loc[p.issn_l.eq(ANGEW_INT_VENUE["issn_l"]), "source_id"].dropna()
    venue = dict(ANGEW_INT_VENUE, source_id=intl.iloc[0] if len(intl) else None)
    for c, v in venue.items():
        p.loc[de, c] = v

    q = sjr.load().dropna(subset=["sjr_title"]).drop_duplicates("sjr_title")
    lut = dict(zip(q.sjr_title.map(norm_title), zip(q.sjr_title, q.issn)))
    keys = list(lut)
    miss = p.issn_l.isna() & p.source_type.eq("journal")
    for name in p.loc[miss, "source_name"].dropna().unique():
        hit = process.extractOne(norm_title(name), keys, scorer=fuzz.ratio, score_cutoff=93)
        if hit:
            title, issn = lut[hit[0]]
            rows = miss & p.source_name.eq(name)
            p.loc[rows, "source_name"], p.loc[rows, "issn_l"], p.loc[rows, "issns"] = title, issn, issn
    return p


def non_papers(papers: pd.DataFrame) -> pd.Series:
    """True for front matter, notices, errata and ISSN-less 'journal' venues."""
    dois = set(papers.doi.dropna())
    erratum = papers.doi.fillna("").map(lambda d: d.endswith("e") and d[:-1] in dois)
    # not .str.match(NON_PAPER): pandas drops a compiled pattern's re.I flag, so "Frontispiz:" slipped through
    notice = papers.title.fillna("").map(lambda t: bool(NON_PAPER.match(t)))
    no_issn = papers.source_type.eq("journal") & papers.work_type.ne("conference-paper") & papers.issn_l.isna()
    return erratum | notice | no_issn


def duplicate_map(papers: pd.DataFrame, auths: pd.DataFrame) -> dict[str, str]:
    """work_id of a duplicate record -> work_id of the record kept for that paper."""
    p = papers.set_index("work_id")
    dup: dict[str, str] = {}
    by_doi = {d: w for w, d in p.doi.items() if isinstance(d, str)}
    for w, d in p.doi.items():
        if isinstance(d, str) and ANGEW_DE in d and d.replace(ANGEW_DE, ANGEW_INT) in by_doi:
            dup[w] = by_doi[d.replace(ANGEW_DE, ANGEW_INT)]

    people = auths.dropna(subset=["author_id"]).groupby("work_id").author_id.apply(set).to_dict()
    c = p[~p.index.isin(dup) & (p.n_authors <= cfg()["hyperauthor_cap"])].copy()
    c["nt"] = c.title.map(norm_title)
    c = c[(c.nt.str.len() >= MIN_TITLE) & c.nt.duplicated(keep=False)]
    c["has_doi"], c["has_issn"] = c.doi.notna(), c.issn_l.notna()
    # a conference paper and its journal version are two outputs; only same-type records are merged
    c["conf"] = c.source_type.eq("conference") | c.work_type.eq("conference-paper")
    for _, g in c.groupby(["nt", "conf"]):
        kept: list[str] = []
        for w, r in g.sort_values(["has_doi", "cited_by_count", "has_issn"], ascending=False).iterrows():
            twin = next((k for k in kept if abs(r.year - p.at[k, "year"]) <= 1
                         and people.get(w, set()) & people.get(k, set())), None)
            if twin:
                dup[w] = twin
            else:
                kept.append(w)
    for w in dup:                                        # ange -> anie -> same-title record
        while dup[w] in dup:
            dup[w] = dup[dup[w]]
    return dup


def main():
    fac = pd.read_csv(INTERIM / "faculty_matched.csv")
    fac = fac[fac.author_ids.fillna("") != ""].copy()
    fac["author_list"] = fac.author_ids.str.split(";")
    all_ids = [a for ids in fac.author_list for a in ids]

    works = fetch_works(all_ids)
    oa.report_spend(f"works for {len(all_ids)} author ids")
    papers, auths, refs = flatten(works)
    raw_n = len(papers)
    papers = papers[papers.work_type.isin(KEEP_TYPES) & papers.source_type.isin(KEEP_SOURCES)
                    & ~papers.is_retracted.fillna(False)]
    typed_n = len(papers)
    papers = fix_venues(papers)
    papers = papers[~non_papers(papers)]
    dup = duplicate_map(papers, auths[auths.work_id.isin(set(papers.work_id))])
    papers = papers[~papers.work_id.isin(dup)].copy()
    # after de-duplication: a German-edition record with no International Edition twin is still the same
    # article (ange.X and anie.X share the suffix), so point it at the International Edition DOI
    papers["doi"] = papers.doi.str.replace(ANGEW_DE, ANGEW_INT, regex=False)
    keep = set(papers.work_id)
    print(f"works: {raw_n} fetched -> {typed_n} journal/conference -> {typed_n - len(papers) - len(dup)} "
          f"non-papers and {len(dup)} duplicate records dropped -> {len(papers)} papers kept")

    # faculty x paper, with the affiliation flag for that faculty's IISER; a faculty member listed only on
    # a duplicate record still gets the paper, under the kept record's id
    inst_oa = {k: v["openalex"] for k, v in inst_by_key().items()}
    id2fac = {a: r for _, r in fac.iterrows() for a in r.author_list}
    rows = []
    for a in auths[auths.author_id.isin(id2fac) & auths.work_id.isin(keep | set(dup))].itertuples():
        f = id2fac[a.author_id]
        rows.append(dict(faculty_key=f"{f.institution}|{f['name']}", institution=f.institution,
                         department=f.department, faculty=f["name"], author_id=a.author_id,
                         work_id=dup.get(a.work_id, a.work_id), position=a.position,
                         affiliated=inst_oa[f.institution] in (a.inst_ids or [])))
    fp = (pd.DataFrame(rows).sort_values("affiliated", ascending=False, kind="stable")
            .drop_duplicates(["faculty_key", "work_id"]))

    auths = auths[auths.work_id.isin(keep)]
    refs = refs[refs.work_id.isin(keep)].assign(ref_id=lambda r: r.ref_id.map(dup).fillna(r.ref_id))
    refs = refs[refs.work_id != refs.ref_id].drop_duplicates()     # a paper citing its own twin

    papers.to_parquet(INTERIM / "papers.parquet", index=False)
    auths.to_parquet(INTERIM / "authorships.parquet", index=False)
    refs.to_parquet(INTERIM / "refs.parquet", index=False)
    fp.to_parquet(INTERIM / "faculty_papers.parquet", index=False)
    print(f"faculty-paper rows {len(fp)}, affiliated {fp.affiliated.mean():.1%}; refs {len(refs)}; "
          f"unique refs {refs.ref_id.nunique()}")
    print(fp[fp.affiliated].groupby("institution").work_id.nunique().to_string())


if __name__ == "__main__":
    main()
