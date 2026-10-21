"""Write the dashboard's data contract (web/public/data/*.json) from the pipeline outputs.

Mirrors web/src/lib/types.ts. Also copies the four submission CSVs into
web/public/data/downloads/ and simplifies the India boundary for the partner map.
"""
from __future__ import annotations

import json
import math
import shutil

import pandas as pd
from shapely.geometry import mapping, shape

from .config import EXTERNAL, FINAL, GROUP, INTERIM, WEB_DATA, cfg, inst_by_key, institutions
from .networks.connections import ruzicka, topic_profile

SHORT = {"IISERB": "Bhopal", "IISERM": "Mohali", "IISERTVM": "TVM"}
COLOR = {"IISERB": "#c266b8", "IISERM": "#c9802a", "IISERTVM": "#3a93d6"}


def clean(o):
    """NaN/inf -> None so the JSON is valid."""
    if isinstance(o, float):
        return None if math.isnan(o) or math.isinf(o) else round(o, 6)
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [clean(v) for v in o]
    if hasattr(o, "item"):
        return clean(o.item())
    return o


def write(name: str, obj) -> None:
    (WEB_DATA / name).write_text(json.dumps(clean(obj), separators=(",", ":"), default=str), encoding="utf-8")
    print(f"  {name:24s} {(WEB_DATA / name).stat().st_size / 1024:8.1f} KB")


def read(name: str):
    return json.loads((INTERIM / name).read_text(encoding="utf-8"))


def india_geo() -> dict:
    g = json.loads((EXTERNAL / "raw" / "india-composite.geojson").read_text(encoding="utf-8"))
    feats = []
    for f in g["features"]:
        geom = shape(f["geometry"]).simplify(0.03, preserve_topology=True)
        m = json.loads(json.dumps(mapping(geom)), parse_float=lambda x: round(float(x), 3))
        feats.append({"type": "Feature", "properties": {"name": "India"}, "geometry": m})
    return {"type": "FeatureCollection", "features": feats}


def insights(stats, cit, co, conn, papers) -> list[dict]:
    B = stats["institutes"]
    out = []
    hp = papers[papers.hyperauthored]
    share = hp.cited_by_count.sum() / max(papers.cited_by_count.sum(), 1)
    out.append(dict(title="A few giant papers, most of the citations",
                    body=f"{len(hp)} papers with more than {cfg()['hyperauthor_cap']} authors ({len(hp) / len(papers):.1%} of output) "
                         f"hold {share:.0%} of all citations. Field-weighted impact tells a fairer story.",
                    page="journals"))
    fastest = max(inst_by_key(), key=lambda k: B[k]["cagr"] or -1)
    out.append(dict(title="Who is growing fastest",
                    body=f"IISER {SHORT[fastest]} grew its affiliated output by {B[fastest]['cagr']:.1%} a year (2016→2025), "
                         f"against {B['ALL']['cagr']:.1%} for the three institutes together.",
                    page="institutes"))
    out.append(dict(title="Collaboration follows departments",
                    body=f"The {co['leiden_communities']} Leiden communities match departments with NMI {co['nmi_department']:.2f}; "
                         f"only {co['cross_institute_edges']} of {co['edges']} faculty ties cross between the three IISERs.",
                    page="collaboration"))
    ratios = {k: conn[k]["impact_ratio"] or 0 for k in inst_by_key()}
    best, worst = max(ratios, key=ratios.get), min(ratios, key=ratios.get)
    if ratios[best] >= 1:
        title = f"IISER {SHORT[best]} is a net exporter"
    else:
        title = "We cite India more than India cites us"
    out.append(dict(title=title,
                    body=f"Citation in/out ratio with other Indian institutes runs from {ratios[worst]:.2f} (IISER {SHORT[worst]}) "
                         f"to {ratios[best]:.2f} (IISER {SHORT[best]}): {conn[best]['citations_in']:,} citations in vs "
                         f"{conn[best]['citations_out']:,} out for {SHORT[best]}.",
                    page="connectivity"))
    lp = co["link_prediction"]
    if lp["auc"].get("adamic_adar"):
        out.append(dict(title="New collaborations are predictable",
                        body=f"Shared co-authors before {lp['split_year']} predict which faculty pairs start working together later "
                             f"(Adamic–Adar AUC {lp['auc']['adamic_adar']:.2f} on {lp['positives']} new ties).",
                        page="collaboration"))
    pl = cit["powerlaw"]
    tail = ("a log-normal tail fits better than a power law" if pl["vs_lognormal_R"] < 0 and pl["vs_lognormal_p"] < 0.1
            else f"in-degree follows a power law (alpha {pl['alpha']:.2f})")
    out.append(dict(title="Three islands of citation",
                    body=f"{cit['self_citation_share']:.0%} of citations between the three IISERs' papers stay inside one institute; "
                         f"{tail}.",
                    page="citation"))
    return out


def main():
    stats = read("stats.json")
    cit = read("citation_stats.json")
    co = read("coauthor_stats.json")
    conn = read("connections_stats.json")
    nodes = read("coauthor_nodes.json")
    ego = read("ego.json")
    fac = pd.read_json(INTERIM / "faculty_stats.json")
    matched = pd.read_csv(INTERIM / "faculty_matched.csv")
    papers = pd.read_parquet(INTERIM / "papers_enriched.parquet")
    data = pd.read_csv(FINAL / f"group{GROUP}_data.csv")
    dept = pd.read_csv(INTERIM / "department_stats.csv")

    WEB_DATA.mkdir(parents=True, exist_ok=True)
    print("web/public/data:")

    # faculty: stats + network metrics + top co-authors
    recs = []
    for r in fac.to_dict("records"):
        r.update(nodes.get(r["key"], {}))
        co_list = []
        for aid in (r["openalex_ids"] or "").split(";"):
            co_list += ego.get(r["key"], []) or ego.get(aid, [])
        r["coauthors"] = sorted({c["name"]: c for c in co_list}.values(), key=lambda c: -c["papers"])[:12]
        recs.append(r)
    write("faculty.json", recs)

    write("institutes.json", {"institutes": stats["institutes"], "tests": stats["tests"], "h_hist": stats["h_hist"],
                              "departments": dept.to_dict("records")})
    write("citation.json", cit)
    shutil.copy(INTERIM / "citation_graph.json", WEB_DATA / "citation_graph.json")
    write("coauthor.json", co)
    shutil.copy(INTERIM / "coauthor_graph.json", WEB_DATA / "coauthor_graph.json")
    write("connections.json", conn)
    write("insights.json", insights(stats, cit, co, conn, papers[papers.work_id.isin(set(data[data.affiliated].work_id))]))
    write("india.json", india_geo())

    # portfolio similarity between our three IISERs
    prof = {k: topic_profile(v["openalex"]) for k, v in inst_by_key().items()}
    keys = list(prof)
    pairs = [dict(a=a, b=b, ruzicka=ruzicka(prof[a][1], prof[b][1]),
                  jaccard=len(prof[a][0] & prof[b][0]) / len(prof[a][0] | prof[b][0]))
             for i, a in enumerate(keys) for b in keys[i + 1:]]
    write("areas.json", {"pairs": pairs})

    # global search index
    items = [dict(k="f", id=r["key"], label=r["name"], sub=f"{r['department']} · IISER {SHORT[r['institution']]}",
                  inst=r["institution"]) for r in recs]
    aff = papers[papers.work_id.isin(set(data[data.affiliated].work_id))]
    for p in aff.sort_values("cited_by_count", ascending=False).head(3000).itertuples():
        items.append(dict(k="p", id=p.doi or p.work_id, label=p.title, sub=f"{p.source_name} · {p.year} · {p.cited_by_count} citations"))
    for j, n in aff.source_name.value_counts().head(300).items():
        items.append(dict(k="j", id=j, label=j, sub=f"{n} papers"))
    write("search.json", items)

    # downloads: the raw data is kept private (instructor's request) -- never in git, never in the
    # deployed site. With a Google Drive link configured every download points there; without one
    # (local preview) the CSVs are copied next to the dashboard in a gitignored folder.
    files = [(f"group{GROUP}_data.csv", "one row per faculty × paper, 14 spec columns + extras"),
             ("citation_network.csv", "directed paper → paper edges, internal + Indian in/out"),
             ("authorship_network.csv", "co-author pairs involving our faculty"),
             ("indian_connections.csv", "partner institutes: shared papers and citation flow")]
    drive = cfg().get("drive_url")
    dl = WEB_DATA / "downloads"
    if drive and dl.exists():
        shutil.rmtree(dl)
    downloads = []
    for f, desc in files:
        if drive:
            url = drive
        else:
            dl.mkdir(exist_ok=True)
            shutil.copy(FINAL / f, dl / f)
            url = f"./data/downloads/{f}"
        downloads.append(dict(label=f, file=f, url=url, desc=desc,
                              rows=sum(1 for _ in open(FINAL / f, encoding="utf-8")) - 1))

    jr = papers[papers.type == "journal"]
    conn_df = pd.read_csv(FINAL / "indian_connections.csv")
    meta = dict(
        generated=pd.Timestamp.now().strftime("%d %b %Y, %H:%M"), group=GROUP,
        institutes=[dict(key=i["key"], name=i["name"], short=SHORT[i["key"]], city=i["city"], color=COLOR[i["key"]],
                         openalex=i["openalex"], ror=i["ror"], lat=i["lat"], lon=i["lon"]) for i in institutions()],
        counts=dict(faculty_listed=len(matched), faculty_matched=int((matched.author_ids.fillna("") != "").sum()),
                    papers=int(data.work_id.nunique()), rows=len(data), citations=int(papers.cited_by_count.sum()),
                    citation_edges=downloads[1]["rows"], coauthor_pairs=downloads[2]["rows"],
                    partners=int(conn_df[(conn_df.shared_papers > 0) & ~conn_df.partner_is_group20].partner_id.nunique()),
                    linked_institutes=int(conn_df.partner_id.nunique())),
        coverage=dict(faculty_match=float((matched.author_ids.fillna("") != "").mean()), doi=float(papers.doi.notna().mean()),
                      quartile=float(jr.sjr_quartile.notna().mean()), affiliated_rows=float(data.affiliated.mean())),
        hyperauthor_cap=cfg()["hyperauthor_cap"], openalex_spend_note="", downloads=downloads,
        links=dict(repo=cfg().get("repo_url") or "", dashboard=cfg().get("dashboard_url") or "",
                   drive=cfg().get("drive_url") or ""),
    )
    write("meta.json", meta)


if __name__ == "__main__":
    main()
