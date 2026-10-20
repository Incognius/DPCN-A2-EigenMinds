"""SCImago journal quartiles, year by year.

scimagojr.com sits behind a Cloudflare bot check, so we read the same data from the open
`sjrdata` R package mirror (github.com/ikashnitsky/sjrdata, refreshed June 2026, years 1999-2025).
Output: data/external/sjr_quartiles.parquet  (issn, year, quartile, sjr, sjr_title, categories, areas)
"""
from __future__ import annotations

import pandas as pd
import pyreadr

from ..config import EXTERNAL

RAW = EXTERNAL / "raw" / "sjr_journals.rda"
OUT = EXTERNAL / "sjr_quartiles.parquet"


def build() -> pd.DataFrame:
    df = list(pyreadr.read_r(str(RAW)).values())[0]
    df = df[df["year"] >= 2015].copy()
    df["year"] = df["year"].astype(int)
    df["issn"] = df["issn"].fillna("").str.split(r",\s*")
    df = df.explode("issn")
    df["issn"] = df["issn"].str.strip().str.upper()
    df = df[df["issn"].str.len() == 8]
    df["issn"] = df["issn"].str[:4] + "-" + df["issn"].str[4:]          # OpenAlex style 1234-567X
    df["quartile"] = df["sjr_best_quartile"].where(df["sjr_best_quartile"].isin(["Q1", "Q2", "Q3", "Q4"]))
    out = (df.rename(columns={"title": "sjr_title"})
             [["issn", "year", "quartile", "sjr", "sjr_title", "categories", "areas"]]
             .drop_duplicates(["issn", "year"]))
    out.to_parquet(OUT, index=False)
    print(f"sjr: {len(out):,} issn-year rows, years {out.year.min()}-{out.year.max()}")
    return out


def load() -> pd.DataFrame:
    return pd.read_parquet(OUT) if OUT.exists() else build()


if __name__ == "__main__":
    build()
