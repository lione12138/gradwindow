from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = "https://catalogue.uottawa.ca/en/graduate/"
APPLICATION_URL = "https://www.uottawa.ca/study/graduate-studies/how-to-apply"


class OttawaAdapter(OfficialCatalogAdapter):
    university_id = "university-of-ottawa"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "ottawa"
    institution_name = "University of Ottawa"
    minimum_expected_programmes = 175
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-graduate-academic-catalogue"
    catalogue_limitation_reason = (
        "uOttawa's official academic catalogue enumerates English and French "
        "master's variants, concentrations, and specialisations. Deadlines are "
        "programme-specific and the central guide does not publish one exact pair."
    )

    def __init__(self, minimum_expected_programmes: int = 175) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalog = self.parse_catalog(fetcher(CATALOG_URL))
        guidance = normalise(
            BeautifulSoup(fetcher(APPLICATION_URL), "html.parser").get_text(
                " ", strip=True
            )
        ).casefold()
        if (
            "check your deadlines and requirements" not in guidance
            or "ouac" not in guidance
        ):
            raise ValueError("uOttawa's official graduate application guide is missing")
        return catalog

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        for link in soup.select('main a[href*="/en/graduate/"]'):
            label = normalise(link.get_text(" ", strip=True))
            folded = label.casefold()
            if not folded.startswith(("master", "maîtrise", "executive master")):
                continue
            rows.append(
                CatalogEntry(
                    name=label,
                    degree_type="Maîtrise"
                    if folded.startswith("maîtrise")
                    else "Master",
                    source_url=urljoin(CATALOG_URL, str(link["href"])),
                )
            )
        return rows
