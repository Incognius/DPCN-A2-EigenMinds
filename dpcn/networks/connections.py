"""Indian connectivity: who our IISERs co-author with and cite / are cited by.

indian_connections.csv  your_inst, partner_inst, shared_papers, total_citations
  shared_papers    unique affiliated papers of `your_inst` with an author from `partner_inst`
  total_citations  citations exchanged = citations_in (partner cites us) + citations_out (we cite them)
  + partner_id, partner_cluster, cross_cluster, citations_in, citations_out, topic_jaccard,
    subfield_overlap, lat, lon

Topic similarity: partner topic profiles come from one cheap group_by call per partner (top-25
partners per institute) -- Jaccard on the top-50 topics and weighted (Ruzicka) on subfields.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict

import pandas as pd

from .. import openalex as oa
from ..clusters import cluster_of
from ..config import FINAL, INTERIM, YEAR_MAX, YEAR_MIN, inst_by_key
from ..enrich.links import load_citers
from .common import paper_institutes

TOP_PARTNERS = 25


def topic_profile(inst_id: str) -> tuple[set, dict]:
    base = f"institutions.id:{inst_id},publication_year:{YEAR_MIN}-{YEAR_MAX}"
    t = oa.get("/works", {"filter": base, "group_by": "primary_topic.id"})
    s = oa.get("/works", {"filter": base, "group_by": "primary_topic.subfield.id"})
    topics = {g["key"] for g in sorted(t.get("group_by", []), key=lambda g: -g["count"])[:50]}
    sub = {g["key"]: g["count"] for g in s.get("group_by", []) if g["key"] != "unknown"}
    tot = sum(sub.values()) or 1
    return topics, {k: v / tot for k, v in sub.items()}


def ruzicka(a: dict, b: dict) -> float:
    keys = set(a) | set(b)
    num = sum(min(a.get(k, 0), b.get(k, 0)) for k in keys)
    den = sum(max(a.get(k, 0), b.get(k, 0)) for k in keys)
    return num / den if den else 0.0


def main():
    insts = inst_by_key()
    ours = {v["openalex"]: k for k, v in insts.items()}
    pinst = paper_institutes()
    papers = pd.read_parquet(INTERIM / "papers_enriched.parquet").set_index("work_id")
    auths = pd.read_parquet(INTERIM / "authorships.parquet")
    refs = pd.read_parquet(INTERIM / "refs.parquet")
    meta = pd.read_parquet(INTERIM / "ref_meta.parquet").set_index("ref_id")
    citing = load_citers()

    names: dict[str, str] = {}
    shared = defaultdict(set)            # (our key, partner id) -> work ids
    for a in auths[auths.work_id.isin(pinst)].itertuples():
        for iid, nm, c in zip(a.inst_ids, a.inst_names, a.inst_countries):
            if c != "IN" or not iid:
                continue
            names[iid] = nm
            for k in pinst[a.work_id]:
                if iid != insts[k]["openalex"]:
                    shared[(k, iid)].add(a.work_id)

    cit_in = Counter(); cit_out = Counter()            # per partner: institution-citation pairs
    in_edges = defaultdict(set); out_edges = defaultdict(set)   # per institute: distinct citations
    in_year = Counter(); out_year = Counter()
    for c in citing[citing.cited_id.isin(pinst)].itertuples():
        for k in pinst[c.cited_id]:
            others = [i for i in c.inst_ids if i != insts[k]["openalex"]]
            for iid, nm in zip(c.inst_ids, c.inst_names):
                if iid != insts[k]["openalex"]:
                    names[iid] = nm
                    cit_in[(k, iid)] += 1
            if others:
                in_edges[k].add((c.citing_id, c.cited_id))
            if others:
                in_year[(k, c.year)] += 1
    for r in refs[refs.work_id.isin(pinst)].itertuples():
        if r.ref_id not in meta.index:
            continue
        m = meta.loc[r.ref_id]
        yr = int(papers.at[r.work_id, "year"])
        for k in pinst[r.work_id]:
            hit = False
            for iid, nm, c in zip(m.inst_ids, m.inst_names, m.inst_countries):
                if c == "IN" and iid != insts[k]["openalex"]:
                    names[iid] = nm
                    cit_out[(k, iid)] += 1
                    hit = True
            if hit:
                out_year[(k, yr)] += 1
                out_edges[k].add((r.work_id, r.ref_id))

    rows = []
    short = {v["openalex"]: v["name"] for v in insts.values()}
    for (k, iid) in set(shared) | set(cit_in) | set(cit_out):
        nm = short.get(iid) or names.get(iid, iid)
        cl = cluster_of(nm)
        rows.append(dict(your_inst=insts[k]["name"], partner_inst=nm, shared_papers=len(shared.get((k, iid), ())),
                         total_citations=cit_in[(k, iid)] + cit_out[(k, iid)], your_key=k, partner_id=iid,
                         partner_cluster=cl, cross_cluster=cl != "IISER",
                         partner_is_group20=iid in ours,
                         citations_in=cit_in[(k, iid)], citations_out=cit_out[(k, iid)]))
    df = pd.DataFrame(rows).sort_values(["your_inst", "shared_papers", "total_citations"], ascending=[True, False, False])

    # topic similarity + geo for the top partners of each institute
    df["topic_jaccard"] = None; df["subfield_overlap"] = None; df["lat"] = None; df["lon"] = None
    profiles = {k: topic_profile(v["openalex"]) for k, v in insts.items()}
    for k in insts:
        top = df[(df.your_key == k)].nlargest(TOP_PARTNERS, ["shared_papers", "total_citations"])
        for idx, r in top.iterrows():
            t, s = topic_profile(r.partner_id)
            T, S = profiles[k]
            df.at[idx, "topic_jaccard"] = len(T & t) / len(T | t) if (T | t) else None
            df.at[idx, "subfield_overlap"] = ruzicka(S, s)
            geo = (oa.get(f"/institutions/{r.partner_id}", {"select": "geo"}).get("geo") or {})
            df.at[idx, "lat"], df.at[idx, "lon"] = geo.get("latitude"), geo.get("longitude")
    oa.report_spend("connections")

    cols = ["your_inst", "partner_inst", "shared_papers", "total_citations", "partner_id", "partner_cluster",
            "cross_cluster", "partner_is_group20", "citations_in", "citations_out", "topic_jaccard",
            "subfield_overlap", "lat", "lon"]
    df[cols].to_csv(FINAL / "indian_connections.csv", index=False)

    summary = {}
    for k in insts:
        sub = df[df.your_key == k]
        tin, tout = len(in_edges[k]), len(out_edges[k])
        summary[k] = dict(
            partners=int((sub.shared_papers > 0).sum()), citing_institutes=int((sub.citations_in > 0).sum()),
            citations_in=tin, citations_out=tout, impact_ratio=tin / tout if tout else None,
            top_citing=sub.nlargest(10, "citations_in")[["partner_inst", "partner_cluster", "citations_in"]].to_dict("records"),
            top_partners=sub.nlargest(15, "shared_papers")[["partner_inst", "partner_cluster", "shared_papers",
                                                            "citations_in", "citations_out", "topic_jaccard",
                                                            "subfield_overlap", "lat", "lon"]].to_dict("records"),
            by_cluster=sub[sub.shared_papers > 0].groupby("partner_cluster").shared_papers.sum().sort_values(ascending=False).to_dict(),
            in_by_year={y: in_year[(k, y)] for y in range(YEAR_MIN, YEAR_MAX + 1)},
            out_by_year={y: out_year[(k, y)] for y in range(YEAR_MIN, YEAR_MAX + 1)},
        )
    (INTERIM / "connections_stats.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    for k, s in summary.items():
        print(k, {x: s[x] for x in ["partners", "citing_institutes", "citations_in", "citations_out", "impact_ratio"]})


if __name__ == "__main__":
    main()
