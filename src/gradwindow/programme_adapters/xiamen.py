from __future__ import annotations

import html as html_module
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, DiscoveredProgramme, DiscoveredWindow, Fetcher
from .official_catalog import normalise, slug

GUIDE_URL = "https://admissions.xmu.edu.cn/Admissions/Master_s_Students.htm"
CHINESE_CATALOG_URL = (
    "https://admissions.xmu.edu.cn/Programs/Chinese_Medium_Master_s.htm"
)
ENGLISH_CATALOG_URL = (
    "https://admissions.xmu.edu.cn/Programs/English_Medium_Master_s.htm"
)
APPLICATION_URL = "http://application.xmu.edu.cn/"

_CODE_RE = re.compile(r"[0-9][0-9A-Z]{5}")
_PDF_URL_RE = re.compile(r"(/virtual_attach_file\.vsb\?[^\"']+?\.pdf)")


class XiamenAdapter:
    university_id = "xiamen-university"
    catalog_url = CHINESE_CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Autumn 2026"
    application_opens_at_basis = "official"
    replace_pending_candidates = True
    window_watch_urls = (GUIDE_URL, CHINESE_CATALOG_URL, ENGLISH_CATALOG_URL)
    retrieval_method = "official-international-master-catalogue-html"
    known_programme_window_scope_type = "programme-group"
    known_programme_window_scope_id = "xiamen-international-master-admissions"

    def __init__(
        self,
        minimum_expected_programmes: int = 180,
        maximum_expected_programmes: int = 210,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.maximum_expected_programmes = maximum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        programmes = _programmes(
            (
                (CHINESE_CATALOG_URL, fetcher(CHINESE_CATALOG_URL)),
                (ENGLISH_CATALOG_URL, fetcher(ENGLISH_CATALOG_URL)),
            )
        )
        if not (
            self.minimum_expected_programmes
            <= len(programmes)
            <= self.maximum_expected_programmes
        ):
            raise ValueError(
                f"Xiamen catalogues contained {len(programmes)} master's "
                f"programmes; expected {self.minimum_expected_programmes}-"
                f"{self.maximum_expected_programmes}"
            )

        guide_html = fetcher(GUIDE_URL)
        guide_pdf_url = _guide_pdf_url(guide_html)
        windows = _application_windows(fetcher(guide_pdf_url))
        programmes.append(
            DiscoveredProgramme(
                id="xiamen-international-master-admissions",
                name="International master's admissions",
                degree_type="Master",
                faculty="Admissions Office",
                department="Admissions Office",
                source_url=GUIDE_URL,
                application_url=APPLICATION_URL,
                windows=windows,
                deadline_text=(
                    "Xiamen University's official 2026 master's guide publishes "
                    "exact application periods for scholarship and self-funded "
                    "applicants."
                ),
                parse_status="parsed",
                retrieval_method="official-international-master-guide-pdf",
                evidence_quality="official-full-text",
            )
        )
        return DiscoveredCatalog(
            application_opens_at="2025-12-01", programmes=programmes
        )


def _programmes(
    pages: tuple[tuple[str, str], ...],
) -> list[DiscoveredProgramme]:
    programmes: dict[str, DiscoveredProgramme] = {}
    for source_url, html in pages:
        faculty = "Xiamen University"
        soup = BeautifulSoup(html, "html.parser")
        for row in soup.select("table tr"):
            cells = [
                normalise(cell.get_text(" ", strip=True))
                for cell in row.select("th,td")
            ]
            code_index = next(
                (
                    index
                    for index, value in enumerate(cells)
                    if _CODE_RE.fullmatch(value)
                ),
                None,
            )
            if code_index is None or code_index + 1 >= len(cells):
                continue
            if code_index == 4 and len(cells) >= 6:
                faculty = cells[2]
            code = cells[code_index]
            name = cells[code_index + 1]
            if not faculty or not name:
                continue
            programme_id = f"xiamen-{slug(faculty)}-{code.lower()}-{slug(name)}"
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type="Master",
                faculty=faculty,
                department=faculty,
                source_url=source_url,
                application_url=APPLICATION_URL,
                windows=[],
                deadline_text=(
                    "Programme is listed in Xiamen University's official 2026 "
                    "international master's catalogue. Its shared application "
                    "periods are represented once at programme-group scope."
                ),
                parse_status="no-deadline",
                retrieval_method="official-international-master-catalogue-html",
                evidence_quality="official-full-text",
            )
    return sorted(
        programmes.values(),
        key=lambda item: (item.faculty.casefold(), item.name.casefold(), item.id),
    )


def _guide_pdf_url(html: str) -> str:
    decoded = html_module.unescape(html)
    match = _PDF_URL_RE.search(decoded)
    if match is None:
        raise ValueError("Xiamen guide page did not expose its current PDF")
    return urljoin(GUIDE_URL, match.group(1))


def _application_windows(text: str) -> list[DiscoveredWindow]:
    compact = normalise(text)
    required = (
        "Application Timeline",
        "Dec. 1, 2025",
        "Feb. 15, 2026",
        "Apr. 10, 2026",
        "May 10, 2026",
        "Self-funded",
    )
    if not all(value.casefold() in compact.casefold() for value in required):
        raise ValueError("Xiamen guide did not expose all exact application dates")
    definitions = (
        (
            "Chinese Government Scholarships",
            "2026-02-15",
        ),
        (
            "University and provincial scholarships",
            "2026-04-10",
        ),
        (
            "Self-funded",
            "2026-05-10",
        ),
    )
    return [
        DiscoveredWindow(
            round=round_name,
            applicant_categories=["international-students"],
            opens_at="2025-12-01",
            closes_at=closes_at,
            intake="Autumn 2026",
            source_url=GUIDE_URL,
            opens_at_basis="official",
        )
        for round_name, closes_at in definitions
    ]
