from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = (
    "https://catalog.ucsc.edu/en/current/general-catalog/academic-programs/"
    "masters-degrees"
)
APPLICATION_URL = "https://graddiv.ucsc.edu/prospective-students/"
DEGREE_RE = re.compile(r"\s+(M\.(?:A|S|F\.A)\.)$")


class UCSCAdapter(OfficialCatalogAdapter):
    university_id = "university-of-california-santa-cruz"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "ucsc"
    institution_name = "University of California, Santa Cruz"
    minimum_expected_programmes = 30
    window_watch_urls = (CATALOG_URL,)
    retrieval_method = "official-current-general-catalog-masters-list"
    catalogue_limitation_reason = (
        "The current UCSC General Catalog provides a complete master's degree "
        "list. Graduate Division admissions pages are not reliably retrievable by "
        "the unattended client, so window discovery is retained as a monitored "
        "access limitation rather than guessed from older dates."
    )

    def __init__(self, minimum_expected_programmes: int = 30) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        main = soup.select_one("#main")
        if main is None:
            return []
        rows = []
        for link in main.select("h1 + .combinedChild + ul > li > a[href]"):
            label = normalise(link.get_text(" ", strip=True))
            match = DEGREE_RE.search(label)
            if match is None:
                continue
            rows.append(
                CatalogEntry(
                    name=label[: match.start()],
                    degree_type=match.group(1),
                    source_url=urljoin(CATALOG_URL, str(link["href"])),
                )
            )
        return rows
