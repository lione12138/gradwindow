from __future__ import annotations

import re
from collections.abc import Callable
from datetime import datetime
from io import BytesIO
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from docx import Document

from ..http_client import DEFAULT_USER_AGENT
from .base import DiscoveredCatalog, DiscoveredProgramme, DiscoveredWindow, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry, normalise

CATALOG_URL = "https://admission.whu.edu.cn/info/1131/5822.htm"
APPLICATION_URL = "https://admission.whu.edu.cn/"
WINDOW_RE = re.compile(
    r"Degree programs\s*\(Autumn\s+(?P<intake>20\d{2})\)\s*:\s*"
    r"(?P<start_month>[A-Z][a-z]{2,8})\s+(?P<start_day>\d{1,2}),\s*"
    r"(?P<start_year>20\d{2})\s*[–-]\s*"
    r"(?P<end_month>[A-Z][a-z]{2,8})\s+(?P<end_day>\d{1,2}),\s*"
    r"(?P<end_year>20\d{2})",
    re.IGNORECASE,
)

DocxFetcher = Callable[[str], bytes]


class WuhanAdapter(OfficialCatalogAdapter):
    university_id = "wuhan-university"
    school_prefix = "wuhan"
    institution_name = "Wuhan University"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-international-admissions-docx-catalogues"
    application_opens_at_basis = "official"
    known_programme_window_scope_type = "institution"
    known_programme_window_scope_id = "wuhan-university"

    def __init__(
        self,
        minimum_expected_programmes: int = 240,
        docx_fetcher: DocxFetcher | None = None,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.docx_fetcher = docx_fetcher or _fetch_docx

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        html = fetcher(CATALOG_URL)
        english_url, chinese_url = _catalogue_urls(html)
        entries = _docx_entries(
            self.docx_fetcher(english_url),
            language="English",
            source_url=english_url,
        )
        entries.extend(
            _docx_entries(
                self.docx_fetcher(chinese_url),
                language="Chinese",
                source_url=chinese_url,
            )
        )
        window = _application_window(html)
        self.intake = window.intake or "Autumn 2026"
        catalog = self._catalog(entries)
        catalog.application_opens_at = window.opens_at
        catalog.programmes.append(
            DiscoveredProgramme(
                id="wuhan-computer-science-graduate",
                name="International degree programmes",
                degree_type="Master/Doctoral",
                faculty=self.institution_name,
                department="School of International Education",
                source_url=CATALOG_URL,
                application_url=APPLICATION_URL,
                windows=[
                    DiscoveredWindow(
                        round=window.round,
                        closes_at=window.closes_at,
                        applicant_categories=list(window.applicant_categories),
                        opens_at=window.opens_at,
                        intake=window.intake,
                        source_url=window.source_url,
                    )
                ],
                deadline_text=(
                    "Wuhan University's official 2026 international admissions "
                    "guide publishes this exact institution-wide self-funded "
                    "degree application period."
                ),
                parse_status="parsed",
                retrieval_method=self.retrieval_method,
                evidence_quality="official-full-text",
            )
        )
        return catalog

    def extract_entries(self, html: str):  # pragma: no cover - custom fetch flow
        raise NotImplementedError


def _catalogue_urls(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    english_url = ""
    chinese_url = ""
    for link in soup.select("a[href]"):
        text = normalise(link.get_text(" ", strip=True))
        url = urljoin(CATALOG_URL, str(link.get("href", "")))
        if "Programs Available to International Students" not in text:
            continue
        if "English-taught" in text:
            english_url = url
        elif "Chinese-taught" in text:
            chinese_url = url
    if not english_url or not chinese_url:
        raise ValueError("Wuhan guide did not link both master's DOCX catalogues")
    return english_url, chinese_url


def _docx_entries(raw: bytes, *, language: str, source_url: str) -> list[CatalogEntry]:
    document = Document(BytesIO(raw))
    entries = []
    for table in document.tables:
        for row in table.rows[1:]:
            cells = [normalise(cell.text) for cell in row.cells]
            if len(cells) < 3 or not _is_programme_duration(cells[2]):
                continue
            name = _english_label(row.cells[1].text)
            if not name:
                continue
            entries.append(
                entry(
                    name=f"{name} ({language}-taught)",
                    degree_type="Master",
                    source_url=source_url,
                    base_url=CATALOG_URL,
                )
            )
    return entries


def _english_label(value: str) -> str:
    candidates = [
        normalise(line)
        for line in value.splitlines()
        if re.search(r"[A-Za-z]{2}", line)
    ]
    return max(candidates, key=len) if candidates else ""


def _is_programme_duration(value: str) -> bool:
    return bool(re.search(r"\bYears?\b|年", value, flags=re.IGNORECASE))


def _application_window(html: str) -> DiscoveredWindow:
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    match = WINDOW_RE.search(text)
    if match is None:
        raise ValueError("Wuhan guide did not expose the self-funded degree period")
    intake_year = match.group("intake")
    return DiscoveredWindow(
        round="Self-funded international degree admissions",
        applicant_categories=["international-students"],
        opens_at=_date(match, "start"),
        closes_at=_date(match, "end"),
        intake=f"Autumn {intake_year}",
        source_url=CATALOG_URL,
    )


def _date(match: re.Match[str], prefix: str) -> str:
    value = (
        f"{match.group(f'{prefix}_month')} {match.group(f'{prefix}_day')} "
        f"{match.group(f'{prefix}_year')}"
    )
    for pattern in ("%b %d %Y", "%B %d %Y"):
        try:
            return datetime.strptime(value, pattern).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"Wuhan guide used an unsupported date: {value}")


def _fetch_docx(url: str) -> bytes:
    if (urlparse(url).hostname or "").lower() != "admission.whu.edu.cn":
        raise ValueError("Refusing to fetch a non-official Wuhan DOCX")
    response = httpx.get(
        url,
        follow_redirects=True,
        timeout=45,
        headers={
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": (
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document,*/*;q=0.8"
            ),
            "Referer": CATALOG_URL,
        },
    )
    response.raise_for_status()
    if len(response.content) > 2_000_000 or not response.content.startswith(b"PK"):
        raise ValueError("Wuhan catalogue did not return a bounded DOCX file")
    return response.content
