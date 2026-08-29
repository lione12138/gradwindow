from __future__ import annotations

import re
from collections.abc import Callable

from bs4 import BeautifulSoup

from .base import (
    BaseProgrammeAdapter,
    DiscoveredCatalog,
    DiscoveredProgramme,
    DiscoveredWindow,
)

UNIVERSITY_ID = "california-institute-of-technology-caltech"
CATALOG_PREFIX = (
    "https://catalog.caltech.edu/current/information-for-graduate-students/"
    "special-regulations-for-graduate-options/"
)
AEROSPACE_URL = f"{CATALOG_PREFIX}aerospace-ae/"
ELECTRICAL_ENGINEERING_URL = f"{CATALOG_PREFIX}electrical-engineering-ee/"
CATALOG_URL = AEROSPACE_URL
APPLICATION_URL = "https://gradoffice.caltech.edu/admissions/applyonline"
AEROSPACE_ADMISSIONS_URL = "https://aerospace.caltech.edu/academics/admissions"


class CaltechAdapter(BaseProgrammeAdapter):
    university_id = UNIVERSITY_ID
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Fall 2027"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (APPLICATION_URL, AEROSPACE_ADMISSIONS_URL)

    def parse_catalog_from_fetcher(
        self,
        fetcher: Callable[[str], str],
    ) -> DiscoveredCatalog:
        aerospace_text = _page_text(fetcher(AEROSPACE_URL))
        electrical_text = _page_text(fetcher(ELECTRICAL_ENGINEERING_URL))
        intake_year, deadline_policy = _application_policy(
            fetcher(self.application_url)
        )
        aerospace_deadline = _aerospace_deadline(
            fetcher(AEROSPACE_ADMISSIONS_URL), intake_year
        )
        programmes = []
        if _is_direct_aerospace(aerospace_text):
            programmes.extend(
                (
                    _programme(
                        programme_id="caltech-aeronautics-ms",
                        name="MS Aeronautics",
                        department="Aerospace",
                        source_url=AEROSPACE_URL,
                        deadline_policy=deadline_policy,
                        intake_year=intake_year,
                        closes_at=aerospace_deadline,
                    ),
                    _programme(
                        programme_id="caltech-space-engineering-ms",
                        name="MS Space Engineering",
                        department="Aerospace",
                        source_url=AEROSPACE_URL,
                        deadline_policy=deadline_policy,
                        intake_year=intake_year,
                        closes_at=aerospace_deadline,
                    ),
                )
            )
        if _is_direct_electrical_engineering(electrical_text):
            programmes.append(
                _programme(
                    programme_id="caltech-electrical-engineering-ms",
                    name="MS Electrical Engineering",
                    department="Electrical Engineering",
                    source_url=ELECTRICAL_ENGINEERING_URL,
                    deadline_policy=deadline_policy,
                    intake_year=intake_year,
                )
            )
        programmes.sort(key=lambda item: item.id)
        if len(programmes) != 3:
            raise ValueError(
                "Caltech catalogue only verified "
                f"{len(programmes)} direct-entry master's programmes; expected 3"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=programmes)


def _page_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main") or soup
    return _normalise(main.get_text(" ", strip=True))


def _is_direct_aerospace(text: str) -> bool:
    lower = text.lower().replace("’", "'")
    return all(
        phrase in lower
        for phrase in (
            "eligible to seek admission to work toward the master's degree",
            "master's degree in aeronautics",
            "master's degree in space engineering",
        )
    )


def _is_direct_electrical_engineering(text: str) -> bool:
    lower = text.lower().replace("’", "'")
    return "applicants for the msee" in lower and "m.s.-only program" in lower


def _application_policy(html: str) -> tuple[int, str]:
    text = _page_text(html)
    cycle = re.search(
        r"application for the (20\d{2})-(20\d{2}) academic year "
        r"will be available in early October",
        text,
        re.I,
    )
    match = re.search(
        r"Deadlines vary by program from December 1 to December 15[.]?",
        text,
        re.I,
    )
    if cycle is None or int(cycle.group(2)) != int(cycle.group(1)) + 1:
        raise ValueError("Caltech application page lacked its target academic year")
    if match is None:
        raise ValueError(
            "Caltech application page did not contain the expected deadline policy"
        )
    return int(cycle.group(1)), match.group(0).rstrip(".")


def _aerospace_deadline(html: str, intake_year: int) -> str:
    text = _page_text(html)
    if not re.search(
        r"academic year beginning in September;?\s+"
        r"the deadline for applications is December 15",
        text,
        re.I,
    ):
        raise ValueError("Caltech Aerospace page lacked its December 15 deadline")
    return f"{intake_year - 1}-12-15"


def _programme(
    *,
    programme_id: str,
    name: str,
    department: str,
    source_url: str,
    deadline_policy: str,
    intake_year: int,
    closes_at: str | None = None,
) -> DiscoveredProgramme:
    windows = []
    parse_status = "no-deadline"
    if closes_at is not None:
        windows.append(
            DiscoveredWindow(
                round="Graduate admissions deadline",
                opens_at=None,
                closes_at=closes_at,
                intake=f"Fall {intake_year}",
                source_url=AEROSPACE_ADMISSIONS_URL,
                opens_at_basis="missing",
            )
        )
        parse_status = "incomplete"
    return DiscoveredProgramme(
        id=programme_id,
        name=name,
        degree_type="MS",
        faculty="Division of Engineering and Applied Science",
        department=department,
        source_url=source_url,
        application_url=APPLICATION_URL,
        windows=windows,
        deadline_text=(
            "The current Caltech Catalog verifies this as a direct-entry master's "
            f"programme for the {intake_year}-{intake_year + 1} application cycle. "
            f"The Graduate Studies Office states: {deadline_policy}. "
            + (
                "The Aerospace department publishes a December 15 deadline, but "
                "the opening is only described as early October, so no exact "
                "opening date is inferred."
                if closes_at is not None
                else "No programme-specific exact deadline is published for this "
                "route, so no application window is inferred."
            )
        ),
        parse_status=parse_status,
        retrieval_method="official-page",
        evidence_quality="official-full-text",
    )


def _normalise(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
