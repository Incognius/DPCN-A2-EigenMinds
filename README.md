# IISER Research Atlas: DPCN Group 20

Research mapping of **IISER Bhopal, IISER Mohali and IISER Thiruvananthapuram**, 2016–2026, for the DPCN course project (Prof. Chittaranjan Hens).

**Group 20 · Team EigenMinds:** Ponnambalam V, Manit Roy, Shashwat Mukadam.

| Deliverable | Where |
|---|---|
| Dataset `group20_data.csv` (14 spec columns + extras) | [`data/final/`](data/final/) |
| `citation_network.csv`, `authorship_network.csv`, `indian_connections.csv` | [`data/final/`](data/final/) |
| Interactive dashboard | [`web/`](web/), deployed to GitHub Pages (link in `web/public/data/meta.json`) |
| Report PDF (≤ 5 pages) | [`submission/Group20_IISER.pdf`](submission/), source in [`report/`](report/) |
| Brief from the instructor | [`docs/brief/`](docs/brief/) |

## What is in the data

- **Faculty.** 410 current regular faculty (Assistant, Associate and full Professors), scraped from each institute's own website. 397 of them (96.8%) are matched to OpenAlex author profiles. Visiting, adjunct, emeritus, INSPIRE/Ramanujan fellows and former faculty are excluded, so the three institutes are counted the same way.
- **Papers.** Journal and conference papers from 2016–2026: articles, reviews, letters and conference papers. Preprints, book chapters, datasets and errata are dropped.
- **Cleaning.** OpenAlex types much more than research papers as articles, so `collect` also drops:
  - cover pages, frontispieces, publisher's notes and addenda, and errata that only show up as `<DOI>e` (the Planck 2018 erratum);
  - "journal" venues with no ISSN (Astronomer's Telegrams, data catalogues, meeting-abstract books). Real journals that OpenAlex lists without an ISSN get it from a close SCImago title match.
  - duplicate records of the same paper, which are counted once. These are Angewandte Chemie's German-edition twins (`ange.*` next to `anie.*`) and same-type records with the same title, published within a year and sharing an author (version or provisional DOIs, repository copies, journal-supplement abstracts). The best-cited record is kept, and citations of the duplicate are redirected to it. A conference paper and its journal version stay separate.
- **Rows.** One row per (faculty member, paper). `affiliated` marks rows where that faculty member's authorship lists their IISER. Institute-level statistics count each paper once, and only when it is affiliated.
- **Quality.**
  - `quartile` is the SCImago best quartile, matched on ISSN and year. 2026 papers use the 2025 values.
  - CORE 2023 ranks are given for conference papers.
- **Indian links.**
  - `cites_indian_inst`: the paper references a work with an Indian institution other than its own IISER.
  - `cited_by_indian_inst`: a paper by an author from another Indian institution cites it.
  - Citing works must be from 2016–2026 and no more than a year older than the paper they cite. This drops a few mis-dated OpenAlex records.
- **Large collaborations.** Papers with more than 50 authors are kept but flagged as `hyperauthored`. They are excluded from the co-authorship graph, and their effect on citation totals is reported separately.

### Extra columns in `group20_data.csv`

After the 14 required columns:

- `institution_key`, `department`, `author_openalex_id`, `work_id`, `affiliated`
- `author_position`, `n_authors`, `hyperauthored`
- `sjr_quartile`, `core_rank`
- `field`, `subfield`, `domain`, `topic`
- `fwci`, `is_oa`, `top_10pct`

## Pipeline

```bash
pip install -r requirements.txt
cp .env.example .env          # add a free OpenAlex key from openalex.org/settings/api
python -m dpcn                # all stages
python -m dpcn stats networks web   # or selected stages
pytest tests/
```

| Stage | Module | Output |
|---|---|---|
| scrape | `dpcn/faculty/scrape.py` | `data/interim/faculty_raw.csv` |
| match | `dpcn/faculty/match.py` (+ `data/manual/faculty_overrides.csv`) | `faculty_matched.csv` |
| collect | `dpcn/collect.py` | papers / authorships / refs parquet |
| links | `dpcn/enrich/links.py` | referenced-work institutions, Indian citing works |
| dataset | `dpcn/build_dataset.py`, `dpcn/enrich/venue.py`, `dpcn/enrich/sjr.py` | `data/final/group20_data.csv` |
| stats | `dpcn/stats.py` | statistics and tests |
| networks | `dpcn/networks/{citation,authorship,connections}.py` | the three network CSVs + metrics |
| figures | `dpcn/figures.py` | `report/figures/` |
| web | `dpcn/export_web.py` | `web/public/data/*.json` |

The OpenAlex API is metered: a free key gives $1/day. A full run from an empty cache costs about **$0.45**. Most of that is the ~3,900 calls that fetch the institutions of 385k referenced works.

Every response is cached outside OneDrive in `%LOCALAPPDATA%/dpcn20/cache`, which you can override with `DPCN_CACHE`. Re-runs are free.

## Dashboard

```bash
cd web
npm install
npm run dev      # http://localhost:5173
npm run build    # static site in web/dist
```

The stack is Vite + React + TypeScript, Tailwind, ECharts and Sigma.js (WebGL graphs). Graph layouts are precomputed in Python with igraph, so the networks render instantly.

There are nine pages:

- Overview
- Institutes
- Faculty
- Journals & Impact
- Research Areas
- Citation Network
- Collaboration
- Indian Connectivity
- Methods & Data

The institute filter in the header cross-filters every page, and the URL hash makes every view linkable.

## Known limits

- **Current faculty only.** Papers by people who left before 2026 are missing, so institute totals undercount total institutional output.
- **Unmatched and common names.** 13 faculty could not be matched in OpenAlex, mostly recent joiners. Common names were resolved with a department–field plausibility rule, and each row records its `match_confidence`.
- **Data sources.** SCImago (scimagojr.com) blocks scripted downloads, so quartiles come from the open [`sjrdata`](https://github.com/ikashnitsky/sjrdata) mirror (data to 2025).
- **Citation counts** are as of October 2026.
