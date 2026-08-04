from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry, normalise

CATALOG_URL = "https://www.titech.ac.jp/english/prospective-students/graduate-programs"
APPLICATION_URL = (
    "https://admissions.isct.ac.jp/en/013/graduate/programs/science-and-engineering"
)
MASTER_CODES = ("MTM", "MS", "ME", "MA")


class ScienceTokyoAdapter(OfficialCatalogAdapter):
    university_id = "tokyo-institute-of-technology"
    school_prefix = "science-tokyo"
    institution_name = "Institute of Science Tokyo"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 19
    retrieval_method = "official-graduate-department-directory"

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalog = fetcher(CATALOG_URL)
        fetcher(APPLICATION_URL)
        return self.parse_catalog(catalog)

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries: list[CatalogEntry] = []
        for row in soup.select("table tr"):
            cells = row.find_all("td")
            if len(cells) < 2:
                continue
            department_cell, certification_cell = cells[-2:]
            certification = normalise(certification_cell.get_text(" ", strip=True))
            degree_type = next(
                (
                    code
                    for code in MASTER_CODES
                    if re.search(rf"\b{re.escape(code)}\b", certification)
                ),
                None,
            )
            source = department_cell.select_one('a[href^="#"]')
            if degree_type is None or source is None:
                continue
            name = normalise(department_cell.get_text(" ", strip=True)).replace(
                "(professional", " (professional"
            )
            entries.append(
                entry(
                    name=name,
                    degree_type=degree_type,
                    source_url=str(source["href"]),
                    base_url=CATALOG_URL,
                )
            )
        return entries
