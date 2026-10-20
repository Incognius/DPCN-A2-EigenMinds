"""Helpers shared by the network stages."""
from __future__ import annotations

import igraph as ig
import numpy as np
import pandas as pd

from ..config import INTERIM, inst_by_key


def paper_institutes() -> dict[str, list[str]]:
    """work_id -> sorted list of our institute keys whose faculty authored it *with affiliation*."""
    fp = pd.read_parquet(INTERIM / "faculty_papers.parquet")
    fp = fp[fp.affiliated]
    return fp.groupby("work_id").institution.apply(lambda s: sorted(set(s))).to_dict()


def inst_name(key: str) -> str:
    return inst_by_key()[key]["name"]


def doi_or_id(doi, wid: str) -> str:
    return doi if isinstance(doi, str) and doi else f"https://openalex.org/{wid}"


def _unit(xy: np.ndarray) -> np.ndarray:
    xy = xy - xy.mean(0)
    return xy / (np.abs(xy).max() or 1)


def layout(nodes: list[str], edges: list[tuple[str, str]], weights=None, seed: int = 7) -> dict:
    """Force-directed positions via igraph (C speed), one component at a time.

    Laying out a disconnected graph in one pass crushes the giant component into the centre while
    hundreds of pairs drift around it. Instead the giant component gets the unit disc and the small
    components sit on concentric rings around it (Gephi-style), each scaled by sqrt(size).
    """
    idx = {n: i for i, n in enumerate(nodes)}
    g = ig.Graph(n=len(nodes), edges=[(idx[a], idx[b]) for a, b in edges], directed=False)
    if weights is not None:
        g.es["weight"] = list(weights)
    np.random.seed(seed)
    comps = sorted(g.connected_components(), key=len, reverse=True)
    out = np.zeros((len(nodes), 2))
    n_giant = len(comps[0])
    ring_r, angle, ring_w = 1.12, 0.0, 0.0
    for ci, members in enumerate(comps):
        sub = g.subgraph(members)
        w = "weight" if weights is not None else None
        if len(members) == 1:
            xy = np.zeros((1, 2))
        elif len(members) > 1000:
            xy = np.array(sub.layout_fruchterman_reingold(weights=w, niter=2000, grid="grid").coords)
        else:
            xy = np.array(sub.layout_fruchterman_reingold(weights=w, niter=800).coords)
        xy = _unit(xy) if len(members) > 1 else xy
        if ci == 0:
            out[members] = xy
            continue
        size = max(0.012, 0.6 * np.sqrt(len(members) / n_giant))
        step = (2 * size + 0.01) / ring_r                # arc taken on the current ring
        if angle + step > 2 * np.pi:                     # ring full: move outwards
            ring_r += ring_w + 0.02
            angle, ring_w = 0.0, 0.0
            step = (2 * size + 0.01) / ring_r
        theta = angle + step / 2
        centre = (ring_r + size) * np.array([np.cos(theta), np.sin(theta)])
        out[members] = xy * size + centre
        angle += step
        ring_w = max(ring_w, 2 * size)
    return {n: (round(float(x), 4), round(float(y), 4)) for n, (x, y) in zip(nodes, out)}
