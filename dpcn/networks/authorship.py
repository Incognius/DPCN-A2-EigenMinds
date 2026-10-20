"""Undirected co-authorship network (nodes = faculty, edge = co-authored a paper).

Analysis graph: our 396 matched faculty across the three IISERs; edge weight = joint papers.
Papers with more than `hyperauthor_cap` authors are left out of the graph (one Planck paper
would otherwise wire every astrophysicist to every other); the sensitivity is reported.

Raw file authorship_network.csv: every co-author pair that involves at least one of our
faculty, from every paper up to the cap; for hyper-authored papers only faculty-faculty pairs.
Columns: author_a, author_b, paper_doi, inst_a, inst_b, year (+ ids, faculty flags, cross flag).
"""
from __future__ import annotations

import itertools
import json
from collections import Counter, defaultdict

import igraph as ig
import leidenalg
import networkx as nx
import numpy as np
import pandas as pd
from community import community_louvain
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score, roc_auc_score

from ..config import FINAL, INTERIM, cfg, inst_by_key
from .common import doi_or_id, layout

CAP = cfg()["hyperauthor_cap"]


def load():
    fp = pd.read_parquet(INTERIM / "faculty_papers.parquet")
    auths = pd.read_parquet(INTERIM / "authorships.parquet")
    papers = pd.read_parquet(INTERIM / "papers_enriched.parquet").set_index("work_id")
    fac = pd.read_csv(INTERIM / "faculty_matched.csv")
    fac = fac[fac.author_ids.fillna("") != ""]
    return fp, auths, papers, fac


def raw_pairs(fp, auths, papers, fac) -> pd.DataFrame:
    id2key = {a: f"{r.institution}|{r['name']}" for _, r in fac.iterrows() for a in r.author_ids.split(";")}
    key2name = {f"{r.institution}|{r['name']}": r["name"] for _, r in fac.iterrows()}
    # our three IISERs always appear under the dataset's names ("IISER Bhopal"), whoever the author is
    ours = {v["openalex"]: v["name"] for v in inst_by_key().values()}
    key2inst = {f"{r.institution}|{r['name']}": (inst_by_key()[r.institution]["name"],
                                                 inst_by_key()[r.institution]["openalex"]) for _, r in fac.iterrows()}
    rows = []
    for wid, g in auths[auths.work_id.isin(set(fp.work_id))].groupby("work_id"):
        p = papers.loc[wid]
        people = []
        for a in g.itertuples():
            k = id2key.get(a.author_id)
            if k:
                inst, iid = key2inst[k]
            else:
                inst = a.inst_names[0] if len(a.inst_names) else None
                iid = a.inst_ids[0] if len(a.inst_ids) else None
                inst = ours.get(iid, inst)
            people.append(dict(id=k or a.author_id, name=key2name.get(k, a.author_name), fac=k is not None,
                               inst=inst, iid=iid))
        people = list({p_["id"]: p_ for p_ in people}.values())
        if len(people) > CAP:
            people = [x for x in people if x["fac"]]
        for x, y in itertools.combinations(people, 2):
            if not (x["fac"] or y["fac"]):
                continue
            if y["fac"] and not x["fac"]:
                x, y = y, x
            rows.append(dict(author_a=x["name"], author_b=y["name"], paper_doi=doi_or_id(p.doi, wid),
                             inst_a=x["inst"], inst_b=y["inst"], year=int(p.year),
                             author_a_id=x["id"], author_b_id=y["id"], a_is_faculty=x["fac"],
                             b_is_faculty=y["fac"], work_id=wid, n_authors=int(p.n_authors),
                             cross_institution=bool(x["iid"] and y["iid"] and x["iid"] != y["iid"])))
    df = pd.DataFrame(rows)
    df.to_csv(FINAL / "authorship_network.csv", index=False)
    print(f"authorship_network.csv: {len(df)} pairs, faculty-faculty {(df.a_is_faculty & df.b_is_faculty).sum()}, "
          f"cross-institution {df.cross_institution.mean():.1%}")
    return df


def faculty_graph(pairs: pd.DataFrame, fac: pd.DataFrame, max_authors=CAP) -> nx.Graph:
    ff = pairs[pairs.a_is_faculty & pairs.b_is_faculty & (pairs.n_authors <= max_authors)]
    G = nx.Graph()
    for _, r in fac.iterrows():
        G.add_node(f"{r.institution}|{r['name']}", name=r["name"], inst=r.institution, dept=r.department)
    for (a, b), g in ff.groupby(["author_a_id", "author_b_id"]):
        if a == b:
            continue
        w = g.work_id.nunique()
        if G.has_edge(a, b):
            G[a][b]["weight"] += w
        else:
            G.add_edge(a, b, weight=w, first_year=int(g.year.min()))
    return G


def communities(G: nx.Graph):
    nodes = list(G)
    idx = {n: i for i, n in enumerate(nodes)}
    ig_g = ig.Graph(n=len(nodes), edges=[(idx[a], idx[b]) for a, b in G.edges()])
    ig_g.es["weight"] = [G[a][b]["weight"] for a, b in G.edges()]
    part = leidenalg.find_partition(ig_g, leidenalg.ModularityVertexPartition, weights="weight", seed=42)
    leiden = {nodes[i]: c for c, members in enumerate(part) for i in members}
    louv = community_louvain.best_partition(G, weight="weight", random_state=42)
    return leiden, part.modularity, louv, community_louvain.modularity(louv, G, weight="weight")


def small_world(G: nx.Graph, n_null=50, seed=1) -> dict:
    """sigma = (C/C_null)/(L/L_null) against configuration-model graphs with the same degrees.
    Averaged over 50 nulls (a handful made sigma swing by +-1 between runs); the spread is reported."""
    H = G.subgraph(max(nx.connected_components(G), key=len)).copy()
    C, L = nx.average_clustering(H), nx.average_shortest_path_length(H)
    rng = np.random.default_rng(seed)
    degs = sorted(d for _, d in H.degree())
    Cr, Lr, sig = [], [], []
    for _ in range(n_null):
        R = nx.Graph(nx.configuration_model(degs, seed=int(rng.integers(1e9))))
        R.remove_edges_from(nx.selfloop_edges(R))
        R = R.subgraph(max(nx.connected_components(R), key=len))
        c, l = nx.average_clustering(R), nx.average_shortest_path_length(R)
        Cr.append(c); Lr.append(l)
        if c > 0:
            sig.append((C / c) / (L / l))
    sigma = (C / np.mean(Cr)) / (L / np.mean(Lr))
    return dict(giant_nodes=H.number_of_nodes(), C=C, L=L, C_null=float(np.mean(Cr)),
                L_null=float(np.mean(Lr)), sigma=float(sigma),
                sigma_p05=float(np.percentile(sig, 5)), sigma_p95=float(np.percentile(sig, 95)), n_null=n_null)


def temporal(pairs: pd.DataFrame, fac: pd.DataFrame) -> list[dict]:
    out = []
    for y in range(2016, 2027):
        G = faculty_graph(pairs[pairs.year <= y], fac)
        G.remove_nodes_from([n for n in list(G) if G.degree(n) == 0])
        if G.number_of_edges() == 0:
            continue
        giant = max(nx.connected_components(G), key=len)
        _, q, _, _ = communities(G)
        cross = sum(1 for a, b in G.edges() if G.nodes[a]["inst"] != G.nodes[b]["inst"])
        out.append(dict(year=y, active_faculty=G.number_of_nodes(), edges=G.number_of_edges(),
                        mean_degree=2 * G.number_of_edges() / G.number_of_nodes(),
                        giant_share=len(giant) / G.number_of_nodes(), modularity=q,
                        cross_inst_edges=cross))
    return out


def link_prediction(pairs: pd.DataFrame, fac: pd.DataFrame, split=2022) -> dict:
    """Train on co-authorships up to `split`, score faculty pairs that first collaborate after it."""
    G0 = faculty_graph(pairs[pairs.year <= split], fac)
    G1 = faculty_graph(pairs, fac)
    new = {tuple(sorted(e)) for e in G1.edges() if not G0.has_edge(*e)}
    active = [n for n in G0 if G0.degree(n) > 0]
    cand = [tuple(sorted(p)) for p in itertools.combinations(active, 2) if not G0.has_edge(*p)]
    y = np.array([p in new for p in cand])
    scores = {}
    for name, fn in [("adamic_adar", nx.adamic_adar_index), ("jaccard", nx.jaccard_coefficient),
                     ("pref_attachment", nx.preferential_attachment),
                     ("resource_alloc", nx.resource_allocation_index)]:
        s = np.array([v for _, _, v in fn(G0, cand)])
        scores[name] = float(roc_auc_score(y, s)) if y.any() else None
    same_dept = np.array([G0.nodes[a]["dept"] == G0.nodes[b]["dept"] and G0.nodes[a]["inst"] == G0.nodes[b]["inst"]
                          for a, b in cand])
    scores["same_department"] = float(roc_auc_score(y, same_dept)) if y.any() else None
    aa = dict(((a, b), v) for a, b, v in nx.adamic_adar_index(G0, cand))
    top = sorted(((v, a, b) for (a, b), v in aa.items() if v > 0), reverse=True)[:15]
    return dict(split_year=split, candidates=len(cand), positives=int(y.sum()), auc=scores,
                top_predictions=[dict(a=a.split("|")[1], b=b.split("|")[1], score=round(v, 3),
                                      realised=(a, b) in new) for v, a, b in top])


def analyse(G: nx.Graph, pairs: pd.DataFrame, fac: pd.DataFrame) -> tuple[dict, dict]:
    leiden, q_leiden, louv, q_louv = communities(G)
    nx.set_node_attributes(G, leiden, "community")
    deg = dict(G.degree())
    strength = dict(G.degree(weight="weight"))
    dist = {(a, b): 1 / d["weight"] for a, b, d in G.edges(data=True)}
    nx.set_edge_attributes(G, dist, "dist")
    btw = nx.betweenness_centrality(G, weight="dist", normalized=True)
    # eigenvector centrality is only defined per component: compute it on the giant component
    giant = G.subgraph(max(nx.connected_components(G), key=len))
    eig = {n: 0.0 for n in G} | nx.eigenvector_centrality_numpy(giant, weight="weight")
    clus = nx.clustering(G)
    core = nx.core_number(G)
    connected = [n for n in G if deg[n] > 0]
    dept_lab = [f"{G.nodes[n]['inst']}|{G.nodes[n]['dept']}" for n in connected]
    inst_lab = [G.nodes[n]["inst"] for n in connected]
    comm_lab = [leiden[n] for n in connected]

    def top(d, k=10):
        return [dict(name=G.nodes[n]["name"], inst=G.nodes[n]["inst"], dept=G.nodes[n]["dept"],
                     value=round(float(v), 4)) for n, v in sorted(d.items(), key=lambda x: -x[1])[:k]]

    # bridges: faculty whose neighbours span several departments / institutes
    bridges = []
    for n in connected:
        nb = list(G.neighbors(n))
        bridges.append(dict(name=G.nodes[n]["name"], inst=G.nodes[n]["inst"], dept=G.nodes[n]["dept"],
                            other_depts=len({(G.nodes[m]["inst"], G.nodes[m]["dept"]) for m in nb}
                                            - {(G.nodes[n]["inst"], G.nodes[n]["dept"])}),
                            other_insts=len({G.nodes[m]["inst"] for m in nb} - {G.nodes[n]["inst"]}),
                            betweenness=btw[n]))
    bridges = sorted(bridges, key=lambda r: (-r["other_depts"], -r["betweenness"]))[:12]

    comm_sizes = Counter(leiden[n] for n in connected)
    comm_summary = []
    for c, size in comm_sizes.most_common(12):
        members = [n for n in connected if leiden[n] == c]
        dc = Counter(f"{G.nodes[m]['inst']} · {G.nodes[m]['dept']}" for m in members)
        comm_summary.append(dict(community=c, size=size, purity=dc.most_common(1)[0][1] / size,
                                 top_groups=dc.most_common(3),
                                 insts=dict(Counter(G.nodes[m]["inst"] for m in members))))

    G_all = faculty_graph(pairs, fac, max_authors=10**6)        # sensitivity: keep hyper-authored
    rc = nx.rich_club_coefficient(nx.Graph(G.subgraph(connected)), normalized=False)
    cross_edges = [(a, b) for a, b in G.edges() if G.nodes[a]["inst"] != G.nodes[b]["inst"]]
    res = dict(
        nodes=G.number_of_nodes(), connected=len(connected), edges=G.number_of_edges(),
        isolates=G.number_of_nodes() - len(connected), density=nx.density(G),
        mean_degree=float(np.mean([deg[n] for n in connected])),
        components=nx.number_connected_components(G.subgraph(connected)),
        giant_share=len(max(nx.connected_components(G.subgraph(connected)), key=len)) / max(len(connected), 1),
        avg_clustering=float(np.mean([clus[n] for n in connected])),
        transitivity=nx.transitivity(G), max_kcore=max(core.values()),
        leiden_communities=len(comm_sizes), leiden_modularity=q_leiden,
        louvain_communities=len(set(louv[n] for n in connected)), louvain_modularity=q_louv,
        nmi_department=normalized_mutual_info_score(dept_lab, comm_lab),
        ari_department=adjusted_rand_score(dept_lab, comm_lab),
        nmi_institute=normalized_mutual_info_score(inst_lab, comm_lab),
        assortativity_department=nx.attribute_assortativity_coefficient(
            G.subgraph(connected), "dept"),
        assortativity_institute=nx.attribute_assortativity_coefficient(G.subgraph(connected), "inst"),
        degree_assortativity=nx.degree_assortativity_coefficient(G.subgraph(connected)),
        cross_institute_edges=len(cross_edges),
        cross_institute_pairs=[dict(a=G.nodes[a]["name"], ia=G.nodes[a]["inst"], b=G.nodes[b]["name"],
                                    ib=G.nodes[b]["inst"], w=G[a][b]["weight"]) for a, b in cross_edges],
        top_degree=top(deg), top_strength=top(strength), top_betweenness=top(btw), top_eigenvector=top(eig),
        bridges=bridges, communities=comm_summary,
        rich_club={int(k): float(v) for k, v in rc.items() if k <= 20},
        degree_hist={int(k): int(v) for k, v in Counter(deg[n] for n in connected).items()},
        small_world=small_world(G.subgraph(connected)),
        with_hyperauthored=dict(edges=G_all.number_of_edges(),
                                mean_degree=2 * G_all.number_of_edges() / max(sum(1 for n in G_all if G_all.degree(n)), 1)),
        temporal=temporal(pairs, fac),
        link_prediction=link_prediction(pairs, fac),
    )
    node_metrics = {n: dict(degree=deg[n], strength=strength[n], betweenness=btw[n], eigenvector=eig.get(n, 0),
                            clustering=clus[n], core=core[n], community=leiden[n]) for n in G}
    return res, node_metrics


def export_graph(G: nx.Graph, nm: dict) -> dict:
    nodes = [n for n in G if G.degree(n) > 0]
    edges = [(a, b) for a, b in G.edges()]
    pos = layout(nodes, edges, weights=[G[a][b]["weight"] for a, b in edges])
    return dict(
        nodes=[dict(id=n, x=pos[n][0], y=pos[n][1], name=G.nodes[n]["name"], inst=G.nodes[n]["inst"],
                    dept=G.nodes[n]["dept"], **{k: (round(v, 5) if isinstance(v, float) else v)
                                                for k, v in nm[n].items()}) for n in nodes],
        edges=[[a, b, G[a][b]["weight"], int(G.nodes[a]["inst"] != G.nodes[b]["inst"])] for a, b in edges])


def ego_lists(pairs: pd.DataFrame) -> dict:
    """Top co-authors (any institution) per faculty member, for the faculty drawer."""
    small = pairs[pairs.n_authors <= CAP]
    out = defaultdict(list)
    for a, g in small.groupby("author_a_id"):
        c = g.groupby(["author_b", "inst_b"]).work_id.nunique().sort_values(ascending=False).head(12)
        out[a] = [dict(name=n, inst=i, papers=int(v)) for (n, i), v in c.items()]
    return out


def main():
    fp, auths, papers, fac = load()
    pairs = raw_pairs(fp, auths, papers, fac)
    G = faculty_graph(pairs, fac)
    res, nm = analyse(G, pairs, fac)
    (INTERIM / "coauthor_stats.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    (INTERIM / "coauthor_graph.json").write_text(json.dumps(export_graph(G, nm), default=str), encoding="utf-8")
    (INTERIM / "coauthor_nodes.json").write_text(json.dumps(nm, default=str), encoding="utf-8")
    (INTERIM / "ego.json").write_text(json.dumps(ego_lists(pairs), default=str), encoding="utf-8")
    keys = ["nodes", "connected", "edges", "leiden_communities", "leiden_modularity", "nmi_department",
            "ari_department", "assortativity_department", "assortativity_institute", "cross_institute_edges"]
    print({k: res[k] for k in keys})
    print("small world", res["small_world"])
    print("link prediction", res["link_prediction"]["auc"], res["link_prediction"]["positives"])


if __name__ == "__main__":
    main()
