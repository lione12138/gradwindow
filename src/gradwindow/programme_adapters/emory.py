from __future__ import annotations

from bs4 import BeautifulSoup

from .base import (
    BaseProgrammeAdapter,
    DiscoveredCatalog,
    DiscoveredProgramme,
    Fetcher,
)
from .official_catalog import normalise, slug

CATALOG_URL = "https://gs.emory.edu/degree-programs/index.html"
APPLICATION_URL = "https://gs.emory.edu/admissions/index.html"


class EmoryAdapter(BaseProgrammeAdapter):
    university_id = "emory-university"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    minimum_expected_programmes = 8

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalog = self.parse_catalog(fetcher(CATALOG_URL))
        fetcher(APPLICATION_URL)
        return catalog

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        programmes: dict[str, DiscoveredProgramme] = {}
        for item in soup.select(".filter-results__content"):
            title = item.select_one(".filter-results__title")
            programme_type = item.select_one(".filter-results__types")
            divisions = item.select_one(".filter-results__divisions")
            if title is None or programme_type is None:
                continue
            type_text = normalise(programme_type.get_text(" ", strip=True))
            if "Master" not in type_text:
                continue
            name = normalise(title.get_text(" ", strip=True))
            faculty = (
                normalise(divisions.get_text(" ", strip=True))
                if divisions is not None
                else "Laney Graduate School"
            )
            programme_id = f"emory-laney-{slug(name)}-master"
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type="Master",
                faculty=faculty or "Laney Graduate School",
                department="Laney Graduate School",
                source_url=CATALOG_URL,
                application_url=APPLICATION_URL,
                windows=[],
                deadline_text=(
                    "Emory's official Laney Graduate School directory marks this "
                    "degree as Master. Application requirements and deadlines are "
                    "programme-specific, and the central catalogue does not publish "
                    "a complete exact opening-and-closing pair, so no dates are "
                    "inferred."
                ),
                parse_status="no-deadline",
                retrieval_method="official-laney-degree-directory",
                evidence_quality="official-full-text",
            )

        result = sorted(programmes.values(), key=lambda item: item.id)
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                "Emory's official Laney directory contained "
                f"{len(result)} master's programmes; expected at least "
                f"{self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)
