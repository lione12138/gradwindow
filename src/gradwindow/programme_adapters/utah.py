from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = "https://gradschool.utah.edu/degree-programs-and-contacts/"
APPLICATION_URL = "https://gradschool.utah.edu/future-students/admissions.php"


class UtahAdapter(OfficialCatalogAdapter):
    university_id = "university-of-utah"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "utah"
    institution_name = "University of Utah"
    minimum_expected_programmes = 115
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-graduate-degree-directory"
    catalogue_limitation_reason = (
        "Utah's Graduate School directory identifies master's degrees and their "
        "official departmental pages. Each graduate programme sets its own "
        "requirements and deadlines, so no central exact window is inferred."
    )

    def __init__(self, minimum_expected_programmes: int = 115) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalog = self.parse_catalog(fetcher(CATALOG_URL))
        guidance = normalise(
            BeautifulSoup(fetcher(APPLICATION_URL), "html.parser").get_text(
                " ", strip=True
            )
        ).casefold()
        if (
            "each graduate program sets its own application deadlines" not in guidance
            or "online application system" not in guidance
        ):
            raise ValueError("Utah's official graduate admission guide is missing")
        return catalog

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        for card in soup.select(".c-grid-layout__cell.bg-white"):
            link = card.select_one("h3 a[href]")
            degree_node = card.select_one("p.h6")
            if link is None or degree_node is None:
                continue
            degree = normalise(degree_node.get_text(" ", strip=True))
            if not degree.casefold().startswith("master"):
                continue
            rows.append(
                CatalogEntry(
                    name=normalise(link.get_text(" ", strip=True)),
                    degree_type=degree,
                    source_url=urljoin(CATALOG_URL, str(link["href"])),
                )
            )
        return rows
