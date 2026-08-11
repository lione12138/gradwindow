from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from io import BytesIO
from urllib.parse import urljoin

import httpx
import pdfplumber
from bs4 import BeautifulSoup

from ..http_client import DEFAULT_USER_AGENT
from .base import DiscoveredCatalog, DiscoveredProgramme, DiscoveredWindow, Fetcher
from .official_catalog import normalise, slug

CATALOG_URL = "https://cie.jlu.edu.cn/lxsq1/zyml.htm"
GUIDE_URL = "https://cie.jlu.edu.cn/info/1079/3656.htm"
APPLICATION_URL = "http://apply.jlu.edu.cn/member/login.do"

_DEADLINE_RE = re.compile(
    r"Deadline:\s*June\s+30\s*,\s*2026",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class GuidePayload:
    entries: tuple[tuple[str, str], ...]


GuideFetcher = Callable[[str], GuidePayload]


class JilinAdapter:
    university_id = "jilin-university"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Autumn 2026"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, GUIDE_URL)
    retrieval_method = "official-international-programme-catalogue-pdf"
    known_programme_window_scope_type = "programme-group"
    known_programme_window_scope_id = "jilin-international-graduate-admissions"

    def __init__(
        self,
        minimum_expected_programmes: int = 110,
        maximum_expected_programmes: int = 150,
        guide_fetcher: GuideFetcher | None = None,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.maximum_expected_programmes = maximum_expected_programmes
        self.guide_fetcher = guide_fetcher or _fetch_guide

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalog_html = fetcher(CATALOG_URL)
        catalogue_pdf_url = _catalogue_pdf_url(catalog_html)
        programmes = _programmes(self.guide_fetcher(catalogue_pdf_url).entries)
        if not (
            self.minimum_expected_programmes
            <= len(programmes)
            <= self.maximum_expected_programmes
        ):
            raise ValueError(
                f"Jilin catalogue contained {len(programmes)} master's programmes; "
                f"expected {self.minimum_expected_programmes}-"
                f"{self.maximum_expected_programmes}"
            )
        guide_html = fetcher(GUIDE_URL)
        closes_at = _closing_date(guide_html)
        programmes.append(
            DiscoveredProgramme(
                id="jilin-international-graduate-admissions",
                name="International graduate admissions",
                degree_type="Master/Doctoral",
                faculty="College of International Education",
                department="College of International Education",
                source_url=GUIDE_URL,
                application_url=APPLICATION_URL,
                windows=[
                    DiscoveredWindow(
                        round="International graduate admissions",
                        applicant_categories=["international-students"],
                        opens_at=None,
                        closes_at=closes_at,
                        intake=self.intake,
                        source_url=GUIDE_URL,
                        opens_at_basis="missing",
                    )
                ],
                deadline_text=(
                    "Jilin's official 2026-2027 graduate guide publishes an "
                    "exact closing date but no exact opening date. This remains "
                    "review guidance rather than a publishable exact window."
                ),
                parse_status="incomplete",
                retrieval_method=self.retrieval_method,
                evidence_quality="official-full-text",
            )
        )
        return DiscoveredCatalog(application_opens_at=None, programmes=programmes)


def _catalogue_pdf_url(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for link in soup.select("a[href]"):
        title = normalise(link.get_text(" ", strip=True))
        if "2026-2027" in title and "PDF" in title.upper():
            return urljoin(CATALOG_URL, str(link.get("href", "")))
    raise ValueError("Jilin catalogue page did not link its 2026-2027 PDF")


def _programmes(
    entries: tuple[tuple[str, str], ...],
) -> list[DiscoveredProgramme]:
    programmes: dict[str, DiscoveredProgramme] = {}
    for raw_faculty, raw_name in entries:
        faculty = normalise(raw_faculty)
        name = normalise(raw_name)
        if not faculty or not name:
            continue
        programme_id = f"jilin-{slug(faculty)}-{slug(name)}-master"
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
                "Programme is listed in Jilin University's official 2026-2027 "
                "international catalogue. The university-wide guide gives no "
                "exact opening date, so no exact programme window is inferred."
            ),
            parse_status="no-deadline",
            retrieval_method="official-international-programme-catalogue-pdf",
            evidence_quality="official-full-text",
        )
    return sorted(
        programmes.values(),
        key=lambda item: (item.faculty.casefold(), item.name.casefold()),
    )


def _closing_date(html: str) -> str:
    text = normalise(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))
    text = re.sub(r"(?<=\d)\s+(?=\d)", "", text)
    text = re.sub(r"\bJu\s+ne\b", "June", text, flags=re.IGNORECASE)
    if _DEADLINE_RE.search(text) is None:
        raise ValueError("Jilin guide did not expose its exact closing date")
    return "2026-06-30"


def _fetch_guide(url: str) -> GuidePayload:
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "application/pdf,application/octet-stream,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8",
        "Referer": CATALOG_URL,
    }
    with httpx.Client(follow_redirects=True, timeout=120, headers=headers) as client:
        response = client.get(url)
        response.raise_for_status()
        content = response.content
    if not content.startswith(b"%PDF") or len(content) > 15_000_000:
        raise ValueError("Jilin catalogue did not return a bounded PDF")

    page_indexes = (2, 3, 4, 7, 11, 12, 13, 14, 15)
    entries: list[tuple[str, str]] = []
    faculty = "Jilin University"
    with pdfplumber.open(BytesIO(content)) as pdf:
        if len(pdf.pages) <= max(page_indexes):
            raise ValueError("Jilin catalogue had fewer pages than expected")
        for page_index in page_indexes:
            for table in pdf.pages[page_index].extract_tables():
                for row in table:
                    if len(row) < 4:
                        continue
                    raw_faculty, _chinese_name, raw_name, raw_duration = row[:4]
                    if normalise(raw_name or "") == "Program Name":
                        continue
                    duration = normalise(raw_duration or "")
                    if duration not in {"2", "3"}:
                        continue
                    if raw_faculty:
                        faculty = _english_label(raw_faculty)
                    name = normalise(raw_name or "")
                    if faculty and name:
                        entries.append((faculty, name))
    return GuidePayload(entries=tuple(entries))


def _english_label(value: str) -> str:
    text = normalise(value)
    match = re.search(r"[A-Za-z].*", text)
    return normalise(match.group(0)) if match else ""
