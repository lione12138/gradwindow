from __future__ import annotations

import re
from datetime import datetime

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, DiscoveredProgramme, DiscoveredWindow, Fetcher
from .official_catalog import normalise, slug

CATALOG_URL = "https://studyat.nwpu.edu.cn/info/1203/9011.htm"
GUIDE_URL = "https://studyat.nwpu.edu.cn/info/1303/8791.htm"
APPLICATION_URL = "http://admission.nwpu.edu.cn/"

_WINDOW_RE = re.compile(
    r"The\s+(?P<round>first|second|third|fourth)\s+batch\s*:\s*"
    r"(?P<opens>[A-Z][a-z]+\s+\d{1,2},\s*20\s*\d{2})\s*[-–—]\s*"
    r"(?P<closes>[A-Z][a-z]+\s+\d{1,2},\s*20\s*\d{2})",
    re.IGNORECASE,
)


class NPUAdapter:
    university_id = "northwestern-polytechnical-university"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Autumn 2026"
    application_opens_at_basis = "official"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, GUIDE_URL)
    retrieval_method = "official-2026-international-master-catalogue-html"
    known_programme_window_scope_type = "programme-group"
    known_programme_window_scope_id = "nwpu-international-master-admissions"

    def __init__(
        self,
        minimum_expected_programmes: int = 45,
        maximum_expected_programmes: int = 55,
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
                f"NPU catalogue contained {len(programmes)} master's programmes; "
                f"expected {self.minimum_expected_programmes}-"
                f"{self.maximum_expected_programmes}"
            )
        windows = _application_windows(fetcher(GUIDE_URL))
        programmes.append(
            DiscoveredProgramme(
                id="nwpu-international-master-admissions",
                name="International master's admissions",
                degree_type="Master",
                faculty="International College",
                department="International College",
                source_url=GUIDE_URL,
                application_url=APPLICATION_URL,
                windows=windows,
                deadline_text=(
                    "NPU's official 2026 master's guide publishes four exact "
                    "application batches for the Autumn 2026 intake."
                ),
                parse_status="parsed",
                retrieval_method="official-2026-international-master-guide-html",
                evidence_quality="official-full-text",
            )
        )
        return DiscoveredCatalog(
            application_opens_at=windows[0].opens_at,
            programmes=programmes,
        )


def _programmes(html: str) -> list[DiscoveredProgramme]:
    soup = BeautifulSoup(html, "html.parser")
    faculty = "Northwestern Polytechnical University"
    programmes: dict[str, DiscoveredProgramme] = {}
    for row in soup.select("table tr"):
        cells = row.find_all(["th", "td"], recursive=False)
        if len(cells) not in {2, 4}:
            continue
        if len(cells) == 4:
            faculty = _english_name(cells[0].get_text(" ", strip=True))
            major_cell = cells[1]
            medium_cell = cells[2]
        else:
            major_cell = cells[0]
            medium_cell = cells[1]
        name = _english_name(major_cell.get_text(" ", strip=True))
        medium = _english_name(medium_cell.get_text(" ", strip=True))
        if not name or not faculty or name.casefold() == "major":
            continue
        programme_id = f"nwpu-{slug(faculty)}-{slug(name)}-master"
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
                "Programme is listed in NPU's official 2026 international "
                f"master's catalogue with {medium or 'an unspecified'} teaching "
                "medium. Shared application batches are represented once at "
                "programme-group scope."
            ),
            parse_status="no-deadline",
            retrieval_method="official-2026-international-master-catalogue-html",
            evidence_quality="official-full-text",
        )
    return sorted(
        programmes.values(),
        key=lambda item: (item.faculty.casefold(), item.name.casefold()),
    )


def _english_name(value: str) -> str:
    value = normalise(value).replace("✭", " ").replace('"', "'")
    match = re.search(r"[A-Za-z]", value)
    return normalise(value[match.start() :]) if match else ""


def _application_windows(html: str) -> list[DiscoveredWindow]:
    text = normalise(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))
    windows = []
    for match in _WINDOW_RE.finditer(text):
        windows.append(
            DiscoveredWindow(
                round=f"{match.group('round').title()} batch",
                applicant_categories=["international-students"],
                opens_at=_date(match.group("opens")),
                closes_at=_date(match.group("closes")),
                intake="Autumn 2026",
                source_url=GUIDE_URL,
                opens_at_basis="official",
            )
        )
    if len(windows) != 4:
        raise ValueError(
            f"NPU guide contained {len(windows)} exact batches; expected four"
        )
    return windows


def _date(value: str) -> str:
    compact = re.sub(r"(?<=\d)\s+(?=\d)", "", normalise(value))
    return datetime.strptime(compact, "%B %d, %Y").date().isoformat()
