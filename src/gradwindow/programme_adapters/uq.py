from __future__ import annotations

import concurrent.futures
import math
import re
import unicodedata
from dataclasses import replace
from datetime import date
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from ..http_client import fetch_page
from .base import (
    BaseProgrammeAdapter,
    DiscoveredCatalog,
    DiscoveredProgramme,
    DiscoveredWindow,
    ParserZeroResultError,
)

UNIVERSITY_ID = "the-university-of-queensland"
TARGET_INTAKE_YEAR = 2027
CATALOG_URL = (
    "https://study.uq.edu.au/study-options/programs?studentType=international&"
    "type=program&year=2027&level%5BPostgraduate%5D=Postgraduate"
)
APPLICATION_URL = "https://apply.uq.edu.au/"
BASE_URL = "https://study.uq.edu.au"
FINDER_PAGE_SIZE = 30
UQ_USER_AGENT = "GradWindow/1.0"

MONTHS = (
    "January|February|March|April|May|June|July|August|September|October|"
    "November|December"
)
MONTH_DAY_RE = re.compile(
    rf"(?P<month>{MONTHS})\s+(?P<day>\d{{1,2}})\s+"
    rf"of\s+the\s+(?P<year_ref>previous\s+year|year\s+of\s+commencement)",
    flags=re.IGNORECASE,
)


class UQAdapter(BaseProgrammeAdapter):
    university_id = UNIVERSITY_ID
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    application_opens_at_basis = "missing"
    intake = "Semester 1/2 2027"
    browser_fallback_limit = 10
    browser_wait_for_selectors = {
        CATALOG_URL: "a[href*='/study-options/programs/master-']"
    }

    def __init__(
        self,
        minimum_expected_programmes: int = 80,
        *,
        detail_workers: int = 2,
        target_intake_year: int = TARGET_INTAKE_YEAR,
        maximum_detail_failure_ratio: float = 0.2,
        detail_fetcher=None,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.detail_workers = detail_workers
        self.target_intake_year = target_intake_year
        self.maximum_detail_failure_ratio = maximum_detail_failure_ratio
        self.detail_fetcher = detail_fetcher or _fetch_uq_html

    def parse_catalog_from_fetcher(self, fetcher) -> DiscoveredCatalog:
        first_page = fetcher(self.catalog_url)
        result_count = _finder_result_count(first_page)
        finder_pages = [first_page]
        for page in range(1, math.ceil(result_count / FINDER_PAGE_SIZE)):
            finder_pages.append(fetcher(f"{self.catalog_url}&page={page}"))

        programmes: dict[str, DiscoveredProgramme] = {}
        for finder_html in finder_pages:
            for clean_url in _finder_programme_urls(finder_html):
                slug = urlparse(clean_url).path.rstrip("/").split("/")[-1]
                programme_id = f"uq-{_slug(slug)}"
                source_url = f"{clean_url}?year={self.target_intake_year}"
                programmes[programme_id] = DiscoveredProgramme(
                    id=programme_id,
                    name=_title_from_slug(slug),
                    degree_type="Master",
                    faculty="",
                    department="",
                    source_url=source_url,
                    application_url=self.application_url,
                    windows=[],
                    deadline_text=(
                        "Programme found in UQ's official 2027 degree finder."
                    ),
                    parse_status="no-deadline",
                )
        values = sorted(programmes.values(), key=lambda item: item.id)
        if len(values) < self.minimum_expected_programmes:
            raise ValueError(
                f"UQ degree finder only contained {len(values)} master programmes; "
                f"expected at least {self.minimum_expected_programmes}"
            )

        def parse_one(
            programme: DiscoveredProgramme,
        ) -> tuple[DiscoveredProgramme, bool]:
            try:
                return (
                    self._parse_detail(
                        programme, self.detail_fetcher(programme.source_url)
                    ),
                    False,
                )
            except Exception as exc:
                return (
                    replace(
                        programme,
                        deadline_text=(
                            "Programme found in UQ's official degree finder, but the detail "
                            f"page could not be fetched: {type(exc).__name__}: "
                            f"{str(exc)[:180]}"
                        ),
                        parse_status="no-deadline",
                    ),
                    True,
                )

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.detail_workers
        ) as executor:
            results = list(executor.map(parse_one, values))
        detailed = [item for item, _failed in results]
        failure_count = sum(failed for _item, failed in results)
        if failure_count / len(values) > self.maximum_detail_failure_ratio:
            raise ParserZeroResultError(
                f"UQ detail retrieval failed for {failure_count}/{len(values)} "
                "programmes"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=detailed)

    def _parse_detail(
        self,
        programme: DiscoveredProgramme,
        html: str,
    ) -> DiscoveredProgramme:
        soup = BeautifulSoup(html, "html.parser")
        title = _page_title(soup) or programme.name
        _validate_detail_year(html, self.target_intake_year)
        windows: list[DiscoveredWindow] = []
        excerpts: list[str] = []
        for section in soup.select("section[data-student-type]"):
            heading = _normalise_text(
                " ".join(h.get_text(" ", strip=True) for h in section.find_all("h3"))
            )
            section_text = _normalise_text(section.get_text(" ", strip=True))
            if "Important dates" not in heading:
                continue
            if "The closing date for this program is" not in section_text:
                continue
            category = section.get("data-student-type")
            applicant_categories = (
                ["international-students"]
                if category == "international"
                else ["domestic-students"]
            )
            excerpts.append(section_text)
            for semester, closes_at in _parse_closing_dates(
                section_text, self.target_intake_year
            ):
                windows.append(
                    DiscoveredWindow(
                        round=semester,
                        closes_at=closes_at,
                        applicant_categories=applicant_categories,
                        opens_at=None,
                        intake=f"{semester} {self.target_intake_year}",
                        source_url=programme.source_url,
                        opens_at_basis="missing",
                    )
                )
        return replace(
            programme,
            id=_programme_id(title, programme.source_url),
            name=title,
            windows=_dedupe_windows(windows),
            deadline_text=" ".join(excerpts)[:1600]
            if excerpts
            else programme.deadline_text,
            parse_status="incomplete" if windows else "no-deadline",
        )


def _finder_result_count(html: str) -> int:
    text = _normalise_text(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))
    match = re.search(r"\b\d+\s*-\s*\d+\s+of\s+(\d+)\s+results\b", text, re.I)
    if match is None:
        raise ParserZeroResultError("UQ degree finder lacked a result count")
    return int(match.group(1))


def _finder_programme_urls(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    urls = {
        str(link["href"]).split("?", 1)[0]
        for link in soup.select("a[href*='/study-options/programs/master-']")
    }
    return sorted(url if url.startswith("http") else f"{BASE_URL}{url}" for url in urls)


def _parse_closing_dates(text: str, intake_year: int) -> list[tuple[str, str]]:
    windows: list[tuple[str, str]] = []
    for sentence in re.split(r"(?<=\.)\s+|(?=To commence study)", text):
        if "To commence study" not in sentence:
            continue
        semester_match = re.search(r"semester\s+(?P<semester>[12])", sentence, re.I)
        date_match = MONTH_DAY_RE.search(sentence)
        if semester_match is None or date_match is None:
            continue
        year = (
            intake_year - 1
            if "previous" in date_match.group("year_ref").lower()
            else intake_year
        )
        month = datetime_month(date_match.group("month"))
        day = int(date_match.group("day"))
        windows.append(
            (
                f"Semester {semester_match.group('semester')}",
                date(year, month, day).isoformat(),
            )
        )
    return windows


def datetime_month(value: str) -> int:
    import datetime as _datetime

    return _datetime.datetime.strptime(value.capitalize(), "%B").month


def _dedupe_windows(windows: list[DiscoveredWindow]) -> list[DiscoveredWindow]:
    seen: set[tuple[str, str, tuple[str, ...]]] = set()
    deduped: list[DiscoveredWindow] = []
    for window in windows:
        key = (window.round, window.closes_at, tuple(window.applicant_categories))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(window)
    return deduped


def _page_title(soup: BeautifulSoup) -> str | None:
    heading = soup.find("h1")
    if heading is not None:
        text = _normalise_text(heading.get_text(" ", strip=True))
        text = re.sub(r"\s*-\s*20\d{2}\s*$", "", text)
        if text:
            return text
    meta = soup.find("meta", property="og:title")
    if meta and meta.get("content"):
        return _normalise_text(str(meta["content"]).split(" - Study", 1)[0])
    return None


def _validate_detail_year(html: str, target_year: int) -> None:
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.find("h1")
    heading_has_year = heading is not None and re.search(
        rf"\b{target_year}\b", heading.get_text(" ", strip=True)
    )
    settings_have_year = re.search(
        rf'"currentQuery"\s*:\s*\{{\s*"year"\s*:\s*"{target_year}"', html
    )
    if not heading_has_year and not settings_have_year:
        raise ValueError(f"UQ detail page did not confirm the {target_year} cycle")


def _fetch_uq_html(url: str) -> str:
    return fetch_page(
        url,
        user_agent=UQ_USER_AGENT,
        timeout=45,
        max_bytes=8_000_000,
        accept="text/html,application/xhtml+xml",
    ).body


def _programme_id(title: str, source_url: str) -> str:
    slug = urlparse(source_url).path.rstrip("/").split("/")[-1]
    code_match = re.search(r"-(\d+)$", slug)
    code = code_match.group(1) if code_match else ""
    base = re.sub(r"^Master of\s+", "", title, flags=re.I)
    suffix = f"-{code}" if code else ""
    return f"uq-{_slug(base)}-master{suffix}"


def _title_from_slug(slug: str) -> str:
    title = re.sub(r"-\d+$", "", slug)
    return " ".join(part.capitalize() for part in title.split("-"))


def _slug(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    )
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", ascii_value.lower())).strip(
        "-"
    )


def _normalise_text(value: str) -> str:
    return " ".join(str(value).replace("\u00a0", " ").split())
