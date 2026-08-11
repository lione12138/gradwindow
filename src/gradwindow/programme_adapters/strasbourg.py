from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = "https://formations.unistra.fr/fr/formations/master-MAS.html"
APPLICATION_URL = "https://en.unistra.fr/fr/formation/admission/candidater"


class StrasbourgAdapter(OfficialCatalogAdapter):
    university_id = "university-of-strasbourg"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "strasbourg"
    institution_name = "University of Strasbourg"
    minimum_expected_programmes = 90
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-french-masters-catalogue"
    catalogue_limitation_reason = (
        "Strasbourg's official catalogue enumerates national master's mentions "
        "and their tracks. The application platform and calendar depend on the "
        "candidate route, so no shared exact window is inferred."
    )

    def __init__(self, minimum_expected_programmes: int = 90) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalog = self.parse_catalog(fetcher(CATALOG_URL))
        guidance = normalise(
            BeautifulSoup(fetcher(APPLICATION_URL), "html.parser").get_text(
                " ", strip=True
            )
        ).casefold()
        if "monmaster" not in guidance or "plateforme de candidature" not in guidance:
            raise ValueError(
                "Strasbourg's official master's application guide is missing"
            )
        return catalog

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        for article in soup.select("article"):
            link = article.select_one("h2 a[href]")
            if link is None:
                continue
            label = normalise(link.get_text(" ", strip=True))
            if not label.casefold().startswith("master "):
                continue
            rows.append(
                CatalogEntry(
                    name=re.sub(r"^Master\s+", "", label, flags=re.IGNORECASE),
                    degree_type="Master",
                    source_url=urljoin(CATALOG_URL, str(link["href"])),
                )
            )
        return rows
