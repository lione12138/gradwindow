from __future__ import annotations

import re
from collections.abc import Callable
from datetime import date
from urllib.parse import urljoin, urlsplit

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
DEADLINE_OPTIONS = (
    "Aeronautics (AE)",
    "Space Engineering (SE)",
    "Electrical Engineering (EE)",
)


class CaltechAdapter(BaseProgrammeAdapter):
    university_id = UNIVERSITY_ID
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Fall 2027"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (APPLICATION_URL,)

    def parse_catalog_from_fetcher(
        self,
        fetcher: Callable[[str], str],
    ) -> DiscoveredCatalog:
        aerospace_text = _page_text(fetcher(AEROSPACE_URL))
        electrical_text = _page_text(fetcher(ELECTRICAL_ENGINEERING_URL))
        application_html = fetcher(self.application_url)
        intake_year, deadline_policy = _application_policy(application_html)
        self.intake = f"Fall {intake_year}"
        deadline_url = _deadline_table_url(application_html, intake_year)
        deadlines = (
            _deadline_table(fetcher(deadline_url), intake_year) if deadline_url else {}
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
                        closes_at=deadlines.get("Aeronautics (AE)"),
                        deadline_url=deadline_url,
                    ),
                    _programme(
                        programme_id="caltech-space-engineering-ms",
                        name="MS Space Engineering",
                        department="Aerospace",
                        source_url=AEROSPACE_URL,
                        deadline_policy=deadline_policy,
                        intake_year=intake_year,
                        closes_at=deadlines.get("Space Engineering (SE)"),
                        deadline_url=deadline_url,
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
                    closes_at=deadlines.get("Electrical Engineering (EE)"),
                    deadline_url=deadline_url,
                )
            )
        programmes.sort(key=lambda item: item.id)
        if len(programmes) != 3:
            raise ValueError(
                "Caltech catalogue only verified "
                f"{len(programmes)} direct-entry master's programmes; expected 3"
            )
        return DiscoveredCatalog(
            application_opens_at=None,
            programmes=programmes,
            diagnostics={
                "applicationCycle": self.intake,
                "deadlineTableUrl": deadline_url,
                "deadlineTableStatus": "matched-cycle"
                if deadline_url
                else "no-matching-cycle-table",
            },
        )


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
        r"applications? for (?:the )?(20\d{2})\s*[-–]\s*(20\d{2}) "
        r"(?:academic year|admission) "
        r"(?:will be available in early October|are now open|is now open)",
        text,
        re.I,
    )
    match = re.search(
        r"Deadlines vary by program from December 1 to "
        r"(?:December 15|January 15)[.]?",
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


def _deadline_table_url(html: str, intake_year: int) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    links = set()
    for link in (soup.find("main") or soup).find_all("a", href=True):
        if (
            _normalise(link.get_text(" ", strip=True)).casefold()
            != "application deadlines"
        ):
            continue
        url = urljoin(APPLICATION_URL, link["href"])
        parts = urlsplit(url)
        if parts.scheme != "https" or parts.netloc != "gradoffice.caltech.edu":
            continue
        cycle = re.search(
            r"(?<!\d)(20\d{2})[-–](20\d{2}|\d{2})(?!\d).*\.pdf$", parts.path, re.I
        )
        if (
            cycle
            and int(cycle[1]) == intake_year
            and cycle[2]
            in {
                str(intake_year + 1),
                str(intake_year + 1)[-2:],
            }
        ):
            links.add(url)
    if len(links) > 1:
        raise ValueError(
            "Caltech application page linked multiple deadline tables for the same cycle"
        )
    return next(iter(links), None)


def _deadline_table(text: str, intake_year: int) -> dict[str, str]:
    if not re.search(
        r"Department\s*\(All degree programs\)\s*Application Deadline", text, re.I
    ):
        raise ValueError("Caltech deadline PDF lacked the all-degree deadline table")
    dates = {}
    for option in DEADLINE_OPTIONS:
        rows = re.findall(
            rf"^\s*{re.escape(option)}[ \t]+(December|January)[ \t]+(\d{{1,2}})[ \t]*$",
            text,
            re.M | re.I,
        )
        if len(rows) != 1:
            raise ValueError(
                f"Caltech deadline PDF lacked a unique deadline for {option}"
            )
        month, day = rows[0]
        january = month.casefold() == "january"
        dates[option] = date(
            intake_year if january else intake_year - 1, 1 if january else 12, int(day)
        ).isoformat()
    return dates


def _programme(
    *,
    programme_id: str,
    name: str,
    department: str,
    source_url: str,
    deadline_policy: str,
    intake_year: int,
    closes_at: str | None = None,
    deadline_url: str | None = None,
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
                source_url=deadline_url,
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
            "The Caltech Catalog verifies this as a direct-entry master's programme. "
            f"The application notice identifies the {intake_year}-{intake_year + 1} cycle. "
            f"The Graduate Studies Office states: {deadline_policy}. "
            + (
                f"The linked all-degree deadline table lists {closes_at} for this option. "
                "The application notice supplies no exact opening date."
                if closes_at is not None
                else "A matching-cycle official deadline table was not found."
            )
        ),
        parse_status=parse_status,
        retrieval_method="official-page",
        evidence_quality="official-full-text",
    )


def _normalise(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
