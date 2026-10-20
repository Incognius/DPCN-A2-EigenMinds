"""Scrape the current regular-faculty roster of each IISER from its own website.

Output: data/interim/faculty_raw.csv  (institution, department, name, designation, profile_url, source)

Scope rule: current *regular* faculty only -- Assistant / Associate / full Professors. Visiting,
adjunct, emeritus, honorary, ad-hoc, INSPIRE / Ramanujan fellows and former faculty are excluded,
so the three institutes are counted the same way.

  * TVM, Bhopal  faculty "cards" render as a name line followed by a designation line; one
                 text-line rule reads every department template (Bhopal has ten different ones).
  * Mohali       the /people page lists regular faculty as links before the "Inspire Faculty"
                 heading, with the department code in the URL (/faculty/dps/<slug>).
"""
from __future__ import annotations

import hashlib
import re
from urllib.parse import urljoin

import pandas as pd
import requests
import truststore
from bs4 import BeautifulSoup

from ..config import CACHE, INTERIM

UA = {"User-Agent": "Mozilla/5.0 (DPCN course project, group 20)"}
# Bhopal sub-sites serve an incomplete cert chain; the Windows store completes it, certifi does not.
truststore.inject_into_ssl()
HTML_CACHE = CACHE / "html"
HTML_CACHE.mkdir(parents=True, exist_ok=True)

TITLE = re.compile(r"^\s*(?:prof(?:essor)?|dr|mr|ms|mrs)\.?\s+", re.I)
NAME = re.compile(r"^[A-Z][A-Za-z.'\-]*(?:\s+[A-Z][A-Za-z.'\-]*){0,5}$")
REGULAR = re.compile(r"^\s*(?:(?:assistant|associate)\s+)?professor\b", re.I)
EXCLUDE = re.compile(r"visiting|adjunct|emeritus|honorary|former|ad-?hoc|inspire|ramanujan|fellow|"
                     r"professor of practice|,", re.I)
NOT_A_NAME = re.compile(r"professor|faculty|physics|chemistry|biology|science|department|school|"
                        r"literature|philosophy|profile|home|people|research|head\b|director|dean|registrar", re.I)

TVM_SCHOOLS = {
    "biology": "Biology", "chemistry": "Chemistry", "datascience": "Data Science",
    "earthscience": "Earth, Environmental & Sustainability Sciences", "maths": "Mathematics",
    "physics": "Physics", "humanities": "Humanities",
}
MOHALI_DEPTS = {
    "dbs": "Biological Sciences", "dcs": "Chemical Sciences", "dps": "Physical Sciences",
    "dms": "Mathematical Sciences", "ees": "Earth & Environmental Sciences",
    "hss": "Humanities & Social Sciences",
}
BHOPAL_DEPTS = {
    "Biological Sciences": "https://bio.iiserb.ac.in/faculty",
    "Chemistry": "https://chm.iiserb.ac.in/faculty",
    "Earth & Environmental Sciences": "https://ees.iiserb.ac.in/people",
    "Mathematics": "https://maths.iiserb.ac.in/faculty",
    "Physics": "https://phy.iiserb.ac.in/faculty",
    "Chemical Engineering": "https://che.iiserb.ac.in/drop_links/faculty/",
    "Data Science & Engineering": "https://dse.iiserb.ac.in/people.php",
    "Electrical Engineering & Computer Science": "https://eecs.iiserb.ac.in/faculty",
    "Economic Sciences": "https://eco.iiserb.ac.in/people.php",
    "Humanities & Social Sciences": "https://hss.iiserb.ac.in/faculty",
}


def fetch(url: str) -> BeautifulSoup:
    path = HTML_CACHE / (hashlib.sha1(url.encode()).hexdigest() + ".html")
    if not path.exists():
        r = requests.get(url, headers=UA, timeout=60)
        r.raise_for_status()
        path.write_bytes(r.content)
    return BeautifulSoup(path.read_bytes(), "lxml")


def clean_name(raw: str) -> str:
    t = re.sub(r"\s+", " ", raw).strip().rstrip(".")
    while TITLE.match(t):
        t = TITLE.sub("", t, count=1)
    if t.isupper() or t.islower():
        t = t.title()
    return t.strip()


def looks_like_name(t: str) -> bool:
    return 3 < len(t) < 45 and bool(NAME.match(t)) and not NOT_A_NAME.search(t)


def card_names(soup: BeautifulSoup) -> list[tuple[str, str]]:
    """(name, designation) for every 'name line → regular-professor line' pair on a page."""
    for t in soup(["nav", "header", "footer", "script", "style"]):
        t.decompose()
    lines = [re.sub(r"\s+", " ", l).strip() for l in soup.get_text("\n", strip=True).split("\n")]
    lines = [l for l in lines if l]
    out: dict[str, str] = {}
    for i, line in enumerate(lines[:-1]):
        nm = clean_name(line)
        if not looks_like_name(nm):
            continue
        desig = lines[i + 1]
        if len(desig) < 70 and REGULAR.search(desig) and not EXCLUDE.search(desig):
            out.setdefault(nm, desig.title() if desig.isupper() else desig)
    return list(out.items())


def scrape_tvm() -> list[dict]:
    rows = []
    for slug, dept in TVM_SCHOOLS.items():
        url = f"https://www.iisertvm.ac.in/faculty/{slug}"
        for nm, desig in card_names(fetch(url)):
            rows.append(dict(institution="IISERTVM", department=dept, name=nm, designation=desig,
                             profile_url="", source=url))
    return rows


def scrape_mohali() -> list[dict]:
    url = "https://www.iisermohali.ac.in/people"
    soup = fetch(url)
    rows = []
    for el in soup.find_all(["a", "h2"]):
        if el.name == "h2" and "inspire" in el.get_text(" ", strip=True).lower():
            break                                   # everything after this heading is non-regular
        if el.name != "a" or not el.get("href"):
            continue
        m = re.search(r"/faculty/(\w+)/([\w.\-]+)$", el["href"])
        if not m or m.group(1) not in MOHALI_DEPTS:
            continue
        rows.append(dict(institution="IISERM", department=MOHALI_DEPTS[m.group(1)],
                         name=clean_name(el.get_text(" ", strip=True)), designation="",
                         profile_url=urljoin(url, el["href"]), source=url))
    return rows


def scrape_bhopal() -> list[dict]:
    rows = []
    for dept, url in BHOPAL_DEPTS.items():
        for nm, desig in card_names(fetch(url)):
            rows.append(dict(institution="IISERB", department=dept, name=nm, designation=desig,
                             profile_url="", source=url))
    return rows


def main() -> pd.DataFrame:
    df = pd.DataFrame(scrape_tvm() + scrape_mohali() + scrape_bhopal())
    df = df[df["name"].map(looks_like_name)]
    df = df.drop_duplicates(["institution", "name"]).reset_index(drop=True)
    df.to_csv(INTERIM / "faculty_raw.csv", index=False)
    print(df.groupby(["institution", "department"]).size().to_string())
    print("total", len(df), "|", df.groupby("institution").size().to_dict())
    return df


if __name__ == "__main__":
    main()
