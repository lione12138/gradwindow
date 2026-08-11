from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = "https://www.uantwerpen.be/en/study/programmes/master/"
APPLICATION_URL = "https://www.uantwerpen.be/en/study/admission-and-enrolment/"


class AntwerpAdapter(OfficialCatalogAdapter):
    university_id = "university-of-antwerp"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "antwerp"
    institution_name = "University of Antwerp"
    minimum_expected_programmes = 25
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-english-masters-directory"
    catalogue_limitation_reason = (
        "Antwerp's official English-language directory covers the master's "
        "programmes presented to international applicants. Programme-specific "
        "admission pages control dates, so no common exact window is inferred."
    )

    def __init__(self, minimum_expected_programmes: int = 25) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalog = self.parse_catalog(fetcher(CATALOG_URL))
        guidance = normalise(
            BeautifulSoup(fetcher(APPLICATION_URL), "html.parser").get_text(
                " ", strip=True
            )
        ).casefold()
        if "how to apply" not in guidance or "master" not in guidance:
            raise ValueError("Antwerp's official admission guidance is missing")
        return catalog

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        for link in soup.select("#main a.wrap[href]"):
            title = link.select_one("h3.heading")
            level = link.select_one(".spec.levels .value")
            if title is None or level is None:
                continue
            if "master" not in normalise(level.get_text(" ", strip=True)).casefold():
                continue
            rows.append(
                CatalogEntry(
                    name=normalise(title.get_text(" ", strip=True)),
                    degree_type="Master",
                    source_url=urljoin(CATALOG_URL, str(link["href"])),
                )
            )
        return rows
