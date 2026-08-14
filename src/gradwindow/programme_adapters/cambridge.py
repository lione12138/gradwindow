from __future__ import annotations

import concurrent.futures
import re
import unicodedata
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from ..browser_rendering import (
    browser_content_fetcher_from_environment,
    browser_markdown_fetcher_from_environment,
)
from .base import (
    BaseProgrammeAdapter,
    DiscoveredCatalog,
    DiscoveredProgramme,
    DiscoveredWindow,
    OfficialSourceTransportError,
)

CATALOG_URL = "https://www.postgraduate.study.cam.ac.uk/courses/directory"
APPLICATION_URL = "https://apply.postgraduate.study.cam.ac.uk/applicant/login"
UNIVERSITY_ID = "university-of-cambridge"
READER_PREFIX = "https://r.jina.ai/http://"
COURSE_DATES_RE = re.compile(
    r"Applications open\s+(?P<opens>[A-Z][a-z]{2,}\.?\s+\d{1,2},\s+20\d{2})"
    r"\s+Application deadline\s+"
    r"(?P<closes>[A-Z][a-z]{2,}\.?\s+\d{1,2},\s+20\d{2})"
    r"\s+Course starts\s+"
    r"(?P<starts>[A-Z][a-z]{2,}\.?\s+\d{1,2},\s+20\d{2})",
    flags=re.IGNORECASE,
)


class CambridgeAdapter(BaseProgrammeAdapter):
    university_id = UNIVERSITY_ID
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Michaelmas 2026"

    def __init__(
        self,
        minimum_expected_programmes: int = 100,
        detail_workers: int = 8,
        browser_content_fetcher: Callable[[str], str] | None = None,
        browser_markdown_fetcher: Callable[[str], str] | None = None,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.detail_workers = detail_workers
        self.browser_content_fetcher = (
            browser_content_fetcher or browser_content_fetcher_from_environment()
        )
        self.browser_markdown_fetcher = (
            browser_markdown_fetcher or browser_markdown_fetcher_from_environment()
        )

    def parse_catalog_from_fetcher(
        self,
        fetcher: Callable[[str], str],
    ) -> DiscoveredCatalog:
        first_html = self._fetch_catalog_page(self.catalog_url, fetcher)
        soup = BeautifulSoup(first_html, "html.parser")
        last_page = _last_page_number(soup)
        html_pages = [first_html]
        html_pages.extend(
            self._fetch_catalog_page(f"{self.catalog_url}?page={page}", fetcher)
            for page in range(1, last_page + 1)
        )
        programmes = [
            programme
            for html in html_pages
            for programme in self._parse_programmes(html)
        ]
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.detail_workers
        ) as executor:
            programmes = list(
                executor.map(
                    lambda programme: self._parse_detail_from_fetcher(
                        programme, fetcher
                    ),
                    programmes,
                )
            )
        return self._catalog_from_programmes(programmes)

    def _fetch_catalog_page(
        self,
        url: str,
        fetcher: Callable[[str], str],
    ) -> str:
        try:
            html = fetcher(url)
            if html and not _is_access_challenge(html):
                return html
            direct_error = "access challenge or empty response"
        except Exception as exc:
            direct_error = f"{type(exc).__name__}: {str(exc)[:180]}"
        if self.browser_content_fetcher is not None:
            try:
                rendered = self.browser_content_fetcher(url)
            except Exception as exc:
                browser_error = f"{type(exc).__name__}: {str(exc)[:180]}"
            else:
                if rendered and not _is_access_challenge(rendered):
                    return rendered
                browser_error = "access challenge or empty response"
        else:
            browser_error = "not configured"
        raise OfficialSourceTransportError(
            "Cambridge official course directory could not be retrieved; "
            f"direct={direct_error}; browser-rendering={browser_error}"
        )

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        return self._catalog_from_programmes(self._parse_programmes(html))

    def _parse_programmes(self, html: str) -> list[DiscoveredProgramme]:
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        if table is None:
            raise ValueError("Cambridge course directory table was not found")
        return [
            programme
            for row in table.select("tbody tr")
            if (programme := self._parse_row(row)) is not None
        ]

    def _catalog_from_programmes(
        self,
        programmes: list[DiscoveredProgramme],
    ) -> DiscoveredCatalog:
        unique = {programme.id: programme for programme in programmes}
        programmes = sorted(unique.values(), key=lambda item: item.id)
        if len(programmes) < self.minimum_expected_programmes:
            raise ValueError(
                "Cambridge catalog only contained "
                f"{len(programmes)} taught master's programmes; expected at least "
                f"{self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=programmes)

    def _parse_row(self, row) -> DiscoveredProgramme | None:
        cells = row.find_all("td", recursive=False)
        if len(cells) < 3:
            return None
        course_level = _normalise_text(cells[1].get_text(" ", strip=True))
        taught_or_research = _normalise_text(cells[2].get_text(" ", strip=True))
        if course_level != "Master's" or taught_or_research != "Taught":
            return None
        link = cells[0].find("a", href=True)
        if link is None:
            return None
        title = _normalise_text(link.get_text(" ", strip=True)).replace(
            " - Closed this cycle", ""
        )
        course_text = _normalise_text(cells[0].get_text(" ", strip=True)).replace(
            " - Closed this cycle", ""
        )
        degree_type = _degree_type(course_text, title)
        if degree_type is None:
            return None
        source_url = urljoin(self.catalog_url, link["href"])
        return DiscoveredProgramme(
            id=_programme_id(title, degree_type),
            name=f"{degree_type} in {title}",
            degree_type=degree_type,
            faculty="",
            department="",
            source_url=source_url,
            application_url=self.application_url,
            windows=[],
            deadline_text=(
                "The Cambridge course directory identifies this taught master's "
                "course; exact application dates are published on the course page."
            ),
            parse_status="no-deadline",
        )

    def _parse_detail(
        self,
        programme: DiscoveredProgramme,
        html: str,
        *,
        source_url: str | None = None,
        retrieval_method: str | None = None,
    ) -> DiscoveredProgramme:
        soup = BeautifulSoup(html, "html.parser")
        text = _normalise_text(soup.get_text(" ", strip=True))
        matches = list(COURSE_DATES_RE.finditer(text))
        if not matches:
            return programme
        target_intakes = _target_cambridge_intakes(self.intake)
        parsed_windows: list[tuple[str, DiscoveredWindow, str]] = []
        seen_windows: set[tuple[str, str, str]] = set()
        for match in matches:
            opens_at = _parse_cambridge_date(match.group("opens"))
            closes_at = _parse_cambridge_date(match.group("closes"))
            starts_at = _parse_cambridge_date(match.group("starts"))
            intake = _cambridge_intake(starts_at)
            if intake not in target_intakes:
                continue
            identity = (intake, opens_at, closes_at)
            if identity in seen_windows:
                continue
            seen_windows.add(identity)
            parsed_windows.append(
                (
                    starts_at,
                    DiscoveredWindow(
                        round="Main deadline",
                        opens_at=opens_at,
                        closes_at=closes_at,
                        intake=intake,
                        source_url=source_url or programme.source_url,
                    ),
                    _normalise_text(match.group(0)),
                )
            )
        if not parsed_windows:
            return programme
        parsed_windows.sort(key=lambda item: (item[0], item[1].closes_at))
        return replace(
            programme,
            windows=[item[1] for item in parsed_windows],
            deadline_text=" | ".join(item[2] for item in parsed_windows),
            parse_status="parsed",
            retrieval_method=retrieval_method,
            evidence_quality="official-full-text",
        )

    def _parse_detail_from_fetcher(
        self,
        programme: DiscoveredProgramme,
        fetcher: Callable[[str], str],
    ) -> DiscoveredProgramme:
        apply_url = f"{programme.source_url.rstrip('/')}/apply"
        attempts = (
            (programme.source_url, "official-course-page"),
            (apply_url, "official-course-apply-page"),
        )
        errors = []
        apply_page_retrieved = False
        for source_url, retrieval_method in attempts:
            try:
                html = fetcher(source_url)
            except Exception as exc:
                errors.append(f"{source_url}: {type(exc).__name__}: {str(exc)[:120]}")
                continue
            if _is_access_challenge(html):
                errors.append(f"{source_url}: access challenge")
                continue
            if source_url == apply_url:
                apply_page_retrieved = True
            parsed = self._parse_detail(
                programme,
                html,
                source_url=source_url,
                retrieval_method=retrieval_method,
            )
            if parsed.parse_status == "parsed":
                return parsed

        if apply_page_retrieved:
            return programme

        if self.browser_markdown_fetcher is not None:
            try:
                rendered_text = self.browser_markdown_fetcher(apply_url)
            except Exception as exc:
                errors.append(
                    "cloudflare-browser-rendering: "
                    f"{type(exc).__name__}: {str(exc)[:120]}"
                )
            else:
                if rendered_text and not _is_access_challenge(rendered_text):
                    return self._parse_detail(
                        programme,
                        rendered_text,
                        source_url=apply_url,
                        retrieval_method="cloudflare-browser-rendering",
                    )
                errors.append(
                    "cloudflare-browser-rendering: access challenge or empty response"
                )

        reader_url = _reader_url(apply_url)
        try:
            reader_text = fetcher(reader_url)
        except Exception as exc:
            errors.append(f"{reader_url}: {type(exc).__name__}: {str(exc)[:120]}")
        else:
            if reader_text and not _is_access_challenge(reader_text):
                return self._parse_detail(
                    programme,
                    reader_text,
                    source_url=apply_url,
                    retrieval_method="official-course-apply-page-via-reader",
                )
            errors.append(f"{reader_url}: access challenge or empty response")

        raise OfficialSourceTransportError(
            "Cambridge official course and apply pages could not be retrieved; "
            + "; ".join(errors)
        )


def _degree_type(course_text: str, title: str) -> str | None:
    suffix = course_text[len(title) :].strip()
    match = re.search(r"\b(MPhil|MSt|MRes|LLM|MBA|MEd|MFin|MMus|MCL)\b", suffix)
    return match.group(1) if match else None


def _last_page_number(soup: BeautifulSoup) -> int:
    last = 0
    for link in soup.select('a[href*="page="]'):
        match = re.search(r"[?&]page=(\d+)", link.get("href", ""))
        if match:
            last = max(last, int(match.group(1)))
    return last


def _parse_cambridge_date(value: str) -> str:
    normalised = _normalise_text(value).replace(".", "")
    for pattern in ("%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(normalised, pattern).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"Unsupported Cambridge date: {value}")


def _cambridge_intake(course_starts_at: str) -> str:
    parsed = datetime.fromisoformat(course_starts_at)
    if parsed.month in {9, 10, 11, 12}:
        return f"Michaelmas {parsed.year}"
    if parsed.month in {1, 2, 3}:
        return f"Lent {parsed.year}"
    if parsed.month in {4, 5, 6}:
        return f"Easter {parsed.year}"
    return f"{parsed.strftime('%B')} {parsed.year}"


def _target_cambridge_intakes(anchor_intake: str) -> set[str]:
    match = re.fullmatch(r"Michaelmas\s+(20\d{2})", anchor_intake)
    if match is None:
        raise ValueError(
            "Cambridge target intake must use the 'Michaelmas YYYY' format"
        )
    academic_year = int(match.group(1))
    return {
        f"Michaelmas {academic_year}",
        f"Lent {academic_year + 1}",
        f"Easter {academic_year + 1}",
    }


def _programme_id(title: str, degree_type: str) -> str:
    return f"cambridge-{_slug(title)}-{_slug(degree_type)}"


def _slug(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    )
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", ascii_value.lower())).strip(
        "-"
    )


def _normalise_text(value: str) -> str:
    return " ".join(value.replace("\u00a0", " ").split())


def _reader_url(source_url: str) -> str:
    return READER_PREFIX + re.sub(r"^https?://", "", source_url)


def _is_access_challenge(value: str) -> bool:
    lowered = value.lower()
    return (
        "request unsuccessful" in lowered
        or "access denied" in lowered
        or "cf-chl-" in lowered
    )
