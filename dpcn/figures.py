"""Print figures for the report (report/figures/*.pdf), in a light variant of the dashboard palette.
Institute colours are the dashboard's; they pass the palette checks on white as well."""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .config import FIGURES, INTERIM

KEYS = ["IISERB", "IISERM", "IISERTVM"]
SHORT = {"IISERB": "Bhopal", "IISERM": "Mohali", "IISERTVM": "TVM"}
COLOR = {"IISERB": "#c266b8", "IISERM": "#c9802a", "IISERTVM": "#3a93d6"}
QCOL = {"Q1": "#5a3053", "Q2": "#8e4f80", "Q3": "#c27fb2", "Q4": "#e8c6df"}
CAT = ["#c266b8", "#c9802a", "#3a93d6", "#199e70", "#9085e9", "#d9546a"]
INK, MUTED, GRID = "#1d161b", "#6b6169", "#e9e4e8"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 8, "axes.titlesize": 9, "axes.titleweight": "bold",
    "axes.labelsize": 8, "axes.edgecolor": "#bdb3ba", "axes.labelcolor": INK, "axes.titlecolor": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "legend.frameon": False,
    "legend.fontsize": 7.5, "figure.dpi": 200, "savefig.bbox": "tight", "savefig.pad_inches": 0.03,
})


def load(name):
    return json.loads((INTERIM / name).read_text(encoding="utf-8"))


def save(fig, name):
    fig.savefig(FIGURES / f"{name}.pdf")
    fig.savefig(FIGURES / f"{name}.png", dpi=170)
    plt.close(fig)
    print("  figure", name)


def fig_output(st):
    """(a) papers per year, (b) quartile mix, (c) h-index distribution."""
    B = st["institutes"]
    fig, ax = plt.subplots(1, 3, figsize=(7.2, 2.15), gridspec_kw={"width_ratios": [1.35, 0.9, 1.1]})
    yrs = list(range(2016, 2027))
    ends = {}
    for k in KEYS:
        y = [B[k]["by_year"][str(t)] for t in yrs]
        ax[0].plot(yrs[:-1], y[:-1], color=COLOR[k], lw=1.8, marker="o", ms=3, label=SHORT[k])
        ax[0].plot(yrs[-2:], y[-2:], color=COLOR[k], lw=1.2, ls=":", marker="o", ms=3, mfc="white")
        ends[k] = y[-2]
    placed = []                                    # direct labels, nudged apart by >= 28 papers
    for k in sorted(ends, key=ends.get, reverse=True):
        yl = ends[k]
        while any(abs(yl - q) < 42 for q in placed):
            yl -= 6
        placed.append(yl)
        ax[0].annotate(SHORT[k], (2025, ends[k]), xytext=(2025.25, yl), color=COLOR[k], fontsize=7, va="center")
    ax[0].set_title("(a) Affiliated papers per year")
    ax[0].set_xticks([2016, 2018, 2020, 2022, 2024, 2026])
    ax[0].text(2026, ax[0].get_ylim()[0], "2026\npartial", fontsize=6, color=MUTED, ha="center", va="bottom")
    ax[0].set_xlim(2015.5, 2027.3)
    left = np.zeros(3)
    for q in ["Q1", "Q2", "Q3", "Q4"]:
        v = np.array([B[k]["quartiles"][q] / max(sum(B[k]["quartiles"].values()), 1) for k in KEYS])
        ax[1].barh([SHORT[k] for k in KEYS], v, left=left, color=QCOL[q], edgecolor="white", lw=0.8, label=q)
        for i, (l, w) in enumerate(zip(left, v)):
            if w > 0.08:
                ax[1].text(l + w / 2, i, f"{w:.0%}", ha="center", va="center", fontsize=6.5, color="white" if q in ("Q1", "Q2") else INK)
        left += v
    ax[1].set_title("(b) SCImago quartile mix")
    ax[1].set_xlim(0, 1); ax[1].xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0)); ax[1].grid(axis="y", visible=False)
    ax[1].invert_yaxis()
    ax[1].legend(ncol=4, loc="lower center", bbox_to_anchor=(0.5, -0.42), handlelength=1, columnspacing=0.8)
    fac = pd.read_json(INTERIM / "faculty_stats.json")
    bins = np.arange(0, 85, 5)
    for i, k in enumerate(KEYS):
        h = fac[fac.institution == k].h_index_career.dropna()
        ax[2].hist(h, bins=bins, histtype="step", lw=1.6, color=COLOR[k], label=f"{SHORT[k]} (med {h.median():.0f})")
    ax[2].set_title("(c) Faculty career h-index"); ax[2].set_xlabel("h-index"); ax[2].set_ylabel("faculty")
    ax[2].legend(loc="upper right")
    fig.tight_layout(w_pad=1.2)
    save(fig, "fig_output")


def fig_fields(st):
    B = st["institutes"]
    fields = [f for f in B["ALL"]["fields"] if f != "Unknown"][:8]
    fig, ax = plt.subplots(figsize=(3.5, 2.4))
    y = np.arange(len(fields))
    for i, k in enumerate(KEYS):
        tot = sum(B[k]["fields"].values())
        ax.barh(y + (i - 1) * 0.27, [B[k]["fields"].get(f, 0) / tot for f in fields], height=0.26, color=COLOR[k], label=SHORT[k])
    ax.set_yticks(y, [f.replace("Biochemistry, Genetics and Molecular Biology", "Biochem., Genetics & Mol. Bio.") for f in fields])
    ax.invert_yaxis(); ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0)); ax.grid(axis="y", visible=False)
    ax.set_title("Field mix (share of each institute's papers)"); ax.legend(loc="lower right")
    save(fig, "fig_fields")


def fig_citation(cs):
    g = load("citation_graph.json")
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.7), gridspec_kw={"width_ratios": [1.25, 1]})
    from matplotlib.collections import LineCollection
    nodes = pd.DataFrame(g["nodes"])
    nodes = nodes[nodes.x ** 2 + nodes.y ** 2 <= 1.02]          # the giant component owns the unit disc
    pos = {r.id: (r.x, r.y) for r in nodes.itertuples()}
    segs = [[pos[a], pos[b]] for a, b in g["edges"] if a in pos and b in pos]
    ax[0].add_collection(LineCollection(segs, colors="#9c8a97", linewidths=0.15, alpha=0.3, zorder=1))
    ax[0].scatter(nodes.x, nodes.y, s=1 + 40 * np.sqrt(nodes.pr / nodes.pr.max()), c=nodes.inst.map(COLOR), lw=0, alpha=0.85, zorder=2)
    ax[0].set_aspect("equal"); ax[0].set_axis_off(); ax[0].set_title(f"(a) Giant component of the citation graph · {len(nodes):,} papers")
    for k in KEYS:
        ax[0].scatter([], [], c=COLOR[k], s=12, label=SHORT[k])
    ax[0].legend(loc="upper center", bbox_to_anchor=(0.5, 0.02), ncol=3)
    d = {int(k): v for k, v in cs["indegree_dist"].items() if int(k) > 0}
    x = np.array(sorted(d)); y = np.array([d[i] for i in x])
    ax[1].loglog(x, y, "o", ms=3, color="#8e4f80", mfc="#c27fb2", label="papers")
    a, xm = cs["powerlaw"]["alpha"], cs["powerlaw"]["xmin"]
    xs = x[x >= xm]
    if len(xs):
        c0 = y[x >= xm][0] / (xs[0] ** -a)
        ax[1].loglog(xs, c0 * xs ** -a, color=INK, lw=1, ls="--", label=f"power law α={a:.2f}")
    ax[1].set_xlabel("internal citations received (in-degree)"); ax[1].set_ylabel("papers")
    ax[1].set_title("(b) In-degree distribution"); ax[1].legend()
    fig.tight_layout()
    save(fig, "fig_citation")


def fig_coauthor(co):
    g = load("coauthor_graph.json")
    nodes = pd.DataFrame(g["nodes"])
    order = [c["community"] for c in co["communities"][:6]]
    col = nodes.community.map(lambda c: CAT[order.index(c)] if c in order else "#c9c1c7")
    pos = {n["id"]: (n["x"], n["y"]) for n in g["nodes"]}
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.8), gridspec_kw={"width_ratios": [1.25, 1]})
    for a, b, w, cross in g["edges"]:
        ax[0].plot([pos[a][0], pos[b][0]], [pos[a][1], pos[b][1]], color="#d4a14a" if cross else "#c8bcc5",
                   lw=0.3 + 0.25 * min(w, 6), alpha=0.9 if cross else 0.45, zorder=1)
    ax[0].scatter(nodes.x, nodes.y, s=4 + 50 * np.sqrt(nodes.strength / nodes.strength.max()), c=col, lw=0.4, edgecolor="white", zorder=2)
    import matplotlib.patheffects as pe
    top = nodes.nlargest(5, "betweenness").sort_values("y")
    offsets = [(-38, -14), (22, -12), (-44, 10), (24, 12), (-10, 20)]
    for (dx, dy), r in zip(offsets, top.itertuples()):
        ax[0].annotate(r.name.split()[-1], (r.x, r.y), xytext=(dx, dy), textcoords="offset points", fontsize=6.5,
                       color=INK, arrowprops=dict(arrowstyle="-", lw=0.4, color=MUTED),
                       path_effects=[pe.withStroke(linewidth=2.2, foreground="white")])
    ax[0].set_aspect("equal"); ax[0].set_axis_off()
    ax[0].set_title(f"(a) Faculty co-authorship · Leiden communities (Q={co['leiden_modularity']:.2f})")
    t = pd.DataFrame(co["temporal"])
    ax[1].plot(t.year, t.giant_share, color="#8e4f80", marker="o", ms=3, label="giant component share")
    ax[1].plot(t.year, t.modularity, color="#3a93d6", marker="s", ms=3, label="modularity Q")
    ax[1].set_ylim(0, 1); ax[1].set_title("(b) Cumulative network over time"); ax[1].legend(loc="lower right")
    ax[1].set_xticks([2016, 2018, 2020, 2022, 2024, 2026])
    fig.tight_layout()
    save(fig, "fig_coauthor")


def fig_connect(conn):
    fig, ax = plt.subplots(1, 2, figsize=(7.2, 2.3), gridspec_kw={"width_ratios": [1, 1.25]})
    x = np.arange(3)
    ax[0].bar(x - 0.2, [conn[k]["citations_in"] for k in KEYS], 0.38, color=[COLOR[k] for k in KEYS], label="in: cited by India")
    ax[0].bar(x + 0.2, [conn[k]["citations_out"] for k in KEYS], 0.38, color="white", edgecolor=[COLOR[k] for k in KEYS], hatch="////", lw=1, label="out: citing India")
    for i, k in enumerate(KEYS):
        ax[0].text(i, max(conn[k]["citations_in"], conn[k]["citations_out"]) * 1.03, f"ratio {conn[k]['impact_ratio']:.2f}", ha="center", fontsize=7, color=INK)
    ax[0].set_xticks(x, [SHORT[k] for k in KEYS]); ax[0].grid(axis="x", visible=False)
    ax[0].set_title("(a) Citation flow with other Indian institutes"); ax[0].legend(loc="upper right", fontsize=6.5)
    ax[0].set_ylim(0, ax[0].get_ylim()[1] * 1.12)
    clusters = {}
    for k in KEYS:
        for c, v in conn[k]["by_cluster"].items():
            clusters.setdefault(c, {})[k] = v
    cl = sorted(clusters, key=lambda c: -sum(clusters[c].values()))[:8]
    yy = np.arange(len(cl)); left = np.zeros(len(cl))
    for k in KEYS:
        v = np.array([clusters[c].get(k, 0) for c in cl])
        ax[1].barh(yy, v, left=left, color=COLOR[k], edgecolor="white", lw=0.6, label=SHORT[k]); left += v
    ax[1].set_yticks(yy, cl); ax[1].invert_yaxis(); ax[1].grid(axis="y", visible=False)
    ax[1].set_title("(b) Co-authored papers by partner cluster"); ax[1].legend(loc="lower right")
    fig.tight_layout()
    save(fig, "fig_connect")


def main():
    st, cs, co, conn = load("stats.json"), load("citation_stats.json"), load("coauthor_stats.json"), load("connections_stats.json")
    fig_output(st)
    fig_fields(st)
    fig_citation(cs)
    fig_coauthor(co)
    fig_connect(conn)


if __name__ == "__main__":
    main()
