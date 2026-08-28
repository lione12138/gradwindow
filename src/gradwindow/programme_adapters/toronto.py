from __future__ import annotations

import hashlib
import json
import random
import re
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .base import (
    BaseProgrammeAdapter,
    DiscoveredCatalog,
    DiscoveredProgramme,
    DiscoveredWindow,
)

UNIVERSITY_ID = "university-of-toronto"
CATALOG_URL = "https://www.sgs.utoronto.ca/programs/"
PROGRAMS_API_URL = (
    "https://www.sgs.utoronto.ca/wp-json/wp/v2/programs"
    "?per_page=100&page={page}"
)
APPLICATION_URL = "https://admissions.sgs.utoronto.ca/apply/"
EXISTING_COMPUTER_SCIENCE_ID = "toronto-computer-science-msc"

_DEGREE_LABEL_RE = re.compile(
    r"(?<!\w)(?P<label>[A-Z][A-Za-z0-9]*"
    r"(?:\s*\([^)]*\))?"
    r"(?:,\s*[A-Z][A-Za-z0-9]*(?:\s*\([^)]*\))?)*)\s*:"
)
_FALL_CYCLE_RE = re.compile(
    r"\bFall(?:\s+Session)?(?:\s+\(September start\))?\s+"
    r"(?P<year>20\d{2})(?:\s+entry)?\b",
    re.I,
)
_DATE_RE = re.compile(
    r"\b(?:"
    r"\d{4}-\d{2}-\d{2}|"
    r"\d{1,2}[-\s](?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|"
    r"May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|"
    r"Nov(?:ember)?|Dec(?:ember)?)[-\s]\d{4}|"
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\s+\d{1,2},?\s+\d{4}"
    r")\b",
    re.I,
)
_ROUND_RE = re.compile(
    r"\b(early|regular|priority|final|round\s+\d+)\s+deadline\b",
    re.I,
)


class TorontoAdapter(BaseProgrammeAdapter):
    """Discover U of T master's programmes and central SGS deadline guidance."""

    university_id = UNIVERSITY_ID
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Fall 2027"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    browser_fallback_limit = 3

    def __init__(
        self,
        minimum_expected_programmes: int = 150,
        workers: int = 2,
        intake_year: int = 2027,
        detail_interval_seconds: float = 0.8,
        detail_jitter_seconds: float = 0.7,
        cache_max_age_days: int = 14,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.workers = workers
        self.intake_year = intake_year
        self.intake = f"Fall {intake_year}"
        self.detail_interval_seconds = detail_interval_seconds
        self.detail_jitter_seconds = detail_jitter_seconds
        self.cache_max_age_days = cache_max_age_days
        self._previous_cache: dict[str, dict] = {}

    def prepare_discovery(self, previous_state: dict) -> None:
        adapter_state = previous_state.get("adapterState", {})
        cache = adapter_state.get("detailCache", {})
        self._previous_cache = cache if isinstance(cache, dict) else {}

    def parse_catalog_from_fetcher(
        self,
        fetcher: Callable[[str], str],
    ) -> DiscoveredCatalog:
        rows, api_pages = _api_rows(fetcher)
        detail_urls = list(dict.fromkeys(row["url"] for row in rows))
        fetched_at = datetime.now(timezone.utc)
        details: dict[str, list[DiscoveredProgramme]] = {}
        cache_hits = 0
        urls_to_fetch = []
        rows_by_url = {row["url"]: row for row in rows}
        for url in detail_urls:
            row = rows_by_url[url]
            cached = self._previous_cache.get(url)
            if _cache_is_fresh(
                cached,
                modified_at=row["modified_at"],
                now=fetched_at,
                max_age_days=self.cache_max_age_days,
            ):
                details[url] = [
                    _programme_from_cache(item) for item in cached["programmes"]
                ]
                cache_hits += 1
            else:
                urls_to_fetch.append(url)

        pacer = _RequestPacer(
            interval_seconds=self.detail_interval_seconds,
            jitter_seconds=self.detail_jitter_seconds,
        )

        def fetch_detail(url: str) -> tuple[str, str]:
            pacer.wait()
            return url, fetcher(url)

        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            pages = dict(executor.map(fetch_detail, urls_to_fetch))

        for url, html in pages.items():
            row = rows_by_url[url]
            details[url] = [
                _programme(
                    row,
                    degree_type,
                    html,
                    intake_year=self.intake_year,
                )
                for degree_type in row["degrees"]
            ]

        programmes = [programme for row in rows for programme in details[row["url"]]]
        programmes.sort(key=lambda item: item.id)
        if len(programmes) < self.minimum_expected_programmes:
            raise ValueError(
                "U of T's official SGS directory only contained "
                f"{len(programmes)} master's programmes; expected at least "
                f"{self.minimum_expected_programmes}"
            )
        detail_cache = {
            row["url"]: {
                "modifiedAt": row["modified_at"],
                "fetchedAt": (
                    self._previous_cache[row["url"]]["fetchedAt"]
                    if row["url"] not in pages
                    else fetched_at.isoformat()
                ),
                "programmes": [
                    _programme_to_cache(programme) for programme in details[row["url"]]
                ],
            }
            for row in rows
        }
        return DiscoveredCatalog(
            application_opens_at=None,
            programmes=programmes,
            diagnostics={
                "apiPages": api_pages,
                "detailPagesFetched": len(pages),
                "detailCacheHits": cache_hits,
            },
            adapter_state={"detailCache": detail_cache},
        )


def _api_rows(fetcher: Callable[[str], str]) -> tuple[list[dict], int]:
    rows = []
    page = 1
    while True:
        payload = json.loads(fetcher(PROGRAMS_API_URL.format(page=page)))
        if not isinstance(payload, list):
            raise ValueError("U of T programmes API did not return a list")
        for item in payload:
            taxonomy = item.get("taxonomy_info", {})
            if not isinstance(taxonomy, dict):
                continue
            degrees = [
                value["label"]
                for value in taxonomy.get("degree-types", [])
                if _is_master_degree(value.get("label", ""))
            ]
            url = item.get("link", "")
            if not degrees or not url.startswith(
                "https://www.sgs.utoronto.ca/programs/"
            ):
                continue
            units = taxonomy.get("graduate-units", [])
            rows.append(
                {
                    "name": _normalise(
                        BeautifulSoup(
                            item.get("title", {}).get("rendered", ""), "html.parser"
                        ).get_text(" ", strip=True)
                    ),
                    "unit": _normalise(units[0].get("label", "")) if units else "",
                    "degrees": degrees,
                    "url": url,
                    "modified_at": item.get("modified", ""),
                }
            )
        if len(payload) < 100:
            return rows, page
        page += 1


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


def _cache_is_fresh(
    cached: object,
    *,
    modified_at: str,
    now: datetime,
    max_age_days: int,
) -> bool:
    if not isinstance(cached, dict):
        return False
    if cached.get("modifiedAt") != modified_at or not isinstance(
        cached.get("programmes"), list
    ):
        return False
    try:
        fetched_at = datetime.fromisoformat(cached["fetchedAt"])
    except (KeyError, TypeError, ValueError):
        return False
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)
    return now - fetched_at <= timedelta(days=max_age_days)


def _is_master_degree(value: str) -> bool:
    compact = re.sub(r"[^A-Za-z]", "", value).upper()
    return compact.startswith("M") or compact.endswith("LLM")


def _programme(
    row: dict,
    degree_type: str,
    html: str,
    *,
    intake_year: int,
) -> DiscoveredProgramme:
    table = _deadline_table(html, row["url"])
    if table is None:
        windows = []
        deadline_text = (
            "The official SGS programme page does not publish a Quick Facts "
            "application deadline table."
        )
    else:
        windows, deadline_text = _deadline_windows(
            table,
            degree_type=degree_type,
            source_url=row["url"],
            intake_year=intake_year,
        )
    page_slug = urlparse(row["url"]).path.rstrip("/").rsplit("/", 1)[-1]
    degree_slug = _slug(degree_type)
    programme_id = f"toronto-{page_slug}-{degree_slug}"
    name = f"{row['name']} ({degree_type})"
    faculty = row["unit"] or "University of Toronto"
    if programme_id == EXISTING_COMPUTER_SCIENCE_ID:
        name = "MSc in Computer Science"
        faculty = "Department of Computer Science"

    return DiscoveredProgramme(
        id=programme_id,
        name=name,
        degree_type=degree_type,
        faculty=faculty,
        department="",
        source_url=row["url"],
        application_url=APPLICATION_URL,
        windows=windows,
        deadline_text=deadline_text,
        parse_status="incomplete" if windows else "no-deadline",
        retrieval_method="official-html",
        evidence_quality="official-full-text",
        evidence_document_hash=hashlib.sha256(html.encode("utf-8")).hexdigest(),
    )


def _programme_to_cache(programme: DiscoveredProgramme) -> dict:
    return {
        "id": programme.id,
        "name": programme.name,
        "degreeType": programme.degree_type,
        "faculty": programme.faculty,
        "department": programme.department,
        "sourceUrl": programme.source_url,
        "applicationUrl": programme.application_url,
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


def _programme_from_cache(item: dict) -> DiscoveredProgramme:
    return DiscoveredProgramme(
        id=item["id"],
        name=item["name"],
        degree_type=item["degreeType"],
        faculty=item["faculty"],
        department=item["department"],
        source_url=item["sourceUrl"],
        application_url=item["applicationUrl"],
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
            for window in item.get("windows", [])
        ],
        deadline_text=item["deadlineText"],
        parse_status=item["parseStatus"],
        retrieval_method=item.get("retrievalMethod"),
        evidence_quality=item.get("evidenceQuality"),
        evidence_document_hash=item.get("evidenceDocumentHash"),
    )


def _deadline_table(html: str, source_url: str):
    soup = BeautifulSoup(html, "html.parser")
    if soup.find("h1") is None:
        raise ValueError(f"U of T programme page did not contain a title: {source_url}")
    for table in soup.find_all("table"):
        if _deadline_row(table) is not None:
            return table
    return None


def _deadline_row(table):
    for row in table.find_all("tr"):
        cells = row.find_all(["th", "td"])
        if cells and _normalise(cells[0].get_text(" ", strip=True)).lower() == (
            "application deadline"
        ):
            return cells
    return None


def _deadline_windows(
    table,
    *,
    degree_type: str,
    source_url: str,
    intake_year: int,
) -> tuple[list[DiscoveredWindow], str]:
    cells = _deadline_row(table)
    if cells is None or len(cells) < 3:
        return [], "The official SGS Quick Facts table has no deadline cells."
    texts = {
        "domestic": _normalise(cells[1].get_text(" ", strip=True)),
        "international": _normalise(cells[2].get_text(" ", strip=True)),
    }
    windows = []
    for category, text in texts.items():
        dates = _deadline_dates(text, degree_type, intake_year)
        for round_label, closes_at in dates:
            round_name = f"Fall {intake_year} {category}"
            if round_label:
                round_name += f" {round_label}"
            round_name += " deadline"
            windows.append(
                DiscoveredWindow(
                    round=round_name,
                    opens_at=None,
                    closes_at=closes_at,
                    applicant_categories=[category],
                    intake=f"Fall {intake_year}",
                    source_url=source_url,
                )
            )
    deadline_text = (
        f"Domestic: {texts['domestic']} International: {texts['international']}"
    )
    return windows, deadline_text


def _deadline_dates(
    text: str,
    degree_type: str,
    intake_year: int,
) -> list[tuple[str, str]]:
    anchors = list(_DEGREE_LABEL_RE.finditer(text))
    aliases = _degree_aliases(degree_type)
    results = []
    for index, anchor in enumerate(anchors):
        labels = {
            _degree_key(value)
            for value in anchor.group("label").split(",")
            if value.strip()
        }
        if aliases.isdisjoint(labels):
            continue
        end = anchors[index + 1].start() if index + 1 < len(anchors) else len(text)
        body = text[anchor.end() : end]
        for date_match in _DATE_RE.finditer(body):
            prefix = body[: date_match.start()]
            cycle_matches = list(_FALL_CYCLE_RE.finditer(prefix))
            if not cycle_matches or int(cycle_matches[-1].group("year")) != intake_year:
                continue
            round_matches = list(_ROUND_RE.finditer(prefix))
            round_label = round_matches[-1].group(1).lower() if round_matches else ""
            result = (round_label, _iso_date(date_match.group(0)))
            if result not in results:
                results.append(result)
    return results


def _degree_aliases(degree_type: str) -> set[str]:
    aliases = {_degree_key(degree_type)}
    base = degree_type.split("(", 1)[0].strip()
    aliases.add(_degree_key(base))
    parenthetical = re.findall(r"\(([^()]*)\)", degree_type)
    aliases.update(_degree_key(value) for value in parenthetical)
    return aliases


def _degree_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _iso_date(value: str) -> str:
    normalised = re.sub(r"\s+", " ", value.strip())
    for date_format in (
        "%Y-%m-%d",
        "%d-%b-%Y",
        "%d-%B-%Y",
        "%d %b %Y",
        "%d %B %Y",
        "%b %d, %Y",
        "%B %d, %Y",
        "%b %d %Y",
        "%B %d %Y",
    ):
        try:
            return datetime.strptime(normalised, date_format).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"Unsupported U of T deadline date: {value}")


def _slug(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", value.lower())).strip("-")


def _normalise(value: str) -> str:
    return " ".join(value.replace("\u200b", " ").split())
