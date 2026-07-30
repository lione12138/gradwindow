from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import (
    CatalogEntry,
    OfficialCatalogAdapter,
    degree_from,
    entry,
)

CATALOG_URL = "https://www.universiteitleiden.nl/en/education/study-programmes?pageNumber=1&type=master"
APPLICATION_URL = (
    "https://www.universiteitleiden.nl/en/education/masters/admission-and-application"
)
PATH_RE = re.compile(r"/en/education/study-programmes/master/")


class LeidenAdapter(OfficialCatalogAdapter):
    university_id = "leiden-university"
    school_prefix = "leiden"
    institution_name = "Leiden University"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 220

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        entries = []
        for page in range(1, 15):
            url = f"https://www.universiteitleiden.nl/en/education/study-programmes?pageNumber={page}&type=master"
            entries.extend(self.extract_entries(fetcher(url)))
        return self._catalog(entries)

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        return [
            entry(
                name=link.get_text(" ", strip=True).removeprefix("Master "),
                degree_type=degree_from(link.get_text(" ", strip=True)),
                source_url=link["href"],
                base_url=CATALOG_URL,
            )
            for link in soup.find_all("a", href=PATH_RE)
            if link.get_text(" ", strip=True).startswith("Master ")
        ]
