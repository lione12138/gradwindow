from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry

CATALOG_URL = "https://www.eur.nl/en/education/master/overview"
APPLICATION_URL = (
    "https://www.eur.nl/en/education/practical-matters/registration/"
    "first-registration/master"
)


class ErasmusAdapter(OfficialCatalogAdapter):
    university_id = "erasmus-university-rotterdam"
    school_prefix = "erasmus"
    institution_name = "Erasmus University Rotterdam"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 115
    retrieval_method = "official-paginated-master-directory"

    def _catalog(self, entries: list[CatalogEntry]) -> DiscoveredCatalog:
        catalog = super()._catalog(entries)
        for programme in catalog.programmes:
            if programme.name == "Data Science and Marketing Analytics":
                # Preserve the pre-existing curated record and its programme group.
                programme.id = "erasmus-data-science-marketing-analytics"
        return catalog

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        page_url = CATALOG_URL
        visited: set[str] = set()
        entries: list[CatalogEntry] = []
        for _ in range(20):
            if page_url in visited:
                raise ValueError("Erasmus master's directory pagination looped")
            visited.add(page_url)
            page = fetcher(page_url)
            entries.extend(self.extract_entries(page))
            soup = BeautifulSoup(page, "html.parser")
            next_link = soup.select_one(".pager__item--next a[href]")
            if next_link is None:
                break
            page_url = urljoin(page_url, next_link["href"])
        else:
            raise ValueError("Erasmus master's directory exceeded 20 pages")
        fetcher(APPLICATION_URL)
        return self._catalog(entries)

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries = []
        for card in soup.select(".teaser.teaser--linked"):
            link = card.select_one(".teaser__title a[href]")
            if link is None:
                continue
            name = link.get_text(" ", strip=True)
            if not name:
                continue
            entries.append(
                entry(
                    name=name,
                    degree_type="Master",
                    source_url=link["href"],
                    base_url=CATALOG_URL,
                )
            )
        return entries
