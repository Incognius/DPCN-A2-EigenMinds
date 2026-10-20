"""Classify Indian institutions into the course's clusters, so cross-cluster links can be flagged
(IISER <-> IIT, IISER <-> CSIR, ...). Name-based; order matters (first match wins)."""
from __future__ import annotations

import re

RULES: list[tuple[str, str]] = [
    ("IISER", r"indian institute of science education and research|\biiser\b"),
    ("IISc", r"indian institute of science(?!.*education)\b"),
    ("IIT", r"indian institute of technology|\biit\b"),
    ("IIIT", r"indian institute of information technology|international institute of information technology|"
             r"indraprastha institute of information technology|\biiit"),
    ("NIT", r"national institute of technology|\bnit\b|motilal nehru national|visvesvaraya national|malaviya national|"
            r"maulana azad national|indian institute of engineering science and technology"),
    ("CSIR", r"council of scientific (and|&) industrial research|\bcsir\b|national chemical laboratory|"
             r"indian institute of chemical technology|central (drug|glass|electrochemical|salt|food|leather|"
             r"road|building|mechanical|electronics|scientific instruments|institute of mining)|"
             r"national (physical|metallurgical|botanical|environmental engineering|geophysical|aerospace) |"
             r"institute of (genomics|microbial|himalayan bioresource|minerals)|cellular and molecular biology|"
             r"indian institute of (toxicology|integrative medicine|petroleum|chemical biology)|"
             r"national institute (of oceanography|for interdisciplinary)|academy of scientific and innovative|"
             r"north east institute of science|advanced materials and processes|national botanical"),
    ("DAE", r"ugc.?dae consortium|bhabha atomic|homi bhabha national|indira gandhi centre for atomic|raja ramanna|"
            r"tata institute of fundamental|saha institute|institute of physics|harish-chandra|"
            r"institute of mathematical sciences|national institute of science education and research|"
            r"variable energy cyclotron|atomic minerals|tata memorial|institute for plasma research|"
            r"department of atomic energy"),
    ("Govt S&T", r"indian space research|\bisro\b|vikram sarabhai|space applications centre|"
                 r"national remote sensing|national atmospheric research|indian institute of space science|"
                 r"ministry of earth sciences|india meteorological|geological survey|national institute of hydrology|"
                 r"indian institute of tropical|national centre for polar|defence research|\bdrdo\b|"
                 r"ministry of|government of|department of science and technology"),
    ("DST/DBT Autonomous", r"s\.? ?n\.? bose|bose institute|raman research|jawaharlal nehru centre|"
                           r"indian association for the cultivation|physical research laboratory|"
                           r"indian institute of astrophysics|aryabhatta|inter-university|institute of nano|"
                           r"national centre for biological|national institute of immunology|"
                           r"centre for dna|regional centre for biotechnology|national brain|"
                           r"institute of life sciences|rajiv gandhi centre for biotechnology|"
                           r"translational health|national centre for cell|agharkar|wadia|birbal sahni|"
                           r"indian institute of geomagnetism|department of biotechnology|indian statistical institute|"
                           r"chennai mathematical|national centre for|centre for nano and soft|stem cell biology|"
                           r"plant genome|institute of bioinformatics|national institute of advanced studies|"
                           r"centre for excellence in basic|poornaprajna|tcg crest"),
    ("Medical", r"national institute of epidemiology|all india institute of medical|\baiims\b|"
                r"post ?graduate institute of medical|indian council of medical|medical college|"
                r"christian medical|sree chitra|nimhans|national institute of mental"),
    ("Agricultural", r"animal diseases|indian council of agricultural|\bicar\b|agricultural|agri|horticulture|"
                     r"veterinary|indian institute of (pulses|soil|rice|wheat|horticultural)"),
    ("IIM/Other national", r"indian institute of management|indian institute of foreign trade|"
                           r"national institute of (design|pharmaceutical)|\bniper\b"),
    ("University", r"universit|vidyapeeth|vishwavidyalaya|college|\bbits\b|birla institute|"
                   r"amrita|manipal|vellore|\bsrm\b|deemed|jaypee|lnm institute|thapar|koneru|kalasalingam|"
                   r"nitte|sri sathya sai|psg institute|institute of higher learning|"
                   r"academy of research and education|jamia|central institute of technology"),
    ("Industry", r"\b(ltd|limited|pvt|private)\b|tata steel|tata consultancy|infosys|wipro|reliance|\(india\)$"),
]
_COMPILED = [(c, re.compile(p, re.I)) for c, p in RULES]
CLUSTERS = [c for c, _ in RULES] + ["Other"]


def cluster_of(name: str | None) -> str:
    if not name:
        return "Other"
    for c, rx in _COMPILED:
        if rx.search(name):
            return c
    return "Other"
