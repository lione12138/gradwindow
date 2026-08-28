from __future__ import annotations

import concurrent.futures
import hashlib
import random
import re
import threading
import time
import unicodedata
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime
from urllib.parse import urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup

from .base import (
    BaseProgrammeAdapter,
    DiscoveredCatalog,
    DiscoveredProgramme,
    DiscoveredWindow,
    OfficialSourceTransportError,
)

UNIVERSITY_ID = "university-of-edinburgh"
CATALOG_URL = "https://study.ed.ac.uk/programmes/postgraduate-taught-a-z"
APPLICATION_GUIDANCE_URL = "https://study.ed.ac.uk/postgraduate/applying/when"
DEFAULT_INTAKE = "September 2026"
COURSE_PATH_RE = re.compile(
    r"^/programmes/postgraduate-taught/(?:(?P<edition>20\d{2})/)?"
    r"(?P<code>\d+)-(?P<slug>[^/]+)/?$",
    re.I,
)
DEGREE_RE = re.compile(
    r"\b(?P<degree>MScR|MVetSci|MCouns|MArch|MMus|MFA|MRes|MPhil|MLitt|"
    r"LLM|MBA|MPH|MEd|MFin|MPA|MPP|MSW|MSc|MA|MS|Master)\b",
    re.I,
)
FULL_DATE_TEXT = (
    r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)?\s*"
    r"\d{1,2}(?:st|nd|rd|th)?\s+[A-Z][a-z]+\s+20\d{2}"
)
EXPLICIT_OPEN_RE = re.compile(
    rf"applications?(?:\s+for[^.\n]{{0,80}}?)?\s+"
    rf"(?:will\s+)?open(?:ed)?\s+on\s+(?P<date>{FULL_DATE_TEXT})",
    re.I,
)
EXTENDED_DEADLINE_RE = re.compile(
    rf"(?:application\s+deadline|[‘'\"]?apply\s+by[’'\"]?\s+deadline|"
    rf"round\s+\d+[^.\n]{{0,50}}?application\s+deadline)"
    rf"[^.\n]{{0,80}}?extended\s+to\s+(?P<date>{FULL_DATE_TEXT})",
    re.I,
)
REMAIN_OPEN_RE = re.compile(
    rf"applications?[^.\n]{{0,100}}?remain\s+open[^.\n]{{0,80}}?"
    rf"until\s+(?P<date>{FULL_DATE_TEXT})",
    re.I,
)
START_DATE_RE = re.compile(r"Start date:\s*(?P<month>[A-Z][a-z]+)\s+(?P<year>20\d{2})")
ENTRY_YEAR_RE = re.compile(r"Year of entry:\s*(?P<year>20\d{2})", re.I)


class EdinburghAdapter(BaseProgrammeAdapter):
    university_id = UNIVERSITY_ID
    catalog_url = CATALOG_URL
    application_url = APPLICATION_GUIDANCE_URL
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    intake = DEFAULT_INTAKE
    browser_fallback_limit = 6

    def __init__(
        self,
        minimum_expected_programmes: int = 250,
        detail_workers: int = 2,
        detail_refresh_budget: int = 24,
        detail_interval_seconds: float = 0.8,
        detail_jitter_seconds: float = 0.7,
        maximum_detail_failure_ratio: float = 0.2,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.detail_workers = detail_workers
        self.detail_refresh_budget = detail_refresh_budget
        self.detail_interval_seconds = detail_interval_seconds
        self.detail_jitter_seconds = detail_jitter_seconds
        self.maximum_detail_failure_ratio = maximum_detail_failure_ratio
        self._previous_cache: dict[str, dict] = {}
        self.catalogue_status = "ok"

    def prepare_discovery(self, previous_state: dict) -> None:
        adapter_state = previous_state.get("adapterState", {})
        cache = adapter_state.get("detailCache", {})
        self._previous_cache = cache if isinstance(cache, dict) else {}

    def parse_catalog_from_fetcher(
        self,
        fetcher: Callable[[str], str],
    ) -> DiscoveredCatalog:
        programmes = {
            programme.id: programme
            for programme in _catalogue_programmes(fetcher(CATALOG_URL))
        }
        catalogue = sorted(programmes.values(), key=lambda item: item.id)
        if len(catalogue) < self.minimum_expected_programmes:
            raise ValueError(
                "University of Edinburgh catalogue only contained "
                f"{len(catalogue)} master's programmes; expected at least "
                f"{self.minimum_expected_programmes} from the official A-Z list"
            )

        cached_programmes = {}
        uncached = []
        for programme in catalogue:
            cached = self._previous_cache.get(programme.source_url)
            if isinstance(cached, dict) and isinstance(cached.get("detail"), dict):
                cached_programmes[programme.source_url] = _merge_cached_detail(
                    programme, cached["detail"]
                )
            else:
                uncached.append(programme)
        refreshable = sorted(
            (
                programme
                for programme in catalogue
                if programme.source_url in cached_programmes
            ),
            key=lambda item: (
                self._previous_cache[item.source_url].get("fetchedAt", ""),
                item.source_url,
            ),
        )[: self.detail_refresh_budget]
        to_fetch = [*uncached, *refreshable]
        pacer = _RequestPacer(
            interval_seconds=self.detail_interval_seconds,
            jitter_seconds=self.detail_jitter_seconds,
        )

        def parse_one(
            programme: DiscoveredProgramme,
        ) -> tuple[DiscoveredProgramme, Exception | None]:
            try:
                pacer.wait()
                return _parse_detail(programme, fetcher(programme.source_url)), None
            except Exception as exc:
                fallback = cached_programmes.get(programme.source_url, programme)
                return fallback, exc

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.detail_workers
        ) as executor:
            results = list(executor.map(parse_one, to_fetch))
        fetched = {
            programme.source_url: programme
            for programme, error in results
            if error is None
        }
        failures = [error for _programme, error in results if error is not None]
        failure_ratio = len(failures) / len(to_fetch) if to_fetch else 0.0
        if failure_ratio > self.maximum_detail_failure_ratio:
            raise OfficialSourceTransportError(
                "University of Edinburgh detail refresh failed for "
                f"{len(failures)} of {len(to_fetch)} programme pages "
                f"({failure_ratio:.1%}); previous exact windows were preserved"
            )
        warnings = _detail_failure_warnings(len(failures), len(to_fetch))
        if failure_ratio >= 0.05:
            self.catalogue_status = "degraded"

        fetched_at = datetime.now().astimezone().isoformat()
        detailed = []
        detail_cache = {}
        for programme in catalogue:
            detail = fetched.get(
                programme.source_url,
                cached_programmes.get(programme.source_url, programme),
            )
            detailed.append(detail)
            previous = self._previous_cache.get(programme.source_url, {})
            detail_cache[programme.source_url] = {
                "fetchedAt": (
                    fetched_at
                    if programme.source_url in fetched
                    else previous.get("fetchedAt", "")
                ),
                "detail": _programme_to_cache(detail),
            }
        return DiscoveredCatalog(
            application_opens_at=None,
            programmes=detailed,
            warnings=warnings,
            diagnostics={
                "catalogueRequests": 1,
                "detailPagesFetched": len(fetched),
                "detailCacheHits": len(catalogue) - len(uncached),
                "detailFailures": len(failures),
                "detailFailureRatio": round(failure_ratio, 4),
            },
            adapter_state={"detailCache": detail_cache},
        )


def _catalogue_programmes(html: str) -> list[DiscoveredProgramme]:
    soup = BeautifulSoup(html, "html.parser")
    programmes = []
    for link in soup.select(
        "div.result h3 a[href], h3.field-content a[href*='/programmes/postgraduate-taught/']"
    ):
        title = _normalise(link.get_text(" ", strip=True))
        source_url = _course_url(link.get("href", ""))
        split = _split_title(title)
        if source_url is None or split is None:
            continue
        base_title, degree_type = split
        if (
            "online-learning" in urlsplit(source_url).path.lower()
            and "online learning" not in base_title.lower()
        ):
            base_title = f"{base_title} (Online Learning)"
        programmes.append(
            DiscoveredProgramme(
                id=f"edinburgh-{_slug(base_title)}-{_slug(degree_type)}",
                name=f"{degree_type} {base_title}",
                degree_type=degree_type,
                faculty="",
                department="",
                source_url=source_url,
                application_url=source_url,
                windows=[],
                deadline_text=(
                    "Programme found in the official University of Edinburgh "
                    "postgraduate taught Degree Finder."
                ),
                parse_status="no-deadline",
                retrieval_method="official-page",
                evidence_quality="official-full-text",
            )
        )
    return programmes


class _RequestPacer:
    def __init__(self, *, interval_seconds: float, jitter_seconds: float) -> None:
        self.interval_seconds = max(0.0, interval_seconds)
        self.jitter_seconds = max(0.0, jitter_seconds)
        self._lock = threading.Lock()
        self._next_request_at = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            request_at = max(now, self._next_request_at)
            self._next_request_at = (
                request_at
                + self.interval_seconds
                + random.uniform(0.0, self.jitter_seconds)
            )
        delay = request_at - now
        if delay > 0:
            time.sleep(delay)


def _detail_failure_warnings(failures: int, attempted: int) -> list[dict[str, object]]:
    if failures == 0 or attempted == 0:
        return []
    ratio = failures / attempted
    return [
        {
            "code": (
                "DETAIL_REFRESH_DEGRADED" if ratio >= 0.05 else "DETAIL_REFRESH_PARTIAL"
            ),
            "message": (
                f"{failures} of {attempted} Edinburgh programme detail pages "
                "failed; cached evidence was retained where available."
            ),
            "failureCount": failures,
            "attemptedCount": attempted,
            "failureRatio": round(ratio, 4),
        }
    ]


def _programme_to_cache(programme: DiscoveredProgramme) -> dict:
    return {
        "faculty": programme.faculty,
        "department": programme.department,
        "deadlineText": programme.deadline_text,
        "parseStatus": programme.parse_status,
        "retrievalMethod": programme.retrieval_method,
        "evidenceQuality": programme.evidence_quality,
        "evidenceDocumentHash": programme.evidence_document_hash,
        "windows": [
            {
                "round": window.round,
                "opensAt": window.opens_at,
                "closesAt": window.closes_at,
                "applicantCategories": window.applicant_categories,
                "intake": window.intake,
                "sourceUrl": window.source_url,
                "opensAtBasis": window.opens_at_basis,
                "deadlineSemantics": window.deadline_semantics,
            }
            for window in programme.windows
        ],
    }


def _merge_cached_detail(
    programme: DiscoveredProgramme, cached: dict
) -> DiscoveredProgramme:
    return replace(
        programme,
        faculty=cached.get("faculty", ""),
        department=cached.get("department", ""),
        deadline_text=cached.get("deadlineText", programme.deadline_text),
        parse_status=cached.get("parseStatus", programme.parse_status),
        retrieval_method=cached.get("retrievalMethod"),
        evidence_quality=cached.get("evidenceQuality"),
        evidence_document_hash=cached.get("evidenceDocumentHash"),
        windows=[
            DiscoveredWindow(
                round=window["round"],
                opens_at=window.get("opensAt"),
                closes_at=window["closesAt"],
                applicant_categories=window.get("applicantCategories", ["all"]),
                intake=window.get("intake"),
                source_url=window.get("sourceUrl"),
                opens_at_basis=window.get("opensAtBasis"),
                deadline_semantics=window.get("deadlineSemantics", "on"),
            )
            for window in cached.get("windows", [])
        ],
    )


def _parse_detail(
    programme: DiscoveredProgramme,
    html: str,
) -> DiscoveredProgramme:
    soup = BeautifulSoup(html, "html.parser")
    school = _key_fact(soup, "School")
    college = _key_fact(soup, "College")
    default_intake, intake_date = _default_intake(soup)
    applying = soup.select_one(".pgt-programme-applying__when")
    if applying is None:
        return replace(
            programme,
            faculty=college,
            department=school,
            deadline_text=(
                "The official programme page does not contain a When to apply "
                "section with an exact application deadline."
            ),
            retrieval_method="official-html",
            evidence_document_hash=hashlib.sha256(html.encode("utf-8")).hexdigest(),
        )

    section_text = _normalise(applying.get_text(" ", strip=True))
    explicit_opening = _explicit_opening(section_text)
    windows = _table_windows(
        applying,
        default_intake=default_intake,
        default_intake_date=intake_date,
        source_url=programme.source_url,
        explicit_opening=explicit_opening,
    )
    windows.extend(
        _extension_windows(
            section_text,
            default_intake=default_intake,
            source_url=programme.source_url,
            opens_at=explicit_opening,
        )
    )
    windows = _deduplicate_windows(windows)
    return replace(
        programme,
        faculty=college,
        department=school,
        windows=windows,
        deadline_text=(
            section_text[:1800]
            if section_text
            else "No exact application deadline was found on the official page."
        ),
        parse_status=(
            "parsed"
            if windows and all(window.opens_at for window in windows)
            else "incomplete"
            if windows
            else "no-deadline"
        ),
        retrieval_method="official-html",
        evidence_document_hash=hashlib.sha256(html.encode("utf-8")).hexdigest(),
    )


def _table_windows(
    applying,
    *,
    default_intake: str,
    default_intake_date: datetime,
    source_url: str,
    explicit_opening: str | None,
) -> list[DiscoveredWindow]:
    windows = []
    for table in applying.select("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        header_cells = rows[0].find_all(["th", "td"], recursive=False)
        headers = [_normalise(cell.get_text(" ", strip=True)) for cell in header_cells]
        if not any(_deadline_header(header) for header in headers):
            continue
        data_rows = rows[1:]
        close_index = next(
            (index for index, header in enumerate(headers) if _deadline_header(header)),
            None,
        )
        open_index = next(
            (
                index
                for index, header in enumerate(headers)
                if "applications open" in header.lower()
                or "application opens" in header.lower()
            ),
            None,
        )
        start_index = next(
            (
                index
                for index, header in enumerate(headers)
                if "start date" in header.lower()
            ),
            None,
        )
        round_index = next(
            (
                index
                for index, header in enumerate(headers)
                if header.lower() in {"round", "year of entry"}
            ),
            None,
        )
        if close_index is None:
            continue

        for row in data_rows:
            values = [
                _normalise(cell.get_text(" ", strip=True))
                for cell in row.find_all(["th", "td"], recursive=False)
            ]
            if close_index >= len(values):
                continue
            intake = default_intake
            row_intake_date = default_intake_date
            if start_index is not None and start_index < len(values):
                parsed_intake = _intake_from_date(values[start_index])
                if parsed_intake is not None:
                    intake, row_intake_date = parsed_intake
            closes_at = _date(values[close_index], row_intake_date)
            if closes_at is None:
                continue
            opens_at = explicit_opening
            if open_index is not None and open_index < len(values):
                opens_at = _date(values[open_index], row_intake_date)
            round_label = "Main application deadline"
            if round_index is not None and round_index < len(values):
                value = values[round_index]
                round_label = (
                    f"{value} entry deadline"
                    if re.fullmatch(r"20\d{2}", value)
                    else f"Round {value}"
                    if value.isdigit()
                    else "Equal consideration deadline"
                    if "year of entry" in headers[round_index].lower()
                    else value
                )
            windows.append(
                DiscoveredWindow(
                    round=round_label,
                    opens_at=opens_at,
                    closes_at=closes_at,
                    intake=intake,
                    source_url=source_url,
                )
            )
    return windows


def _extension_windows(
    text: str,
    *,
    default_intake: str,
    source_url: str,
    opens_at: str | None,
) -> list[DiscoveredWindow]:
    windows = []
    for pattern in (EXTENDED_DEADLINE_RE, REMAIN_OPEN_RE):
        for match in pattern.finditer(text):
            closes_at = _date(match.group("date"), None)
            if closes_at:
                windows.append(
                    DiscoveredWindow(
                        round="Extended application deadline",
                        opens_at=opens_at,
                        closes_at=closes_at,
                        intake=default_intake,
                        source_url=source_url,
                    )
                )
    return windows


def _deduplicate_windows(windows: list[DiscoveredWindow]) -> list[DiscoveredWindow]:
    unique = {}
    for window in windows:
        key = (window.intake, window.opens_at, window.closes_at)
        previous = unique.get(key)
        if previous is None or _round_priority(window.round) > _round_priority(
            previous.round
        ):
            unique[key] = window
    return sorted(
        unique.values(),
        key=lambda item: (item.closes_at, item.round, item.intake or ""),
    )


def _round_priority(value: str) -> int:
    if value == "Extended application deadline":
        return 3
    if value.startswith("Round "):
        return 2
    return 1


def _deadline_header(value: str) -> bool:
    lower = value.lower()
    return (
        "application deadline" in lower
        or "apply by" in lower
        or "equal consideration deadline" in lower
    )


def _explicit_opening(text: str) -> str | None:
    match = EXPLICIT_OPEN_RE.search(text)
    return _date(match.group("date"), None) if match else None


def _default_intake(soup: BeautifulSoup) -> tuple[str, datetime]:
    metadata = soup.select_one(".pgt-programme-metadata__study-options")
    metadata_text = _normalise(metadata.get_text(" ", strip=True)) if metadata else ""
    match = START_DATE_RE.search(metadata_text)
    if match:
        label = f"{match.group('month')} {match.group('year')}"
        return label, datetime.strptime(label, "%B %Y")
    page_text = _normalise(soup.get_text(" ", strip=True))
    entry_match = ENTRY_YEAR_RE.search(page_text)
    year = entry_match.group("year") if entry_match else "2026"
    label = f"September {year}"
    return label, datetime.strptime(label, "%B %Y")


def _intake_from_date(value: str) -> tuple[str, datetime] | None:
    parsed = _datetime(value)
    if parsed is None:
        return None
    return parsed.strftime("%B %Y"), parsed


def _date(value: str, intake_date: datetime | None) -> str | None:
    parsed = _datetime(value)
    if parsed is not None:
        return parsed.date().isoformat()
    if intake_date is None:
        return None
    cleaned = _clean_date(value)
    for date_format in ("%d %B", "%d %b"):
        try:
            partial = datetime.strptime(cleaned, date_format)
        except ValueError:
            continue
        candidate = partial.replace(year=intake_date.year)
        if candidate >= intake_date:
            candidate = candidate.replace(year=intake_date.year - 1)
        return candidate.date().isoformat()
    return None


def _datetime(value: str) -> datetime | None:
    cleaned = _clean_date(value)
    for date_format in ("%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(cleaned, date_format)
        except ValueError:
            continue
    return None


def _clean_date(value: str) -> str:
    cleaned = re.sub(
        r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b,?",
        "",
        value,
        flags=re.I,
    )
    cleaned = re.sub(r"(\d)(?:st|nd|rd|th)\b", r"\1", cleaned, flags=re.I)
    return _normalise(cleaned.strip(" ,.;"))


def _key_fact(soup: BeautifulSoup, label: str) -> str:
    for item in soup.select(
        ".pgt-programme-metadata__key-facts .pgt-programme-metadata__item"
    ):
        heading = item.find("b")
        if (
            heading
            and _normalise(heading.get_text(" ", strip=True)).lower() == label.lower()
        ):
            value = item.find("p")
            return _normalise(value.get_text(" ", strip=True)) if value else ""
    return ""


def _split_title(value: str) -> tuple[str, str] | None:
    match = DEGREE_RE.search(value)
    if match is None:
        return None
    degree_type = _canonical_degree(match.group("degree"))
    base_title = _normalise(value[: match.start()]) or value
    return base_title, degree_type


def _canonical_degree(value: str) -> str:
    known = {
        "msc": "MSc",
        "mscr": "MScR",
        "mvetsci": "MVetSci",
        "mcouns": "MCouns",
        "march": "MArch",
        "mmus": "MMus",
        "mfa": "MFA",
        "mres": "MRes",
        "mphil": "MPhil",
        "mlitt": "MLitt",
        "llm": "LLM",
        "mba": "MBA",
        "mph": "MPH",
        "med": "MEd",
        "mfin": "MFin",
        "mpa": "MPA",
        "mpp": "MPP",
        "msw": "MSW",
        "ma": "MA",
        "ms": "MS",
        "master": "Master",
    }
    return known[value.lower()]


def _course_url(href: str) -> str | None:
    absolute = urljoin(CATALOG_URL, href)
    parts = urlsplit(absolute)
    if COURSE_PATH_RE.match(parts.path) is None:
        return None
    return urlunsplit(("https", "study.ed.ac.uk", parts.path.rstrip("/"), "", ""))


def _slug(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    )
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", ascii_value.lower())).strip(
        "-"
    )


def _normalise(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())
