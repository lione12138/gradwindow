from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import date, datetime
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .base import (
    DiscoveredCatalog,
    DiscoveredProgramme,
    DiscoveredWindow,
    Fetcher,
)
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise, slug

CATALOG_URL = "https://www.tufts.edu/graduate-programs"
APPLICATION_URL = "https://www.tufts.edu/admissions/graduate"
DEADLINES_URL = "https://asegrad.tufts.edu/applying/application-deadlines"

_TERM_START_MONTHS = {"Spring": 1, "Summer": 6, "Fall": 9}
_DEADLINE_RE = re.compile(
    r"(?P<rolling>rolling through\s+)?"
    r"(?P<month>January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+(?P<day>\d{1,2})"
    r"(?:\s*\((?P<label>[^)]+)\))?",
    re.I,
)


@dataclass(frozen=True, slots=True)
class TuftsEntry(CatalogEntry):
    faculty: str


class TuftsAdapter(OfficialCatalogAdapter):
    university_id = "tufts-university"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "tufts"
    institution_name = "Tufts University"
    window_watch_urls = (DEADLINES_URL,)
    retrieval_method = "official-paginated-graduate-programmes-directory"
    browser_fallback_limit = 2
    catalogue_limitation_reason = (
        "Tufts' university-wide directory supplies canonical identities. The "
        "central A&S/Engineering table supplies recurring month-and-day deadlines; "
        "other graduate schools remain programme-level deadline monitors."
    )

    def __init__(
        self,
        minimum_expected_programmes: int = 93,
        minimum_expected_deadline_programmes: int = 50,
        reference_date: date | None = None,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.minimum_expected_deadline_programmes = minimum_expected_deadline_programmes
        self.reference_date = reference_date or date.today()

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        entries: list[TuftsEntry] = []
        next_url: str | None = CATALOG_URL
        seen: set[str] = set()
        while next_url and next_url not in seen:
            seen.add(next_url)
            html = fetcher(next_url)
            entries.extend(self.extract_entries(html))
            next_url = _next_page_url(html, next_url)
        if len(entries) < self.minimum_expected_programmes:
            raise ValueError(
                f"Tufts' catalogue contained {len(entries)} master's programmes; "
                f"expected at least {self.minimum_expected_programmes}"
            )

        deadline_document = fetcher(DEADLINES_URL)
        deadline_rows = _deadline_rows(deadline_document)
        matched_deadline_programmes = sum(
            _source_key(item.source_url) in deadline_rows for item in entries
        )
        if matched_deadline_programmes < self.minimum_expected_deadline_programmes:
            raise ValueError(
                "Tufts' central deadline table matched "
                f"{matched_deadline_programmes} master's programme(s); expected at "
                f"least {self.minimum_expected_deadline_programmes}"
            )

        evidence_hash = hashlib.sha256(deadline_document.encode()).hexdigest()
        programmes = []
        for item in entries:
            deadline_row = deadline_rows.get(_source_key(item.source_url), {})
            windows = [
                window
                for term, value in deadline_row.items()
                for window in _deadline_windows(
                    term,
                    value,
                    source_url=DEADLINES_URL,
                    reference_date=self.reference_date,
                )
            ]
            programme_id = f"tufts-{slug(item.name)}-master"
            if windows:
                dates = ", ".join(
                    f"{window.intake} {window.round}: {window.closes_at}"
                    for window in windows
                )
                deadline_text = (
                    "Tufts' official A&S/Engineering recurring deadline table "
                    f"lists {dates}. The cycle years are deterministically mapped "
                    "to the next applicable intake, and no exact opening date is "
                    "published."
                )
                parse_status = "incomplete"
                document_hash = evidence_hash
            else:
                deadline_text = (
                    "Programme found in Tufts' official university-wide directory. "
                    "No matching complete exact opening-and-closing window was "
                    "published in the checked central A&S/Engineering table."
                )
                parse_status = "no-deadline"
                document_hash = None
            programmes.append(
                DiscoveredProgramme(
                    id=programme_id,
                    name=item.name,
                    degree_type="Master",
                    faculty=item.faculty,
                    department=item.faculty,
                    source_url=item.source_url,
                    application_url=APPLICATION_URL,
                    windows=windows,
                    deadline_text=deadline_text,
                    parse_status=parse_status,
                    retrieval_method=(
                        "official-directory-and-central-deadline-table"
                        if windows
                        else self.retrieval_method
                    ),
                    evidence_quality="official-full-text",
                    evidence_document_hash=document_hash,
                )
            )
        programmes.sort(key=lambda item: item.name.casefold())
        return DiscoveredCatalog(application_opens_at=None, programmes=programmes)

    def extract_entries(self, html: str) -> list[TuftsEntry]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        for card in soup.select("article.node--type-program"):
            title = card.select_one("h4.program--title")
            degree = card.select_one(".program--degree")
            school = card.select_one(".icon-program--schools")
            link = card.select_one("a.program--cta[href]")
            if title is None or degree is None or link is None:
                continue
            degree_text = normalise(degree.get_text(" ", strip=True))
            label = normalise(title.get_text(" ", strip=True))
            if "master" not in degree_text.casefold() or re.search(
                r"\s+-\s+Doctorate$", label, re.I
            ):
                continue
            name = re.sub(
                r"\s+-\s+Master(?:'s|’s)(?: and Doctorate)?$", "", label
            ).strip()
            rows.append(
                TuftsEntry(
                    name=name,
                    degree_type="Master",
                    source_url=_canonical_source_url(
                        urljoin(CATALOG_URL, str(link["href"]))
                    ),
                    faculty=(
                        normalise(school.get_text(" ", strip=True))
                        if school
                        else self.institution_name
                    ),
                )
            )
        return rows


def _next_page_url(html: str, current_url: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    link = soup.select_one('a[rel~="next"][href]')
    return urljoin(current_url, str(link["href"])) if link else None


def _deadline_rows(document: str) -> dict[str, dict[str, str]]:
    soup = BeautifulSoup(document, "html.parser")
    rows = {}
    for table in soup.select("table"):
        headers = [
            normalise(cell.get_text(" ", strip=True))
            for cell in table.select("thead th")
        ]
        if headers[:4] != ["Program", "Fall", "Spring", "Summer"]:
            continue
        for row in table.select("tbody tr"):
            cells = row.find_all(["th", "td"], recursive=False)
            link = cells[0].find("a", href=True) if cells else None
            if len(cells) != len(headers) or link is None:
                continue
            source_url = urljoin(DEADLINES_URL, str(link["href"]))
            if "master" not in urlparse(source_url).path.casefold():
                continue
            rows[_source_key(source_url)] = {
                header: normalise(cell.get_text(" ", strip=True))
                for header, cell in zip(headers[1:], cells[1:], strict=True)
                if normalise(cell.get_text(" ", strip=True)).casefold() != "n/a"
            }
    return rows


def _deadline_windows(
    term: str,
    value: str,
    *,
    source_url: str,
    reference_date: date,
) -> list[DiscoveredWindow]:
    if term not in _TERM_START_MONTHS:
        return []
    matches = list(_DEADLINE_RE.finditer(value))
    if not matches:
        return []
    intake_year = (
        reference_date.year
        if reference_date < date(reference_date.year, _TERM_START_MONTHS[term], 1)
        else reference_date.year + 1
    )
    windows = _materialise_windows(term, intake_year, matches, source_url)
    if (
        windows
        and max(window.closes_at for window in windows) < reference_date.isoformat()
    ):
        intake_year += 1
        windows = _materialise_windows(term, intake_year, matches, source_url)
    return windows


def _materialise_windows(
    term: str,
    intake_year: int,
    matches: list[re.Match[str]],
    source_url: str,
) -> list[DiscoveredWindow]:
    start_month = _TERM_START_MONTHS[term]
    windows = []
    for match in matches:
        month = datetime.strptime(match.group("month"), "%B").month
        deadline_year = intake_year - 1 if month > start_month else intake_year
        closes_at = date(deadline_year, month, int(match.group("day"))).isoformat()
        if match.group("rolling"):
            round_name = "Rolling final deadline"
        elif label := match.group("label"):
            round_name = f"{normalise(label).capitalize()} deadline"
        else:
            round_name = "Published deadline"
        windows.append(
            DiscoveredWindow(
                round=round_name,
                closes_at=closes_at,
                intake=f"{term} {intake_year}",
                source_url=source_url,
            )
        )
    return windows


def _canonical_source_url(value: str) -> str:
    value = re.split(r"[?&]utm_", value, maxsplit=1, flags=re.I)[0]
    parsed = urlparse(value)
    return parsed._replace(
        scheme="https",
        query="",
        fragment="",
        path=parsed.path.rstrip("/"),
    ).geturl()


def _source_key(value: str) -> str:
    parsed = urlparse(_canonical_source_url(value))
    return f"{(parsed.hostname or '').casefold()}{parsed.path.casefold()}"
