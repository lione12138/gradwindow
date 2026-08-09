from __future__ import annotations

import re
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry

CATALOG_URL = "https://bulletin.wustl.edu/azindex/"
APPLICATION_URL = "https://gradstudies.wustl.edu/admissions/"
DEGREE_RE = re.compile(
    r"\b(MSDAS|MSSSM|MSAE|MSEE|MSME|MEng|MFA|MBA|MArch|MPH|MSW|MUD|MLA|"
    r"MDes|MCM|MACC|LLM|MS|MA|Master)\b",
    re.IGNORECASE,
)
EXCLUDED_PATH_PARTS = (
    "certificate",
    "-cert/",
    "-phd/",
    "/policies/",
    "/financial/",
    "/academic/",
    "/admissions/",
    "/exchange-programs/",
)


class WashUAdapter(OfficialCatalogAdapter):
    university_id = "washington-university-in-st-louis"
    school_prefix = "washu"
    institution_name = "Washington University in St. Louis"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    minimum_expected_programmes = 45
    retrieval_method = "official-2026-2027-bulletin-index"

    def _catalog(self, entries: list[CatalogEntry]):
        catalog = super()._catalog(entries)
        for programme in catalog.programmes:
            if programme.name == "Computer Science, MS (CSE)":
                programme.id = "washu-computer-science-ms"
        return catalog

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries: list[CatalogEntry] = []
        for anchor in soup.select("a[href]"):
            href = str(anchor["href"])
            path = urlsplit(urljoin(CATALOG_URL, href)).path
            name = " ".join(anchor.get_text(" ", strip=True).split())
            lowered_path = path.casefold()
            if not path.startswith("/grad/") or not name:
                continue
            if "accelerated" in name.casefold():
                continue
            if any(part in lowered_path for part in EXCLUDED_PATH_PARTS):
                continue
            if path.rstrip("/").endswith(("/masters", "/degrees", "/sever")):
                continue
            is_caps_degree = path.startswith("/grad/caps/") and re.search(
                r"/(?:m|am|ms|matl)-", path
            )
            degree_match = DEGREE_RE.search(name)
            if not is_caps_degree and degree_match is None:
                continue
            if is_caps_degree:
                name = name.split(", School of Continuing", 1)[0]
            degree_type = degree_match.group(1) if degree_match else "Master"
            entries.append(
                entry(
                    name=name,
                    degree_type=degree_type,
                    source_url=urljoin(CATALOG_URL, href),
                    base_url=CATALOG_URL,
                )
            )
        return entries
