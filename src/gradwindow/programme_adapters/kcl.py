from __future__ import annotations

import concurrent.futures
import json
import re
import threading
import time
import unicodedata
from collections.abc import Callable, Iterable
from dataclasses import replace
from datetime import datetime
from html import escape
from urllib.parse import urlencode, urljoin, urlsplit, urlunsplit
from xml.etree import ElementTree

from bs4 import BeautifulSoup

from ..browser_rendering import browser_content_fetcher_from_environment
from .base import (
    BaseProgrammeAdapter,
    DiscoveredCatalog,
    DiscoveredProgramme,
    DiscoveredWindow,
    OfficialSourceTransportError,
    ParserError,
)

UNIVERSITY_ID = "king-s-college-london-kcl"
SITEMAP_URL = "https://www.kcl.ac.uk/sitemap.xml"
CATALOG_URL = "https://www.kcl.ac.uk/study/postgraduate-taught/courses"
APPLICATION_URL = "https://www.kcl.ac.uk/study/postgraduate-taught/how-to-apply"
DEFAULT_INTAKE = "September 2026"
COURSE_PATH_RE = re.compile(
    r"^/study/postgraduate-taught/courses/(?P<slug>[^/]+?)/?$",
    flags=re.IGNORECASE,
)
MASTER_DEGREE_RE = re.compile(
    r"\b(?P<degree>MSc|MRes|MPhil|MLitt|LLM|MBA|MPH|MEd|MMus|MFA|MA)\b",
    flags=re.IGNORECASE,
)
DATE_PATTERN = r"\d{1,2}\s+[A-Z][a-z]+\s+20\d{2}"
APPLICANT_DEADLINE_RE = re.compile(
    rf"(?P<label>Overseas(?:\s*\(international\))?\s+fee\s+status|"
    rf"Home\s+fee\s+status|All\s+applicants)[^:]{{0,80}}:\s*"
    rf"(?P<date>{DATE_PATTERN})",
    flags=re.IGNORECASE,
)
FIRST_DEADLINE_RE = re.compile(
    rf"(?:first|initial)\s+application\s+deadline(?:\s+is)?(?:\s+on)?\s+"
    rf"(?P<date>{DATE_PATTERN})",
    flags=re.IGNORECASE,
)
ALL_FINAL_DEADLINE_RE = re.compile(
    rf"(?:final\s+application\s+deadline|applications?\s+(?:will\s+)?close)"
    rf"[^.\n:]{{0,100}}(?:is|on|:)\s*(?P<date>{DATE_PATTERN})",
    flags=re.IGNORECASE,
)
NO_FURTHER_APPLICATIONS_RE = re.compile(
    rf"no\s+further\s+applications?[^.\n]{{0,100}}"
    rf"(?:accepted|submitted)[^.\n]{{0,40}}after\s+(?P<date>{DATE_PATTERN})",
    flags=re.IGNORECASE,
)
INTAKE_RE = re.compile(
    r"(?P<term>January|September)\s+(?P<year>20\d{2})\s+(?:intake|entry)",
    re.I,
)
STARTUP_SCRIPT_RE = re.compile(r"startup-[^/]+\.js$")
DELIVERY_TOKEN_RE = re.compile(r'accessToken:\s*"(?P<token>[^"]+)"')
DELIVERY_API_RE = re.compile(
    r'api:\s*"https://api-"\s*\+\s*alias\s*\+\s*"\.cloud\.contensis\.com"'
)
PROGRAMME_ID_ALIASES = {
    "/study/postgraduate-taught/courses/advanced-clinical-practice-msc-pg-dip-pg-cert": (
        "kcl-advanced-clinical-practice-msc-pg-dip"
    ),
    "/study/postgraduate-taught/courses/applied-neuroscience-msc": (
        "kcl-applied-neuroscience-msc-pg-dip-online"
    ),
    "/study/postgraduate-taught/courses/global-security-ma-pg-dip-pg-cert": (
        "kcl-global-security-ma-pg-dip-pg-cert-online-ma"
    ),
    "/study/postgraduate-taught/courses/international-financial-and-commercial-law-llm": (
        "kcl-international-financial-commercial-law-llm-online-llm"
    ),
}


class _HostRateLimiter:
    def __init__(
        self,
        *,
        minimum_interval: float,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.minimum_interval = max(0, minimum_interval)
        self._sleep = sleep
        self._monotonic = monotonic
        self._lock = threading.Lock()
        self._last_request_by_host: dict[str, float] = {}

    def wait(self, url: str) -> None:
        host = (urlsplit(url).hostname or "").lower()
        if not host or self.minimum_interval <= 0:
            return
        with self._lock:
            now = self._monotonic()
            previous = self._last_request_by_host.get(host)
            if previous is not None:
                remaining = self.minimum_interval - (now - previous)
                if remaining > 0:
                    self._sleep(remaining)
            self._last_request_by_host[host] = self._monotonic()


class KCLAdapter(BaseProgrammeAdapter):
    university_id = UNIVERSITY_ID
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = DEFAULT_INTAKE
    application_opens_at_basis = "missing"

    def __init__(
        self,
        minimum_expected_programmes: int = 140,
        detail_workers: int = 3,
        detail_attempts: int = 3,
        minimum_expected_delivery_windows: int = 5,
        minimum_interval_seconds: float = 1.25,
        retry_backoff_seconds: float = 0.75,
        browser_content_fetcher: Callable[[str], str] | None = None,
        use_environment_browser: bool = True,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.detail_workers = max(1, min(detail_workers, 3))
        self.detail_attempts = max(1, detail_attempts)
        self.minimum_expected_delivery_windows = max(
            0,
            minimum_expected_delivery_windows,
        )
        self.retry_backoff_seconds = max(0, retry_backoff_seconds)
        self.browser_content_fetcher = browser_content_fetcher
        if self.browser_content_fetcher is None and use_environment_browser:
            self.browser_content_fetcher = browser_content_fetcher_from_environment()
        self.rate_limiter = _HostRateLimiter(
            minimum_interval=minimum_interval_seconds,
        )
        self._diagnostic_lock = threading.Lock()
        self._detail_retries = 0
        self._browser_fallbacks = 0
        self.sitemap_diagnostics = "not inspected"
        self.catalogue_titles: dict[str, str] = {}

    def parse_catalog_from_fetcher(
        self,
        fetcher: Callable[[str], str],
    ) -> DiscoveredCatalog:
        self._detail_retries = 0
        self._browser_fallbacks = 0
        course_urls = self._course_urls(fetcher)
        if len(course_urls) < self.minimum_expected_programmes:
            raise ValueError(
                "King's College London sitemap only contained "
                f"{len(course_urls)} postgraduate taught master's course URLs; "
                f"expected at least {self.minimum_expected_programmes}. "
                f"Sitemap diagnostics: {self.sitemap_diagnostics}"
            )

        delivery_diagnostics: dict[str, object] = {}
        try:
            delivery_programmes = self._delivery_programmes(fetcher, course_urls)
        except Exception as exc:
            delivery_programmes = []
            delivery_diagnostics["deliveryApiError"] = (
                f"{type(exc).__name__}: {str(exc)[:180]}"
            )
        else:
            delivery_windows = sum(
                len(programme.windows) for programme in delivery_programmes
            )
            delivery_diagnostics.update(
                {
                    "deliveryApiProgrammes": len(delivery_programmes),
                    "deliveryApiWindows": delivery_windows,
                }
            )
            if (
                len(delivery_programmes) >= self.minimum_expected_programmes
                and delivery_windows >= self.minimum_expected_delivery_windows
            ):
                return DiscoveredCatalog(
                    application_opens_at=None,
                    programmes=delivery_programmes,
                    diagnostics={
                        "detailFailures": 0,
                        "transportFailures": 0,
                        "parserFailures": 0,
                        "detailRetries": self._detail_retries,
                        "browserFallbacks": self._browser_fallbacks,
                        **delivery_diagnostics,
                    },
                )

        def parse_one(
            course_url: str,
        ) -> tuple[DiscoveredProgramme | None, dict | None]:
            detail_url = course_url.rstrip("/")
            try:
                html, retrieval_method = self._fetch_detail_page(
                    fetcher,
                    detail_url,
                )
            except Exception as exc:
                fallback = _programme_from_slug(
                    course_url,
                    catalogue_title=self.catalogue_titles.get(course_url, ""),
                )
                if fallback is None:
                    return None, {
                        "failureType": "transport",
                        "programmeId": course_url,
                        "sourceUrl": detail_url,
                        "error": f"{type(exc).__name__}: {str(exc)[:180]}",
                    }
                programme = replace(
                    fallback,
                    deadline_text=(
                        "Course found in the official KCL sitemap, but its "
                        "course detail page could not be fetched during discovery: "
                        f"{type(exc).__name__}: {str(exc)[:180]}"
                    ),
                )
                return programme, {
                    "failureType": "transport",
                    "programmeId": programme.id,
                    "sourceUrl": detail_url,
                    "error": f"{type(exc).__name__}: {str(exc)[:180]}",
                }
            try:
                programme = _parse_programme(
                    course_url,
                    detail_url,
                    html,
                    catalogue_title=self.catalogue_titles.get(course_url, ""),
                )
                if programme is not None:
                    programme = replace(
                        programme,
                        retrieval_method=retrieval_method,
                        evidence_quality="official-full-text",
                    )
            except Exception as exc:
                fallback = _programme_from_slug(
                    course_url,
                    catalogue_title=self.catalogue_titles.get(course_url, ""),
                )
                if fallback is None:
                    return None, {
                        "failureType": "parser",
                        "programmeId": course_url,
                        "sourceUrl": detail_url,
                        "error": f"{type(exc).__name__}: {str(exc)[:180]}",
                    }
                programme = replace(
                    fallback,
                    deadline_text=(
                        "Course found in the official KCL sitemap, but its "
                        "course detail page could not be parsed during discovery: "
                        f"{type(exc).__name__}: {str(exc)[:180]}"
                    ),
                )
                return programme, {
                    "failureType": "parser",
                    "programmeId": programme.id,
                    "sourceUrl": detail_url,
                    "error": f"{type(exc).__name__}: {str(exc)[:180]}",
                }
            return programme, None

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.detail_workers
        ) as executor:
            outcomes = list(executor.map(parse_one, course_urls))
        programmes = [programme for programme, _failure in outcomes if programme]
        detail_failures = [failure for _programme, failure in outcomes if failure]
        transport_failures = [
            failure
            for failure in detail_failures
            if failure.get("failureType") == "transport"
        ]
        parser_failures = [
            failure
            for failure in detail_failures
            if failure.get("failureType") == "parser"
        ]
        if len(transport_failures) * 10 > len(course_urls):
            raise OfficialSourceTransportError(
                f"{len(transport_failures)} of {len(course_urls)} KCL programme "
                "course detail pages failed during discovery, exceeding the "
                "10% critical-detail threshold."
            )
        if len(parser_failures) * 10 > len(course_urls):
            raise ParserError(
                f"{len(parser_failures)} of {len(course_urls)} KCL programme "
                "course detail pages failed parsing during discovery, exceeding "
                "the 10% critical-detail threshold."
            )
        programmes = sorted(
            {programme.id: programme for programme in programmes}.values(),
            key=lambda item: item.id,
        )
        if len(programmes) < self.minimum_expected_programmes:
            raise ValueError(
                "King's College London discovery only produced "
                f"{len(programmes)} master's programmes; expected at least "
                f"{self.minimum_expected_programmes}"
            )
        warnings = []
        if transport_failures:
            failed_programme_ids = sorted(
                str(failure["programmeId"]) for failure in transport_failures
            )
            warnings.append(
                {
                    "reason": "TRANSPORT_ERROR",
                    "message": (
                        f"{len(transport_failures)} of {len(course_urls)} KCL "
                        "programme detail pages failed during discovery; "
                        "affected programmes were retained without deadlines."
                    ),
                    "sourceUrl": transport_failures[0]["sourceUrl"],
                    "detailFailures": len(transport_failures),
                    "totalDetailPages": len(course_urls),
                    "failedProgrammeIds": failed_programme_ids,
                }
            )
        if parser_failures:
            failed_programme_ids = sorted(
                str(failure["programmeId"]) for failure in parser_failures
            )
            warnings.append(
                {
                    "reason": "PARSER_ERROR",
                    "message": (
                        f"{len(parser_failures)} of {len(course_urls)} KCL "
                        "programme detail pages failed parsing; affected "
                        "programmes were retained without deadlines."
                    ),
                    "sourceUrl": parser_failures[0]["sourceUrl"],
                    "parserFailures": len(parser_failures),
                    "totalDetailPages": len(course_urls),
                    "failedProgrammeIds": failed_programme_ids,
                }
            )
        return DiscoveredCatalog(
            application_opens_at=None,
            programmes=programmes,
            warnings=warnings,
            diagnostics={
                "detailFailures": len(detail_failures),
                "transportFailures": len(transport_failures),
                "parserFailures": len(parser_failures),
                "detailRetries": self._detail_retries,
                "browserFallbacks": self._browser_fallbacks,
                **delivery_diagnostics,
            },
        )

    def _delivery_programmes(
        self,
        fetcher: Callable[[str], str],
        course_urls: list[str],
    ) -> list[DiscoveredProgramme]:
        html = self._fetch_with_retry(fetcher, self.catalog_url)
        soup = BeautifulSoup(html, "html.parser")
        startup_src = next(
            (
                script.get("src", "")
                for script in soup.find_all("script", src=True)
                if STARTUP_SCRIPT_RE.search(script.get("src", ""))
            ),
            "",
        )
        if not startup_src:
            raise ValueError("KCL delivery API startup script was not found")
        startup_url = urljoin(self.catalog_url, startup_src)
        startup_script = self._fetch_with_retry(fetcher, startup_url)
        token_match = DELIVERY_TOKEN_RE.search(startup_script)
        if token_match is None or DELIVERY_API_RE.search(startup_script) is None:
            raise ValueError("KCL delivery API configuration was not found")

        api_url = "https://api-kcl.cloud.contensis.com/api/delivery/projects/website/"
        api_url += "contentTypes/postgraduateCourse/entries?"
        api_url += urlencode(
            {
                "pageSize": 500,
                "versionStatus": "published",
                "language": "en-GB",
                "accessToken": token_match.group("token"),
            }
        )
        payload = _json_object(self._fetch_with_retry(fetcher, api_url))
        items = payload.get("items")
        if not isinstance(items, list):
            raise ValueError("KCL delivery API did not return an item list")
        try:
            total_count = int(payload.get("totalCount", len(items)))
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "KCL delivery API returned an invalid total count"
            ) from exc
        if total_count > len(items):
            raise ValueError(
                "KCL delivery API response was unexpectedly paginated: "
                f"{len(items)} of {total_count} entries"
            )

        expected_urls = set(course_urls)
        programmes = {}
        for item in items:
            if not isinstance(item, dict):
                continue
            source_url = _absolute_course_url((item.get("sys") or {}).get("uri", ""))
            if source_url not in expected_urls:
                continue
            title = _normalise_text(item.get("entryTitle", ""))
            if not title:
                continue
            self.catalogue_titles[source_url] = title
            programme = _parse_programme(
                source_url,
                source_url,
                _delivery_entry_document(item, title),
                catalogue_title=title,
            )
            if programme is None:
                continue
            faculty, department = _delivery_academic_units(item)
            programmes[programme.id] = replace(
                programme,
                faculty=programme.faculty or faculty,
                department=programme.department or department,
                retrieval_method="official-api",
                evidence_quality="official-full-text",
            )
        return sorted(programmes.values(), key=lambda item: item.id)

    def _fetch_detail_page(
        self,
        fetcher: Callable[[str], str],
        url: str,
    ) -> tuple[str, str]:
        try:
            return self._fetch_with_retry(
                fetcher, url, track_detail=True
            ), "official-html"
        except Exception as direct_error:
            if self.browser_content_fetcher is None:
                raise
            try:
                rendered = self.browser_content_fetcher(url)
            except Exception as browser_error:
                raise RuntimeError(
                    "KCL detail page failed direct retrieval and browser fallback: "
                    f"direct={type(direct_error).__name__}: {str(direct_error)[:120]}; "
                    f"browser={type(browser_error).__name__}: {str(browser_error)[:120]}"
                ) from direct_error
            if not rendered.strip():
                raise RuntimeError(
                    "KCL detail page browser fallback returned an empty response"
                ) from direct_error
            with self._diagnostic_lock:
                self._browser_fallbacks += 1
            return rendered, "cloudflare-browser-rendering"

    def _fetch_with_retry(
        self,
        fetcher: Callable[[str], str],
        url: str,
        *,
        track_detail: bool = False,
    ) -> str:
        last_error: Exception | None = None
        for attempt in range(self.detail_attempts):
            self.rate_limiter.wait(url)
            try:
                return fetcher(url)
            except Exception as exc:
                last_error = exc
                if attempt + 1 >= self.detail_attempts:
                    break
                if track_detail:
                    with self._diagnostic_lock:
                        self._detail_retries += 1
                time.sleep(self.retry_backoff_seconds * (2**attempt))
        if last_error is None:
            raise ValueError("KCL detail attempts must be greater than zero")
        raise last_error

    def _course_urls(self, fetcher: Callable[[str], str]) -> list[str]:
        root_xml = self._fetch_with_retry(fetcher, SITEMAP_URL)
        root_locations = _xml_locations(root_xml)
        root_name = _xml_root_name(root_xml)
        course_urls = _filter_course_urls(root_locations)
        postgraduate_samples = [
            url for url in root_locations if "postgraduate" in url.lower()
        ][:8]
        self.sitemap_diagnostics = (
            f"root={root_name}, rootLocations={len(root_locations)}, "
            f"sample={root_locations[:3]}, postgraduateSample={postgraduate_samples}"
        )
        if course_urls:
            return course_urls

        if root_name != "sitemapindex":
            return self._catalogue_page_urls(fetcher)
        sitemap_urls = root_locations
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=self.detail_workers
        ) as executor:
            child_payloads = list(
                executor.map(
                    lambda url: self._fetch_with_retry(fetcher, url),
                    sitemap_urls,
                )
            )
        child_locations = [
            location
            for payload in child_payloads
            for location in _xml_locations(payload)
        ]
        self.sitemap_diagnostics = (
            f"root={root_name}, rootLocations={len(root_locations)}, "
            f"childDocuments={len(child_payloads)}, "
            f"childLocations={len(child_locations)}, sample={child_locations[:3]}"
        )
        return _filter_course_urls(child_locations)

    def _catalogue_page_urls(self, fetcher: Callable[[str], str]) -> list[str]:
        html = self._fetch_with_retry(fetcher, self.catalog_url)
        soup = BeautifulSoup(html, "html.parser")
        page_urls = _filter_course_urls(
            link.get("href", "") for link in soup.find_all("a", href=True)
        )
        startup_src = next(
            (
                script.get("src", "")
                for script in soup.find_all("script", src=True)
                if STARTUP_SCRIPT_RE.search(script.get("src", ""))
            ),
            "",
        )
        if not startup_src:
            self.sitemap_diagnostics += (
                f"; catalogueLinks={len(page_urls)}, startupScript=missing"
            )
            return page_urls

        startup_url = urljoin(self.catalog_url, startup_src)
        startup_script = self._fetch_with_retry(fetcher, startup_url)
        token_match = DELIVERY_TOKEN_RE.search(startup_script)
        if token_match is None or DELIVERY_API_RE.search(startup_script) is None:
            self.sitemap_diagnostics += (
                f"; catalogueLinks={len(page_urls)}, deliveryConfig=missing"
            )
            return page_urls

        api_url = "https://api-kcl.cloud.contensis.com/api/delivery/projects/website/"
        api_url += "contentTypes/postgraduateCourse/entries?"
        api_url += urlencode(
            {
                "pageSize": 500,
                "versionStatus": "published",
                "language": "en-GB",
                "fields": "sys,entryTitle",
                "accessToken": token_match.group("token"),
            }
        )
        payload = json.loads(self._fetch_with_retry(fetcher, api_url))
        api_entries = {
            _absolute_course_url(item.get("sys", {}).get("uri", "")): _normalise_text(
                item.get("entryTitle", "")
            )
            for item in payload.get("items", [])
        }
        api_urls = _filter_course_urls(api_entries)
        self.catalogue_titles = {
            url: api_entries[url] for url in api_urls if api_entries.get(url)
        }
        self.sitemap_diagnostics += (
            f"; catalogueLinks={len(page_urls)}, apiTotal={payload.get('totalCount')}, "
            f"apiCourseLinks={len(api_urls)}"
        )
        return api_urls or page_urls


def _xml_locations(payload: str) -> list[str]:
    root = ElementTree.fromstring(payload)
    return [
        _normalise_text(node.text or "")
        for node in root.iter()
        if node.tag.rsplit("}", 1)[-1].lower() == "loc" and (node.text or "").strip()
    ]


def _json_object(value: str) -> dict:
    try:
        payload = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError("KCL delivery API did not return JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("KCL delivery API returned an invalid payload")
    return payload


def _delivery_entry_document(item: dict, title: str) -> str:
    sections = []
    deadline_field = next(
        (
            field
            for field in (
                "applicationClosingDateInfoOverride",
                "applicationDeadlineOnlineOverride",
                "selectionProcess",
            )
            if item.get(field)
        ),
        None,
    )
    fields = [
        field
        for field in (
            deadline_field,
            "detailsDisclaimerOverride",
            "onlineCourseDates",
            "startDates",
        )
        if field
    ]
    for field in fields:
        value = item.get(field)
        fragments = list(_delivery_fragments(value))
        if not fragments:
            continue
        label = _delivery_field_label(str(field))
        sections.append(f"<h2>{escape(label)}</h2>{''.join(fragments)}")
    return (
        "<html><head><title>"
        f"{escape(title)} | King's College London"
        "</title></head><body>"
        f"{''.join(sections)}"
        "</body></html>"
    )


def _delivery_field_label(field: str) -> str:
    if field in {
        "applicationClosingDateInfoOverride",
        "applicationDeadlineOnlineOverride",
        "selectionProcess",
    }:
        return "Application closing date guidance"
    return re.sub(r"(?<!^)(?=[A-Z])", " ", field).replace("_", " ")


def _delivery_academic_units(item: dict) -> tuple[str, str]:
    units = []
    for value in item.get("orgUnits") or []:
        if not isinstance(value, dict):
            continue
        name = _normalise_text(value.get("entryTitle", ""))
        if name and name not in units:
            units.append(name)
    return tuple((units + ["", ""])[:2])


def _delivery_fragments(value) -> Iterable[str]:
    if isinstance(value, str):
        clean = value.strip()
        if not clean:
            return
        if re.search(r"</?[a-z][^>]*>", clean, re.I):
            yield clean
        else:
            yield f"<p>{escape(clean)}</p>"
        return
    if isinstance(value, dict):
        for nested in value.values():
            yield from _delivery_fragments(nested)
        return
    if isinstance(value, list):
        for nested in value:
            yield from _delivery_fragments(nested)


def _xml_root_name(payload: str) -> str:
    return ElementTree.fromstring(payload).tag.rsplit("}", 1)[-1].lower()


def _filter_course_urls(urls: Iterable[str]) -> list[str]:
    courses = set()
    for url in urls:
        parts = urlsplit(url)
        match = COURSE_PATH_RE.match(parts.path)
        if match is None or match.group("slug").lower() == "new":
            continue
        if MASTER_DEGREE_RE.search(match.group("slug").replace("-", " ")) is None:
            continue
        courses.add(
            urlunsplit(
                (
                    parts.scheme or "https",
                    parts.netloc or "www.kcl.ac.uk",
                    parts.path.rstrip("/"),
                    "",
                    "",
                )
            )
        )
    return sorted(courses)


def _absolute_course_url(url: str) -> str:
    parts = urlsplit(url)
    return urlunsplit(
        (
            parts.scheme or "https",
            parts.netloc or "www.kcl.ac.uk",
            parts.path.rstrip("/"),
            "",
            "",
        )
    )


def _parse_programme(
    course_url: str,
    detail_url: str,
    html: str,
    *,
    catalogue_title: str = "",
) -> DiscoveredProgramme | None:
    soup = BeautifulSoup(html, "html.parser")
    title = _programme_title(soup)
    degree_match = MASTER_DEGREE_RE.search(title)
    if degree_match is None:
        slug = urlsplit(course_url).path.rstrip("/").rsplit("/", 1)[-1]
        degree_match = MASTER_DEGREE_RE.search(slug.replace("-", " "))
        if degree_match is None:
            return None
        base_title = catalogue_title or title
        if not base_title or "King's College London" in base_title:
            return _programme_from_slug(course_url, catalogue_title=catalogue_title)
        title = f"{base_title} {_canonical_degree(degree_match.group('degree'))}"
    degree_type = _canonical_degree(degree_match.group("degree"))
    windows, excerpt = _parse_deadlines(soup, detail_url)
    faculty, department = _taught_in(soup)
    return DiscoveredProgramme(
        id=_programme_id(course_url, title),
        name=title,
        degree_type=degree_type,
        faculty=faculty,
        department=department,
        source_url=detail_url,
        application_url=APPLICATION_URL,
        windows=windows,
        deadline_text=excerpt
        or "No exact application deadline was found on the course detail page.",
        parse_status="incomplete" if windows else "no-deadline",
    )


def _programme_from_slug(
    course_url: str,
    *,
    catalogue_title: str = "",
) -> DiscoveredProgramme | None:
    slug = urlsplit(course_url).path.rstrip("/").rsplit("/", 1)[-1]
    degree_match = MASTER_DEGREE_RE.search(slug.replace("-", " "))
    if degree_match is None:
        return None
    degree_type = _canonical_degree(degree_match.group("degree"))
    if catalogue_title:
        title = f"{catalogue_title} {degree_type}"
    else:
        words = slug.replace("-", " ")
        title = " ".join(
            _canonical_degree(word)
            if MASTER_DEGREE_RE.fullmatch(word)
            else word.title()
            for word in words.split()
        )
    return DiscoveredProgramme(
        id=_programme_id(course_url, title),
        name=title,
        degree_type=degree_type,
        faculty="",
        department="",
        source_url=course_url.rstrip("/"),
        application_url=APPLICATION_URL,
        windows=[],
        deadline_text="Course found in the official KCL sitemap.",
        parse_status="no-deadline",
    )


def _programme_title(soup: BeautifulSoup) -> str:
    title = _normalise_text(soup.title.get_text(" ", strip=True) if soup.title else "")
    title = re.split(
        r"\s+-\s+Entry Requirements|\s+\|\s+King", title, maxsplit=1, flags=re.I
    )[0]
    if MASTER_DEGREE_RE.search(title):
        return title
    heading = soup.find("h1")
    return _normalise_text(heading.get_text(" ", strip=True) if heading else title)


def _programme_id(course_url: str, title: str) -> str:
    path = urlsplit(course_url).path.rstrip("/").lower()
    return PROGRAMME_ID_ALIASES.get(path, f"kcl-{_slug(title)}")


def _parse_deadlines(
    soup: BeautifulSoup,
    source_url: str,
) -> tuple[list[DiscoveredWindow], str]:
    text = _normalise_text(soup.get_text(" ", strip=True))
    lower = text.lower()
    start = lower.find("application closing date guidance")
    if start < 0:
        return [], ""
    end_candidates = [
        position
        for label in ("key links", "taught in", "base campus")
        if (position := lower.find(label, start + 20)) >= 0
    ]
    end = min(end_candidates) if end_candidates else min(len(text), start + 3000)
    section = text[start:end]
    candidates: list[tuple[int, str, str, list[str]]] = []
    for match in APPLICANT_DEADLINE_RE.finditer(section):
        label = match.group("label").lower()
        categories = (
            ["international"]
            if label.startswith("overseas")
            else ["home"]
            if label.startswith("home")
            else ["all"]
        )
        candidates.append(
            (
                match.start(),
                "Final application deadline",
                match.group("date"),
                categories,
            )
        )
    for match in FIRST_DEADLINE_RE.finditer(section):
        candidates.append(
            (match.start(), "First application deadline", match.group("date"), ["all"])
        )
    for match in ALL_FINAL_DEADLINE_RE.finditer(section):
        candidates.append(
            (match.start(), "Final application deadline", match.group("date"), ["all"])
        )
    for match in NO_FURTHER_APPLICATIONS_RE.finditer(section):
        candidates.append(
            (match.start(), "Final application deadline", match.group("date"), ["all"])
        )

    windows = []
    seen = set()
    for position, round_label, date_text, categories in sorted(candidates):
        closes_at = datetime.strptime(date_text, "%d %B %Y").date().isoformat()
        intake = _intake_for_deadline(section, position) or DEFAULT_INTAKE
        identity = (round_label, tuple(categories), closes_at, intake)
        if identity in seen:
            continue
        seen.add(identity)
        windows.append(
            DiscoveredWindow(
                round=round_label,
                applicant_categories=categories,
                opens_at=None,
                closes_at=closes_at,
                intake=intake,
                source_url=source_url,
            )
        )
    return windows, section[:1800]


def _intake_for_deadline(section: str, position: int) -> str | None:
    matches = list(INTAKE_RE.finditer(section[:position]))
    if matches:
        match = matches[-1]
        return f"{match.group('term').title()} {match.group('year')}"
    all_intakes = {
        f"{match.group('term').title()} {match.group('year')}"
        for match in INTAKE_RE.finditer(section)
    }
    return next(iter(all_intakes)) if len(all_intakes) == 1 else None


def _taught_in(soup: BeautifulSoup) -> tuple[str, str]:
    heading = next(
        (
            item
            for item in soup.find_all(["h2", "h3"])
            if _normalise_text(item.get_text(" ", strip=True)).lower() == "taught in"
        ),
        None,
    )
    if heading is None:
        return "", ""
    section = heading.find_parent(
        "div", class_=re.compile(r"FacultiesAndDepartmentsstyled__")
    )
    if section is not None:
        names = list(
            dict.fromkeys(
                name
                for link in section.find_all("a")
                if (name := _normalise_text(link.get_text(" ", strip=True)))
            )
        )
        return tuple((names + ["", ""])[:2])

    names = []
    for item in heading.find_all_next(["a", "h2", "h3"]):
        if (
            item.name in {"h2", "h3"}
            and item is not heading
            and not item.find_parent("a")
        ):
            break
        name = _normalise_text(item.get_text(" ", strip=True))
        if name and name not in names:
            names.append(name)
        if len(names) == 2:
            break
    return (names + ["", ""])[:2]


def _canonical_degree(value: str) -> str:
    mapping = {
        "msc": "MSc",
        "mres": "MRes",
        "mphil": "MPhil",
        "mlitt": "MLitt",
        "llm": "LLM",
        "mba": "MBA",
        "mph": "MPH",
        "med": "MEd",
        "mmus": "MMus",
        "mfa": "MFA",
        "ma": "MA",
    }
    return mapping[value.lower()]


def _slug(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    )
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", ascii_value.lower())).strip(
        "-"
    )


def _normalise_text(value: str) -> str:
    return " ".join(str(value).replace("\u00a0", " ").split())
