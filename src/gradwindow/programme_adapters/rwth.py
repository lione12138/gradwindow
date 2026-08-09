from __future__ import annotations

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import (
    CatalogEntry,
    OfficialCatalogAdapter,
    degree_from,
    entry,
)

CATALOG_URL = (
    "https://www.rwth-aachen.de/cms/root/studium/vor-dem-studium/"
    "studiengaenge/~yev/liste-aktuelle-studiengaenge/?lidx=1"
)
APPLICATION_URL = "https://www.rwth-aachen.de/go/id/bxip/lidx/1"


class RWTHAdapter(OfficialCatalogAdapter):
    university_id = "rheinisch-westf-lische-technische-hochschule-aachen"
    school_prefix = "rwth"
    institution_name = "RWTH Aachen University"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    minimum_expected_programmes = 80
    retrieval_method = "official-degree-programme-directory"

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        entries: list[CatalogEntry] = []
        for page in range(1, 5):
            separator = "&" if "?" in CATALOG_URL else "?"
            entries.extend(
                self.extract_entries(fetcher(f"{CATALOG_URL}{separator}page={page}"))
            )
        fetcher(APPLICATION_URL)
        return self._catalog(entries)

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries: list[CatalogEntry] = []
        for row in soup.select("table tr"):
            if "Degree Master" not in " ".join(row.stripped_strings):
                continue
            anchor = row.select_one("a.iconless[href]")
            if anchor is None:
                continue
            entries.append(
                entry(
                    name=anchor.get_text(" ", strip=True),
                    degree_type=degree_from(anchor.get_text(" ", strip=True)),
                    source_url=str(anchor["href"]),
                    base_url=CATALOG_URL,
                )
            )
        return entries
