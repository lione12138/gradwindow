from __future__ import annotations

from collections.abc import Callable
from io import BytesIO

import pdfplumber
from bs4 import BeautifulSoup

from ..http_client import DEFAULT_USER_AGENT, fetch_page
from .base import DiscoveredCatalog, DiscoveredProgramme, Fetcher
from .official_catalog import normalise, slug

CATALOG_URL = "https://www.istudy.sdu.edu.cn/__local/2/D3/51/6B94993A02258785A601DCE6FCA_AC0CD911_1A289.pdf"
GUIDE_URL = "https://www.istudy.sdu.edu.cn/info/1291/3972.htm"
APPLICATION_URL = "https://apply.istudy.sdu.edu.cn/"

CatalogueEntries = tuple[tuple[str, str, str, str], ...]
CatalogueFetcher = Callable[[str], CatalogueEntries]


class ShandongAdapter:
    university_id = "shandong-university"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "2026-2027 academic year"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (GUIDE_URL,)
    catalogue_limitation_reason = (
        "Shandong's current official application instructions are six images; "
        "the adapter verifies that guide but does not OCR dates into records."
    )

    def __init__(
        self,
        minimum_expected_programmes: int = 50,
        maximum_expected_programmes: int = 65,
        catalogue_fetcher: CatalogueFetcher | None = None,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.maximum_expected_programmes = maximum_expected_programmes
        self.catalogue_fetcher = catalogue_fetcher or _fetch_catalogue

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        entries = self.catalogue_fetcher(CATALOG_URL)
        _verify_image_guide(fetcher(GUIDE_URL))
        programmes = _programmes(entries)
        if not (
            self.minimum_expected_programmes
            <= len(programmes)
            <= self.maximum_expected_programmes
        ):
            raise ValueError(
                f"Shandong catalogue contained {len(programmes)} master's "
                f"programmes; expected {self.minimum_expected_programmes}-"
                f"{self.maximum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=programmes)


def _programmes(entries: CatalogueEntries) -> list[DiscoveredProgramme]:
    programmes: dict[str, DiscoveredProgramme] = {}
    for raw_faculty, raw_campus, raw_name, raw_medium in entries:
        faculty = normalise(raw_faculty)
        campus = normalise(raw_campus)
        name = normalise(raw_name)
        medium = normalise(raw_medium)
        if not faculty or not name or medium not in {"Chinese", "English"}:
            continue
        programme_id = f"shandong-{slug(faculty)}-{slug(name)}-{slug(medium)}"
        programmes[programme_id] = DiscoveredProgramme(
            id=programme_id,
            name=f"{name} ({medium}-medium)",
            degree_type="Master",
            faculty=faculty,
            department=campus or faculty,
            source_url=CATALOG_URL,
            application_url=APPLICATION_URL,
            windows=[],
            deadline_text=(
                "Programme is listed in Shandong University's official "
                "2026-2027 international master's catalogue. The matching "
                "application guide is image-only, so no dates are inferred."
            ),
            parse_status="no-deadline",
            retrieval_method="official-2026-international-master-catalogue-pdf",
            evidence_quality="official-full-text",
        )
    return sorted(
        programmes.values(),
        key=lambda item: (item.faculty.casefold(), item.name.casefold()),
    )


def _verify_image_guide(html: str) -> None:
    soup = BeautifulSoup(html, "html.parser")
    title = normalise(soup.title.get_text(" ", strip=True) if soup.title else "")
    content = soup.select_one(".v_news_content")
    if "2026 Application Instructions" not in title or content is None:
        raise ValueError("Shandong's current 2026 application guide was not found")
    if len(content.select("img[src]")) < 6:
        raise ValueError("Shandong's image-only application guide changed")


def _fetch_catalogue(url: str) -> CatalogueEntries:
    page = fetch_page(
        url,
        user_agent=DEFAULT_USER_AGENT,
        timeout=90,
        max_bytes=2_000_000,
        accept="application/pdf,application/octet-stream,*/*;q=0.8",
    )
    if page.truncated or not page.raw_bytes.startswith(b"%PDF"):
        raise ValueError("Shandong catalogue did not return a bounded PDF")

    raw_rows: list[tuple[int, list[str | None]]] = []
    with pdfplumber.open(BytesIO(page.raw_bytes)) as pdf:
        if len(pdf.pages) != 5:
            raise ValueError("Shandong catalogue page count changed unexpectedly")
        for page_index, pdf_page in enumerate(pdf.pages):
            tables = pdf_page.extract_tables()
            if not tables:
                raise ValueError("Shandong catalogue contained a page without a table")
            raw_rows.extend((page_index, row) for row in tables[0][1:])

    entries: list[tuple[str, str, str, str]] = []
    faculty = ""
    campus = ""
    index = 0
    while index < len(raw_rows):
        page_index, row = raw_rows[index]
        index += 1
        if len(row) < 5:
            continue
        row_faculty = normalise(row[0] or "")
        row_campus = normalise(row[1] or "")
        name = normalise(row[2] or "")
        duration = normalise(row[3] or "")
        if (
            row_faculty == "School of"
            and name == "Mechanical"
            and index < len(raw_rows)
        ):
            next_page, continuation = raw_rows[index]
            if next_page == page_index + 1 and len(continuation) >= 4:
                row_faculty += f" {normalise(continuation[0] or '')}"
                row_campus += f" {normalise(continuation[1] or '')}"
                name += f" {normalise(continuation[2] or '')}"
                index += 1
        if row_faculty:
            faculty = row_faculty
        if row_campus:
            campus = row_campus
        if (
            duration in {"2 years", "3 years"}
            and name
            and name != "(Professional Degree)"
        ):
            medium = "Chinese" if page_index < 2 else "English"
            entries.append((faculty, campus, name, medium))
    return tuple(entries)
