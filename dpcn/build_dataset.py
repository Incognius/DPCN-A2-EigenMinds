"""Assemble data/final/group20_data.csv: the 14 spec columns first, then extra columns.

One row per (faculty member, paper) -- the spec's `author` column is the faculty member.
A paper co-authored by two of our faculty appears twice; institution-level statistics
de-duplicate on work_id. `affiliated` says whether that faculty authorship carries their IISER.
"""
from __future__ import annotations

import re

import pandas as pd

from .config import FINAL, GROUP, INTERIM, cfg, inst_by_key
from .enrich.links import load_citers
from .enrich.venue import core_ranks, journal_quartiles

SPEC_COLUMNS = ["group", "institution", "author", "title", "year", "type", "journal_name", "issn",
                "doi", "citations", "quartile", "coauthor_institutes", "cites_indian_inst",
                "cited_by_indian_inst"]


def clean_venue(name):
    """OpenAlex sometimes joins a venue's name variants with '/' ('Physical review. B./Physical review. B').
    Keep one variant when the parts are the same name; leave genuine slashes ('IEEE/CVF ...') alone."""
    if not isinstance(name, str):
        return name
    parts = [x.strip() for x in name.split("/") if x.strip()]
    key = lambda x: re.sub(r"[^a-z0-9]", "", x.lower())
    if len(parts) > 1 and all(key(x) in key(parts[0]) or key(parts[0]) in key(x) for x in parts[1:]):
        name = max(parts, key=len)
    name = re.sub(r"\bPhysical review\.?\s*", "Physical Review ", name).strip().rstrip(".")
    return name


def enriched_papers() -> pd.DataFrame:
    """Paper-level table with quartile, CORE rank, venue type and the hyper-authorship flag."""
    p = pd.read_parquet(INTERIM / "papers.parquet")
    p["source_name"] = p.source_name.map(clean_venue)
    p["type"] = ["conference" if (s == "conference" or t == "conference-paper") else "journal"
                 for s, t in zip(p.source_type, p.work_type)]
    p["sjr_quartile"] = journal_quartiles(p)
    p["core_rank"] = core_ranks(p)
    p["quartile"] = p.sjr_quartile.where(p.type == "journal", p.core_rank)
    p["hyperauthored"] = p.n_authors > cfg()["hyperauthor_cap"]
    p.to_parquet(INTERIM / "papers_enriched.parquet", index=False)
    return p


def indian_flags(own_inst_id: str, work_ids: set[str]) -> tuple[dict, dict]:
    """Per work: does it cite / is it cited by an Indian institution other than `own_inst_id`?"""
    refs = pd.read_parquet(INTERIM / "refs.parquet")
    meta = pd.read_parquet(INTERIM / "ref_meta.parquet")
    ind_ref = {r.ref_id for r in meta.itertuples()
               if any(c == "IN" and i != own_inst_id for i, c in zip(r.inst_ids, r.inst_countries))}
    refs = refs[refs.work_id.isin(work_ids)]
    cites = refs.assign(ind=refs.ref_id.isin(ind_ref)).groupby("work_id").ind.any().to_dict()
    citing = load_citers()
    citing = citing[citing.cited_id.isin(work_ids)]
    cited = (citing.assign(ind=[any(i != own_inst_id for i in ids) for ids in citing.inst_ids])
                   .groupby("cited_id").ind.any().to_dict())
    return cites, cited


def main() -> pd.DataFrame:
    papers = enriched_papers().set_index("work_id")
    fp = pd.read_parquet(INTERIM / "faculty_papers.parquet")
    auths = pd.read_parquet(INTERIM / "authorships.parquet")
    insts = inst_by_key()

    # distinct institution names per paper (for coauthor_institutes)
    paper_insts = {}
    for wid, g in auths.groupby("work_id"):
        seen = {}
        for ids, names in zip(g.inst_ids, g.inst_names):
            for i, n in zip(ids, names):
                seen.setdefault(i, n)
        paper_insts[wid] = seen

    frames = []
    for key, inst in insts.items():
        sub = fp[fp.institution == key].copy()
        cites, cited = indian_flags(inst["openalex"], set(sub.work_id))
        pp = papers.loc[sub.work_id]
        sub["group"] = GROUP
        sub["institution_name"] = inst["name"]
        sub["coauthor_institutes"] = ["; ".join(n for i, n in paper_insts.get(w, {}).items()
                                                if i != inst["openalex"] and n)
                                      for w in sub.work_id]
        sub["cites_indian_inst"] = [bool(cites.get(w, False)) for w in sub.work_id]
        sub["cited_by_indian_inst"] = [bool(cited.get(w, False)) for w in sub.work_id]
        for c in ["title", "year", "type", "source_name", "issn_l", "doi", "cited_by_count", "quartile",
                  "core_rank", "sjr_quartile", "n_authors", "hyperauthored", "field", "subfield", "domain",
                  "topic", "fwci", "is_oa", "top_10pct"]:
            sub[c] = pp[c].values
        frames.append(sub)

    df = pd.concat(frames, ignore_index=True)
    out = df.rename(columns={"institution_name": "institution", "institution": "institution_key",
                             "faculty": "author", "source_name": "journal_name", "issn_l": "issn",
                             "cited_by_count": "citations", "author_id": "author_openalex_id"})
    extras = ["institution_key", "department", "author_openalex_id", "work_id", "affiliated",
              "author_position", "n_authors", "hyperauthored", "sjr_quartile", "core_rank", "field",
              "subfield", "domain", "topic", "fwci", "is_oa", "top_10pct"]
    out = out.rename(columns={"position": "author_position"})
    out["issn"] = out["issn"].where(out["type"] == "journal")
    out = out[SPEC_COLUMNS + extras].sort_values(["institution", "author", "year", "title"])
    out.to_csv(FINAL / f"group{GROUP}_data.csv", index=False, encoding="utf-8")
    print(f"group{GROUP}_data.csv: {len(out)} rows, {out.work_id.nunique()} unique papers")
    print(out.groupby("institution").agg(rows=("work_id", "size"), papers=("work_id", "nunique"),
                                         q_cov=("quartile", lambda s: s.notna().mean())).to_string())
    return out


if __name__ == "__main__":
    main()
