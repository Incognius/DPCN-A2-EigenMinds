"""Run the whole pipeline or one stage:  python -m dpcn [stage ...]

Stages, in order:
  scrape    faculty rosters from the three institute websites
  match     faculty names -> OpenAlex author IDs
  collect   2016-2026 publications of matched faculty
  links     referenced works + Indian citing works (the slow, ~1 h, ~$0.4 step)
  dataset   group20_data.csv
  stats     faculty / department / institute statistics and tests
  networks  citation + co-authorship networks, Indian connections
  figures   report figures
  web       dashboard JSON
  finalize  web + report numbers + PDF + submission zips (run after changing links in config)
Every OpenAlex response is cached, so re-running a stage is free.
"""
from __future__ import annotations

import sys

from . import build_dataset, collect, export_web, figures, package, report_numbers, stats
from .enrich import links, sjr
from .faculty import match, scrape
from .networks import authorship, citation, connections

STAGES = {
    "scrape": [scrape.main],
    "match": [match.main],
    "collect": [collect.main],
    "links": [links.fetch_ref_meta, links.fetch_indian_citers],
    "dataset": [sjr.load, build_dataset.main],
    "stats": [stats.main],
    "networks": [citation.main, authorship.main, connections.main],
    "figures": [figures.main],
    "web": [export_web.main],
    "finalize": [export_web.main, report_numbers.main, package.main],
}

if __name__ == "__main__":
    wanted = sys.argv[1:] or list(STAGES)
    for name in wanted:
        print(f"\n=== {name} ===")
        for fn in STAGES[name]:
            fn()
