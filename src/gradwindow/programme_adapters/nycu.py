from __future__ import annotations

import re
from collections.abc import Callable
from datetime import datetime
from io import BytesIO
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup
from pypdf import PdfReader

from ..http_client import DEFAULT_USER_AGENT, fetch_page
from .base import (
    DiscoveredCatalog,
    DiscoveredProgramme,
    DiscoveredWindow,
    Fetcher,
)
from .official_catalog import normalise, slug

CATALOG_URL = (
    "https://oia.nycu.edu.tw/oia/en/app/artwebsite/view?"
    "id=786&module=artwebsite&serno=aa792259-32d5-422d-b382-3171b79f64f3"
)
APPLICATION_URL = "https://oia.nycu.edu.tw/oia/en/app/folder/782"
_GUIDE_TEXT = "Spring 2027 Admission Guidelines for International Degree Students"
_WINDOW_RE = re.compile(
    r"Online application system starts.*?"
    r"(?P<start_month>[A-Z][a-z]+)\s+(?P<start_day>\d{1,2}),\s*"
    r"(?P<start_year>20\d{2}).*?"
    r"Online application deadline.*?"
    r"(?P<end_month>[A-Z][a-z]+)\s+(?P<end_day>\d{1,2}),\s*"
    r"(?P<end_year>20\d{2})",
    re.IGNORECASE | re.DOTALL,
)

PdfTextFetcher = Callable[[str], str]


class NYCUAdapter:
    university_id = "national-yang-ming-chiao-tung-university"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Spring 2027"
    application_opens_at_basis = "official"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-international-admissions-guide-pdf"
    known_programme_window_scope_type = "programme-group"
    known_programme_window_scope_id = "nycu-international-degree-admissions"

    def __init__(
        self,
        minimum_expected_programmes: int = 55,
        pdf_text_fetcher: PdfTextFetcher | None = None,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.pdf_text_fetcher = pdf_text_fetcher or _fetch_pdf_text

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        guide_url = _guide_url(fetcher(CATALOG_URL))
        guide_text = self.pdf_text_fetcher(guide_url)
        programmes = _programmes(guide_text)
        if len(programmes) < self.minimum_expected_programmes:
            raise ValueError(
                f"NYCU guide contained {len(programmes)} Spring master's routes; "
                f"expected at least {self.minimum_expected_programmes}"
            )
        opens_at, closes_at = _application_window(guide_text)
        programmes.append(
            DiscoveredProgramme(
                id="nycu-international-degree-programmes",
                name="International degree-seeking programmes",
                degree_type="Master/Doctoral",
                faculty="Office of International Affairs",
                department="Office of International Affairs",
                source_url=CATALOG_URL,
                application_url=APPLICATION_URL,
                windows=[
                    DiscoveredWindow(
                        round="International degree admissions",
                        applicant_categories=["international-students"],
                        opens_at=opens_at,
                        closes_at=closes_at,
                        intake=self.intake,
                        source_url=CATALOG_URL,
                    )
                ],
                deadline_text=(
                    "NYCU's official Spring 2027 international admissions guide "
                    "publishes this exact programme-group application period."
                ),
                parse_status="parsed",
                retrieval_method=self.retrieval_method,
                evidence_quality="official-full-text",
            )
        )
        return DiscoveredCatalog(application_opens_at=opens_at, programmes=programmes)


def _guide_url(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for link in soup.select("a[href]"):
        if _GUIDE_TEXT not in normalise(link.get_text(" ", strip=True)):
            continue
        url = str(link.get("href", "")).strip()
        if _google_drive_file_id(url):
            return url
    raise ValueError("NYCU programmes page did not link the Spring 2027 guide")


def _programmes(text: str) -> list[DiscoveredProgramme]:
    programmes: dict[str, DiscoveredProgramme] = {}
    for page_text in text.split("\f"):
        if "Intake Degree Program" not in page_text:
            continue
        table_text = page_text.split("Intake Degree Program", 1)[1]
        table_text = table_text.split("Application Regulations", 1)[0]
        if not re.search(r"\bSpring\b.*?\bMaster\b", table_text, re.DOTALL):
            continue
        name = _page_heading(page_text.split("Intake Degree Program", 1)[0])
        if not name or (
            re.search(r"\b(?:Ph\.?D\.?|Doctoral)\b", name, re.IGNORECASE)
            and "Master" not in name
        ):
            continue
        programme_id = f"nycu-{slug(name)}-master"
        programmes[programme_id] = DiscoveredProgramme(
            id=programme_id,
            name=name,
            degree_type="Master",
            faculty="National Yang Ming Chiao Tung University",
            department=name,
            source_url=CATALOG_URL,
            application_url=APPLICATION_URL,
            windows=[],
            deadline_text=(
                "Programme is listed for Spring 2027 in NYCU's official "
                "international admissions guide. Its shared application period "
                "is represented once at programme-group scope."
            ),
            parse_status="no-deadline",
            retrieval_method="official-international-admissions-guide-pdf",
            evidence_quality="official-full-text",
        )
    return sorted(programmes.values(), key=lambda item: item.name.casefold())


def _page_heading(value: str) -> str:
    lines = [normalise(line) for line in value.splitlines() if normalise(line)]
    lines = [
        line
        for line in lines
        if not re.fullmatch(r"\d+", line)
        and "Campus】" not in line
        and not line.startswith("College of ")
        and line not in {"School of Law", "Industry Academia Innovation School"}
    ]
    return normalise(" ".join(lines))


def _application_window(text: str) -> tuple[str, str]:
    match = _WINDOW_RE.search(text)
    if match is None:
        raise ValueError("NYCU guide did not expose its exact application period")
    return _date(match, "start"), _date(match, "end")


def _date(match: re.Match[str], prefix: str) -> str:
    value = (
        f"{match.group(f'{prefix}_month')} {match.group(f'{prefix}_day')} "
        f"{match.group(f'{prefix}_year')}"
    )
    return datetime.strptime(value, "%B %d %Y").date().isoformat()


def _google_drive_file_id(url: str) -> str:
    parsed = urlparse(url)
    if parsed.hostname not in {"drive.google.com", "docs.google.com"}:
        return ""
    match = re.search(r"/file/d/([^/]+)", parsed.path)
    if match:
        return match.group(1)
    return parse_qs(parsed.query).get("id", [""])[0]


def _fetch_pdf_text(url: str) -> str:
    file_id = _google_drive_file_id(url)
    if not file_id:
        raise ValueError("NYCU guide was not an official-page-linked Google Drive file")
    download_url = (
        "https://drive.usercontent.google.com/download?"
        f"id={file_id}&export=download&confirm=t"
    )
    page = fetch_page(
        download_url,
        user_agent=DEFAULT_USER_AGENT,
        timeout=60,
        max_bytes=5_000_000,
        accept="application/pdf,application/octet-stream,*/*;q=0.8",
    )
    if page.truncated or not page.raw_bytes.startswith(b"%PDF"):
        raise ValueError("NYCU guide did not return a bounded PDF")
    reader = PdfReader(BytesIO(page.raw_bytes))
    return "\f".join(pdf_page.extract_text() or "" for pdf_page in reader.pages)
