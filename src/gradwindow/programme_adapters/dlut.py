from __future__ import annotations

import re
from collections.abc import Callable
from io import BytesIO

import httpx
import pdfplumber
from bs4 import BeautifulSoup

from ..http_client import DEFAULT_USER_AGENT
from .base import DiscoveredCatalog, DiscoveredProgramme, DiscoveredWindow, Fetcher
from .official_catalog import normalise, slug

GUIDE_URL = (
    "https://sie.dlut.edu.cn/English/Scholarship1/CSC_Scholarship/"
    "Chinese_University_Program.htm"
)
CHINESE_CATALOG_URL = (
    "https://sie.dlut.edu.cn/system/_content/download.jsp?"
    "urltype=news.DownloadAttachUrl&owner=1894224773&"
    "wbfileid=B9D19060C32062C2E25E81113BFB5E1C"
)
ENGLISH_CATALOG_URL = (
    "https://sie.dlut.edu.cn/system/_content/download.jsp?"
    "urltype=news.DownloadAttachUrl&owner=1894224773&"
    "wbfileid=43EAEAB7CBB336132C11D79BBE14E329"
)
APPLICATION_URL = "https://dut.at0086.cn/StuApplication/Login.aspx"

CatalogueEntries = tuple[tuple[str, str, str], ...]
CatalogueFetcher = Callable[[tuple[str, str]], CatalogueEntries]


class DLUTAdapter:
    university_id = "dalian-university-of-technology"
    catalog_url = GUIDE_URL
    application_url = APPLICATION_URL
    intake = "Autumn 2026"
    application_opens_at_basis = "official"
    replace_pending_candidates = True
    window_watch_urls = (GUIDE_URL,)
    known_programme_window_scope_type = "programme-group"
    known_programme_window_scope_id = "dlut-cgs-high-level-postgraduate-admissions"
    catalogue_limitation_reason = (
        "DUT's official general master's page gives an exact November 1, 2025 "
        "opening but only a June 2026 closing month. The adapter therefore "
        "publishes no general exact window; its parsed exact window is restricted "
        "to Chinese Government Scholarship applicants."
    )

    def __init__(
        self,
        minimum_expected_programmes: int = 78,
        maximum_expected_programmes: int = 82,
        catalogue_fetcher: CatalogueFetcher | None = None,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.maximum_expected_programmes = maximum_expected_programmes
        self.catalogue_fetcher = catalogue_fetcher or _fetch_catalogues

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        programmes = _programmes(
            self.catalogue_fetcher((CHINESE_CATALOG_URL, ENGLISH_CATALOG_URL))
        )
        if not (
            self.minimum_expected_programmes
            <= len(programmes)
            <= self.maximum_expected_programmes
        ):
            raise ValueError(
                f"DLUT catalogues contained {len(programmes)} master's programmes; "
                f"expected {self.minimum_expected_programmes}-"
                f"{self.maximum_expected_programmes}"
            )
        opens_at, closes_at = _application_window(fetcher(GUIDE_URL))
        programmes.append(_scholarship_group(opens_at, closes_at))
        return DiscoveredCatalog(application_opens_at=opens_at, programmes=programmes)


def _programmes(entries: CatalogueEntries) -> list[DiscoveredProgramme]:
    programmes: dict[str, DiscoveredProgramme] = {}
    for raw_faculty, raw_name, raw_medium in entries:
        faculty = normalise(raw_faculty)
        name = normalise(raw_name)
        medium = normalise(raw_medium)
        if not faculty or not name or medium not in {"Chinese", "English"}:
            continue
        programme_id = f"dlut-{slug(faculty)}-{slug(name)}-{slug(medium)}"
        programmes[programme_id] = DiscoveredProgramme(
            id=programme_id,
            name=f"{name} ({medium}-medium)",
            degree_type="Master",
            faculty=faculty,
            department=faculty,
            source_url=GUIDE_URL,
            application_url=APPLICATION_URL,
            windows=[],
            deadline_text=(
                "Programme is listed in Dalian University of Technology's "
                "official 2026 international master's catalogue. The exact "
                "scholarship window is represented once at programme-group scope."
            ),
            parse_status="no-deadline",
            retrieval_method="official-2026-international-master-catalogue-pdf",
            evidence_quality="official-full-text",
        )
    return sorted(
        programmes.values(),
        key=lambda item: (item.faculty.casefold(), item.name.casefold()),
    )


def _scholarship_group(opens_at: str, closes_at: str) -> DiscoveredProgramme:
    return DiscoveredProgramme(
        id="dlut-cgs-high-level-postgraduate-admissions",
        name="Chinese Government Scholarship postgraduate admissions",
        degree_type="Master/Doctoral",
        faculty="School of International Education",
        department="School of International Education",
        source_url=GUIDE_URL,
        application_url=APPLICATION_URL,
        windows=[
            DiscoveredWindow(
                round="Chinese Government Scholarship postgraduate round",
                applicant_categories=["chinese-government-scholarship"],
                opens_at=opens_at,
                closes_at=closes_at,
                intake="Autumn 2026",
                source_url=GUIDE_URL,
                opens_at_basis="official",
            )
        ],
        deadline_text=(
            "DUT's official Chinese Government Scholarship high-level "
            "postgraduate page publishes this exact restricted application period."
        ),
        parse_status="parsed",
        retrieval_method="official-2026-cgs-postgraduate-guide-html",
        evidence_quality="official-full-text",
    )


def _application_window(html: str) -> tuple[str, str]:
    text = normalise(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))
    if re.search(r"From November 1,? 2025 to February 15,? 2026", text, re.I) is None:
        raise ValueError("DUT guide did not expose its exact application period")
    return "2025-11-01", "2026-02-15"


def _fetch_catalogues(urls: tuple[str, str]) -> CatalogueEntries:
    entries: list[tuple[str, str, str]] = []
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "application/pdf,application/octet-stream,*/*;q=0.8",
        "Referer": GUIDE_URL,
    }
    with httpx.Client(follow_redirects=True, timeout=90, headers=headers) as client:
        for url, medium, expected_pages in (
            (urls[0], "Chinese", 3),
            (urls[1], "English", 2),
        ):
            response = client.get(url)
            response.raise_for_status()
            content = response.content
            if not content.startswith(b"%PDF") or len(content) > 1_000_000:
                raise ValueError("DUT catalogue did not return a bounded PDF")
            faculty = "Dalian University of Technology"
            with pdfplumber.open(BytesIO(content)) as pdf:
                if len(pdf.pages) != expected_pages:
                    raise ValueError("DUT catalogue page count changed")
                for pdf_page in pdf.pages:
                    tables = pdf_page.extract_tables()
                    if not tables:
                        raise ValueError(
                            "DUT catalogue contained a page without a table"
                        )
                    for row in tables[0]:
                        if len(row) < 6:
                            continue
                        if row[2] and "Faculty & School" not in normalise(row[2]):
                            faculty = normalise(row[2])
                        name = normalise(row[5] or "")
                        teaching = normalise(row[3] or "")
                        if name and medium in teaching:
                            entries.append((faculty, name, medium))
    return tuple(entries)
