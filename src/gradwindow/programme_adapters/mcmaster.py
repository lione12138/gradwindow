from __future__ import annotations

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry, normalise

CATALOG_URL = "https://gs.mcmaster.ca/programs/"
APPLICATION_URL = "https://gs.mcmaster.ca/how-to-apply/"
EXISTING_COMPUTING_ID = "mcmaster-computer-science-msc"


class McMasterAdapter(OfficialCatalogAdapter):
    university_id = "mcmaster-university"
    school_prefix = "mcmaster"
    institution_name = "McMaster University"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 75
    retrieval_method = "official-graduate-program-directory"

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalog = fetcher(CATALOG_URL)
        fetcher(APPLICATION_URL)
        return self.parse_catalog(catalog)

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries: list[CatalogEntry] = []
        for card in soup.select(".card"):
            heading = card.select_one("h3.card-title")
            source = card.select_one("a.card-link[href]")
            if heading is None or source is None:
                continue
            name = normalise(heading.get_text(" ", strip=True))
            for badge in card.select(".badge"):
                degree_type = normalise(badge.get_text(" ", strip=True))
                if not degree_type.startswith("M") or "PhD" in degree_type:
                    continue
                entries.append(
                    entry(
                        name=name,
                        degree_type=degree_type,
                        source_url=str(source["href"]),
                        base_url=CATALOG_URL,
                    )
                )
        return entries

    def _catalog(self, entries: list[CatalogEntry]) -> DiscoveredCatalog:
        catalog = super()._catalog(entries)
        for programme in catalog.programmes:
            if (
                programme.name == "Computing and Software"
                and programme.degree_type == "MSc"
            ):
                programme.id = EXISTING_COMPUTING_ID
        return catalog
