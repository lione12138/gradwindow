from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry

CATALOG_URL = "https://www.unibe.ch/studies/programs/masters/programs/index_eng.html"
APPLICATION_URL = (
    "https://www.unibe.ch/studies/programs/masters/application/"
    "international/index_eng.html"
)
FALL_DEADLINES_URL = "https://www.unibe.ch/studies/dates/students/fall/index_eng.html"
PROGRAMME_MODE_RE = re.compile(r"\s+\((?:Mono|Major)(?:,\s*(?:Mono|Major))*\)$")


class BernAdapter(OfficialCatalogAdapter):
    university_id = "university-of-bern"
    school_prefix = "bern"
    institution_name = "University of Bern"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL, FALL_DEADLINES_URL)
    minimum_expected_programmes = 70
    retrieval_method = "official-mono-major-master-directory"

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalog = fetcher(CATALOG_URL)
        fetcher(APPLICATION_URL)
        fetcher(FALL_DEADLINES_URL)
        return self.parse_catalog(catalog)

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        heading = next(
            (
                item
                for item in soup.select("h2")
                if "Mono/major study programs from A to Z"
                in item.get_text(" ", strip=True)
            ),
            None,
        )
        if heading is None:
            return []
        container = heading.find_next_sibling("div")
        if container is None:
            return []
        entries = []
        for link in container.select("ul.nav-list > li > a[href]"):
            name = PROGRAMME_MODE_RE.sub("", link.get_text(" ", strip=True))
            entries.append(
                entry(
                    name=name,
                    degree_type="Master",
                    source_url=link["href"],
                    base_url=CATALOG_URL,
                )
            )
        return entries
