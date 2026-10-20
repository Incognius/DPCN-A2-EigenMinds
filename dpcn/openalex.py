"""Small OpenAlex client: API key from .env, cursor paging, OR-batched filters, on-disk cache.

Every response is cached under data/cache keyed by the request (without the key), so reruns are
free and an interrupted stage resumes where it stopped. Spend is read from meta.cost_usd.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Iterable, Iterator

import requests
from dotenv import load_dotenv

from .config import CACHE, ROOT

load_dotenv(ROOT / ".env")

BASE = "https://api.openalex.org"
_session = requests.Session()
SPEND = {"usd": 0.0, "calls": 0, "cached": 0}


def short_id(x: str | None) -> str | None:
    """'https://openalex.org/W123' -> 'W123'."""
    if not x:
        return None
    return x.rsplit("/", 1)[-1]


def _cache_path(endpoint: str, params: dict) -> os.PathLike:
    key = json.dumps([endpoint, sorted(params.items())], sort_keys=True)
    h = hashlib.sha1(key.encode()).hexdigest()
    d = CACHE / endpoint.strip("/").split("/")[0]
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{h}.json"


def get(endpoint: str, params: dict | None = None, use_cache: bool = True) -> dict:
    params = dict(params or {})
    path = _cache_path(endpoint, params)
    if use_cache and path.exists():
        SPEND["cached"] += 1
        return json.loads(path.read_text(encoding="utf-8"))

    q = dict(params)
    if os.getenv("OPENALEX_API_KEY"):
        q["api_key"] = os.environ["OPENALEX_API_KEY"]
    if os.getenv("OPENALEX_MAILTO"):
        q["mailto"] = os.environ["OPENALEX_MAILTO"]

    for attempt in range(6):
        try:
            r = _session.get(f"{BASE}{endpoint}", params=q, timeout=120)
        except requests.exceptions.RequestException:
            time.sleep(2 ** attempt)        # dropped connection on a huge (hyper-authored) page
            continue
        if r.status_code == 200:
            data = r.json()
            SPEND["calls"] += 1
            SPEND["usd"] += float(data.get("meta", {}).get("cost_usd") or 0)
            path.write_text(json.dumps(data), encoding="utf-8")
            return data
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(2 ** attempt)
            continue
        raise RuntimeError(f"OpenAlex {r.status_code} on {endpoint} {params}: {r.text[:300]}")
    raise RuntimeError(f"OpenAlex kept failing on {endpoint} {params}")


def paginate(endpoint: str, params: dict, per_page: int = 100) -> Iterator[dict]:
    """Yield every result of a list query using cursor paging."""
    cursor = "*"
    while cursor:
        data = get(endpoint, {**params, "per_page": per_page, "cursor": cursor})
        yield from data.get("results", [])
        cursor = data.get("meta", {}).get("next_cursor")
        if not data.get("results"):
            break


def batched(items: Iterable[str], n: int) -> Iterator[list[str]]:
    buf: list[str] = []
    for it in items:
        buf.append(it)
        if len(buf) == n:
            yield buf
            buf = []
    if buf:
        yield buf


def report_spend(label: str) -> None:
    print(f"[openalex] {label}: {SPEND['calls']} paid calls, {SPEND['cached']} cache hits, "
          f"${SPEND['usd']:.4f}")
