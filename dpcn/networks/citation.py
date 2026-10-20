"""Directed citation network (nodes = papers, edge A -> B = "A cites B").

Analysis graph: papers of our three IISERs (affiliated) citing each other.
Raw file citation_network.csv additionally carries the cross-institute edges:
  out_india  our paper -> a referenced paper with another Indian institution
  in_india   a paper with another Indian institution -> our paper
Columns: source_doi, target_doi, source_inst, target_inst, year (+ ids, scope, cross flags).
"""
from __future__ import annotations

import json

import networkx as nx
import numpy as np
import pandas as pd
import powerlaw

from ..config import FINAL, INTERIM, inst_by_key
from ..enrich.links import load_citers
from .common import doi_or_id, inst_name, layout, paper_institutes


def build_edges():
    papers = pd.read_parquet(INTERIM / "papers_enriched.parquet").set_index("work_id")
    refs = pd.read_parquet(INTERIM / "refs.parquet")
    meta = pd.read_parquet(INTERIM / "ref_meta.parquet").set_index("ref_id")
    citing = load_citers()
    pinst = paper_institutes()
    ours = {v["openalex"] for v in inst_by_key().values()}
    corpus = set(pinst)

    def our_label(wid):
        return "; ".join(inst_name(k) for k in pinst.get(wid, []))

    rows = []
    # internal + outbound
    for r in refs[refs.work_id.isin(corpus) & (refs.work_id != refs.ref_id)].itertuples():   # OpenAlex has a few self-references
        src_year = papers.at[r.work_id, "year"]
        if r.ref_id in corpus:
            rows.append(dict(source_id=r.work_id, target_id=r.ref_id, scope="internal",
                             source_inst=our_label(r.work_id), target_inst=our_label(r.ref_id), year=src_year))
        elif r.ref_id in meta.index:
            m = meta.loc[r.ref_id]
            ind = [n for i, n, c in zip(m.inst_ids, m.inst_names, m.inst_countries) if c == "IN" and i not in ours]
            if ind:
                rows.append(dict(source_id=r.work_id, target_id=r.ref_id, scope="out_india",
                                 source_inst=our_label(r.work_id), target_inst="; ".join(dict.fromkeys(ind)),
                                 year=src_year, target_doi=m.doi))
    # inbound from other Indian institutes
    for c in citing[citing.cited_id.isin(corpus)].itertuples():
        ind = [n for i, n in zip(c.inst_ids, c.inst_names) if i not in ours]
        if ind:
            rows.append(dict(source_id=c.citing_id, target_id=c.cited_id, scope="in_india",
                             source_inst="; ".join(dict.fromkeys(ind)), target_inst=our_label(c.cited_id),
                             year=c.year, source_doi=c.doi))
    e = pd.DataFrame(rows)
    doi = papers.doi.to_dict()
    e["source_doi"] = [d if isinstance(d, str) else doi_or_id(doi.get(s), s)
                       for s, d in zip(e.source_id, e.get("source_doi", [None] * len(e)))]
    e["target_doi"] = [d if isinstance(d, str) else doi_or_id(doi.get(t), t)
                       for t, d in zip(e.target_id, e.get("target_doi", [None] * len(e)))]
    e["cross_institute"] = e.source_inst != e.target_inst
    e = e[["source_doi", "target_doi", "source_inst", "target_inst", "year", "source_id", "target_id",
           "scope", "cross_institute"]].drop_duplicates(["source_id", "target_id"])
    e["year"] = e.year.astype(int)
    e.to_csv(FINAL / "citation_network.csv", index=False)
    print("citation_network.csv", e.scope.value_counts().to_dict())
    return e, papers, pinst


def analyse(e: pd.DataFrame, papers: pd.DataFrame, pinst: dict) -> dict:
    internal = e[e.scope == "internal"]
    G = nx.DiGraph()
    G.add_nodes_from(pinst)
    G.add_edges_from(zip(internal.source_id, internal.target_id))
    indeg = dict(G.in_degree())
    pr = nx.pagerank(G, alpha=0.85)
    hubs, auth = nx.hits(G, max_iter=500, normalized=True)
    wcc = sorted(nx.weakly_connected_components(G), key=len, reverse=True)

    # PageRank again without hyper-authored papers (sensitivity)
    hyper = set(papers.index[papers.hyperauthored])
    G2 = G.subgraph([n for n in G if n not in hyper])
    pr2 = nx.pagerank(G2, alpha=0.85)

    def paper_card(w, score):
        p = papers.loc[w]
        return dict(work_id=w, title=p.title, year=int(p.year), journal=p.source_name,
                    citations=int(p.cited_by_count), internal_in=indeg.get(w, 0),
                    score=round(float(score), 6), inst=pinst.get(w, []), doi=p.doi,
                    hyperauthored=bool(p.hyperauthored))

    top_pr = [paper_card(w, s) for w, s in sorted(pr.items(), key=lambda x: -x[1])[:10]]
    top_pr2 = [paper_card(w, s) for w, s in sorted(pr2.items(), key=lambda x: -x[1])[:10]]
    top_auth = [paper_card(w, s) for w, s in sorted(auth.items(), key=lambda x: -x[1])[:10]]

    # in-degree distribution + heavy-tail test
    ind = np.array([d for d in indeg.values() if d > 0])
    fit = powerlaw.Fit(ind, discrete=True, verbose=False)
    R, p = fit.distribution_compare("power_law", "lognormal", normalized_ratio=True)
    R2, p2 = fit.distribution_compare("power_law", "exponential", normalized_ratio=True)
    dist = pd.Series(list(indeg.values())).value_counts().sort_index()

    # IISER x IISER flow (each source-institute x target-institute pair counted once per edge)
    keys = list(inst_by_key())
    M = pd.DataFrame(0, index=keys, columns=keys)
    for s, t in zip(internal.source_id, internal.target_id):
        for a in pinst.get(s, []):
            for b in pinst.get(t, []):
                M.loc[a, b] += 1
    self_share = float(np.trace(M.values) / M.values.sum()) if M.values.sum() else 0.0
    lag = (papers.loc[internal.source_id, "year"].values - papers.loc[internal.target_id, "year"].values)

    return dict(
        nodes=G.number_of_nodes(), edges=G.number_of_edges(),
        density=nx.density(G), isolated=sum(1 for n in G if G.degree(n) == 0),
        wcc_count=len(wcc), giant_wcc=len(wcc[0]), giant_wcc_share=len(wcc[0]) / G.number_of_nodes(),
        reciprocity=nx.reciprocity(G) if G.number_of_edges() else 0,
        mean_internal_in=float(np.mean(list(indeg.values()))),
        pagerank_top=top_pr, pagerank_top_excl_hyper=top_pr2, hits_authority_top=top_auth,
        indegree_dist={int(k): int(v) for k, v in dist.items()},
        powerlaw=dict(alpha=float(fit.power_law.alpha), xmin=float(fit.power_law.xmin),
                      vs_lognormal_R=float(R), vs_lognormal_p=float(p),
                      vs_exponential_R=float(R2), vs_exponential_p=float(p2)),
        flow_matrix=M.to_dict(), self_citation_share=self_share,
        lag_hist={int(k): int(v) for k, v in pd.Series(lag).value_counts().sort_index().items()},
        median_lag=float(np.median(lag)) if len(lag) else None,
        scope_counts=e.scope.value_counts().to_dict(),
    ), G, pr


def export_graph(G: nx.DiGraph, pr: dict, papers: pd.DataFrame, pinst: dict) -> dict:
    """Web payload: papers with >= 1 internal citation edge (the visible structure)."""
    nodes = [n for n in G if G.degree(n) > 0]
    edges = [(a, b) for a, b in G.edges() if a in set(nodes) and b in set(nodes)]
    pos = layout(nodes, edges)
    out_nodes = []
    for n in nodes:
        p = papers.loc[n]
        out_nodes.append(dict(id=n, x=pos[n][0], y=pos[n][1], pr=round(pr[n] * 1e4, 3),
                              inst=(pinst.get(n) or ["?"])[0], multi=len(pinst.get(n, [])) > 1,
                              year=int(p.year), t=p.title[:140], j=p.source_name, c=int(p.cited_by_count),
                              indeg=G.in_degree(n), f=p.field, h=bool(p.hyperauthored), doi=p.doi))
    return dict(nodes=out_nodes, edges=[[a, b] for a, b in edges])


def main():
    e, papers, pinst = build_edges()
    res, G, pr = analyse(e, papers, pinst)
    graph = export_graph(G, pr, papers, pinst)
    (INTERIM / "citation_stats.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    (INTERIM / "citation_graph.json").write_text(json.dumps(graph, default=str), encoding="utf-8")
    print({k: res[k] for k in ["nodes", "edges", "giant_wcc_share", "self_citation_share", "median_lag"]})
    print("powerlaw", res["powerlaw"])
    print("graph payload", len(graph["nodes"]), "nodes", len(graph["edges"]), "edges")


if __name__ == "__main__":
    main()
