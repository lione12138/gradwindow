from __future__ import annotations

import re
from collections.abc import Callable
from io import BytesIO
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from pypdf import PdfReader

from ..http_client import DEFAULT_USER_AGENT, fetch_page
from .base import DiscoveredCatalog, DiscoveredProgramme, DiscoveredWindow, Fetcher
from .official_catalog import normalise

CATALOG_PAGE_URL = "https://yjs.suda.edu.cn/54/32/c8386a676914/page.htm"
GUIDE_URL = "https://yjs.suda.edu.cn/54/2c/c8365a676908/page.htm"
APPLICATION_URL = "https://yz.chsi.com.cn/"
_FACULTY_RE = re.compile(
    r"^(?P<code>\d{3})\s+(?P<name>.+?(?:学院|研究院|中心|学部|医院))$"
)
_PROGRAMME_RE = re.compile(
    r"^(?P<code>\d{4}[0-9A-Z]{2})(?P<name>.+?)"
    r"（(?P<label>[^）]*(?:学术学位|专业学位)[^）]*)）(?:\s+.*)?$"
)

PdfTextFetcher = Callable[[str], str]


class SoochowChinaAdapter:
    university_id = "soochow-university-china"
    catalog_url = CATALOG_PAGE_URL
    guide_url = GUIDE_URL
    application_url = APPLICATION_URL
    intake = "Autumn 2026"
    application_opens_at_basis = "official"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_PAGE_URL, GUIDE_URL)
    known_programme_window_scope_type = "institution"
    known_programme_window_scope_id = "soochow-university-china"

    def __init__(
        self,
        minimum_expected_programmes: int = 150,
        maximum_expected_programmes: int = 240,
        pdf_text_fetcher: PdfTextFetcher | None = None,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.maximum_expected_programmes = maximum_expected_programmes
        self.pdf_text_fetcher = pdf_text_fetcher or _fetch_pdf_text

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        pdf_url = _catalogue_pdf_url(fetcher(CATALOG_PAGE_URL))
        programmes = _programmes(self.pdf_text_fetcher(pdf_url), pdf_url)
        if not (
            self.minimum_expected_programmes
            <= len(programmes)
            <= self.maximum_expected_programmes
        ):
            raise ValueError(
                f"Soochow catalogue contained {len(programmes)} master's programmes; "
                f"expected {self.minimum_expected_programmes}-"
                f"{self.maximum_expected_programmes}"
            )
        _validate_guide(fetcher(GUIDE_URL))
        programmes.append(_deadline_group())
        return DiscoveredCatalog(
            application_opens_at="2025-10-10", programmes=programmes
        )


def _catalogue_pdf_url(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    node = soup.select_one(".wp_pdf_player[pdfsrc]")
    if node is None:
        raise ValueError("Soochow catalogue page did not expose its PDF")
    url = urljoin(CATALOG_PAGE_URL, str(node.get("pdfsrc", "")))
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "yjs.suda.edu.cn"
        or not parsed.path.lower().endswith(".pdf")
    ):
        raise ValueError("Soochow catalogue PDF is not an official HTTPS source")
    return url


def _programmes(text: str, source_url: str) -> list[DiscoveredProgramme]:
    faculty_code = ""
    faculty = ""
    programmes: dict[str, DiscoveredProgramme] = {}
    for raw_line in text.splitlines():
        line = normalise(raw_line)
        faculty_match = _FACULTY_RE.match(line)
        if faculty_match is not None:
            faculty_code = faculty_match.group("code")
            faculty = faculty_match.group("name")
            continue
        match = _PROGRAMME_RE.match(line)
        if match is None or not faculty:
            continue
        name = normalise(match.group("name"))
        label = normalise(match.group("label"))
        if not name or name.startswith(("考试", "科目", "参考书")):
            continue
        code = match.group("code").lower()
        programme_id = f"soochow-{faculty_code}-{code}"
        programmes[programme_id] = DiscoveredProgramme(
            id=programme_id,
            name=name,
            degree_type=label,
            faculty=faculty,
            department=faculty,
            source_url=source_url,
            application_url=APPLICATION_URL,
            windows=[],
            deadline_text=(
                "Programme is listed in Soochow University's official 2026 "
                "master's catalogue. The exact national registration rounds "
                "are represented once at institution scope."
            ),
            parse_status="no-deadline",
            retrieval_method="official-2026-masters-catalogue-pdf",
            evidence_quality="official-full-text",
        )
    return sorted(programmes.values(), key=lambda row: (row.faculty, row.id))


def _validate_guide(html: str) -> None:
    text = normalise(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))
    compact = re.sub(r"\s+", "", text)
    expected = (
        "2025年10月16日至10月27日",
        "2025年10月10日至10月13日",
    )
    if not all(value in compact for value in expected):
        raise ValueError("Soochow's official 2026 registration rounds are missing")


def _deadline_group() -> DiscoveredProgramme:
    windows = [
        DiscoveredWindow(
            round="National master's pre-registration",
            applicant_categories=["domestic-students"],
            opens_at="2025-10-10",
            closes_at="2025-10-13",
            intake="Autumn 2026",
            source_url=GUIDE_URL,
            opens_at_basis="official",
        ),
        DiscoveredWindow(
            round="National master's formal registration",
            applicant_categories=["domestic-students"],
            opens_at="2025-10-16",
            closes_at="2025-10-27",
            intake="Autumn 2026",
            source_url=GUIDE_URL,
            opens_at_basis="official",
        ),
    ]
    return DiscoveredProgramme(
        id="soochow-national-master-admissions",
        name="National master's admissions",
        degree_type="Master",
        faculty="Graduate School",
        department="Graduate Admissions Office",
        source_url=GUIDE_URL,
        application_url=APPLICATION_URL,
        windows=windows,
        deadline_text=(
            "Soochow University's official 2026 guide publishes the exact "
            "national pre-registration and formal registration periods."
        ),
        parse_status="parsed",
        retrieval_method="official-2026-masters-guide-html",
        evidence_quality="official-full-text",
    )


def _fetch_pdf_text(url: str) -> str:
    page = fetch_page(
        url,
        user_agent=DEFAULT_USER_AGENT,
        timeout=90,
        max_bytes=1_000_000,
        accept="application/pdf,*/*;q=0.8",
    )
    if page.truncated or not page.raw_bytes.startswith(b"%PDF"):
        raise ValueError("Soochow catalogue did not return a bounded PDF")
    reader = PdfReader(BytesIO(page.raw_bytes))
    if not 65 <= len(reader.pages) <= 80:
        raise ValueError("Soochow catalogue page count changed unexpectedly")
    return "\n".join(
        pdf_page.extract_text(extraction_mode="layout") or ""
        for pdf_page in reader.pages
    )
