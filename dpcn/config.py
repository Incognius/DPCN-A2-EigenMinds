"""Paths and the institution config, shared by every pipeline stage."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
# raw API/HTML cache lives outside OneDrive (it grows to ~1 GB); override with DPCN_CACHE
CACHE = Path(os.getenv("DPCN_CACHE", Path(os.getenv("LOCALAPPDATA", ROOT / "data")) / "dpcn20" / "cache"))
EXTERNAL = DATA / "external"
MANUAL = DATA / "manual"
INTERIM = DATA / "interim"
FINAL = DATA / "final"
WEB_DATA = ROOT / "web" / "public" / "data"
FIGURES = ROOT / "report" / "figures"

for _d in (CACHE, EXTERNAL, MANUAL, INTERIM, FINAL, WEB_DATA, FIGURES):
    _d.mkdir(parents=True, exist_ok=True)


@lru_cache
def cfg() -> dict:
    return yaml.safe_load((ROOT / "config" / "institutions.yaml").read_text(encoding="utf-8"))


def institutions() -> list[dict]:
    return cfg()["institutions"]


def inst_by_openalex() -> dict[str, dict]:
    return {i["openalex"]: i for i in institutions()}


def inst_by_key() -> dict[str, dict]:
    return {i["key"]: i for i in institutions()}


GROUP = 20
YEAR_MIN, YEAR_MAX = 2016, 2026
