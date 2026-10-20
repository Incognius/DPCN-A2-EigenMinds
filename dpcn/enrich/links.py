"""Citation links between our corpus and the rest of (Indian) science.

out-flow  every referenced work of a corpus paper -> its year + Indian institutions
in-flow   every work with an Indian author that cites a corpus paper (cites:W..|W.. filter)

Outputs (data/interim):
  ref_meta.parquet     ref_id, year, doi, inst_ids, inst_names, inst_countries  (one row per ref)
  citing.parquet       citing_id, cited_id, year, doi, inst_ids, inst_names  (Indian citers only)
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pandas as pd

from .. import openalex as oa
from ..config import INTERIM

LIGHT = "id,doi,publication_year,authorships"


def _insts(w: dict) -> tuple[list, list, list]:
    ids, names, ctry = [], [], []
    seen = set()
    for a in w.get("authorships") or []:
        for i in a.get("institutions") or []:
            iid = oa.short_id(i.get("id"))
            if iid and iid not in seen:
                seen.add(iid)
                ids.append(iid)
                names.append(i.get("display_name"))
                ctry.append(i.get("country_code"))
    return ids, names, ctry


def fetch_ref_meta() -> pd.DataFrame:
    refs = pd.read_parquet(INTERIM / "refs.parquet")
    papers = pd.read_parquet(INTERIM / "papers.parquet")
    todo = sorted(set(refs.ref_id))
    rows = []
    known = set(papers.work_id)                              # corpus papers we already have
    batches = list(oa.batched([r for r in todo if r not in known], 100))

    def one(batch):                                          # ~3 s per call, so run 8 at once
        data = oa.get("/works", {"filter": f"openalex_id:{'|'.join(batch)}", "select": LIGHT,
                                 "per_page": 100})
        out = []
        for w in data.get("results", []):
            ids, names, ctry = _insts(w)
            out.append(dict(ref_id=oa.short_id(w["id"]), year=w.get("publication_year"),
                            doi=w.get("doi"), inst_ids=ids, inst_names=names, inst_countries=ctry))
        return out

    with ThreadPoolExecutor(max_workers=8) as ex:
        for i, out in enumerate(ex.map(one, batches)):
            rows.extend(out)
            if i % 250 == 0:
                oa.report_spend(f"refs batch {i}/{len(batches)}")
    auths = pd.read_parquet(INTERIM / "authorships.parquet")
    for wid, g in auths.groupby("work_id"):                  # corpus refs: reuse our own data
        ids, names, ctry, seen = [], [], [], set()
        for row in g.itertuples():
            for iid, nm, c in zip(row.inst_ids, row.inst_names, row.inst_countries):
                if iid not in seen:
                    seen.add(iid); ids.append(iid); names.append(nm); ctry.append(c)
        p = papers.loc[papers.work_id == wid].iloc[0]
        rows.append(dict(ref_id=wid, year=p.year, doi=p.doi, inst_ids=ids, inst_names=names,
                         inst_countries=ctry))
    df = pd.DataFrame(rows).drop_duplicates("ref_id")
    df.to_parquet(INTERIM / "ref_meta.parquet", index=False)
    oa.report_spend(f"ref meta {len(df)}")
    return df


def fetch_indian_citers() -> pd.DataFrame:
    papers = pd.read_parquet(INTERIM / "papers.parquet")
    cited = papers[papers.cited_by_count > 0].work_id.tolist()
    def one(batch):
        bset, out = set(batch), []
        flt = f"cites:{'|'.join(batch)},authorships.institutions.country_code:IN"
        for w in oa.paginate("/works", {"filter": flt, "select": LIGHT + ",referenced_works"}):
            ids, names, ctry = _insts(w)
            ind = [(a, b) for a, b, c in zip(ids, names, ctry) if c == "IN"]
            for target in {oa.short_id(r) for r in w.get("referenced_works") or []} & bset:
                out.append(dict(citing_id=oa.short_id(w["id"]), cited_id=target,
                                year=w.get("publication_year"), doi=w.get("doi"),
                                inst_ids=[a for a, _ in ind], inst_names=[b for _, b in ind]))
        return out

    rows = []
    batches = list(oa.batched(cited, 100))
    with ThreadPoolExecutor(max_workers=8) as ex:
        for i, out in enumerate(ex.map(one, batches)):
            rows.extend(out)
            if i % 20 == 0:
                oa.report_spend(f"citers batch {i}/{len(batches)}")
    df = pd.DataFrame(rows).drop_duplicates(["citing_id", "cited_id"])
    df.to_parquet(INTERIM / "citing.parquet", index=False)
    oa.report_spend(f"indian citing edges {len(df)}")
    return df


if __name__ == "__main__":
    import sys
    if "citers" in sys.argv:
        fetch_indian_citers()
    else:
        fetch_ref_meta()
