from __future__ import annotations

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry

CATALOG_URL = "https://www.purdue.edu/academics/ogsps/program-search/"
APPLICATION_URL = "https://www.purdue.edu/academics/ogsps/admissions/how-to-apply/"


class PurdueAdapter(OfficialCatalogAdapter):
    university_id = "purdue-university"
    school_prefix = "purdue"
    institution_name = "Purdue University"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 120
    retrieval_method = "official-main-campus-graduate-program-directory"

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalog = fetcher(CATALOG_URL)
        fetcher(APPLICATION_URL)
        return self.parse_catalog(catalog)

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries = []
        for card in soup.select(".program-card"):
            categories = card.get("data-category", "")
            level = card.select_one(".degree_level-label")
            heading = card.select_one("h2")
            source = card.select_one(
                'a[href*="purdue.edu/academics/ogsps/admissions/gradrequirements/"]'
            )
            if (
                "west-lafayette" not in categories
                or level is None
                or "Masters" not in level.get_text(" ", strip=True)
                or heading is None
                or source is None
            ):
                continue
            entries.append(
                entry(
                    name=heading.get_text(" ", strip=True),
                    degree_type="Master",
                    source_url=source["href"],
                    base_url=CATALOG_URL,
                )
            )
        return entries
