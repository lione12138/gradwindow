from __future__ import annotations

import re
from collections.abc import Callable
from io import BytesIO
from urllib.parse import urljoin

import pdfplumber
from bs4 import BeautifulSoup

from ..http_client import DEFAULT_USER_AGENT, fetch_page
from .base import DiscoveredCatalog, DiscoveredProgramme, DiscoveredWindow, Fetcher
from .official_catalog import normalise, slug

CATALOG_PAGE_URL = "https://ensie.nankai.edu.cn/info/1084/1334.htm"
GUIDE_URL = "https://ensie.nankai.edu.cn/info/1085/1328.htm"
APPLICATION_URL = "https://nankai.at0086.cn/StuApplication/Login.aspx"

_PDF_RE = re.compile(r'showVsbpdfIframe\(["\'](?P<url>[^"\']+\.pdf)', re.I)
_WINDOW_RE = re.compile(
    r"20th\s+October\D{0,20}2025\D{1,40}31th\s+May\s+2026",
    re.IGNORECASE,
)

CatalogueEntries = tuple[tuple[str, str, str], ...]
CatalogueFetcher = Callable[[str], CatalogueEntries]


class NankaiAdapter:
    university_id = "nankai-university"
    catalog_url = CATALOG_PAGE_URL
    application_url = APPLICATION_URL
    intake = "Autumn 2026"
    application_opens_at_basis = "official"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_PAGE_URL, GUIDE_URL)
    known_programme_window_scope_type = "programme-group"
    known_programme_window_scope_id = "nankai-international-master-admissions"

    def __init__(
        self,
        minimum_expected_programmes: int = 160,
        maximum_expected_programmes: int = 180,
        catalogue_fetcher: CatalogueFetcher | None = None,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.maximum_expected_programmes = maximum_expected_programmes
        self.catalogue_fetcher = catalogue_fetcher or _fetch_catalogue

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalogue_page = fetcher(CATALOG_PAGE_URL)
        pdf_url = _catalogue_pdf_url(catalogue_page)
        programmes = _programmes(self.catalogue_fetcher(pdf_url))
        if not (
            self.minimum_expected_programmes
            <= len(programmes)
            <= self.maximum_expected_programmes
        ):
            raise ValueError(
                f"Nankai catalogue contained {len(programmes)} master's "
                f"programmes; expected {self.minimum_expected_programmes}-"
                f"{self.maximum_expected_programmes}"
            )
        opens_at, closes_at = _application_window(fetcher(GUIDE_URL))
        programmes.append(
            DiscoveredProgramme(
                id="nankai-international-master-admissions",
                name="International master's admissions",
                degree_type="Master",
                faculty="International Students Section",
                department="International Students Section",
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
                    "Nankai's official 2026 postgraduate overview publishes "
                    "this exact international application period."
                ),
                parse_status="parsed",
                retrieval_method="official-2026-postgraduate-guide-html",
                evidence_quality="official-full-text",
            )
        )
        return DiscoveredCatalog(application_opens_at=opens_at, programmes=programmes)


def _catalogue_pdf_url(html: str) -> str:
    match = _PDF_RE.search(html)
    if match is None:
        raise ValueError("Nankai catalogue page did not expose its embedded PDF")
    return urljoin(CATALOG_PAGE_URL, match.group("url"))


def _programmes(entries: CatalogueEntries) -> list[DiscoveredProgramme]:
    programmes: dict[str, DiscoveredProgramme] = {}
    for raw_faculty, raw_name, raw_medium in entries:
        faculty = normalise(raw_faculty)
        name = normalise(raw_name)
        medium = normalise(raw_medium)
        if not faculty or not name or medium not in {"Chinese", "English"}:
            continue
        display_name = f"{name} ({medium}-medium)"
        programme_id = f"nankai-{slug(faculty)}-{slug(name)}-{slug(medium)}"
        programmes[programme_id] = DiscoveredProgramme(
            id=programme_id,
            name=display_name,
            degree_type="Master",
            faculty=faculty,
            department=faculty,
            source_url=CATALOG_PAGE_URL,
            application_url=APPLICATION_URL,
            windows=[],
            deadline_text=(
                "Programme is listed in Nankai University's official 2026 "
                "international master's catalogue. The shared exact window "
                "is represented once at programme-group scope."
            ),
            parse_status="no-deadline",
            retrieval_method="official-2026-international-master-catalogue-pdf",
            evidence_quality="official-full-text",
        )
    return sorted(
        programmes.values(),
        key=lambda item: (item.faculty.casefold(), item.name.casefold()),
    )


def _application_window(html: str) -> tuple[str, str]:
    text = normalise(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))
    if _WINDOW_RE.search(text) is None:
        raise ValueError("Nankai guide did not expose its exact application period")
    return "2025-10-20", "2026-05-31"


def _fetch_catalogue(url: str) -> CatalogueEntries:
    page = fetch_page(
        url,
        user_agent=DEFAULT_USER_AGENT,
        timeout=90,
        max_bytes=3_000_000,
        accept="application/pdf,application/octet-stream,*/*;q=0.8",
    )
    if page.truncated or not page.raw_bytes.startswith(b"%PDF"):
        raise ValueError("Nankai catalogue did not return a bounded PDF")
    entries: list[tuple[str, str, str]] = []
    faculty = ""
    with pdfplumber.open(BytesIO(page.raw_bytes)) as pdf:
        if len(pdf.pages) != 12:
            raise ValueError("Nankai catalogue page count changed unexpectedly")
        for pdf_page in pdf.pages:
            tables = pdf_page.extract_tables()
            if not tables:
                raise ValueError("Nankai catalogue contained a page without a table")
            for row in tables[0]:
                if len(row) < 10:
                    continue
                if row[1]:
                    faculty = normalise(row[1])
                name = normalise(row[3] or "")
                medium = normalise(row[5] or "")
                duration = normalise(row[9] or "")
                if faculty and name and medium in {"Chinese", "English"} and duration:
                    entries.append((faculty, name, medium))
    return tuple(entries)
