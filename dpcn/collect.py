"""Fetch every 2016-2026 publication of the matched faculty from OpenAlex.

Scope: journal and conference outputs only, as the spec's `type` column allows (journal|conference):
work types article / review / letter / conference paper whose venue is a journal or conference.
Preprints, book chapters, datasets, peer reviews and errata are dropped.

Outputs (data/interim):
  papers.parquet       one row per work
  authorships.parquet  one row per (work, author position) with that author's institutions
  refs.parquet         one row per (work, referenced work)
  faculty_papers.parquet  one row per (faculty, work) with the `affiliated` flag
"""
from __future__ import annotations

import json

import pandas as pd

from . import openalex as oa
from .config import INTERIM, YEAR_MAX, YEAR_MIN, inst_by_key

SELECT = ("id,doi,title,publication_year,publication_date,type,primary_location,authorships,"
          "cited_by_count,referenced_works,primary_topic,fwci,open_access,counts_by_year,"
          "citation_normalized_percentile,is_retracted,language")
KEEP_TYPES = {"article", "review", "letter", "conference-paper", "proceedings-article"}
KEEP_SOURCES = {"journal", "conference"}


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
    keep = set(papers.work_id)
    auths, refs = auths[auths.work_id.isin(keep)], refs[refs.work_id.isin(keep)]
    print(f"works: {raw_n} fetched -> {len(papers)} journal/conference papers kept")

    # faculty x paper, with the affiliation flag for that faculty's IISER
    inst_oa = {k: v["openalex"] for k, v in inst_by_key().items()}
    id2fac = {a: r for _, r in fac.iterrows() for a in r.author_list}
    rows = []
    for a in auths[auths.author_id.isin(id2fac)].itertuples():
        f = id2fac[a.author_id]
        rows.append(dict(faculty_key=f"{f.institution}|{f['name']}", institution=f.institution,
                         department=f.department, faculty=f["name"], author_id=a.author_id,
                         work_id=a.work_id, position=a.position,
                         affiliated=inst_oa[f.institution] in (a.inst_ids or [])))
    fp = pd.DataFrame(rows).drop_duplicates(["faculty_key", "work_id"])

    papers.to_parquet(INTERIM / "papers.parquet", index=False)
    auths.to_parquet(INTERIM / "authorships.parquet", index=False)
    refs.to_parquet(INTERIM / "refs.parquet", index=False)
    fp.to_parquet(INTERIM / "faculty_papers.parquet", index=False)
    print(f"faculty-paper rows {len(fp)}, affiliated {fp.affiliated.mean():.1%}; refs {len(refs)}; "
          f"unique refs {refs.ref_id.nunique()}")
    print(fp[fp.affiliated].groupby("institution").work_id.nunique().to_string())


if __name__ == "__main__":
    main()
