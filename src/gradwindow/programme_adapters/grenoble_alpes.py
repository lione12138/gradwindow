from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = (
    "https://formations.univ-grenoble-alpes.fr/fr/catalogue-2021/master-XB.html"
)
APPLICATION_URL = (
    "https://www.univ-grenoble-alpes.fr/education/how-to-apply/"
    "applying-and-registering/apply/"
)


class GrenobleAlpesAdapter(OfficialCatalogAdapter):
    university_id = "universite-grenoble-alpes"
    school_prefix = "grenoble-alpes"
    institution_name = "Université Grenoble Alpes"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    minimum_expected_programmes = 70
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-french-master-mentions-catalogue"
    catalogue_limitation_reason = (
        "UGA's official catalogue enumerates master's mentions. Its official "
        "application guide routes candidates by year, residence and status to "
        "Mon Master, PEF or eCandidat, so no shared exact dates are inferred."
    )

    def __init__(self, minimum_expected_programmes: int = 70) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalog = self.parse_catalog(fetcher(CATALOG_URL))
        guidance = normalise(
            BeautifulSoup(fetcher(APPLICATION_URL), "html.parser").get_text(
                " ", strip=True
            )
        ).casefold()
        if "master" not in guidance or "mon master" not in guidance:
            raise ValueError("Grenoble Alpes's official application routing is missing")
        return catalog

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries: list[CatalogEntry] = []
        for link in soup.select("a[href]"):
            label = normalise(link.get_text(" ", strip=True))
            if not label.casefold().startswith("master "):
                continue
            entries.append(
                CatalogEntry(
                    name=re.sub(r"^Master\s+", "", label, flags=re.I),
                    degree_type="Master",
                    source_url=urljoin(CATALOG_URL, str(link["href"])),
                )
            )
        return entries
