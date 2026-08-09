from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry, normalise

CATALOG_URL = (
    "https://tu-dresden.de/studium/vor-dem-studium/studienangebot/sins/"
    "sins_start_results?abschluss=3&listView=1&set_language=en"
)
APPLICATION_URL = (
    "https://tu-dresden.de/studium/vor-dem-studium/bewerbung?set_language=en"
)


class TUDresdenAdapter(OfficialCatalogAdapter):
    university_id = "technische-universitat-dresden"
    school_prefix = "tu-dresden"
    institution_name = "Technische Universität Dresden"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-sins-programme-directory"

    def __init__(self, minimum_expected_programmes: int = 65) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        return self.parse_catalog(fetcher(CATALOG_URL))

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries = []
        seen_urls = set()
        for heading in soup.select("h2"):
            name = normalise(heading.get_text(" ", strip=True))
            card = heading.find_parent("a", href=True)
            if card is None or not name:
                continue
            source_url = str(card.get("href", "")).strip()
            if not re.search(r"/sins/\d+$", source_url) or source_url in seen_urls:
                continue
            seen_urls.add(source_url)
            entries.append(
                entry(
                    name=name,
                    degree_type="Master",
                    source_url=source_url,
                    base_url=CATALOG_URL,
                )
            )
        return entries
