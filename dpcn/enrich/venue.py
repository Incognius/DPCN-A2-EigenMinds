"""Venue quality: SCImago quartile for journals (ISSN + year), CORE rank for conferences.

SCImago years run to 2025, so 2026 papers use the 2025 quartile. CORE 2023 is matched on the
conference acronym or a fuzzy match of the cleaned conference name (>= 90).
"""
from __future__ import annotations

import re

import pandas as pd
from rapidfuzz import fuzz, process

from ..config import EXTERNAL
from . import sjr

CORE_RAW = EXTERNAL / "raw" / "core2023.csv"


def journal_quartiles(papers: pd.DataFrame) -> pd.Series:
    q = sjr.load()
    lut = {(r.issn, r.year): r.quartile for r in q.itertuples() if isinstance(r.quartile, str)}
    out = []
    for p in papers.itertuples():
        yr = min(int(p.year), 2025)
        issns = [p.issn_l] + (p.issns.split(";") if p.issns else [])
        val = None
        for i in issns:
            if not i:
                continue
            for y in (yr, yr - 1, yr + 1):           # journals enter / leave SCImago a year off
                val = lut.get((i, y))
                if val:
                    break
            if val:
                break
        out.append(val)
    return pd.Series(out, index=papers.index)


def _clean_conf(name: str) -> str:
    s = re.sub(r"\b(19|20)\d{2}\b", " ", name or "")
    s = re.sub(r"\b(proceedings of( the)?|ieee|acm|ifip|\d+(st|nd|rd|th)|annual|"
               r"lecture notes in computer science)\b", " ", s, flags=re.I)
    return re.sub(r"[^a-z ]", " ", s.lower()).split("(")[0].strip()


def core_ranks(papers: pd.DataFrame) -> pd.Series:
    core = pd.read_csv(CORE_RAW, header=None,
                       names=["cid", "title", "acronym", "source", "rank", "primary", "for1", "for2", "for3"])
    core = core[core["rank"].isin(["A*", "A", "B", "C"])]
    titles = {_clean_conf(t): r for t, r in zip(core.title, core["rank"])}
    acr = {str(a).strip().upper(): r for a, r in zip(core.acronym, core["rank"]) if isinstance(a, str)}
    keys = list(titles)
    out = []
    for p in papers.itertuples():
        if p.source_type != "conference" and p.work_type != "conference-paper":
            out.append(None)
            continue
        name = p.source_name or ""
        m = re.findall(r"\b([A-Z][A-Za-z]{2,}[A-Z])\b", name)          # e.g. 'NeurIPS', 'ICASSP'
        hit = next((acr[a.upper()] for a in m if a.upper() in acr), None)
        if not hit and keys:
            best = process.extractOne(_clean_conf(name), keys, scorer=fuzz.token_set_ratio)
            if best and best[1] >= 90:
                hit = titles[best[0]]
        out.append(hit)
    return pd.Series(out, index=papers.index)
