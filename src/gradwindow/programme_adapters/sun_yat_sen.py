from __future__ import annotations

import re
from collections.abc import Callable
from io import BytesIO
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader

from ..http_client import DEFAULT_USER_AGENT, fetch_page
from .base import DiscoveredCatalog, DiscoveredProgramme, Fetcher
from .official_catalog import normalise

CATALOG_URL = "https://graduate.sysu.edu.cn/zsw/article/493"
APPLICATION_URL = "https://graduate.sysu.edu.cn/zsw/"
_FACULTY_RE = re.compile(r"^(?P<code>\d{3})\s+(?P<name>.+?)(?:\s+\d+)?$")
_PROGRAMME_RE = re.compile(r"^(?P<code>\d{4}[0-9A-Z]{2})\s+(?P<rest>.+)$")
_FACULTY_MARKERS = (
    "学院",
    "学系",
    "中心",
    "医院",
    "研究院",
    "实验室",
    "基地",
    "系",
    "所",
    "部",
)

PdfTextFetcher = Callable[[str], str]


class SunYatSenAdapter:
    university_id = "sun-yat-sen-university"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "2026"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL,)
    retrieval_method = "official-2026-masters-catalogue-pdf"
    catalogue_limitation_reason = (
        "The official 2026 catalogue lists admissions units and master's subjects, "
        "but the linked registration notices do not establish one universal exact "
        "opening-and-closing pair for every applicant and programme."
    )

    def __init__(
        self,
        minimum_expected_programmes: int = 450,
        pdf_text_fetcher: PdfTextFetcher | None = None,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.pdf_text_fetcher = pdf_text_fetcher or _fetch_pdf_text

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        pdf_url = _catalogue_pdf_url(fetcher(CATALOG_URL))
        programmes = _programmes(self.pdf_text_fetcher(pdf_url), pdf_url)
        if len(programmes) < self.minimum_expected_programmes:
            raise ValueError(
                f"Sun Yat-sen catalogue contained {len(programmes)} master's "
                f"routes; expected at least {self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=programmes)


def _catalogue_pdf_url(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for link in soup.select("a[href]"):
        label = normalise(link.get_text(" ", strip=True))
        href = str(link.get("href", ""))
        if "硕士研究生招生学科专业目录" in label and ".pdf" in href.casefold():
            url = urljoin(CATALOG_URL, href)
            parsed = urlparse(url)
            if parsed.scheme == "https" and parsed.hostname == "graduate.sysu.edu.cn":
                return url
    raise ValueError("Sun Yat-sen's official 2026 master's catalogue PDF is missing")


def _programmes(text: str, source_url: str) -> list[DiscoveredProgramme]:
    current_faculty_code = ""
    current_faculty = ""
    programmes: dict[str, DiscoveredProgramme] = {}
    for raw_line in text.splitlines():
        line = normalise(raw_line)
        faculty_match = _FACULTY_RE.match(line)
        if faculty_match and any(
            marker in faculty_match.group("name") for marker in _FACULTY_MARKERS
        ):
            current_faculty_code = faculty_match.group("code")
            current_faculty = re.sub(
                r"\s+\d+$", "", faculty_match.group("name")
            ).strip()
            continue
        programme_match = _PROGRAMME_RE.match(line)
        if not programme_match or not current_faculty:
            continue
        remainder = re.split(r"\s+[①②③④]", programme_match.group("rest"), maxsplit=1)[0]
        name = re.split(r"\s+\d+(?:\s|$)", remainder, maxsplit=1)[0].strip()
        if not name:
            continue
        subject_code = programme_match.group("code")
        programme_id = f"sysu-{current_faculty_code}-{subject_code.lower()}"
        programmes[programme_id] = DiscoveredProgramme(
            id=programme_id,
            name=name,
            degree_type="Master",
            faculty=current_faculty,
            department=current_faculty,
            source_url=source_url,
            application_url=APPLICATION_URL,
            windows=[],
            deadline_text=(
                "招生专业来自中山大学官方 2026 年硕士研究生招生学科专业目录。"
                "官方材料未为该专业给出适用于所有申请人的完整精确开放及截止日期，"
                "因此不推断日期。"
            ),
            parse_status="no-deadline",
            retrieval_method="official-2026-masters-catalogue-pdf",
            evidence_quality="official-full-text",
        )
    return sorted(programmes.values(), key=lambda row: (row.faculty, row.id))


def _fetch_pdf_text(url: str) -> str:
    error: Exception | None = None
    for _ in range(3):
        try:
            page = fetch_page(
                url,
                user_agent=DEFAULT_USER_AGENT,
                timeout=90,
                max_bytes=6_000_000,
                accept="application/pdf,*/*;q=0.8",
            )
            if page.truncated or not page.raw_bytes.startswith(b"%PDF"):
                raise ValueError("Sun Yat-sen catalogue did not return a bounded PDF")
            reader = PdfReader(BytesIO(page.raw_bytes))
            return "\n".join(
                pdf_page.extract_text(extraction_mode="layout") or ""
                for pdf_page in reader.pages
            )
        except (httpx.HTTPError, ValueError) as exc:
            error = exc
    raise ValueError(f"Sun Yat-sen catalogue could not be read: {error}")
