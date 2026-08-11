from __future__ import annotations

import re
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, DiscoveredProgramme, DiscoveredWindow, Fetcher
from .official_catalog import normalise, slug

CATALOG_URL = "https://www.unil.ch/unil/fr/home/menuinst/etudier/masters.html"
APPLICATION_URL = "https://candidature.unil.ch/"
_MONTHS = {
    "janvier": 1,
    "février": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "août": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "décembre": 12,
}


class LausanneAdapter:
    university_id = "university-of-lausanne"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Spring 2027"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-master-catalogue-and-application-portal"
    known_programme_window_scope_type = "programme-group"
    known_programme_window_scope_id = "lausanne-master-admissions"

    def __init__(self, minimum_expected_programmes: int = 40) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        programmes = _programmes(fetcher(CATALOG_URL))
        if len(programmes) < self.minimum_expected_programmes:
            raise ValueError(
                f"Lausanne catalogue contained {len(programmes)} master's "
                f"programmes; expected at least {self.minimum_expected_programmes}"
            )
        general_close, visa_close, intake = _application_closes(
            fetcher(APPLICATION_URL)
        )
        programmes.append(
            DiscoveredProgramme(
                id="lausanne-master-admissions",
                name="Master admissions",
                degree_type="Master",
                faculty="University of Lausanne",
                department="Admissions Office",
                source_url=APPLICATION_URL,
                application_url=APPLICATION_URL,
                windows=[
                    DiscoveredWindow(
                        round="General application deadline",
                        applicant_categories=["all"],
                        opens_at=None,
                        closes_at=general_close,
                        intake=intake,
                        source_url=APPLICATION_URL,
                        opens_at_basis="missing",
                    ),
                    DiscoveredWindow(
                        round="Study-visa application deadline",
                        applicant_categories=["international-students"],
                        opens_at=None,
                        closes_at=visa_close,
                        intake=intake,
                        source_url=APPLICATION_URL,
                        opens_at_basis="missing",
                    ),
                ],
                deadline_text=(
                    "UNIL's official application portal publishes exact closing "
                    "dates but no exact opening date. These remain review guidance "
                    "rather than publishable exact windows."
                ),
                parse_status="incomplete",
                retrieval_method=self.retrieval_method,
                evidence_quality="official-full-text",
            )
        )
        return DiscoveredCatalog(application_opens_at=None, programmes=programmes)


def _programmes(html: str) -> list[DiscoveredProgramme]:
    programmes: dict[str, DiscoveredProgramme] = {}
    soup = BeautifulSoup(html, "html.parser")
    for accordion in soup.select(".accordion-question"):
        faculty_node = accordion.select_one(".accordion-btn-text")
        faculty = normalise(
            faculty_node.get_text(" ", strip=True)
            if faculty_node is not None
            else "University of Lausanne"
        )
        for link in accordion.select(".accordion-text a[href*='/masters/']"):
            name = normalise(link.get_text(" ", strip=True))
            source_url = urljoin(CATALOG_URL, str(link.get("href", "")).strip())
            if not name or not source_url:
                continue
            programme_id = f"lausanne-{slug(source_url.rsplit('/', 1)[-1])}-master"
            programmes.setdefault(
                programme_id,
                DiscoveredProgramme(
                    id=programme_id,
                    name=name,
                    degree_type="Master",
                    faculty=faculty,
                    department=faculty,
                    source_url=source_url,
                    application_url=APPLICATION_URL,
                    windows=[],
                    deadline_text=(
                        "Programme is listed in UNIL's official master catalogue. "
                        "The shared application portal gives closing dates but no "
                        "exact opening date, so no exact window is inferred."
                    ),
                    parse_status="no-deadline",
                    retrieval_method=(
                        "official-master-catalogue-and-application-portal"
                    ),
                    evidence_quality="official-full-text",
                ),
            )
    return sorted(programmes.values(), key=lambda item: item.name.casefold())


def _application_closes(html: str) -> tuple[str, str, str]:
    soup = BeautifulSoup(html, "html.parser")
    heading = next(
        (
            normalise(value)
            for value in soup.stripped_strings
            if normalise(value).startswith("Semestre de printemps ")
        ),
        "",
    )
    year_match = re.search(r"(20\d{2})", heading)
    if year_match is None:
        raise ValueError("UNIL portal did not expose its current spring intake")
    intake_year = int(year_match.group(1))

    for row in soup.select("table tr"):
        cells = row.select("td")
        if len(cells) != 2 or normalise(cells[0].get_text(" ", strip=True)) != "Master":
            continue
        deadline_text = normalise(cells[1].get_text(" ", strip=True))
        dates = re.findall(
            r"(\d{1,2})\s+([A-Za-zÀ-ÿ]+)(?:\s+si visa en vue d'études)?",
            deadline_text,
            re.IGNORECASE,
        )
        if len(dates) < 2:
            continue
        general_close = _french_date(dates[0], intake_year - 1)
        visa_close = _french_date(dates[1], intake_year - 1)
        return general_close, visa_close, f"Spring {intake_year}"
    raise ValueError("UNIL portal did not expose master closing dates")


def _french_date(value: tuple[str, str], year: int) -> str:
    day, raw_month = value
    month = _MONTHS.get(raw_month.casefold())
    if month is None:
        raise ValueError(f"Unsupported UNIL month: {raw_month}")
    return datetime(year, month, int(day)).date().isoformat()
