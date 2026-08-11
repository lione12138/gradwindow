from __future__ import annotations

import concurrent.futures
import html as html_module
import json
import math
import re
import unicodedata
from collections.abc import Callable
from dataclasses import replace
from datetime import date, datetime, timezone
from urllib.parse import urldefrag, urljoin, urlparse

from bs4 import BeautifulSoup

from .base import (
    BaseProgrammeAdapter,
    DiscoveredCatalog,
    DiscoveredProgramme,
    DiscoveredWindow,
)

UNIVERSITY_ID = "technical-university-of-munich"
CATALOG_URL = (
    "https://www.tum.de/en/studies/degree-programs?tx_solr%5Bq%5D=&graduation=Master"
)
APPLICATION_URL = (
    "https://www.tum.de/en/studies/application/"
    "application-info-portal/online-application"
)
EXISTING_INFORMATICS_ID = "tum-informatics-msc"

DEGREE_TYPES = {
    "Master of Science (M.Sc.)": "MSc",
    "Master of Education (M.Ed.)": "MEd",
    "Master of Arts (M.A.)": "MA",
    "Master of Business Administration (MBA)": "MBA",
    "Master of Advanced Studies (MAS)": "MAS",
}

_EXACT_WINDOW_RE = re.compile(
    r"(?P<intake>(?:Winter|Summer)\s+semester\s+20\d{2}(?:/\d{2})?)"
    r"\s*:\s*"
    r"(?P<opens>\d{2}\.\d{2}\.20\d{2})\s*[–—-]\s*"
    r"(?P<closes>\d{2}\.\d{2}\.20\d{2})",
    re.IGNORECASE,
)

_RECURRING_WINDOW_RE = re.compile(
    r"(?P<intake>Winter|Summer)\s+semester\s*:\s*"
    r"(?P<opens>\d{2}\.\d{2}\.)(?!\d)\s*[–—-]\s*"
    r"(?P<closes>\d{2}\.\d{2}\.?)(?!\d)",
    re.IGNORECASE,
)

RECURRING_WINDOW_BASIS = "official-recurring-policy"
REGULAR_DEGREE_TYPES = {"MSc", "MA"}


class TUMAdapter(BaseProgrammeAdapter):
    """Discover TUM master's programmes and official application policies."""

    university_id = UNIVERSITY_ID
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme and semester"
    application_opens_at_basis = "official"
    replace_pending_candidates = True

    def __init__(
        self,
        minimum_expected_programmes: int = 110,
        detail_workers: int = 8,
        minimum_detail_success_ratio: float = 0.9,
        minimum_expected_summer_windows: int | None = None,
        reference_date: date | None = None,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.detail_workers = detail_workers
        self.minimum_detail_success_ratio = minimum_detail_success_ratio
        self.minimum_expected_summer_windows = (
            40
            if minimum_expected_summer_windows is None
            and minimum_expected_programmes >= 110
            else int(minimum_expected_summer_windows or 0)
        )
        self.reference_date = reference_date or datetime.now(timezone.utc).date()

    def parse_catalog_from_fetcher(
        self,
        fetcher: Callable[[str], str],
    ) -> DiscoveredCatalog:
        first_html = fetcher(CATALOG_URL)
        page_count = _page_count(first_html)
        page_html = [first_html]
        if page_count > 1:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=min(self.detail_workers, page_count - 1)
            ) as executor:
                page_html.extend(
                    executor.map(
                        fetcher,
                        [catalog_page_url(page) for page in range(2, page_count + 1)],
                    )
                )

        programmes_by_url: dict[str, DiscoveredProgramme] = {}
        for page in page_html:
            for programme in _catalogue_programmes(page):
                programmes_by_url[programme.source_url] = programme
        programmes = sorted(programmes_by_url.values(), key=lambda item: item.id)
        if len(programmes) < self.minimum_expected_programmes:
            raise ValueError(
                "TUM official master catalogue only contained "
                f"{len(programmes)} master's programmes; expected at least "
                f"{self.minimum_expected_programmes}"
            )

        def parse_one(
            programme: DiscoveredProgramme,
        ) -> tuple[DiscoveredProgramme, bool]:
            try:
                return (
                    _parse_detail(
                        programme,
                        fetcher(programme.source_url),
                        reference_date=self.reference_date,
                    ),
                    True,
                )
            except Exception as exc:
                return (
                    replace(
                        programme,
                        deadline_text=(
                            "Official TUM programme page could not be checked during "
                            f"discovery: {type(exc).__name__}: {str(exc)[:180]}"
                        ),
                        retrieval_method="official-tum-catalogue-detail-fetch-error",
                    ),
                    False,
                )

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.detail_workers
        ) as executor:
            parsed = list(executor.map(parse_one, programmes))
        successful_details = sum(success for _, success in parsed)
        minimum_successes = math.ceil(
            len(programmes) * self.minimum_detail_success_ratio
        )
        if successful_details < minimum_successes:
            raise ValueError(
                "TUM detail-page discovery only checked "
                f"{successful_details} of {len(programmes)} programmes; "
                f"expected at least {minimum_successes}"
            )
        summer_window_programmes = sum(
            any(
                (window.intake or "").lower().startswith("summer semester")
                for window in programme.windows
            )
            for programme, _success in parsed
        )
        if summer_window_programmes < self.minimum_expected_summer_windows:
            raise ValueError(
                "TUM official detail pages only produced "
                f"{summer_window_programmes} summer-window programmes; expected "
                f"at least {self.minimum_expected_summer_windows}"
            )
        return DiscoveredCatalog(
            application_opens_at=None,
            programmes=[programme for programme, _ in parsed],
        )


def catalog_page_url(page: int) -> str:
    return (
        "https://www.tum.de/en/studies/degree-programs?"
        f"tx_solr%5Bpage%5D={page}&tx_solr%5Bq%5D=&graduation=Master"
    )


def _page_count(html: str) -> int:
    soup = BeautifulSoup(html, "html.parser")
    pages = [1]
    for link in soup.select('nav[aria-label="pagebrowser"] a[href]'):
        match = re.search(r"tx_solr%5Bpage%5D=(\d+)", str(link.get("href", "")))
        if match:
            pages.append(int(match.group(1)))
    return max(pages)


def _catalogue_programmes(html: str) -> list[DiscoveredProgramme]:
    soup = BeautifulSoup(html, "html.parser")
    programmes = []
    for article in soup.select("#studycourselist-174899 article.list-teaser"):
        heading = article.select_one("h3")
        degree = article.select_one(".roofline")
        link = article.select_one('a[href*="/en/studies/degree-programs/detail/"]')
        if heading is None or degree is None or link is None:
            continue
        name = _normalise(heading.get_text(" ", strip=True))
        degree_label = _normalise(degree.get_text(" ", strip=True))
        degree_type = DEGREE_TYPES.get(degree_label)
        source_url = _programme_url(str(link.get("href", "")))
        if not name or degree_type is None or source_url is None:
            continue
        url_slug = urlparse(source_url).path.rstrip("/").split("/")[-1]
        programme_id = f"tum-{_slug(url_slug)}"
        if url_slug == "informatics-master-of-science-msc":
            programme_id = EXISTING_INFORMATICS_ID
        programmes.append(
            DiscoveredProgramme(
                id=programme_id,
                name=f"{degree_type} {name}",
                degree_type=degree_type,
                faculty="Technical University of Munich",
                department="",
                source_url=source_url,
                application_url=APPLICATION_URL,
                windows=[],
                deadline_text=(
                    "Programme found in TUM's official filtered master catalogue; "
                    "the official detail page has not yet been checked."
                ),
                parse_status="no-deadline",
                retrieval_method="official-tum-master-catalogue-and-detail-page",
                evidence_quality="official-full-text",
            )
        )
    return programmes


def _parse_detail(
    programme: DiscoveredProgramme,
    html: str,
    *,
    reference_date: date,
) -> DiscoveredProgramme:
    soup = BeautifulSoup(html, "html.parser")
    course = _course_json_ld(soup)
    deadline = _normalise(course.get("applicationDeadline", ""))
    application_url = _application_url(course) or APPLICATION_URL
    faculty_link = soup.select_one(
        ".flex__lg-3 .in2studyfinder.no-js .ce-textmedia--aside h2 a[href]"
    )
    faculty = (
        _normalise(faculty_link.get_text(" ", strip=True))
        if faculty_link is not None
        else programme.faculty
    )
    start_of_degree = _detail_value(soup, "Start of Degree Program")
    exact_windows = _exact_windows(deadline, programme.source_url)
    recurring_windows = _recurring_windows(
        programme,
        deadline,
        start_of_degree,
        programme.source_url,
        reference_date,
    )
    windows = exact_windows + recurring_windows
    if recurring_windows:
        materialized = ", ".join(
            f"{window.intake}: {window.opens_at} to {window.closes_at}"
            for window in recurring_windows
        )
        deadline_text = (
            f"Official TUM recurring application period: {deadline} "
            f"Start of Degree Program: {start_of_degree or 'not stated'}. "
            "The next cycle was deterministically materialized for monitoring: "
            f"{materialized}. The cycle year is not written literally on the page."
        )
        parse_status = "recurring-policy"
    elif exact_windows:
        deadline_text = deadline
        parse_status = "parsed"
    elif deadline:
        deadline_text = (
            f"Official TUM application period: {deadline} The page does not "
            "publish a cycle year with both exact dates, so no application "
            "window is inferred."
        )
        parse_status = "no-deadline"
    else:
        deadline_text = (
            "The current official TUM programme page does not publish an "
            "application period."
        )
        parse_status = "no-deadline"
    return replace(
        programme,
        faculty=faculty,
        application_url=application_url,
        windows=windows,
        deadline_text=deadline_text,
        parse_status=parse_status,
    )


def _detail_value(soup: BeautifulSoup, label: str) -> str:
    wanted = _normalise(label).casefold()
    for heading in soup.find_all(["strong", "dt", "h2", "h3"]):
        if _normalise(heading.get_text(" ", strip=True)).casefold() != wanted:
            continue
        container = heading.parent
        if container is None:
            continue
        text = _normalise(container.get_text(" ", strip=True))
        if text.casefold().startswith(wanted):
            return text[len(label) :].strip(" :")
        return text
    return ""


def _course_json_ld(soup: BeautifulSoup) -> dict:
    for script in soup.select('script[type="application/ld+json"]'):
        raw = script.string or script.get_text()
        if not raw.strip():
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        payloads = payload if isinstance(payload, list) else [payload]
        for item in payloads:
            if not isinstance(item, dict):
                continue
            types = item.get("@type", [])
            if isinstance(types, str):
                types = [types]
            if "Course" in types:
                return item
    raise ValueError("official TUM detail page did not contain Course JSON-LD")


def _application_url(course: dict) -> str | None:
    action = course.get("potentialAction")
    if not isinstance(action, dict):
        return None
    target = action.get("target")
    if not isinstance(target, dict):
        return None
    value = str(target.get("urlTemplate", ""))
    parsed = urlparse(value)
    if parsed.scheme == "https" and (
        parsed.hostname == "www.tum.de" or parsed.hostname == "tum.de"
    ):
        return value
    return None


def _exact_windows(deadline: str, source_url: str) -> list[DiscoveredWindow]:
    windows = []
    for match in _EXACT_WINDOW_RE.finditer(deadline):
        windows.append(
            DiscoveredWindow(
                round="Application period",
                opens_at=_iso_date(match.group("opens")),
                closes_at=_iso_date(match.group("closes")),
                intake=_normalise(match.group("intake")),
                source_url=source_url,
            )
        )
    return windows


def _recurring_windows(
    programme: DiscoveredProgramme,
    deadline: str,
    start_of_degree: str,
    source_url: str,
    reference_date: date,
) -> list[DiscoveredWindow]:
    if programme.degree_type not in REGULAR_DEGREE_TYPES:
        return []
    if "executive" in programme.name.casefold():
        return []

    eligible_terms = _eligible_terms(start_of_degree)
    windows = []
    for match in _RECURRING_WINDOW_RE.finditer(deadline):
        term = match.group("intake").title()
        if term.casefold() not in eligible_terms:
            continue
        opens_at, closes_at, intake = _materialize_recurring_period(
            term,
            match.group("opens"),
            match.group("closes"),
            reference_date,
        )
        windows.append(
            DiscoveredWindow(
                round="Recurring application period",
                opens_at=opens_at,
                closes_at=closes_at,
                intake=intake,
                source_url=source_url,
                opens_at_basis=RECURRING_WINDOW_BASIS,
            )
        )
    return windows


def _eligible_terms(start_of_degree: str) -> set[str]:
    value = start_of_degree.casefold()
    terms = set()
    if "both winter and summer" in value:
        return {"winter", "summer"}
    if "winter semester" in value:
        terms.add("winter")
    if "summer semester" in value:
        terms.add("summer")
    return terms


def _materialize_recurring_period(
    term: str,
    opens_text: str,
    closes_text: str,
    reference_date: date,
) -> tuple[str, str, str]:
    opens_month, opens_day = _month_day(opens_text)
    closes_month, closes_day = _month_day(closes_text)
    for opens_year in range(reference_date.year - 1, reference_date.year + 3):
        opens_at = date(opens_year, opens_month, opens_day)
        closes_year = opens_year + (
            (closes_month, closes_day) < (opens_month, opens_day)
        )
        closes_at = date(closes_year, closes_month, closes_day)
        if closes_at < reference_date:
            continue
        if term.casefold() == "summer":
            intake_year = opens_year + 1
            intake = f"Summer semester {intake_year}"
        else:
            intake_year = closes_year
            intake = f"Winter semester {intake_year}/{str(intake_year + 1)[-2:]}"
        return opens_at.isoformat(), closes_at.isoformat(), intake
    raise ValueError("could not materialize the next recurring TUM application period")


def _month_day(value: str) -> tuple[int, int]:
    parsed = datetime.strptime(value.rstrip("."), "%d.%m")
    return parsed.month, parsed.day


def _programme_url(value: str) -> str | None:
    absolute, _fragment = urldefrag(urljoin("https://www.tum.de", value))
    parsed = urlparse(absolute)
    if parsed.hostname not in {"www.tum.de", "tum.de"}:
        return None
    if not parsed.path.startswith("/en/studies/degree-programs/detail/"):
        return None
    return absolute.rstrip("/")


def _iso_date(value: str) -> str:
    return datetime.strptime(value, "%d.%m.%Y").date().isoformat()


def _slug(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore")
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.decode().lower()).strip("-")


def _normalise(value: object) -> str:
    decoded = html_module.unescape(str(value or "")).replace("\xa0", " ")
    return re.sub(r"\s+", " ", decoded).strip()
