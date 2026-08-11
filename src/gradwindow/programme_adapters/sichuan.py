from __future__ import annotations

import re
from datetime import datetime

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, DiscoveredProgramme, DiscoveredWindow, Fetcher
from .official_catalog import normalise, slug

CATALOG_URL = "https://global.scu.edu.cn/oso/article/index/1073"
GUIDE_URL = (
    "https://global.scu.edu.cn/oso/article/details/"
    "26d7342c-12a9-4441-8748-2b549c0be104?lang=en"
)
APPLICATION_URL = "https://scu.17gz.org/member/login.do"
_WINDOW_RE = re.compile(
    r"(?P<open_month>[A-Z][a-z]+)\s*(?P<open_day>\d{1,2}),\s*"
    r"(?P<open_year>20\d{2})\s*[-\u2013\u2014]+\s*"
    r"(?P<close_month>[A-Z][a-z]+)\s*(?P<close_day>\d{1,2}),\s*"
    r"(?P<close_year>20\d{2})",
    re.IGNORECASE,
)


class SichuanAdapter:
    university_id = "sichuan-university"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Autumn 2026"
    application_opens_at_basis = "official"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, GUIDE_URL)
    retrieval_method = "official-international-programme-catalogue"
    known_programme_window_scope_type = "programme-group"
    known_programme_window_scope_id = "sichuan-international-graduate-admissions"

    def __init__(self, minimum_expected_programmes: int = 240) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        programmes = _programmes(fetcher(CATALOG_URL))
        if len(programmes) < self.minimum_expected_programmes:
            raise ValueError(
                f"Sichuan catalogue contained {len(programmes)} master's programmes; "
                f"expected at least {self.minimum_expected_programmes}"
            )
        opens_at, closes_at = _application_window(fetcher(GUIDE_URL))
        programmes.append(
            DiscoveredProgramme(
                id="sichuan-international-graduate-admissions",
                name="International graduate admissions",
                degree_type="Master/Doctoral",
                faculty="Overseas Students Office",
                department="Overseas Students Office",
                source_url=GUIDE_URL,
                application_url=APPLICATION_URL,
                windows=[
                    DiscoveredWindow(
                        round="International graduate admissions",
                        applicant_categories=["international-students"],
                        opens_at=opens_at,
                        closes_at=closes_at,
                        intake=self.intake,
                        source_url=GUIDE_URL,
                        opens_at_basis="official",
                    )
                ],
                deadline_text=(
                    "Sichuan University's official 2026 guide publishes this exact "
                    "programme-group application period."
                ),
                parse_status="parsed",
                retrieval_method=self.retrieval_method,
                evidence_quality="official-full-text",
            )
        )
        return DiscoveredCatalog(application_opens_at=opens_at, programmes=programmes)


def _programmes(html: str) -> list[DiscoveredProgramme]:
    programmes: dict[str, DiscoveredProgramme] = {}
    faculty = "Sichuan University"
    soup = BeautifulSoup(html, "html.parser")
    for row in soup.select("tr"):
        cells = [
            normalise(cell.get_text(" ", strip=True)) for cell in row.select("th,td")
        ]
        if len(cells) >= 6 and cells[0].casefold() != "master's degree":
            match = re.search(r"[A-Za-z].*", cells[2])
            if match:
                faculty = normalise(match.group(0))
            continue
        if len(cells) < 2 or cells[0].casefold() != "master's degree":
            continue
        name = normalise(cells[1])
        if not name:
            continue
        programme_id = f"sichuan-{slug(faculty)}-{slug(name)}-master"
        programmes[programme_id] = DiscoveredProgramme(
            id=programme_id,
            name=name,
            degree_type="Master",
            faculty=faculty,
            department=faculty,
            source_url=CATALOG_URL,
            application_url=APPLICATION_URL,
            windows=[],
            deadline_text=(
                "Programme is listed in Sichuan University's official catalogue. "
                "Its shared exact application period is represented once at "
                "programme-group scope."
            ),
            parse_status="no-deadline",
            retrieval_method="official-international-programme-catalogue",
            evidence_quality="official-full-text",
        )
    return sorted(
        programmes.values(),
        key=lambda item: (item.faculty.casefold(), item.name.casefold()),
    )


def _application_window(html: str) -> tuple[str, str]:
    text = normalise(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))
    match = _WINDOW_RE.search(text)
    if match is None:
        raise ValueError("Sichuan guide did not expose its exact application period")
    return _date(match, "open"), _date(match, "close")


def _date(match: re.Match[str], prefix: str) -> str:
    value = (
        f"{match.group(f'{prefix}_month')} {match.group(f'{prefix}_day')} "
        f"{match.group(f'{prefix}_year')}"
    )
    return datetime.strptime(value, "%B %d %Y").date().isoformat()
