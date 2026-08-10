from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme, Fetcher
from .official_catalog import normalise, slug

CATALOG_URL = "https://catalog.colorado.edu/graduate/academic-offerings/"
DEADLINES_URL = (
    "https://www.colorado.edu/graduateschool/admissions/where-begin/"
    "program-information-deadlines"
)
APPLICATION_URL = (
    "https://www.colorado.edu/graduateschool/admissions/where-begin/how-apply"
)


class ColoradoBoulderAdapter(BaseProgrammeAdapter):
    university_id = "university-of-colorado-boulder"
    catalog_url = CATALOG_URL
    admissions_url = DEADLINES_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, DEADLINES_URL)
    retrieval_method = "official-courseleaf-graduate-catalogue"
    catalogue_limitation_reason = (
        "CU Boulder publishes deadlines by programme. Its central programme table "
        "does not provide a complete exact opening-and-closing pair with years for "
        "every master's route, so the official deadline table remains monitored."
    )

    def __init__(self, minimum_expected_programmes: int = 90) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalogue = self.parse_catalog(fetcher(CATALOG_URL))
        policy = normalise(
            BeautifulSoup(fetcher(DEADLINES_URL), "html.parser").get_text(
                " ", strip=True
            )
        ).casefold()
        if "program information" not in policy or "deadline" not in policy:
            raise ValueError(
                "CU Boulder's official programme deadline table is missing"
            )
        return catalogue

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        programmes: dict[str, DiscoveredProgramme] = {}
        for link in soup.select('a[href*="/graduate/colleges-schools/"]'):
            href = str(link.get("href", ""))
            if "/programs-study/" not in href:
                continue
            label = normalise(link.get_text(" ", strip=True).replace("\u200b", ""))
            if "master" not in label.casefold() or " - " not in label:
                continue
            name, degree_type = (part.strip() for part in label.rsplit(" - ", 1))
            source_url = urljoin(CATALOG_URL, href)
            programme_id = f"colorado-boulder-{slug(name)}-{slug(degree_type)}"
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type=degree_type,
                faculty="University of Colorado Boulder Graduate School",
                department="University of Colorado Boulder Graduate School",
                source_url=source_url,
                application_url=APPLICATION_URL,
                windows=[],
                deadline_text=(
                    "Programme found in CU Boulder's official graduate catalogue. "
                    "The university publishes programme-specific deadlines without "
                    "a complete exact opening-and-closing pair here, so no date is "
                    "inferred."
                ),
                parse_status="no-deadline",
                retrieval_method=self.retrieval_method,
                evidence_quality="official-full-text",
            )
        result = sorted(programmes.values(), key=lambda row: row.name.casefold())
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                f"CU Boulder catalogue contained {len(result)} master's routes; "
                f"expected at least {self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)
