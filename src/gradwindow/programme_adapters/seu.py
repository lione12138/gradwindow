from __future__ import annotations

import hashlib
from collections.abc import Callable
from io import BytesIO
from urllib.parse import urljoin

import pdfplumber
from bs4 import BeautifulSoup

from ..http_client import DEFAULT_USER_AGENT, fetch_page
from .base import DiscoveredCatalog, DiscoveredProgramme, DiscoveredWindow, Fetcher
from .official_catalog import normalise, slug

CATALOG_PAGE_URL = "https://cis.seu.edu.cn/hwenglish/13998/list.htm"
GUIDE_URL = "https://cis.seu.edu.cn/hwenglish/2025/1125/c14041a546671/page.htm"
APPLICATION_URL = "http://fs.seu.edu.cn/"
EXPECTED_GUIDE_SHA256 = (
    "5f9dfc01aa2bdd9818e13e7e52454737bc6aeac3e807d88bc7727abad873f6ee"
)

CatalogueEntries = tuple[tuple[str, str, str], ...]
CatalogueFetcher = Callable[[str], CatalogueEntries]
GuideHashFetcher = Callable[[str], str]


class SEUAdapter:
    university_id = "southeast-university"
    catalog_url = CATALOG_PAGE_URL
    application_url = APPLICATION_URL
    intake = "Autumn 2026"
    application_opens_at_basis = "official"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_PAGE_URL, GUIDE_URL)
    known_programme_window_scope_type = "programme-group"
    known_programme_window_scope_id = "seu-international-postgraduate-admissions"

    def __init__(
        self,
        minimum_expected_programmes: int = 88,
        maximum_expected_programmes: int = 100,
        catalogue_fetcher: CatalogueFetcher | None = None,
        guide_hash_fetcher: GuideHashFetcher | None = None,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.maximum_expected_programmes = maximum_expected_programmes
        self.catalogue_fetcher = catalogue_fetcher or _fetch_catalogue
        self.guide_hash_fetcher = guide_hash_fetcher or _fetch_guide_hash

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalogue_pdf_url = _embedded_pdf_url(
            fetcher(CATALOG_PAGE_URL), CATALOG_PAGE_URL
        )
        programmes = _programmes(self.catalogue_fetcher(catalogue_pdf_url))
        if not (
            self.minimum_expected_programmes
            <= len(programmes)
            <= self.maximum_expected_programmes
        ):
            raise ValueError(
                f"SEU catalogue contained {len(programmes)} master's programmes; "
                f"expected {self.minimum_expected_programmes}-"
                f"{self.maximum_expected_programmes}"
            )
        guide_pdf_url = _embedded_pdf_url(fetcher(GUIDE_URL), GUIDE_URL)
        guide_hash = self.guide_hash_fetcher(guide_pdf_url)
        if guide_hash != EXPECTED_GUIDE_SHA256:
            raise ValueError(
                "SEU image-only 2026 guide changed; its exact dates require "
                "fresh visual review before discovery can continue"
            )
        programmes.append(_admission_group(guide_hash))
        return DiscoveredCatalog(
            application_opens_at="2025-11-22",
            programmes=programmes,
        )


def _embedded_pdf_url(html: str, page_url: str) -> str:
    node = BeautifulSoup(html, "html.parser").select_one("[pdfsrc$='.pdf']")
    if node is None:
        raise ValueError(f"SEU page did not expose its embedded PDF: {page_url}")
    return urljoin(page_url, str(node.get("pdfsrc", "")))


def _programmes(entries: CatalogueEntries) -> list[DiscoveredProgramme]:
    programmes: dict[str, DiscoveredProgramme] = {}
    for raw_faculty, raw_name, _duration in entries:
        faculty = normalise(raw_faculty)
        name = normalise(raw_name)
        if not faculty or not name:
            continue
        programme_id = f"seu-{slug(faculty)}-{slug(name)}-master"
        programmes[programme_id] = DiscoveredProgramme(
            id=programme_id,
            name=name,
            degree_type="Master",
            faculty=faculty,
            department=faculty,
            source_url=CATALOG_PAGE_URL,
            application_url=APPLICATION_URL,
            windows=[],
            deadline_text=(
                "Programme is listed in Southeast University's official "
                "international graduate programme PDF. The shared exact "
                "application period is represented once at programme-group scope."
            ),
            parse_status="no-deadline",
            retrieval_method="official-international-master-catalogue-pdf",
            evidence_quality="official-full-text",
        )
    return sorted(
        programmes.values(),
        key=lambda item: (item.faculty.casefold(), item.name.casefold()),
    )


def _admission_group(guide_hash: str) -> DiscoveredProgramme:
    return DiscoveredProgramme(
        id="seu-international-postgraduate-admissions",
        name="International postgraduate admissions",
        degree_type="Master/Doctoral",
        faculty="College of International Students",
        department="College of International Students",
        source_url=GUIDE_URL,
        application_url=APPLICATION_URL,
        windows=[
            DiscoveredWindow(
                round="International postgraduate admissions",
                applicant_categories=["international-students"],
                opens_at="2025-11-22",
                closes_at="2026-05-15",
                intake="Autumn 2026",
                source_url=GUIDE_URL,
                opens_at_basis="official",
            )
        ],
        deadline_text=(
            "Southeast University's official 2026 image-based guide publishes "
            "the exact application period November 22, 2025 to May 15, 2026."
        ),
        parse_status="parsed",
        retrieval_method="official-2026-image-pdf-visually-verified",
        evidence_quality="official-full-text",
        evidence_document_hash=guide_hash,
    )


def _fetch_catalogue(url: str) -> CatalogueEntries:
    content = _fetch_pdf(url, max_bytes=1_000_000)
    entries: list[tuple[str, str, str]] = []
    faculty = "Southeast University"
    with pdfplumber.open(BytesIO(content)) as pdf:
        if len(pdf.pages) != 5:
            raise ValueError("SEU master's catalogue page count changed")
        for pdf_page in pdf.pages:
            tables = pdf_page.extract_tables()
            if not tables:
                raise ValueError(
                    "SEU master's catalogue contained a page without a table"
                )
            for row in tables[0]:
                if len(row) < 3:
                    continue
                if row[0] and "School/College" not in normalise(row[0]):
                    faculty = normalise(row[0])
                name = normalise(row[1] or "")
                duration = normalise(row[2] or "")
                if name and duration in {"2", "3"}:
                    entries.append((faculty, name, duration))
    return tuple(entries)


def _fetch_guide_hash(url: str) -> str:
    return hashlib.sha256(_fetch_pdf(url, max_bytes=4_000_000)).hexdigest()


def _fetch_pdf(url: str, *, max_bytes: int) -> bytes:
    page = fetch_page(
        url,
        user_agent=DEFAULT_USER_AGENT,
        timeout=90,
        max_bytes=max_bytes,
        accept="application/pdf,application/octet-stream,*/*;q=0.8",
    )
    if page.truncated or not page.raw_bytes.startswith(b"%PDF"):
        raise ValueError("SEU source did not return a bounded PDF")
    return page.raw_bytes
