from __future__ import annotations

from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry

CATALOG_URL = "https://www.uu.nl/sitemap.xml"
APPLICATION_URL = "https://www.uu.nl/en/masters/general-information/application-and-admission/application-procedure"

_NON_PROGRAMME_SLUGS = {
    "masters-programmes",
    "economics-masters-programmes",
    "research-masters-programmes",
    "law-masters-programmes",
    "the-llms-honours-programme",
    "elective-courses-faculty-social-and-behavioural-sciences",
    "science-behind-the-scenes",
    "this-programme-doesnt-exist-anymore",
}
_NAME_FIXES = {"Gima": "GIMA", "Llms": "LLMs"}


class UtrechtAdapter(OfficialCatalogAdapter):
    university_id = "utrecht-university"
    school_prefix = "utrecht"
    institution_name = "Utrecht University"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-sitemap-masters-directory"

    def __init__(self, minimum_expected_programmes: int = 95) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        sitemap_index = BeautifulSoup(fetcher(CATALOG_URL), "xml")
        sitemap_urls = [
            node.get_text(strip=True) for node in sitemap_index.select("loc")
        ]
        if not sitemap_urls:
            raise ValueError("Utrecht sitemap index exposed no child sitemaps")
        entries: list[CatalogEntry] = []
        for sitemap_url in sitemap_urls:
            entries.extend(self.extract_entries(fetcher(sitemap_url)))
        return self._catalog(entries)

    def extract_entries(self, xml: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(xml, "xml")
        entries: list[CatalogEntry] = []
        for location in soup.select("loc"):
            source_url = location.get_text(strip=True)
            path = urlparse(source_url).path.rstrip("/")
            parts = path.split("/")
            if len(parts) != 4 or parts[1:3] != ["en", "masters"]:
                continue
            programme_slug = parts[-1]
            if programme_slug in _NON_PROGRAMME_SLUGS:
                continue
            name = " ".join(word.capitalize() for word in programme_slug.split("-"))
            for old, new in _NAME_FIXES.items():
                name = name.replace(old, new)
            entries.append(
                entry(
                    name=name,
                    degree_type="Master",
                    source_url=source_url,
                    base_url=CATALOG_URL,
                )
            )
        return entries
