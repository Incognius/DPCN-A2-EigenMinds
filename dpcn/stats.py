"""Faculty / department / institute statistics and the tests that go beyond description.

Institute-level numbers count each paper once (unique work_id) and only papers where at least one
of that institute's faculty lists the institute (`affiliated`). Faculty-level numbers use all of a
faculty member's 2016-2026 papers, with the affiliated subset alongside.

Output: data/interim/stats.json (consumed by export_web.py and figures.py)
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pymannkendall as mk
import scikit_posthocs as sp
import statsmodels.api as sm
from scipy import stats as st

from .config import FINAL, GROUP, INTERIM, YEAR_MAX, YEAR_MIN, inst_by_key

YEARS = list(range(YEAR_MIN, YEAR_MAX + 1))
FULL_YEARS = list(range(YEAR_MIN, YEAR_MAX))           # 2026 is a partial year (data to Oct)


def h_index(cites) -> int:
    c = sorted((int(x) for x in cites), reverse=True)
    return sum(1 for i, x in enumerate(c, 1) if x >= i)


def gini(x) -> float:
    x = np.sort(np.asarray(x, dtype=float))
    if x.sum() == 0:
        return 0.0
    n = len(x)
    return float((2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum()))


def lorenz(x, k=50) -> list[list[float]]:
    x = np.sort(np.asarray(x, dtype=float))
    cum = np.concatenate([[0], np.cumsum(x)]) / max(x.sum(), 1)
    idx = np.linspace(0, len(x), k + 1).astype(int)
    return [[round(i / len(x), 4), round(float(cum[i]), 4)] for i in idx]


def load():
    d = pd.read_csv(FINAL / f"group{GROUP}_data.csv")
    fac = pd.read_csv(INTERIM / "faculty_matched.csv")
    papers = pd.read_parquet(INTERIM / "papers_enriched.parquet")
    auths = pd.read_parquet(INTERIM / "authorships.parquet")
    return d, fac, papers, auths


def institute_papers(d: pd.DataFrame, key: str | None) -> pd.DataFrame:
    sub = d[d.affiliated] if key is None else d[(d.affiliated) & (d.institution_key == key)]
    return sub.drop_duplicates("work_id")


def nb_trend(counts: pd.Series) -> dict:
    """Negative-binomial GLM: papers ~ year + covid(2020-21). Full years only."""
    y = counts.reindex(FULL_YEARS, fill_value=0).astype(float)
    t = np.arange(len(y))
    X = sm.add_constant(np.column_stack([t, np.isin(y.index, [2020, 2021]).astype(float)]))
    try:
        m = sm.GLM(y.values, X, family=sm.families.NegativeBinomial(alpha=0.05)).fit()
        growth = float(np.exp(m.params[1]) - 1)
        return dict(annual_growth=growth, growth_p=float(m.pvalues[1]),
                    covid_effect=float(np.exp(m.params[2]) - 1), covid_p=float(m.pvalues[2]))
    except Exception as e:                                  # pragma: no cover
        return dict(error=str(e))


def institute_block(d, papers, auths, key) -> dict:
    ip = institute_papers(d, key)
    wids = set(ip.work_id)
    pp = papers[papers.work_id.isin(wids)]
    by_year = ip.groupby("year").size().reindex(YEARS, fill_value=0)
    first, last = by_year.loc[YEAR_MIN], by_year.loc[YEAR_MAX - 1]
    cagr = (last / first) ** (1 / (YEAR_MAX - 1 - YEAR_MIN)) - 1 if first else None
    jr = pp[pp.type == "journal"]
    qd = jr.sjr_quartile.value_counts().reindex(["Q1", "Q2", "Q3", "Q4"], fill_value=0)
    q_by_year = (jr.dropna(subset=["sjr_quartile"]).groupby(["year", "sjr_quartile"]).size()
                   .unstack(fill_value=0).reindex(YEARS, fill_value=0))
    core = pp[pp.type == "conference"].core_rank.fillna("Unranked").value_counts()

    # international collaboration: any non-Indian institution on the paper
    a = auths[auths.work_id.isin(wids)]
    intl = a.groupby("work_id").inst_countries.apply(
        lambda s: any(c not in (None, "IN") for lst in s for c in lst))
    mk_res = mk.original_test(by_year.loc[FULL_YEARS].values)

    top_j = (jr.groupby("source_name").agg(papers=("work_id", "size"), citations=("cited_by_count", "sum"),
                                            quartile=("sjr_quartile", lambda s: s.mode().iat[0] if s.notna().any() else None))
               .sort_values(["papers", "citations"], ascending=False).head(10).reset_index())
    top_c = (pp.sort_values("cited_by_count", ascending=False).head(10)
               [["work_id", "title", "source_name", "year", "cited_by_count", "doi", "n_authors", "hyperauthored"]])
    top_c_core = (pp[~pp.hyperauthored].sort_values("cited_by_count", ascending=False).head(10)
                  [["work_id", "title", "source_name", "year", "cited_by_count", "doi", "n_authors"]])
    fields = pp.field.fillna("Unknown").value_counts()
    subfields = (pp.groupby(["domain", "field", "subfield"]).size().rename("n").reset_index()
                   .sort_values("n", ascending=False))
    return dict(
        papers=int(len(ip)), citations=int(pp.cited_by_count.sum()),
        citations_excl_hyper=int(pp[~pp.hyperauthored].cited_by_count.sum()),
        hyperauthored_papers=int(pp.hyperauthored.sum()),
        mean_citations=float(pp.cited_by_count.mean()), median_citations=float(pp.cited_by_count.median()),
        median_fwci=float(pp.fwci.median()) if pp.fwci.notna().any() else None,
        mean_fwci=float(pp.fwci.clip(upper=20).mean()) if pp.fwci.notna().any() else None,
        top10pct_share=float(pp.top_10pct.astype("boolean").fillna(False).mean()),
        oa_share=float(pp.is_oa.astype("boolean").fillna(False).mean()),
        intl_share=float(intl.mean()) if len(intl) else 0.0,
        journal_papers=int(len(jr)), conference_papers=int((pp.type == "conference").sum()),
        quartile_coverage=float(jr.sjr_quartile.notna().mean()) if len(jr) else 0.0,
        quartiles=qd.to_dict(),
        q1_share=float(qd["Q1"] / qd.sum()) if qd.sum() else 0.0,
        q_by_year={int(y): r.to_dict() for y, r in q_by_year.iterrows()},
        core=core.to_dict(),
        by_year={int(k): int(v) for k, v in by_year.items()},
        cites_by_year={int(k): int(v) for k, v in pp.groupby("year").cited_by_count.sum().reindex(YEARS, fill_value=0).items()},
        cagr=float(cagr) if cagr is not None else None,
        trend_nb=nb_trend(by_year),
        mann_kendall=dict(trend=mk_res.trend, p=float(mk_res.p), tau=float(mk_res.Tau),
                          sen_slope=float(mk_res.slope)),
        gini_citations=gini(pp.cited_by_count), lorenz=lorenz(pp.cited_by_count),
        top_journals=top_j.to_dict("records"),
        top_cited=top_c.to_dict("records"), top_cited_excl_hyper=top_c_core.to_dict("records"),
        fields=fields.to_dict(), subfields=subfields.head(60).to_dict("records"),
    )


def faculty_table(d, fac) -> pd.DataFrame:
    rows = []
    for f in fac.itertuples():
        key = f"{f.institution}|{f.name}"
        sub = d[(d.institution_key == f.institution) & (d.author == f.name)]
        aff = sub[sub.affiliated]
        jr = sub[sub.type == "journal"]
        top_j = jr.journal_name.value_counts()
        rows.append(dict(
            key=key, name=f.name, institution=f.institution, department=f.department,
            designation=f.designation if isinstance(f.designation, str) else "",
            openalex_ids=f.author_ids if isinstance(f.author_ids, str) else "",
            match_confidence=f.confidence,
            papers=len(sub), papers_affiliated=len(aff),
            citations=int(sub.citations.sum()), citations_affiliated=int(aff.citations.sum()),
            h_index_window=h_index(sub.citations), h_index_career=int(f.h_index_career) if pd.notna(f.h_index_career) else None,
            i10_career=int(f.i10_index_career) if pd.notna(f.i10_index_career) else None,
            works_career=int(f.works_count_career) if pd.notna(f.works_count_career) else None,
            q1_share=float((jr.sjr_quartile == "Q1").sum() / jr.sjr_quartile.notna().sum()) if jr.sjr_quartile.notna().any() else None,
            top_journal=top_j.index[0] if len(top_j) else None,
            first_author_share=float((sub.author_position == 0).mean()) if len(sub) else None,
            median_fwci=float(sub.fwci.median()) if sub.fwci.notna().any() else None,
            hyperauthored_papers=int(sub.hyperauthored.sum()),
            field=f.field_main if isinstance(f.field_main, str) else None,
            first_year_at_inst=f.first_year_at_inst if pd.notna(f.first_year_at_inst) else None,
            by_year={int(y): int(n) for y, n in sub.groupby("year").size().items()},
        ))
    return pd.DataFrame(rows)


def department_table(d, ft) -> pd.DataFrame:
    rows = []
    for (inst, dept), g in ft.groupby(["institution", "department"]):
        sub = d[(d.institution_key == inst) & (d.department == dept) & d.affiliated].drop_duplicates("work_id")
        jr = sub[sub.type == "journal"]
        rows.append(dict(institution=inst, department=dept, faculty=len(g), papers=len(sub),
                         papers_per_faculty=len(sub) / max(len(g), 1),
                         citations=int(sub.citations.sum()),
                         q1_share=float((jr.sjr_quartile == "Q1").sum() / jr.sjr_quartile.notna().sum()) if jr.sjr_quartile.notna().any() else None,
                         median_h_career=float(g.h_index_career.median()) if g.h_index_career.notna().any() else None,
                         median_h_window=float(g.h_index_window.median())))
    return pd.DataFrame(rows)


def tests(d, ft, papers) -> dict:
    out = {}
    groups = [g.h_index_career.dropna().values for _, g in ft.groupby("institution")]
    kw = st.kruskal(*groups)
    dunn = sp.posthoc_dunn(ft.dropna(subset=["h_index_career"]), val_col="h_index_career",
                           group_col="institution", p_adjust="holm")
    out["h_index_kruskal"] = dict(H=float(kw.statistic), p=float(kw.pvalue),
                                  dunn_holm={f"{a}~{b}": float(dunn.loc[a, b])
                                             for i, a in enumerate(dunn.index) for b in dunn.columns[i + 1:]})
    groups_w = [g.h_index_window.values for _, g in ft.groupby("institution")]
    kw2 = st.kruskal(*groups_w)
    out["h_window_kruskal"] = dict(H=float(kw2.statistic), p=float(kw2.pvalue))

    # quartile mix x institute (unique affiliated journal papers)
    rows = []
    for k in inst_by_key():
        ip = institute_papers(d, k)
        ip = ip[ip.type == "journal"].dropna(subset=["sjr_quartile"])
        rows.append(ip.sjr_quartile.value_counts().reindex(["Q1", "Q2", "Q3", "Q4"], fill_value=0).values)
    chi = st.chi2_contingency(np.array(rows))
    n = np.array(rows).sum()
    out["quartile_chi2"] = dict(chi2=float(chi.statistic), p=float(chi.pvalue), dof=int(chi.dof),
                                cramers_v=float(np.sqrt(chi.statistic / (n * (min(np.array(rows).shape) - 1)))))
    # FWCI by institute (field-normalised, so the physics/biology mix does not drive it)
    fw = [institute_papers(d, k).fwci.dropna().values for k in inst_by_key()]
    kw3 = st.kruskal(*fw)
    out["fwci_kruskal"] = dict(H=float(kw3.statistic), p=float(kw3.pvalue))
    # citations vs team size (log-log Spearman)
    pu = papers.drop_duplicates("work_id")
    rho = st.spearmanr(pu.n_authors, pu.cited_by_count)
    out["teamsize_citation_spearman"] = dict(rho=float(rho.statistic), p=float(rho.pvalue))
    return out


def main() -> dict:
    d, fac, papers, auths = load()
    fac = fac[fac.author_ids.fillna("") != ""]
    res = {"institutes": {}, "generated": pd.Timestamp.now().isoformat(timespec="minutes")}
    for k in inst_by_key():
        res["institutes"][k] = institute_block(d, papers, auths, k)
    res["institutes"]["ALL"] = institute_block(d, papers, auths, None)
    ft = faculty_table(d, fac)
    dt = department_table(d, ft)
    res["tests"] = tests(d, ft, papers)
    res["h_hist"] = {k: np.histogram(g.h_index_career.dropna(), bins=range(0, 105, 5))[0].tolist()
                     for k, g in ft.groupby("institution")}
    ft.to_json(INTERIM / "faculty_stats.json", orient="records")
    dt.to_csv(INTERIM / "department_stats.csv", index=False)
    (INTERIM / "stats.json").write_text(json.dumps(res, default=lambda o: None if o is pd.NA else str(o), indent=1),
                                        encoding="utf-8")
    for k, b in res["institutes"].items():
        print(f"{k:9s} papers={b['papers']:5d} cites={b['citations']:7d} Q1={b['q1_share']:.1%} "
              f"cagr={b['cagr'] or 0:.1%} medFWCI={b['median_fwci']} intl={b['intl_share']:.1%}")
    print(json.dumps(res["tests"], indent=1)[:1500])
    return res


if __name__ == "__main__":
    main()
