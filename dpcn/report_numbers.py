"""Write report/numbers.tex: every number quoted in the report as a LaTeX macro, straight from the
pipeline outputs, so the text can never drift from the data."""
from __future__ import annotations

import json

import pandas as pd

from .config import FINAL, GROUP, INTERIM, ROOT

KEYS = {"IISERB": "B", "IISERM": "M", "IISERTVM": "T", "ALL": "All"}


def tex_escape(s: str) -> str:
    for a, b in [("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"),
                 ("_", r"\_"), ("{", r"\{"), ("}", r"\}"), ("~", r"\textasciitilde{}"), ("^", r"\^{}")]:
        s = s.replace(a, b)
    return s


def main():
    st = json.loads((INTERIM / "stats.json").read_text(encoding="utf-8"))
    cs = json.loads((INTERIM / "citation_stats.json").read_text(encoding="utf-8"))
    co = json.loads((INTERIM / "coauthor_stats.json").read_text(encoding="utf-8"))
    cn = json.loads((INTERIM / "connections_stats.json").read_text(encoding="utf-8"))
    meta = json.loads((ROOT / "web" / "public" / "data" / "meta.json").read_text(encoding="utf-8"))
    fac = pd.read_json(INTERIM / "faculty_stats.json")
    data = pd.read_csv(FINAL / f"group{GROUP}_data.csv", low_memory=False)
    m: dict[str, str] = {}

    def num(v, d=0):
        return f"{v:,.{d}f}"

    def pc(v, d=1):
        return f"{100 * v:.{d}f}\\%"

    m["FacListed"] = num(meta["counts"]["faculty_listed"])
    m["FacMatched"] = num(meta["counts"]["faculty_matched"])
    m["FacMatchPct"] = pc(meta["coverage"]["faculty_match"])
    m["Papers"] = num(meta["counts"]["papers"])
    words = "None One Two Three Four Five Six Seven Eight Nine Ten".split()
    m["TopTenPlanck"] = words[sum(str(p["title"]).startswith("Planck")
                                  for p in st["institutes"]["ALL"]["top_cited"][:10])]
    m["Rows"] = num(meta["counts"]["rows"])
    m["AffRowsPct"] = pc(meta["coverage"]["affiliated_rows"], 0)
    m["DoiPct"] = pc(meta["coverage"]["doi"])
    m["QuartPct"] = pc(meta["coverage"]["quartile"])
    m["CitEdges"] = num(meta["counts"]["citation_edges"])
    m["CoPairs"] = num(meta["counts"]["coauthor_pairs"])
    m["PartnerRows"] = num(meta["counts"]["partners"])
    m["HyperCap"] = str(meta["hyperauthor_cap"])

    for k, s in KEYS.items():
        b = st["institutes"][k]
        m[f"Pap{s}"] = num(b["papers"])
        m[f"Cit{s}"] = num(b["citations"])
        m[f"CitNoHyp{s}"] = num(b["citations_excl_hyper"])
        m[f"Hyp{s}"] = num(b["hyperauthored_papers"])
        m[f"QOne{s}"] = pc(b["q1_share"])
        m[f"CAGR{s}"] = pc(b["cagr"] or 0)
        m[f"FWCI{s}"] = num(b["median_fwci"] or 0, 2)
        m[f"TopTen{s}"] = pc(b["top10pct_share"])
        m[f"Intl{s}"] = pc(b["intl_share"], 0)
        m[f"OA{s}"] = pc(b["oa_share"], 0)
        m[f"Gini{s}"] = num(b["gini_citations"], 2)
        m[f"Growth{s}"] = pc(b["trend_nb"].get("annual_growth", 0))
        m[f"GrowthP{s}"] = f"{b['trend_nb'].get('growth_p', 1):.3f}"
        m[f"Covid{s}"] = pc(b["trend_nb"].get("covid_effect", 0))
        m[f"CovidP{s}"] = f"{b['trend_nb'].get('covid_p', 1):.2f}"
        m[f"MK{s}"] = b["mann_kendall"]["trend"]
        m[f"Conf{s}"] = num(b["conference_papers"])
        if k != "ALL":
            h = fac[fac.institution == k].h_index_career.dropna()
            m[f"HMed{s}"] = num(h.median(), 0)
            m[f"NFac{s}"] = num(int((fac.institution == k).sum()))
            c = cn[k]
            m[f"In{s}"] = num(c["citations_in"]); m[f"Out{s}"] = num(c["citations_out"])
            m[f"Ratio{s}"] = num(c["impact_ratio"] or 0, 2)
            m[f"Partners{s}"] = num(c["partners"])
            m[f"TopCiter{s}"] = tex_escape(c["top_citing"][0]["partner_inst"]) if c["top_citing"] else "--"
            m[f"TopPartner{s}"] = tex_escape(c["top_partners"][0]["partner_inst"]) if c["top_partners"] else "--"
            j = b["top_journals"][0]
            m[f"TopJ{s}"] = tex_escape(j["source_name"]); m[f"TopJN{s}"] = num(j["papers"])

    T = st["tests"]
    m["KWH"] = num(T["h_index_kruskal"]["H"], 2); m["KWP"] = f"{T['h_index_kruskal']['p']:.3f}"
    m["ChiSq"] = num(T["quartile_chi2"]["chi2"], 1); m["ChiP"] = f"{T['quartile_chi2']['p']:.2g}"
    m["CramerV"] = num(T["quartile_chi2"]["cramers_v"], 3)
    m["FwciH"] = num(T["fwci_kruskal"]["H"], 1); m["FwciP"] = f"{T['fwci_kruskal']['p']:.2g}"
    m["TeamRho"] = num(T["teamsize_citation_spearman"]["rho"], 2)

    m["CNodes"] = num(cs["nodes"]); m["CEdges"] = num(cs["edges"]); m["CGiant"] = pc(cs["giant_wcc_share"], 0)
    m["CSelf"] = pc(cs["self_citation_share"], 0); m["CLag"] = num(cs["median_lag"] or 0, 0)
    m["CAlpha"] = num(cs["powerlaw"]["alpha"], 2); m["CXmin"] = num(cs["powerlaw"]["xmin"], 0)
    m["CRLN"] = num(cs["powerlaw"]["vs_lognormal_R"], 2); m["CPLN"] = f"{cs['powerlaw']['vs_lognormal_p']:.2f}"
    m["CREXP"] = num(cs["powerlaw"]["vs_exponential_R"], 1); m["CPEXP"] = f"{cs['powerlaw']['vs_exponential_p']:.2g}"
    m["CInIndia"] = num(cs["scope_counts"].get("in_india", 0)); m["COutIndia"] = num(cs["scope_counts"].get("out_india", 0))
    top = cs["pagerank_top"][0]
    m["PRTopTitle"] = tex_escape(top["title"][:90]); m["PRTopYear"] = str(top["year"])
    toph = cs["pagerank_top_excl_hyper"][0]
    m["PRTopCoreTitle"] = tex_escape(toph["title"][:90])

    m["ANodes"] = num(co["nodes"]); m["AConn"] = num(co["connected"]); m["AEdges"] = num(co["edges"])
    m["AIso"] = num(co["isolates"]); m["AMeanDeg"] = num(co["mean_degree"], 1)
    m["AGiant"] = pc(co["giant_share"], 0); m["AClust"] = num(co["avg_clustering"], 2)
    m["ALeiden"] = num(co["leiden_communities"]); m["AQ"] = num(co["leiden_modularity"], 2)
    m["ALouvQ"] = num(co["louvain_modularity"], 2)
    m["ANMI"] = num(co["nmi_department"], 2); m["AARI"] = num(co["ari_department"], 2)
    m["AAssDept"] = num(co["assortativity_department"], 2); m["AAssInst"] = num(co["assortativity_institute"], 2)
    m["ADegAss"] = num(co["degree_assortativity"], 2)
    m["ACross"] = num(co["cross_institute_edges"]); m["AEdgesHyp"] = num(co["with_hyperauthored"]["edges"])
    sw = co["small_world"]
    m["ASigma"] = num(sw["sigma"], 1); m["AC"] = num(sw["C"], 2); m["ACnull"] = num(sw["C_null"], 2)
    m["AL"] = num(sw["L"], 2); m["ALnull"] = num(sw["L_null"], 2)
    m["ACratio"] = num(sw["C"] / sw["C_null"], 0)
    m["ASigmaLo"] = num(sw.get("sigma_p05", sw["sigma"]), 1); m["ASigmaHi"] = num(sw.get("sigma_p95", sw["sigma"]), 1)
    t0, t1 = co["temporal"][0], co["temporal"][-1]
    m["AGiantStart"] = pc(t0["giant_share"], 0); m["AGiantEnd"] = pc(t1["giant_share"], 0)
    m["AModStart"] = num(t0["modularity"], 2); m["AModEnd"] = num(t1["modularity"], 2)
    m["AYearStart"] = str(t0["year"]); m["AYearEnd"] = str(t1["year"])
    for i, r in enumerate(co["top_betweenness"][:3]):
        m[f"ABtw{'ABC'[i]}"] = tex_escape(f"{r['name']} ({r['dept']}, "
                                          f"{ {'IISERB': 'Bhopal', 'IISERM': 'Mohali', 'IISERTVM': 'TVM'}[r['inst']]})")
    for i, r in enumerate(co["top_degree"][:3]):
        m[f"ADeg{'ABC'[i]}"] = tex_escape(f"{r['name']} ({int(r['value'])})")
    lp = co["link_prediction"]
    m["LPSplit"] = str(lp["split_year"]); m["LPPos"] = num(lp["positives"])
    for name, mac in [("adamic_adar", "LPAA"), ("jaccard", "LPJac"), ("pref_attachment", "LPPA"), ("same_department", "LPDept")]:
        m[mac] = num(lp["auc"].get(name) or 0, 2)

    m["DashURL"] = meta["links"]["dashboard"] or "(link added on deployment)"
    m["RepoURL"] = meta["links"]["repo"] or "(link added on deployment)"
    m["Partners"] = num(meta["counts"]["partners"]); m["Linked"] = num(meta["counts"]["linked_institutes"])
    sims = [p["ruzicka"] for p in json.loads((ROOT / "web" / "public" / "data" / "areas.json").read_text())["pairs"]]
    m["SimLo"] = num(min(sims), 2); m["SimHi"] = num(max(sims), 2)
    out = "% generated by dpcn/report_numbers.py -- do not edit\n" + "\n".join(
        f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in m.items()) + "\n"
    (ROOT / "report" / "numbers.tex").write_text(out, encoding="utf-8")
    print(f"report/numbers.tex: {len(m)} macros")
    tables(st, cs, co)


def _short(t: str, n: int) -> str:
    t = " ".join(str(t).split())
    return tex_escape(t if len(t) <= n else t[: n - 1].rstrip() + "…")


# \input inside a tabular cannot be followed by \bottomrule in the parent file, so each
# generated table body closes its own rule
END = "\n\\bottomrule\n"


def tables(st, cs, co):
    """The list-type requirements as small LaTeX tables (report/tab_*.tex)."""
    S = {"IISERB": "Bhopal", "IISERM": "Mohali", "IISERTVM": "TVM"}
    rows = []
    for k, s in S.items():
        for i, j in enumerate(st["institutes"][k]["top_journals"][:5]):
            rows.append(f"{s if i == 0 else ''} & {_short(j['source_name'], 46)} & {j['papers']} & {j['quartile'] or '--'} \\\\")
        rows.append("\\addlinespace[2pt]")
    (ROOT / "report" / "tab_journals.tex").write_text("\n".join(rows[:-1]) + END, encoding="utf-8")

    rows = []
    for i, p in enumerate(st["institutes"]["ALL"]["top_cited"][:10], 1):
        doi = (p.get("doi") or "").replace("https://doi.org/", "")
        rows.append(f"{i} & {_short(p['title'], 62)} & {_short(p['source_name'] or '', 26)} & {p['year']} & "
                    f"{p['cited_by_count']:,} & \\texttt{{\\scriptsize {tex_escape(doi)}}} \\\\")
    (ROOT / "report" / "tab_cited.tex").write_text("\n".join(rows) + END, encoding="utf-8")

    rows = []
    for i, p in enumerate(st["institutes"]["ALL"]["top_cited_excl_hyper"][:5], 1):
        rows.append(f"{i} & {_short(p['title'], 70)} & {_short(p['source_name'] or '', 26)} & {p['year']} & {p['cited_by_count']:,} \\\\")
    (ROOT / "report" / "tab_cited_core.tex").write_text("\n".join(rows) + END, encoding="utf-8")

    rows = []
    for i, p in enumerate(cs["pagerank_top"][:10], 1):
        inst = "/".join(S[k] for k in p.get("inst") or [])
        rows.append(f"{i} & {_short(p['title'], 64)} & {p['year']} & {inst} & {p['internal_in']} & {p['citations']:,} \\\\")
    (ROOT / "report" / "tab_pagerank.tex").write_text("\n".join(rows) + END, encoding="utf-8")

    rows = []
    for i in range(8):
        d, b = co["top_degree"][i], co["top_betweenness"][i]
        rows.append(f"{i + 1} & {tex_escape(d['name'])} ({S[d['inst']]}) & {int(d['value'])} & "
                    f"{tex_escape(b['name'])} ({S[b['inst']]}) & {b['value']:.3f} \\\\")
    (ROOT / "report" / "tab_central.tex").write_text("\n".join(rows) + END, encoding="utf-8")
    print("report/tab_*.tex written")


if __name__ == "__main__":
    main()
