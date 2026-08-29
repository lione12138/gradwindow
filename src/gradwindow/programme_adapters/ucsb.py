from __future__ import annotations

import hashlib
import re
from collections import Counter
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import (
    BaseProgrammeAdapter,
    DiscoveredCatalog,
    DiscoveredProgramme,
    DiscoveredWindow,
    Fetcher,
)
from .official_catalog import normalise, slug

CATALOG_URL = "https://engage.graddiv.ucsb.edu/portal/programs"
SEARCH_URL = f"{CATALOG_URL}?cmd=search"
APPLICATION_URL = "https://www.graddiv.ucsb.edu/how-apply"

_MASTER_DEGREE_RE = re.compile(
    r"(?<![A-Za-z])(MEd|MEDS|MESM|METL|MFA|MS|MA|MM|MTM)(?![A-Za-z])",
    re.I,
)
_DEGREE_TYPES = {
    "ma": "MA",
    "med": "MEd",
    "meds": "MEDS",
    "mesm": "MESM",
    "metl": "METL",
    "mfa": "MFA",
    "mm": "MM",
    "ms": "MS",
    "mtm": "MTM",
}
_PROFESSIONAL_DEGREES = {"MEd", "MEDS", "MESM", "METL", "MFA", "MM", "MTM"}
_DATE_RE = re.compile(
    r"(?P<month>January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+(?P<day>\d{1,2}),\s+(?P<year>20\d{2})",
    re.I,
)


class UCSBAdapter(BaseProgrammeAdapter):
    university_id = "university-of-california-santa-barbara-ucsb"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Primarily Fall; varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = ()
    browser_fallback_limit = 2
    catalogue_granularity = "programme-route-level"

    def __init__(
        self,
        minimum_expected_departments: int = 45,
        minimum_expected_programmes: int = 80,
    ) -> None:
        self.minimum_expected_departments = minimum_expected_departments
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        root_document = fetcher(CATALOG_URL)
        _require_embedded_master_policy(root_document)
        department_urls = _department_urls(fetcher(SEARCH_URL))
        if len(department_urls) < self.minimum_expected_departments:
            raise ValueError(
                f"UCSB's portal contained {len(department_urls)} departments; "
                f"expected at least {self.minimum_expected_departments}"
            )

        routes = []
        for department_url in department_urls:
            routes.extend(_department_routes(fetcher(department_url), department_url))
        if len(routes) < self.minimum_expected_programmes:
            raise ValueError(
                "UCSB's official portal contained "
                f"{len(routes)} master's degree routes; expected at least "
                f"{self.minimum_expected_programmes}"
            )

        base_id_counts = Counter(_base_id(route) for route in routes)
        programmes = []
        for route in routes:
            detail_document = fetcher(route["source_url"])
            windows = _deadline_windows(detail_document, route["source_url"])
            if not windows:
                raise ValueError(
                    "UCSB's programme detail page contained no deadline table: "
                    f"{route['source_url']}"
                )
            base_id = _base_id(route)
            has_collision = base_id_counts[base_id] > 1
            programme_id = (
                f"{base_id}-{slug(route['objective'])}" if has_collision else base_id
            )
            programme_name = (
                f"{route['name']} — {route['objective']}"
                if has_collision
                else route["name"]
            )
            admission_route = _admission_route(route)
            dates = ", ".join(
                f"{window.intake} {window.round}: {window.closes_at}"
                for window in windows
            )
            programmes.append(
                DiscoveredProgramme(
                    id=programme_id,
                    name=programme_name,
                    degree_type=route["degree_type"],
                    faculty="UC Santa Barbara Graduate Division",
                    department=route["department"],
                    source_url=route["source_url"],
                    application_url=APPLICATION_URL,
                    windows=windows,
                    deadline_text=(
                        f"UCSB's official portal lists {dates}. No exact opening "
                        "date is published on the checked portal page. "
                        f"Admission route: {admission_route}."
                    ),
                    parse_status="incomplete",
                    retrieval_method="official-slate-portal",
                    evidence_quality="official-full-text",
                    evidence_document_hash=hashlib.sha256(
                        detail_document.encode()
                    ).hexdigest(),
                    admission_route=admission_route,
                )
            )

        programmes.sort(key=lambda item: item.id)
        return DiscoveredCatalog(application_opens_at=None, programmes=programmes)


def _require_embedded_master_policy(document: str) -> None:
    text = normalise(BeautifulSoup(document, "html.parser").get_text(" ", strip=True))
    if not re.search(
        r"Masters/Ph\.D\. programs require application to,? and enrollment in,? "
        r"the doctoral program",
        text,
        re.I,
    ):
        raise ValueError(
            "UCSB's portal did not contain its doctoral-program enrollment policy"
        )


def _department_urls(document: str) -> list[str]:
    soup = BeautifulSoup(document, "html.parser")
    return sorted(
        {
            urljoin(CATALOG_URL, str(link["href"]))
            for link in soup.select('a[href*="cmd=dept"]')
        }
    )


def _department_routes(document: str, department_url: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(document, "html.parser")
    heading = soup.select_one("h1")
    if heading is None:
        raise ValueError(f"UCSB department page had no heading: {department_url}")
    department = normalise(heading.get_text(" ", strip=True))
    routes = []
    for link in soup.select('a[href*="cmd=prog"]'):
        label = normalise(link.get_text(" ", strip=True))
        if " - " not in label:
            continue
        objective, name = label.split(" - ", 1)
        degree_match = _MASTER_DEGREE_RE.search(objective)
        if degree_match is None:
            continue
        routes.append(
            {
                "department": department,
                "objective": objective,
                "name": name,
                "degree_type": _DEGREE_TYPES[degree_match.group(1).casefold()],
                "source_url": urljoin(CATALOG_URL, str(link["href"])),
            }
        )
    return routes


def _deadline_windows(document: str, source_url: str) -> list[DiscoveredWindow]:
    soup = BeautifulSoup(document, "html.parser")
    heading = soup.find(
        ["h2", "h3"], string=lambda value: bool(value and "Deadline" in value)
    )
    table = heading.find_next("table") if heading else None
    if table is None:
        return []
    headers = [
        normalise(cell.get_text(" ", strip=True)) for cell in table.select("thead th")
    ]
    windows = []
    for row in table.select("tbody tr"):
        cells = [
            normalise(cell.get_text(" ", strip=True))
            for cell in row.find_all(["th", "td"], recursive=False)
        ]
        if len(cells) != len(headers) or not cells:
            continue
        intake = cells[0]
        for header, value in zip(headers[1:], cells[1:], strict=True):
            closes_at = _date(value)
            if closes_at is None:
                continue
            windows.append(
                DiscoveredWindow(
                    round=header.capitalize(),
                    closes_at=closes_at,
                    intake=intake,
                    source_url=source_url,
                )
            )
    return windows


def _date(value: str) -> str | None:
    match = _DATE_RE.search(value)
    if match is None:
        return None
    return (
        datetime.strptime(
            f"{match.group('month')} {match.group('day')} {match.group('year')}",
            "%B %d %Y",
        )
        .date()
        .isoformat()
    )


def _base_id(route: dict[str, str]) -> str:
    return f"ucsb-{slug(route['name'])}-{slug(route['degree_type'])}"


def _admission_route(route: dict[str, str]) -> str:
    objective = route["objective"]
    if objective.startswith("Ph.D."):
        return "master-phd-embedded"
    if "Current UCSB Undergraduates Only" in route["name"]:
        return "restricted-master"
    if route["degree_type"] in _PROFESSIONAL_DEGREES or "Credential" in objective:
        return "professional-master"
    return "direct-master"
