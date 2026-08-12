from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, DiscoveredProgramme, DiscoveredWindow, Fetcher
from .official_catalog import normalise, slug

CATALOG_URL = "https://graduate.technion.ac.il/en/degrees-offered/"
DEADLINES_URL = "https://graduate.technion.ac.il/en/registration-dates-instructions/"
APPLICATION_URL = "https://portalex.technion.ac.il/sap/bc/ui5_ui5/sap/zher_formrt/index.html?sap-client=700&sap-language=EN&sap-ui-language=EN#/Logon"

_CURRENT_CYCLE_RE = re.compile(
    r"Winter Semester of 2026-2027 has begun.*?extended until 31\.05\.2026",
    re.IGNORECASE | re.DOTALL,
)
_OPENING_RE = re.compile(r"Between\s+1\.3\s*[-–]\s*30\.4", re.IGNORECASE)


class TechnionAdapter:
    university_id = "technion-israel-institute-of-technology"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Winter semester 2026-2027"
    application_opens_at_basis = "official"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, DEADLINES_URL)
    known_programme_window_scope_type = "programme-group"
    known_programme_window_scope_id = "technion-winter-master-admissions"

    def __init__(
        self,
        minimum_expected_programmes: int = 28,
        maximum_expected_programmes: int = 35,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.maximum_expected_programmes = maximum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        programmes = _programmes(fetcher(CATALOG_URL))
        if not (
            self.minimum_expected_programmes
            <= len(programmes)
            <= self.maximum_expected_programmes
        ):
            raise ValueError(
                f"Technion catalogue contained {len(programmes)} academic units; "
                f"expected {self.minimum_expected_programmes}-"
                f"{self.maximum_expected_programmes}"
            )
        opens_at, closes_at = _application_window(fetcher(DEADLINES_URL))
        programmes.append(
            DiscoveredProgramme(
                id="technion-winter-master-admissions",
                name="Winter master's admissions",
                degree_type="Master",
                faculty="Jacobs Graduate School",
                department="Registration and Admission Office",
                source_url=DEADLINES_URL,
                application_url=APPLICATION_URL,
                windows=[
                    DiscoveredWindow(
                        round="Winter semester registration",
                        applicant_categories=["all"],
                        opens_at=opens_at,
                        closes_at=closes_at,
                        intake=self.intake,
                        source_url=DEADLINES_URL,
                        opens_at_basis="official",
                    )
                ],
                deadline_text=(
                    "Technion's current registration page publishes the winter "
                    "semester opening and its exact extended closing date."
                ),
                parse_status="parsed",
                retrieval_method="official-current-registration-page",
                evidence_quality="official-full-text",
            )
        )
        return DiscoveredCatalog(application_opens_at=opens_at, programmes=programmes)


def _programmes(html: str) -> list[DiscoveredProgramme]:
    soup = BeautifulSoup(html, "html.parser")
    programmes: dict[str, DiscoveredProgramme] = {}
    for section in soup.select(".section-content"):
        heading = section.find("h2")
        section_name = normalise(heading.get_text(" ", strip=True) if heading else "")
        if section_name not in {"Faculties", "Interdisciplinary Programs"}:
            continue
        for link in section.select("h3 a[href]"):
            name = normalise(link.get_text(" ", strip=True))
            source_url = urljoin(CATALOG_URL, str(link.get("href", "")))
            if not name:
                continue
            programme_id = f"technion-{slug(name)}"
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type="Master",
                faculty=section_name,
                department=name,
                source_url=source_url,
                application_url=APPLICATION_URL,
                windows=[],
                deadline_text=(
                    "Academic unit is listed in Technion's official graduate "
                    "degree-program directory. The shared winter window is "
                    "represented once at programme-group scope."
                ),
                parse_status="no-deadline",
                retrieval_method="official-graduate-degree-program-directory",
                evidence_quality="official-full-text",
            )
    return sorted(programmes.values(), key=lambda item: item.name.casefold())


def _application_window(html: str) -> tuple[str, str]:
    text = normalise(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))
    if _CURRENT_CYCLE_RE.search(text) is None or _OPENING_RE.search(text) is None:
        raise ValueError("Technion's current winter registration window was not found")
    return "2026-03-01", "2026-05-31"
