"""Checks the four submission files against the instruction note (sections 5, 6, 7c)."""
import pandas as pd
import pytest

from dpcn.build_dataset import SPEC_COLUMNS
from dpcn.config import FINAL, GROUP, inst_by_key


@pytest.fixture(scope="module")
def data():
    return pd.read_csv(FINAL / f"group{GROUP}_data.csv", low_memory=False)


def test_spec_columns_first_and_in_order(data):
    assert list(data.columns[: len(SPEC_COLUMNS)]) == SPEC_COLUMNS


def test_years_in_window(data):
    assert data.year.between(2016, 2026).all()


def test_all_institutes_present(data):
    assert set(data.institution) == {v["name"] for v in inst_by_key().values()}


def test_group_and_types(data):
    assert (data.group == GROUP).all()
    assert set(data.type) <= {"journal", "conference"}
    assert set(data.quartile.dropna()) <= {"Q1", "Q2", "Q3", "Q4", "A*", "A", "B", "C"}


def test_boolean_flags(data):
    for c in ["cites_indian_inst", "cited_by_indian_inst", "affiliated"]:
        assert set(data[c].unique()) <= {True, False}


def test_no_duplicate_faculty_paper_rows(data):
    assert not data.duplicated(["institution", "author", "work_id"]).any()


def test_issn_only_for_journals(data):
    assert data.loc[data.type == "conference", "issn"].isna().all()


@pytest.mark.parametrize("name,cols", [
    ("citation_network.csv", ["source_doi", "target_doi", "source_inst", "target_inst", "year"]),
    ("authorship_network.csv", ["author_a", "author_b", "paper_doi", "inst_a", "inst_b", "year"]),
    ("indian_connections.csv", ["your_inst", "partner_inst", "shared_papers", "total_citations"]),
])
def test_network_file_headers(name, cols):
    df = pd.read_csv(FINAL / name, nrows=5)
    assert list(df.columns[: len(cols)]) == cols


def test_internal_citation_edges_point_into_corpus(data):
    e = pd.read_csv(FINAL / "citation_network.csv", low_memory=False)
    internal = e[e.scope == "internal"]
    ids = set(data.work_id)
    assert internal.source_id.isin(ids).all() and internal.target_id.isin(ids).all()
    assert e.source_doi.notna().all() and e.target_doi.notna().all()


def test_connections_exclude_self(data):
    c = pd.read_csv(FINAL / "indian_connections.csv")
    assert not (c.your_inst == c.partner_inst).any()
    assert (c.total_citations == c.citations_in + c.citations_out).all()
