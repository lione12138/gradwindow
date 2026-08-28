from __future__ import annotations

import concurrent.futures
import json
import math
import re
import unicodedata
from collections.abc import Callable, Iterable
from dataclasses import replace
from datetime import datetime
from urllib.parse import urlencode, urljoin, urlsplit

from bs4 import BeautifulSoup

from .base import (
    BaseProgrammeAdapter,
    DiscoveredCatalog,
    DiscoveredProgramme,
    DiscoveredWindow,
)

UNIVERSITY_ID = "university-of-oxford"
CATALOG_URL = "https://www.ox.ac.uk/admissions/graduate/courses/find-your-course"
LISTING_API_ROOT = "https://www.ox.ac.uk/api/listing"
APPLICATION_URL = (
    "https://www.ox.ac.uk/admissions/graduate/application-guide/"
    "starting-your-application/your-application-account"
)
DEFAULT_INTAKE = "2027-28"
COURSE_PATH_RE = re.compile(
    r"^/admissions/graduate/courses/(?P<slug>[a-z0-9][a-z0-9-]+?)/?$",
    flags=re.IGNORECASE,
)
MASTER_DEGREE_RE = re.compile(
    r"\b(?P<degree>BPhil|MPhil|MSc|MSt|MBA|EMBA|MPP|MFA|MTh|BCL|MJur|MCL|"
    r"MFin|LLM|MPH|MEd|MMus|MRes|MLitt)\b",
    flags=re.IGNORECASE,
)
RESEARCH_MASTER_RE = re.compile(
    r"\b(?:MSc|MPhil|MRes).{0,100}\bby\s+Research\b",
    flags=re.IGNORECASE,
)
OXFORD_RESEARCH_MPHIL_TITLES = {"law", "socio-legal research"}
SEPARATE_PROCESS_DEGREES = {"MBA", "EMBA"}
EXCLUDED_COURSE_SLUGS = {
    "changes-to-courses",
    "courses-a-z-listing",
    "departments",
    "find-your-course",
    "open-courses",
    "research-courses",
    "taught-courses",
    "ucas-listings",
}
MODE_STATUS_RE = re.compile(
    r"^(?P<mode>Full[ -]time|Part[ -]time)\s*:\s*(?P<status>.+)$",
    flags=re.IGNORECASE,
)
DATE_RE = re.compile(
    r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)?\s*"
    r"(?P<day>\d{1,2})\s+"
    r"(?P<month>January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+"
    r"(?P<year>20\d{2})\b",
    flags=re.IGNORECASE,
)
US_DATE_RE = re.compile(
    r"\b(?P<month>January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+"
    r"(?P<day>\d{1,2}),\s+(?P<year>20\d{2})\b",
    flags=re.IGNORECASE,
)
EXPECTED_START_RE = re.compile(
    r"Expected\s+start\s+date\s+"
    r"(?P<month>January|February|March|April|May|June|July|August|"
    r"September|October|November|December)\s+(?P<year>20\d{2})",
    flags=re.IGNORECASE,
)
UPCOMING_CYCLE_RE = re.compile(
    r"applications\s+open\s*\(for\s+entry\s+in\s+(?P<intake>20\d{2}-\d{2})\)",
    flags=re.IGNORECASE,
)
RESULT_COUNT_RE = re.compile(r"\bof\s+(?P<count>\d[\d,]*)\s+Results\b", re.I)
DEADLINE_SIGNAL_RE = re.compile(
    r"application\s+deadlines?|applications?\s+(?:close|must be submitted)|"
    r"(?:final\s+)?deadline\s+(?:is|will be)",
    re.I,
)


class OxfordAdapter(BaseProgrammeAdapter):
    university_id = UNIVERSITY_ID
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = DEFAULT_INTAKE
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL,)
    catalogue_granularity = "programme-mode-level"

    # Oxford blocks the normal GitHub-runner transport. The current course finder
    # needs one rendered page plus up to 33 lightweight official listing API pages.
    # Keep the larger budget local to Oxford instead of weakening the global limit.
    browser_fallback_limit = 200
    browser_wait_for_selectors = {
        CATALOG_URL: (
            '[data-js-filter-listing] article[filter-listing-type="listing_course_graduate"]'
        )
    }

    def __init__(
        self,
        minimum_expected_programmes: int = 125,
        detail_workers: int = 6,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.detail_workers = detail_workers

    def parse_catalog_from_fetcher(
        self,
        fetcher: Callable[[str], str],
    ) -> DiscoveredCatalog:
        first_html = fetcher(self.catalog_url)
        soup = BeautifulSoup(first_html, "html.parser")
        listing_id, items_per_page, sorts = _listing_settings(soup)
        total_results = _result_count(soup)

        programmes = self._parse_programmes(first_html)
        page_count = math.ceil(total_results / items_per_page)
        for page in range(1, page_count):
            api_url = _listing_api_url(listing_id, page=page, sorts=sorts)
            programmes.extend(self._parse_api_programmes(fetcher(api_url)))

        programmes = self._unique_programmes(programmes)
        self._validate_catalog_size(programmes)
        programmes = self._parse_open_details(programmes, fetcher)
        return DiscoveredCatalog(
            application_opens_at=None,
            programmes=programmes,
            diagnostics={
                "source": "official-course-finder-api",
                "listingId": listing_id,
                "listingResultCount": total_results,
                "listingPageCount": page_count,
            },
        )

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        programmes = self._unique_programmes(self._parse_programmes(html))
        self._validate_catalog_size(programmes)
        return DiscoveredCatalog(application_opens_at=None, programmes=programmes)

    def _parse_api_programmes(self, payload_text: str) -> list[DiscoveredProgramme]:
        payload = _json_payload(payload_text)
        programmes = []
        for fragment in _json_strings(payload):
            if "/admissions/graduate/courses/" not in fragment:
                continue
            programmes.extend(self._parse_programmes(fragment))
        return programmes

    def _parse_programmes(self, html: str) -> list[DiscoveredProgramme]:
        soup = BeautifulSoup(html, "html.parser")
        containers = soup.select(
            'article[filter-listing-type="listing_course_graduate"], '
            "section#courses-offered li"
        )
        if not containers:
            containers = soup.find_all("article")

        programmes = []
        for container in containers:
            programmes.extend(self._parse_course_container(container))
        return programmes

    def _parse_course_container(self, container) -> list[DiscoveredProgramme]:
        link = next(
            (
                link
                for link in container.find_all("a", href=True)
                if _course_url(link.get("href", "")) is not None
            ),
            None,
        )
        if link is None:
            return []

        source_url = _course_url(link.get("href", ""))
        title = _normalise_text(link.get_text(" ", strip=True))
        if source_url is None or not title:
            return []

        context = _normalise_text(container.get_text(" ", strip=True))
        degree_match = MASTER_DEGREE_RE.search(title)
        if degree_match is None:
            degree_match = MASTER_DEGREE_RE.search(context)
        if (
            degree_match is None
            or RESEARCH_MASTER_RE.search(title)
            or re.search(r"\bDPhil\b", title, re.I)
        ):
            return []

        degree_type = _canonical_degree(degree_match.group("degree"))
        base_title = _base_title(title, degree_type)
        if degree_type in SEPARATE_PROCESS_DEGREES or (
            degree_type == "MPhil"
            and base_title.casefold() in OXFORD_RESEARCH_MPHIL_TITLES
        ):
            return []

        modes = _study_modes(container)
        if base_title.casefold() != "law and finance" and all(
            _separate_process_status(status) for _, status in modes
        ):
            return []

        faculty = _course_faculty(container) or "University of Oxford"
        programmes = []
        for mode, status in modes:
            programmes.append(
                DiscoveredProgramme(
                    id=_programme_id(base_title, degree_type, mode),
                    name=f"{_programme_name(title, base_title, degree_type)} ({mode})",
                    degree_type=degree_type,
                    faculty=faculty,
                    department=mode,
                    source_url=source_url,
                    application_url=self.application_url,
                    windows=[],
                    deadline_text=(
                        f"{mode}: {status}. Programme found in Oxford's official "
                        "postgraduate course finder; no exact application deadline "
                        "was published in the listing card."
                    ),
                    parse_status="no-deadline",
                    retrieval_method="official-course-finder-api",
                    evidence_quality="official-full-text",
                )
            )
        return programmes

    def _parse_open_details(
        self,
        programmes: list[DiscoveredProgramme],
        fetcher: Callable[[str], str],
    ) -> list[DiscoveredProgramme]:
        open_urls = sorted(
            {
                programme.source_url
                for programme in programmes
                if _status_needs_detail(programme.deadline_text)
            }
        )
        if not open_urls:
            return programmes

        def fetch_one(url: str) -> tuple[str, str | Exception]:
            try:
                return url, fetcher(url)
            except Exception as exc:
                return url, exc

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.detail_workers
        ) as executor:
            details = dict(executor.map(fetch_one, open_urls))

        parsed = []
        for programme in programmes:
            detail = details.get(programme.source_url)
            if detail is None:
                parsed.append(programme)
            elif isinstance(detail, Exception):
                parsed.append(
                    replace(
                        programme,
                        deadline_text=(
                            f"{programme.deadline_text} The open course page could "
                            "not be fetched during discovery: "
                            f"{type(detail).__name__}: {str(detail)[:180]}"
                        ),
                    )
                )
            else:
                parsed.append(self._parse_detail(programme, detail))
        return parsed

    def _parse_detail(
        self,
        programme: DiscoveredProgramme,
        html: str,
    ) -> DiscoveredProgramme:
        soup = BeautifulSoup(html, "html.parser")
        h1 = soup.select_one("main h1") or soup.find("h1")
        page_name = (
            _normalise_text(h1.get_text(" ", strip=True)) if h1 is not None else ""
        )
        mode = programme.department
        mode_card = _mode_card(soup, mode)
        scope = mode_card or _application_deadline_section(soup)
        deadlines, excerpt = _application_deadlines(scope)
        intake = _intake_from_detail(
            _normalise_text(scope.get_text(" ", strip=True))
            if scope is not None
            else ""
        )
        if not deadlines:
            status = _status_excerpt(scope) if scope is not None else ""
            return replace(
                programme,
                name=_mode_name(page_name, mode) or programme.name,
                deadline_text=status or programme.deadline_text,
            )

        windows = [
            DiscoveredWindow(
                round=(
                    "Main application deadline"
                    if len(deadlines) == 1
                    else f"Application deadline {index}"
                ),
                opens_at=None,
                closes_at=deadline,
                intake=intake,
                source_url=programme.source_url,
                opens_at_basis="missing",
            )
            for index, deadline in enumerate(deadlines, start=1)
        ]
        return replace(
            programme,
            name=_mode_name(page_name, mode) or programme.name,
            windows=windows,
            deadline_text=excerpt,
            parse_status="incomplete",
        )

    @staticmethod
    def _unique_programmes(
        programmes: list[DiscoveredProgramme],
    ) -> list[DiscoveredProgramme]:
        return sorted(
            {programme.id: programme for programme in programmes}.values(),
            key=lambda item: item.id,
        )

    def _validate_catalog_size(
        self,
        programmes: list[DiscoveredProgramme],
    ) -> None:
        unique_programme_count = len({programme.source_url for programme in programmes})
        if unique_programme_count < self.minimum_expected_programmes:
            raise ValueError(
                "Oxford's current postgraduate course finder only contained "
                f"{unique_programme_count} unique taught master's programmes "
                f"({len(programmes)} programme-mode records); expected at least "
                f"{self.minimum_expected_programmes}. The rendered response may be "
                "blocked or listing API pagination may be incomplete."
            )


def _listing_settings(soup: BeautifulSoup) -> tuple[str, int, list[dict]]:
    listing = soup.select_one("[data-js-filter-listing-id]")
    listing_id = listing.get("data-js-filter-listing-id", "") if listing else ""
    for script in soup.find_all("script"):
        text = script.string or script.get_text()
        if not text or '"listing"' not in text:
            continue
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            continue
        listings = payload.get("listing", {})
        if not isinstance(listings, dict):
            continue
        config = listings.get(listing_id) if listing_id else None
        if not isinstance(config, dict) and len(listings) == 1:
            listing_id, config = next(iter(listings.items()))
        if not listing_id or not isinstance(config, dict):
            continue
        items_per_page = int(config.get("items_per_page", 12))
        if items_per_page <= 0:
            raise ValueError("Oxford course finder published an invalid page size")
        sorts = config.get("default_sorts", [])
        return str(listing_id), items_per_page, sorts if isinstance(sorts, list) else []
    raise ValueError("Oxford course finder listing configuration was not found")


def _result_count(soup: BeautifulSoup) -> int:
    text = _normalise_text(soup.get_text(" ", strip=True))
    match = RESULT_COUNT_RE.search(text)
    if match is None:
        raise ValueError("Oxford course finder did not render its result count")
    return int(match.group("count").replace(",", ""))


def _listing_api_url(listing_id: str, *, page: int, sorts: list[dict]) -> str:
    params: list[tuple[str, str]] = [("page", str(page))]
    for sort in sorts:
        key = str(sort.get("search_key", "")).strip()
        if not key:
            continue
        params.extend(
            (
                (f"sort[{key}][path]", key),
                (f"sort[{key}][direction]", str(sort.get("direction", "asc"))),
            )
        )
    return f"{LISTING_API_ROOT}/{listing_id}?{urlencode(params)}"


def _json_payload(payload_text: str):
    stripped = payload_text.strip()
    if stripped.startswith("{") or stripped.startswith("["):
        return json.loads(stripped)
    soup = BeautifulSoup(payload_text, "html.parser")
    pre = soup.find("pre")
    if pre is None:
        raise ValueError("Oxford listing API did not return JSON")
    return json.loads(pre.get_text())


def _json_strings(value) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _json_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _json_strings(item)


def _course_url(href: str) -> str | None:
    absolute = urljoin(CATALOG_URL, href)
    parts = urlsplit(absolute)
    if parts.hostname not in {"ox.ac.uk", "www.ox.ac.uk"}:
        return None
    match = COURSE_PATH_RE.match(parts.path.rstrip("/"))
    if match is None or match.group("slug").casefold() in EXCLUDED_COURSE_SLUGS:
        return None
    return f"https://www.ox.ac.uk{parts.path.rstrip('/')}"


def _study_modes(container) -> list[tuple[str, str]]:
    modes: dict[str, str] = {}
    for tag in container.select('[data-component-id="numiko:tag"]'):
        text = _normalise_text(tag.get_text(" ", strip=True))
        match = MODE_STATUS_RE.match(text)
        if match:
            mode = _canonical_mode(match.group("mode"))
            modes[mode] = _normalise_text(match.group("status"))
    if modes:
        return list(modes.items())

    text = _normalise_text(container.get_text(" ", strip=True))
    for match in re.finditer(r"\((Full[ -]time|Part[ -]time)\)", text, re.I):
        mode = _canonical_mode(match.group(1))
        modes[mode] = "Status not published"
    return list(modes.items()) or [("Unspecified mode", "Status not published")]


def _canonical_mode(value: str) -> str:
    return "Part time" if value.casefold().startswith("part") else "Full time"


def _course_faculty(container) -> str:
    for selector in (
        ".course-department",
        ".department",
        '[class*="department"]',
        "[data-department]",
    ):
        field = container.select_one(selector)
        if field is not None:
            value = _normalise_text(field.get_text(" ", strip=True))
            if value:
                return value
    return ""


def _status_needs_detail(deadline_text: str) -> bool:
    status = deadline_text.split(". Programme found", 1)[0].casefold()
    return not any(
        marker in status
        for marker in (
            "closed",
            "not open",
            "apply directly",
            "apply via gov.uk",
            "status not published",
        )
    )


def _separate_process_status(status: str) -> bool:
    lowered = status.casefold()
    return "apply directly" in lowered or "separate process" in lowered


def _mode_card(soup: BeautifulSoup, mode: str):
    for heading in soup.find_all(["h2", "h3"]):
        if (
            _normalise_text(heading.get_text(" ", strip=True)).casefold()
            != mode.casefold()
        ):
            continue
        node = heading.parent
        for _ in range(6):
            if node is None:
                break
            headings = node.find_all(["h2", "h3"])
            text = _normalise_text(node.get_text(" ", strip=True))
            if len(headings) == 1 and "Expected start date" in text:
                return node
            node = node.parent
    return None


def _application_deadline_section(soup: BeautifulSoup):
    for heading in soup.find_all(["h2", "h3", "h4"]):
        if re.fullmatch(
            r"Application deadlines?",
            _normalise_text(heading.get_text(" ", strip=True)),
            re.I,
        ):
            return heading.find_parent("section") or heading.parent
    return None


def _application_deadlines(scope) -> tuple[list[str], str]:
    if scope is None:
        return [], ""
    fragments = []
    for node in scope.find_all(["p", "li"]):
        text = _normalise_text(node.get_text(" ", strip=True))
        if DEADLINE_SIGNAL_RE.search(text):
            fragments.append(text)
    if not fragments:
        text = _normalise_text(scope.get_text(" ", strip=True))
        if DEADLINE_SIGNAL_RE.search(text):
            fragments.append(text)

    dates = []
    for fragment in fragments:
        dates.extend(_date_from_match(match) for match in DATE_RE.finditer(fragment))
        dates.extend(_date_from_match(match) for match in US_DATE_RE.finditer(fragment))
    return sorted(set(dates)), _normalise_text(" ".join(fragments))[:1800]


def _date_from_match(match: re.Match[str]) -> str:
    value = f"{match.group('day')} {match.group('month')} {match.group('year')}"
    return datetime.strptime(value, "%d %B %Y").date().isoformat()


def _intake_from_detail(text: str) -> str:
    match = EXPECTED_START_RE.search(text)
    if match:
        return f"{match.group('month').title()} {match.group('year')}"
    upcoming = UPCOMING_CYCLE_RE.search(text)
    if upcoming:
        return upcoming.group("intake")
    return DEFAULT_INTAKE


def _status_excerpt(scope) -> str:
    text = _normalise_text(scope.get_text(" ", strip=True))
    status_markers = (
        "Closed to applications",
        "Applications are still open",
        "Register to receive an email",
    )
    positions = [text.find(marker) for marker in status_markers if marker in text]
    if not positions:
        return ""
    return text[min(positions) : min(positions) + 600]


def _canonical_degree(value: str) -> str:
    canonical = {
        "bphil": "BPhil",
        "emba": "EMBA",
        "mba": "MBA",
        "bcl": "BCL",
        "mjur": "MJur",
    }
    return canonical.get(value.casefold(), value[0].upper() + value[1:])


def _base_title(title: str, degree_type: str) -> str:
    value = _normalise_text(title)
    patterns = (
        rf"^{re.escape(degree_type)}\s+in\s+",
        rf",\s*{re.escape(degree_type)}$",
        rf"\s+{re.escape(degree_type)}$",
    )
    for pattern in patterns:
        stripped = re.sub(pattern, "", value, flags=re.I).strip(" ,-()")
        if stripped != value:
            return stripped
    return value


def _programme_name(title: str, base_title: str, degree_type: str) -> str:
    if re.match(rf"^{re.escape(degree_type)}\s+in\b", title, re.I):
        return title
    if re.search(rf",\s*{re.escape(degree_type)}$", title, re.I):
        return f"{degree_type} in {base_title}"
    return title if MASTER_DEGREE_RE.search(title) else f"{degree_type} in {base_title}"


def _mode_name(page_name: str, mode: str) -> str:
    if not page_name:
        return ""
    return f"{page_name} ({mode})"


def _programme_id(title: str, degree_type: str, mode: str) -> str:
    return f"oxford-{_slug(title)}-{_slug(degree_type)}-{_slug(mode)}"


def _slug(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    )
    return re.sub("-+", "-", re.sub("[^a-z0-9]+", "-", ascii_value.lower())).strip("-")


def _normalise_text(value: str) -> str:
    return " ".join(str(value).replace("\u00a0", " ").split())
