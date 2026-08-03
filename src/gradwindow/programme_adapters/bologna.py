from __future__ import annotations

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry

CATALOG_URL = (
    "https://www.unibo.it/en/study/second-cycle-degree"
    "?pagenumber=1&pagesize=200&order=asc&sort=title&orderby=alphabetic"
)
APPLICATION_URL = "https://www.unibo.it/en/study/enrolment-fees-and-other-procedures"


class BolognaAdapter(OfficialCatalogAdapter):
    university_id = "alma-mater-studiorum-university-of-bologna"
    school_prefix = "bologna"
    institution_name = "University of Bologna"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 135
    retrieval_method = "official-second-cycle-degree-directory"

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalog = fetcher(CATALOG_URL)
        fetcher(APPLICATION_URL)
        return self.parse_catalog(catalog)

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries = []
        for card in soup.select(".card-list-abstract .item"):
            heading = card.select_one("div.title h3")
            link = card.select_one('a[href*="/study/second-cycle-degree/programme/"]')
            if heading is None or link is None:
                continue
            entries.append(
                entry(
                    name=heading.get_text(" ", strip=True),
                    degree_type="Master",
                    source_url=link["href"],
                    base_url=CATALOG_URL,
                )
            )
        return entries
