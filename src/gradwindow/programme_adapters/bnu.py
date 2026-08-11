from __future__ import annotations

import json
import re
from datetime import datetime

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, DiscoveredProgramme, DiscoveredWindow, Fetcher
from .official_catalog import normalise, slug

CATALOG_URL = (
    "https://admission-is.bnu.edu.cn/docs/2025-10/2d7c778261b7448599daa85a2a645bc8.xlsx"
)
GUIDE_URL = (
    "https://admission-is.bnu.edu.cn/english/admissionprogram/"
    "postgraduateprogram/masterdegree/admissionbrochure2/index.html"
)
APPLICATION_URL = "https://international.bnu.edu.cn/"

_SCHOOL_RE = re.compile(r"^\d{3}\s+(?P<name>\D.+)$")
_MAJOR_RE = re.compile(r"^\d{6}\s+(?P<name>\D.+)$")
_WINDOW_RE = re.compile(
    r"From\s+(?P<open_month>[A-Z][a-z]+)\s+(?P<open_day>\d{1,2}),\s*"
    r"(?P<open_year>20\d{2})\s+to\s+"
    r"(?P<close_month>[A-Z][a-z]+)\s+(?P<close_day>\d{1,2}),\s*"
    r"(?P<close_year>20\d{2})",
    re.IGNORECASE,
)


class BNUAdapter:
    university_id = "beijing-normal-university"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Autumn 2026"
    application_opens_at_basis = "official"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, GUIDE_URL)
    retrieval_method = "official-international-master-catalogue-xlsx"
    known_programme_window_scope_type = "programme-group"
    known_programme_window_scope_id = "bnu-international-master-admissions"

    def __init__(
        self,
        minimum_expected_programmes: int = 70,
        maximum_expected_programmes: int = 90,
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
                f"BNU catalogue contained {len(programmes)} master's programmes; "
                f"expected {self.minimum_expected_programmes}-"
                f"{self.maximum_expected_programmes}"
            )
        opens_at, closes_at = _application_window(fetcher(GUIDE_URL))
        programmes.append(
            DiscoveredProgramme(
                id="bnu-international-master-admissions",
                name="International master's admissions",
                degree_type="Master",
                faculty="Admission Office",
                department="Admission Office",
                source_url=GUIDE_URL,
                application_url=APPLICATION_URL,
                windows=[
                    DiscoveredWindow(
                        round="International master's admissions",
                        applicant_categories=["international-students"],
                        opens_at=opens_at,
                        closes_at=closes_at,
                        intake=self.intake,
                        source_url=GUIDE_URL,
                        opens_at_basis="official",
                    )
                ],
                deadline_text=(
                    "BNU's official 2026 master's brochure publishes this exact "
                    "programme-group online application period."
                ),
                parse_status="parsed",
                retrieval_method=self.retrieval_method,
                evidence_quality="official-full-text",
            )
        )
        return DiscoveredCatalog(application_opens_at=opens_at, programmes=programmes)


def _programmes(payload: str) -> list[DiscoveredProgramme]:
    try:
        workbook = json.loads(payload)
        rows = workbook["worksheets"][0]["rows"]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("BNU catalogue did not return a readable workbook") from exc

    faculty = "Beijing Normal University"
    programmes: dict[str, DiscoveredProgramme] = {}
    for row in rows:
        if not isinstance(row, list) or len(row) < 2:
            continue
        english = normalise(row[1] or "")
        school_match = _SCHOOL_RE.match(english)
        if school_match:
            faculty = normalise(school_match.group("name"))
            continue
        major_match = _MAJOR_RE.match(english)
        if major_match is None:
            continue
        name = normalise(major_match.group("name"))
        if not name:
            continue
        programme_id = f"bnu-{slug(faculty)}-{slug(name)}-master"
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
                "Programme is listed in BNU's official 2026 international "
                "master's catalogue. Its shared exact application period is "
                "represented once at programme-group scope."
            ),
            parse_status="no-deadline",
            retrieval_method="official-international-master-catalogue-xlsx",
            evidence_quality="official-full-text",
        )
    return sorted(
        programmes.values(),
        key=lambda item: (item.faculty.casefold(), item.name.casefold()),
    )


def _application_window(html: str) -> tuple[str, str]:
    text = normalise(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))
    text = re.sub(r"(?<=\d)\s+(?=\d)", "", text)
    match = _WINDOW_RE.search(text)
    if match is None:
        raise ValueError("BNU brochure did not expose its exact application period")
    return _date(match, "open"), _date(match, "close")


def _date(match: re.Match[str], prefix: str) -> str:
    value = (
        f"{match.group(f'{prefix}_month')} {match.group(f'{prefix}_day')} "
        f"{match.group(f'{prefix}_year')}"
    )
    return datetime.strptime(value, "%B %d %Y").date().isoformat()
