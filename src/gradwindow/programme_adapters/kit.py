from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry

CATALOG_URL = "https://www.sle.kit.edu/english/vorstudium/83.php"
APPLICATION_URL = "https://www.sle.kit.edu/english/vorstudium/88.php"
DEADLINES_URL = "https://www.sle.kit.edu/english/vorstudium/3968.php"
DEGREE_RE = re.compile(r"\b(M\.Sc\.|M\.A\.|M\.Ed\.|M\.Arch\.)", re.IGNORECASE)
DEGREE_TYPES = {
    "m.sc.": "MSc",
    "m.a.": "MA",
    "m.ed.": "MEd",
    "m.arch.": "MArch",
}


class KITAdapter(OfficialCatalogAdapter):
    university_id = "karlsruhe-institute-of-technology-kit"
    school_prefix = "kit"
    institution_name = "Karlsruhe Institute of Technology"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL, DEADLINES_URL)
    minimum_expected_programmes = 65
    retrieval_method = "official-masters-degree-directory"

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalog = fetcher(CATALOG_URL)
        fetcher(APPLICATION_URL)
        fetcher(DEADLINES_URL)
        return self.parse_catalog(catalog)

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries = []
        for tile in soup.select("main .content div.service-tile"):
            heading = tile.select_one(".headline")
            link = tile.select_one("a[href]")
            if heading is None or link is None:
                continue
            name = heading.get_text(" ", strip=True).replace("\u00ad", "")
            match = DEGREE_RE.search(name)
            if match is None:
                continue
            entries.append(
                entry(
                    name=name,
                    degree_type=DEGREE_TYPES[match.group(1).casefold()],
                    source_url=link["href"],
                    base_url=CATALOG_URL,
                )
            )
        return entries
