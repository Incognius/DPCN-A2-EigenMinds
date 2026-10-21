"""Build the submission bundles in submission/.

  Group20_IISER.zip        what we hand in: the report PDF + the four CSVs + a data README
  Group20_IISER_data.zip   the four CSVs + README, for the Google Drive link (data stays off GitHub)

`python -m dpcn finalize` = web export + report numbers + LaTeX build + these zips, so a new
dashboard or Drive link (config/institutions.yaml) reaches every deliverable in one command.
"""
from __future__ import annotations

import shutil
import subprocess
import zipfile

from .config import FINAL, GROUP, ROOT, cfg

SUB = ROOT / "submission"
PDF = SUB / f"Group{GROUP}_IISER.pdf"
CSVS = [f"group{GROUP}_data.csv", "citation_network.csv", "authorship_network.csv", "indian_connections.csv"]

DATA_README = """DPCN Research Mapping Project, Group 20 (team EigenMinds: Ponnambalam V, Manit Roy, Shashwat Mukadam)
IISER Bhopal, IISER Mohali, IISER Thiruvananthapuram, 2016-2026. Source: OpenAlex (Oct 2026), SCImago, CORE 2023.

group20_data.csv        one row per (faculty member, paper). The 14 required columns come first:
                        group, institution, author, title, year, type, journal_name, issn, doi, citations,
                        quartile, coauthor_institutes, cites_indian_inst, cited_by_indian_inst.
                        Extra columns: institution_key, department, author_openalex_id, work_id, affiliated
                        (the faculty authorship lists the IISER), author_position, n_authors, hyperauthored
                        (>50 authors), sjr_quartile, core_rank, field, subfield, domain, topic, fwci, is_oa,
                        top_10pct. Institute statistics count each affiliated paper once (unique work_id).
citation_network.csv    directed edges "source cites target": source_doi, target_doi, source_inst,
                        target_inst, year (+ source_id, target_id, scope, cross_institute).
                        scope = internal (both papers ours) | out_india (we cite another Indian institute)
                        | in_india (another Indian institute cites us).
authorship_network.csv  co-author pairs involving at least one of our faculty: author_a, author_b,
                        paper_doi, inst_a, inst_b, year (+ ids, faculty flags, n_authors, cross_institution).
                        Papers with >50 authors contribute only faculty-faculty pairs.
indian_connections.csv  your_inst, partner_inst, shared_papers, total_citations (= citations_in +
                        citations_out) (+ partner cluster, cross_cluster, topic Jaccard, subfield overlap,
                        coordinates).
"""


def build_report() -> None:
    subprocess.run(["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
                   cwd=ROOT / "report", check=True, stdout=subprocess.DEVNULL)
    SUB.mkdir(exist_ok=True)
    shutil.copy(ROOT / "report" / "main.pdf", PDF)
    print(f"report -> {PDF.relative_to(ROOT)}")


def zip_bundles() -> None:
    SUB.mkdir(exist_ok=True)
    readme = DATA_README + (f"\nDashboard: {cfg().get('dashboard_url') or '(see report)'}\n")
    for name, with_pdf in [(f"Group{GROUP}_IISER.zip", True), (f"Group{GROUP}_IISER_data.zip", False)]:
        with zipfile.ZipFile(SUB / name, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            if with_pdf:
                z.write(PDF, PDF.name)
            for f in CSVS:
                z.write(FINAL / f, f"data/{f}")
            z.writestr("data/README.txt", readme)
        print(f"zip    -> submission/{name} ({(SUB / name).stat().st_size / 1e6:.1f} MB)")


def main() -> None:
    build_report()
    zip_bundles()


if __name__ == "__main__":
    main()
