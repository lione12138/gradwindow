from __future__ import annotations

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry, normalise

CATALOG_URL = "https://grad.uwo.ca/admissions/programs/index.cfm"
APPLICATION_URL = "https://grad.uwo.ca/admissions/apply.html"
EXISTING_COMPUTER_SCIENCE_ID = "western-computer-science-msc"


class WesternAdapter(OfficialCatalogAdapter):
    university_id = "western-university"
    school_prefix = "western"
    institution_name = "Western University"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 80
    retrieval_method = "official-graduate-program-directory"

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalog = fetcher(CATALOG_URL)
        fetcher(APPLICATION_URL)
        return self.parse_catalog(catalog)

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries: list[CatalogEntry] = []
        for row in soup.select("#programTable tr.MASTERS"):
            cells = row.find_all("td")
            if len(cells) < 2:
                continue
            name = normalise(cells[0].get_text(" ", strip=True))
            source = cells[1].select_one('a[href*="program.cfm"]')
            if not name or source is None:
                continue
            entries.append(
                entry(
                    name=name,
                    degree_type=source.get_text(" ", strip=True),
                    source_url=str(source["href"]),
                    base_url=CATALOG_URL,
                )
            )
        return entries

    def _catalog(self, entries: list[CatalogEntry]) -> DiscoveredCatalog:
        catalog = super()._catalog(entries)
        for programme in catalog.programmes:
            if (
                programme.name == "Computer Science"
                and programme.degree_type == "Master of Science"
            ):
                programme.id = EXISTING_COMPUTER_SCIENCE_ID
        return catalog
