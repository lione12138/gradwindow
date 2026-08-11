from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO

import pdfplumber
from bs4 import BeautifulSoup
from pypdf import PdfReader

from ..http_client import DEFAULT_USER_AGENT, fetch_page
from .base import DiscoveredCatalog, DiscoveredProgramme, DiscoveredWindow, Fetcher
from .official_catalog import normalise, slug

CATALOG_URL = "https://isc.bit.edu.cn/docs/2025-11/b59c4c1d2b41494f9e2edc2c0993742b.pdf"
GUIDE_URL = "https://isc.bit.edu.cn/aboutbit/faq/b163461.htm"
APPLICATION_URL = "http://apply.isc.bit.edu.cn/"

_WINDOW_RE = re.compile(
    r"Application Period:\s*"
    r"(?P<open_month>[A-Z][a-z]+)\s+(?P<open_day>\d{1,2})\s*(?:st|nd|rd|th)?\s*,\s*"
    r"(?P<open_year>20\d{2})\s+to\s+"
    r"(?P<close_month>[A-Z][a-z]+)\s+(?P<close_day>\d{1,2})\s*(?:st|nd|rd|th)?\s*,\s*"
    r"(?P<close_year>20\d{2})",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class GuidePayload:
    entries: tuple[tuple[str, str], ...]


GuideFetcher = Callable[[str], GuidePayload]


class BITAdapter:
    university_id = "beijing-institute-of-technology"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Autumn 2026"
    application_opens_at_basis = "official"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, GUIDE_URL)
    retrieval_method = "official-international-admission-book-pdf"
    known_programme_window_scope_type = "programme-group"
    known_programme_window_scope_id = "bit-international-graduate-admissions"

    def __init__(
        self,
        minimum_expected_programmes: int = 35,
        maximum_expected_programmes: int = 55,
        guide_fetcher: GuideFetcher | None = None,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.maximum_expected_programmes = maximum_expected_programmes
        self.guide_fetcher = guide_fetcher or _fetch_guide

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        programmes = _programmes(self.guide_fetcher(CATALOG_URL).entries)
        if not (
            self.minimum_expected_programmes
            <= len(programmes)
            <= self.maximum_expected_programmes
        ):
            raise ValueError(
                f"BIT admission book contained {len(programmes)} master's "
                f"programmes; expected {self.minimum_expected_programmes}-"
                f"{self.maximum_expected_programmes}"
            )
        opens_at, closes_at = _application_window(fetcher(GUIDE_URL))
        programmes.append(
            DiscoveredProgramme(
                id="bit-international-graduate-admissions",
                name="International graduate admissions",
                degree_type="Master/Doctoral",
                faculty="Office of International Students",
                department="Office of International Students",
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
                    "BIT's official 2026 graduate admission page publishes this "
                    "exact programme-group application period."
                ),
                parse_status="parsed",
                retrieval_method=self.retrieval_method,
                evidence_quality="official-full-text",
            )
        )
        return DiscoveredCatalog(application_opens_at=opens_at, programmes=programmes)


def _programmes(
    entries: tuple[tuple[str, str], ...],
) -> list[DiscoveredProgramme]:
    programmes: dict[str, DiscoveredProgramme] = {}
    for campus, raw_name in entries:
        name = normalise(raw_name)
        faculty = normalise(campus)
        if not name or not faculty:
            continue
        programme_id = f"bit-{slug(faculty)}-{slug(name)}-master"
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
                "Programme is listed in BIT's official 2026 international "
                "admission book. Its shared exact application period is "
                "represented once at programme-group scope."
            ),
            parse_status="no-deadline",
            retrieval_method="official-international-admission-book-pdf",
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
        raise ValueError("BIT guide did not expose its exact application period")
    return _date(match, "open"), _date(match, "close")


def _date(match: re.Match[str], prefix: str) -> str:
    value = (
        f"{match.group(f'{prefix}_month')} {match.group(f'{prefix}_day')} "
        f"{match.group(f'{prefix}_year')}"
    )
    return datetime.strptime(value, "%B %d %Y").date().isoformat()


def _fetch_guide(url: str) -> GuidePayload:
    page = fetch_page(
        url,
        user_agent=DEFAULT_USER_AGENT,
        timeout=90,
        max_bytes=8_000_000,
        accept="application/pdf,application/octet-stream,*/*;q=0.8",
    )
    if page.truncated or not page.raw_bytes.startswith(b"%PDF"):
        raise ValueError("BIT admission book did not return a bounded PDF")

    entries: list[tuple[str, str]] = []
    with pdfplumber.open(BytesIO(page.raw_bytes)) as pdf:
        beijing_first = pdf.pages[12].extract_tables()
        if not beijing_first:
            raise ValueError("BIT admission book lacked its first programme table")
        for row in beijing_first[0]:
            if len(row) < 3:
                continue
            name = normalise(row[1] or "")
            degree = normalise(row[2] or "")
            if name and name != "Major" and degree != "Ph.D.":
                entries.append(("Beijing Campus", name))

        beijing_second = pdf.pages[13].extract_tables()
        if not beijing_second:
            raise ValueError("BIT admission book lacked its second programme table")
        for row in beijing_second[0]:
            if len(row) < 3:
                continue
            name = normalise(row[2] or "")
            if name and name != "Major":
                entries.append(("Beijing Campus", name))

    reader = PdfReader(BytesIO(page.raw_bytes))
    page_fourteen = reader.pages[13].extract_text() or ""
    if "Design" in {normalise(line) for line in page_fourteen.splitlines()}:
        entries.append(("Beijing Campus", "Design"))
    entries.extend(_zhuhai_entries(reader.pages[14].extract_text() or ""))
    return GuidePayload(entries=tuple(entries))


def _zhuhai_entries(text: str) -> list[tuple[str, str]]:
    lines = [normalise(line) for line in text.splitlines() if normalise(line)]
    domain_indexes = [
        index for index, line in enumerate(lines) if line.endswith(" Domain")
    ]
    if not domain_indexes:
        raise ValueError("BIT admission book lacked its Zhuhai domains")
    entries: list[tuple[str, str]] = []
    for line in lines[max(domain_indexes) + 1 :]:
        if line.startswith("CH"):
            break
        name = line.replace("T echnology", "Technology")
        if name and not name.startswith("Master"):
            entries.append(("Zhuhai Campus", name))
    return entries
