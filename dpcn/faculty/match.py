"""Match scraped faculty names to OpenAlex author IDs.

Instead of one paid search per name, we pull every author OpenAlex has ever affiliated with each
IISER (about 7.5k, ~80 cheap list calls) and fuzzy-match locally. OpenAlex often splits one
person into several author profiles; those are merged when they share an ORCID, or carry the
exact same normalised name *and* the same main field (so a student namesake is not merged in).

Inputs : data/interim/faculty_raw.csv, data/manual/faculty_overrides.csv (optional)
Output : data/interim/faculty_matched.csv  (one row per faculty, `author_ids` is ';'-joined)
"""
from __future__ import annotations

import re
import unicodedata

import pandas as pd
from rapidfuzz import fuzz

from .. import openalex as oa
from ..config import INTERIM, MANUAL, inst_by_key

SELECT = ("id,display_name,display_name_alternatives,orcid,works_count,cited_by_count,"
          "summary_stats,affiliations,last_known_institutions,topics")


def norm(name: str) -> str:
    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode()
    s = re.sub(r"[.\-']", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def initials_form(name: str) -> str:
    """'kana m sureshan' -> 'k m sureshan' so initial-only variants line up."""
    parts = norm(name).split()
    return " ".join([p[0] for p in parts[:-1]] + parts[-1:]) if parts else ""


def _surname_ok(fac: list[str], cand: list[str]) -> bool:
    """Faculty's surname (or first token: some sites list surname first) must appear in the candidate."""
    squashed = "".join(cand)
    last, first = fac[-1], fac[0]
    if len(last) > 1 and (last in cand or (len(last) > 3 and last in squashed)
                          or any(fuzz.ratio(last, c) >= 88 for c in cand if len(c) > 1)):
        return True
    return len(first) > 1 and first in cand and len(fac) > 1 and fac[-1] in "".join(cand[:1])


def name_score(a: str, b: str) -> float:
    na, nb = norm(a), norm(b)
    ta, tb = na.split(), nb.split()
    if not ta or not tb:
        return 0.0
    if len(ta) == 1 or len(tb) == 1:                      # mononyms: exact only
        return 100.0 if na == nb else 0.0
    if not _surname_ok(ta, tb):
        return 0.0
    # given names must agree too (Ankan/Ayan Ghosh are different people); initials are wildcards
    ga = [t for t in ta[:-1] if len(t) > 1] or ta[1:]
    gb = [t for t in tb if len(t) > 1]
    if ga and gb and all(len(t) > 1 for t in ta[:1]) and len(tb[0]) > 1:
        if not any(fuzz.ratio(x, y) >= 85 or x in "".join(gb) for x in ga for y in gb):
            return 0.0
    s = max(fuzz.token_sort_ratio(na, nb),
            fuzz.ratio("".join(sorted(ta)), "".join(sorted(tb))))
    if ta[0] == tb[0] and ta[-1] == tb[-1]:               # middle name dropped / added
        s = max(s, 92)
    uses_initials = any(len(t) == 1 for t in ta + tb)
    if uses_initials and initials_form(na) == initials_form(nb):
        s = max(s, 90)
    return float(s)


def fetch_authors(inst_id: str) -> pd.DataFrame:
    rows = []
    for a in oa.paginate("/authors", {"filter": f"affiliations.institution.id:{inst_id}",
                                      "select": SELECT}):
        years = sorted({y for af in a.get("affiliations") or []
                        if oa.short_id(af["institution"]["id"]) == inst_id for y in af.get("years", [])})
        topics = a.get("topics") or []
        rows.append(dict(
            author_id=oa.short_id(a["id"]), display_name=a["display_name"],
            alternatives=a.get("display_name_alternatives") or [],
            orcid=a.get("orcid"), works_count=a.get("works_count", 0),
            cited_by_count=a.get("cited_by_count", 0),
            h_index=(a.get("summary_stats") or {}).get("h_index"),
            i10_index=(a.get("summary_stats") or {}).get("i10_index"),
            inst_years=years, first_year=min(years) if years else None,
            last_year=max(years) if years else None,
            field=topics[0]["field"]["display_name"] if topics else None,
        ))
    return pd.DataFrame(rows)


def best_matches(fac: pd.Series, cands: pd.DataFrame) -> pd.DataFrame:
    def score(r):
        # aliases are noisy (initial-only variants collide), so an alias must be a near-exact hit
        alt = max((name_score(fac["name"], n) for n in r.alternatives[:20]), default=0)
        return max(name_score(fac["name"], r.display_name), alt - 5 if alt >= 95 else 0)
    c = cands.assign(score=cands.apply(score, axis=1))
    c = c[c.score >= 80]
    # common names have namesakes (often students) at the same institute: among equally good
    # name matches prefer the profile whose field fits the department, then the larger profile
    c = c.assign(plausible=[field_plausible(fac["department"], f) for f in c.field])
    return c.sort_values(["score", "plausible", "works_count"], ascending=False)


# OpenAlex top-level fields that are plausible for each department family (keyword on dept name)
DEPT_FIELDS = {
    "biolog": {"Biochemistry, Genetics and Molecular Biology", "Agricultural and Biological Sciences",
               "Immunology and Microbiology", "Neuroscience", "Medicine", "Environmental Science",
               "Pharmacology, Toxicology and Pharmaceutics"},
    "chemical eng": {"Chemical Engineering", "Materials Science", "Chemistry", "Engineering", "Energy",
                     "Environmental Science"},
    "chemi": {"Chemistry", "Materials Science", "Chemical Engineering", "Physics and Astronomy",
              "Biochemistry, Genetics and Molecular Biology", "Energy"},
    "physic": {"Physics and Astronomy", "Materials Science", "Mathematics", "Engineering", "Chemistry",
               "Earth and Planetary Sciences", "Computer Science"},
    "math": {"Mathematics", "Computer Science", "Physics and Astronomy", "Decision Sciences"},
    "earth": {"Earth and Planetary Sciences", "Environmental Science", "Agricultural and Biological Sciences",
              "Engineering", "Physics and Astronomy", "Energy"},
    "data": {"Computer Science", "Engineering", "Mathematics", "Decision Sciences", "Physics and Astronomy"},
    "electrical": {"Computer Science", "Engineering", "Mathematics", "Physics and Astronomy",
                   "Materials Science", "Decision Sciences"},
    "econom": {"Economics, Econometrics and Finance", "Social Sciences", "Business, Management and Accounting",
               "Decision Sciences"},
    "human": {"Arts and Humanities", "Social Sciences", "Psychology", "Economics, Econometrics and Finance"},
}


def field_plausible(department: str, field: str | None) -> bool:
    d = department.lower()
    for key, fields in DEPT_FIELDS.items():
        if key in d:
            return field in fields
    return True


def global_fallback(name: str, department: str) -> pd.DataFrame | None:
    """Faculty with no IISER-affiliated profile (new joiners, affiliation not yet indexed):
    one paid name search across OpenAlex; accept only a near-exact name, biggest profile."""
    if len(norm(name).split()) < 2:
        return None
    data = oa.get("/authors", {"search": name, "select": SELECT, "per_page": 10})
    rows = []
    for a in data.get("results", []):
        sc = name_score(name, a["display_name"])
        topics = a.get("topics") or []
        fld = topics[0]["field"]["display_name"] if topics else None
        if sc >= 95 and field_plausible(department, fld):
            rows.append(dict(author_id=oa.short_id(a["id"]), display_name=a["display_name"],
                             orcid=a.get("orcid"), works_count=a.get("works_count", 0),
                             cited_by_count=a.get("cited_by_count", 0),
                             h_index=(a.get("summary_stats") or {}).get("h_index"),
                             i10_index=(a.get("summary_stats") or {}).get("i10_index"),
                             first_year=None, last_year=None, score=sc,
                             field=topics[0]["field"]["display_name"] if topics else None))
    if not rows:
        return None
    return pd.DataFrame(rows).sort_values("works_count", ascending=False).head(1)


def main() -> pd.DataFrame:
    fac = pd.read_csv(INTERIM / "faculty_raw.csv")
    overrides = (pd.read_csv(MANUAL / "faculty_overrides.csv", dtype=str)
                 if (MANUAL / "faculty_overrides.csv").exists() else pd.DataFrame())

    out = []
    for key, inst in inst_by_key().items():
        cands = fetch_authors(inst["openalex"])
        cands.to_parquet(INTERIM / f"authors_{key}.parquet", index=False)
        oa.report_spend(f"authors {key} ({len(cands)})")
        for _, f in fac[fac.institution == key].iterrows():
            ov = overrides[(overrides.get("institution") == key) & (overrides.get("name") == f["name"])] \
                if len(overrides) else overrides
            m = best_matches(f, cands)
            if len(ov):
                ids = ov.iloc[0]["author_ids"].split(";")
                chosen = cands[cands.author_id.isin(ids)]
                conf = "manual"
            elif m.empty:
                g = global_fallback(f["name"], f["department"])
                if g is None:
                    out.append({**f, "author_ids": "", "openalex_name": "", "confidence": "unmatched",
                                "match_score": 0})
                    continue
                chosen, conf, m = g, "low", g
            else:
                # primary = highest name score, ties broken by the larger profile
                top = m.iloc[0]
                exact = m[(m.score >= max(95, top.score - 1))]
                if not top.plausible and len(norm(f["name"]).split()) and top.score < 92:
                    out.append({**f, "author_ids": "", "openalex_name": "", "confidence": "unmatched",
                                "match_score": float(top.score)})
                    continue
                same = exact[(exact.field == top.field) & (exact.works_count >= 2)
                             & (exact.orcid.isna() | (exact.orcid == top.orcid) | pd.isna(top.orcid))]
                if top.orcid:
                    same = pd.concat([same, m[m.orcid == top.orcid]])
                chosen = pd.concat([top.to_frame().T, same]).drop_duplicates("author_id")
                recent = (top.last_year or 0) >= 2022
                single = len(norm(f["name"]).split()) == 1
                conf = ("high" if top.score >= 92 and recent and not single
                        else "medium" if top.score >= 85 else "low")
            primary = chosen.sort_values("works_count", ascending=False).iloc[0]
            out.append({
                **f,
                "author_ids": ";".join(chosen.author_id),
                "n_author_ids": len(chosen),
                "openalex_name": primary.display_name,
                "orcid": primary.orcid,
                "confidence": conf,
                "match_score": float(m.iloc[0].score) if len(m) else 100.0,
                "works_count_career": int(chosen.works_count.sum()),
                "cited_by_career": int(chosen.cited_by_count.sum()),
                "h_index_career": int(primary.h_index or 0),
                "i10_index_career": int(primary.i10_index or 0),
                "first_year_at_inst": primary.first_year,
                "field_main": primary.field,
            })
    df = pd.DataFrame(out)
    df["field_plausible"] = [field_plausible(d, f) if isinstance(f, str) else None
                             for d, f in zip(df.department, df.get("field_main"))]
    df.to_csv(INTERIM / "faculty_matched.csv", index=False)
    print(df.groupby(["institution", "confidence"]).size().unstack(fill_value=0).to_string())
    return df


if __name__ == "__main__":
    main()
