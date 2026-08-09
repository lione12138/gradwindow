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
from .official_catalog import degree_from, normalise, slug

CATALOG_URL = "https://uct.ac.za/students/study-uct-handbooks/handbooks"
APPLICATION_URL = (
    "https://uct.ac.za/students/applications-apply-postgraduate-qualifications/"
    "applications-and-registration"
)
_HANDBOOK_MARKERS = {
    "commerce-handbook-6b": "Commerce",
    "ebe-handbook-7b": "Engineering & the Built Environment",
    "fhs-handbook-8b": "Health Sciences",
    "hum-handbook-9b": "Humanities",
    "law-handbook-10": "Law",
    "sci-handbook-11": "Science",
}
_TOC_RE = re.compile(
    r"^(Master(?:'s| of| in| Programme| Degree|:)[^.]{0,180}?)"
    r"\s*\.{3,}\s*\d+\s*$",
    re.IGNORECASE,
)
_SCIENCE_RE = re.compile(
    r"^(?:MSc/MPhil|MSc|MPhil)\s+"
    r"[A-Z]{2}\d{3}(?:/\d+)?\s+[A-Z]{2,4}\d{2}\s+"
    r"(?P<name>.{3,120})$",
    re.IGNORECASE,
)

PdfTextFetcher = Callable[[str], str]


class CapeTownAdapter:
    university_id = "university-of-cape-town"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-2026-faculty-handbooks"

    def __init__(
        self,
        minimum_expected_programmes: int = 80,
        pdf_text_fetcher: PdfTextFetcher | None = None,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.pdf_text_fetcher = pdf_text_fetcher or _fetch_pdf_text

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        handbooks = _handbooks(fetcher(CATALOG_URL))
        programmes: dict[str, DiscoveredProgramme] = {}
        for source_url, faculty in handbooks:
            for name in _handbook_names(self.pdf_text_fetcher(source_url)):
                programme_id = f"uct-{slug(faculty)}-{slug(name)}"
                if "computer science" in name.casefold():
                    programme_id = "uct-masters-computer-science"
                programmes[programme_id] = DiscoveredProgramme(
                    id=programme_id,
                    name=name,
                    degree_type=degree_from(name),
                    faculty=faculty,
                    department=faculty,
                    source_url=source_url,
                    application_url=APPLICATION_URL,
                    windows=[],
                    deadline_text=(
                        "Programme is listed in UCT's official 2026 faculty "
                        "handbook. Central dates apply only to most coursework "
                        "programmes and faculty exceptions exist, so no exact "
                        "programme window is inferred."
                    ),
                    parse_status="no-deadline",
                    retrieval_method=self.retrieval_method,
                    evidence_quality="official-full-text",
                )
        result = sorted(programmes.values(), key=lambda item: (item.faculty, item.name))
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                f"UCT handbooks contained {len(result)} master's routes; "
                f"expected at least {self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)


def _handbooks(html: str) -> list[tuple[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    results = {}
    for link in soup.select("a[href]"):
        url = urljoin(CATALOG_URL, str(link.get("href", "")))
        lowered = url.lower()
        for marker, faculty in _HANDBOOK_MARKERS.items():
            if marker in lowered and _is_official_pdf(url):
                results[url] = faculty
    if len(results) != len(_HANDBOOK_MARKERS):
        raise ValueError("UCT handbook page did not expose all six faculty PDFs")
    return sorted(results.items())


def _handbook_names(text: str) -> list[str]:
    names = []
    for raw_line in text.splitlines():
        line = normalise(raw_line)
        toc_match = _TOC_RE.match(line)
        science_match = _SCIENCE_RE.match(line)
        if toc_match:
            name = toc_match.group(1).strip(" .")
        elif science_match:
            name = f"MSc/MPhil in {science_match.group('name').strip(' .')}"
        else:
            continue
        lowered = name.casefold()
        if "in abeyance" in lowered:
            continue
        if any(
            phrase in lowered
            for phrase in (
                "master's degrees",
                "master's degree",
                "master's by dissertation only",
                "master's degrees rules",
                "master's study programmes",
            )
        ):
            continue
        if name not in names:
            names.append(name)
    return names


def _fetch_pdf_text(url: str) -> str:
    error: Exception | None = None
    for _ in range(3):
        try:
            page = fetch_page(
                url,
                user_agent=DEFAULT_USER_AGENT,
                timeout=75,
                max_bytes=6_000_000,
                accept="application/pdf,*/*;q=0.8",
            )
            if page.truncated or not page.raw_bytes.startswith(b"%PDF"):
                raise ValueError("UCT handbook did not return a bounded PDF")
            reader = PdfReader(BytesIO(page.raw_bytes))
            return "\n".join(
                pdf_page.extract_text() or "" for pdf_page in reader.pages[:70]
            )
        except (httpx.HTTPError, ValueError) as exc:
            error = exc
    raise ValueError(f"UCT handbook could not be read: {error}")


def _is_official_pdf(url: str) -> bool:
    parsed = urlparse(url)
    return (
        parsed.scheme == "https"
        and parsed.hostname is not None
        and parsed.hostname.lower().endswith("uct.ac.za")
        and parsed.path.lower().endswith(".pdf")
    )
