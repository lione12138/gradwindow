from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Callable
from datetime import datetime
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .base import (
    BaseProgrammeAdapter,
    DiscoveredCatalog,
    DiscoveredProgramme,
    DiscoveredWindow,
)

UNIVERSITY_ID = "princeton-university"
CATALOG_URL = (
    "https://gradschool.princeton.edu/academics/degrees-requirements/fields-study"
)
DEADLINES_URL = "https://gradschool.princeton.edu/admission-onboarding/prepare/application-deadlines"
APPLICATION_URL = "https://gradschool.princeton.edu/admission-onboarding/apply"
EXISTING_COMPUTER_SCIENCE_ID = "princeton-computer-science-mse"

_MONTHS = (
    "January|February|March|April|May|June|July|August|September|October|"
    "November|December"
)
_DATE_RE = re.compile(
    rf"(?P<month>{_MONTHS})\s+(?P<day>\d{{1,2}})(?:,\s*(?P<year>20\d{{2}}))?",
    re.I,
)
_DEGREE_RE = re.compile(
    r"M\.Arch\.|M\.S\.E\.|M\.Eng\.|M\.Fin\.|M\.P\.A\.|M\.P\.P\.|M\.S\."
)
_MARKDOWN_ROW_RE = re.compile(
    r"^\|\s*\[(?P<name>[^]]+)\]\((?P<url>https?://[^)]+)\)\s*\|"
    r"\s*(?P<offerings>[^|]+)\|",
    re.M,
)
_OPENING_POLICY_RE = re.compile(
    rf"application for Fall (?P<intake>20\d{{2}}) will open (?:in|on) "
    rf"(?P<month>{_MONTHS})(?:\s+(?P<day>\d{{1,2}}),?)?\s+"
    rf"(?P<year>20\d{{2}})",
    re.I,
)
_DEGREE_TYPES = {
    "M.Arch.": "MARCH",
    "M.S.E.": "MSE",
    "M.Eng.": "MENG",
    "M.Fin.": "MFIN",
    "M.P.A.": "MPA",
    "M.P.P.": "MPP",
    "M.S.": "MS",
}
RESTRICTED_MASTER_POLICIES = {
    "Chemistry": (
        "The Chemistry M.S. is restricted to employees of firms with active "
        "membership in Princeton's Industrial Associates Program."
    )
}


class PrincetonAdapter(BaseProgrammeAdapter):
    """Discover Princeton's terminal master's programmes and deadline evidence."""

    university_id = UNIVERSITY_ID
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Fall admission"
    application_opens_at_basis = "official"
    replace_pending_candidates = True
    browser_fallback_limit = 2
    window_watch_urls = (DEADLINES_URL,)

    def __init__(self, minimum_expected_programmes: int = 13) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(
        self,
        fetcher: Callable[[str], str],
    ) -> DiscoveredCatalog:
        catalog_document = fetcher(CATALOG_URL)
        policy_document = fetcher(DEADLINES_URL)
        opening_policy = _next_cycle_opening_policy(policy_document)
        deadline_rows = _deadline_rows(policy_document, opening_policy["intake_year"])
        records = _catalogue_records(catalog_document)

        programmes = []
        for record in records:
            for degree_label in record["degrees"]:
                closes_at = _central_closing_date(
                    deadline_rows,
                    department=record["name"],
                    degree_label=degree_label,
                )
                programmes.append(
                    _programme(
                        department=record["name"],
                        degree_label=degree_label,
                        source_url=record["source_url"],
                        closes_at=closes_at,
                        intake_year=opening_policy["intake_year"],
                        opening_policy=opening_policy,
                        evidence_document=f"{catalog_document}\n{policy_document}",
                    )
                )

        programmes = sorted(
            {programme.id: programme for programme in programmes}.values(),
            key=lambda item: item.id,
        )
        if len(programmes) < self.minimum_expected_programmes:
            raise ValueError(
                "Princeton's official catalogue only contained "
                f"{len(programmes)} master's programmes; expected at least "
                f"{self.minimum_expected_programmes}"
            )
        intake_year = opening_policy["intake_year"]
        self.intake = f"Fall {intake_year}"
        return DiscoveredCatalog(application_opens_at=None, programmes=programmes)


def _catalogue_records(document: str) -> list[dict[str, object]]:
    records = _markdown_catalogue_records(document)
    if not records and "<" in document[:1000]:
        records = _html_catalogue_records(document)
    if not records:
        raise ValueError("Princeton's official Fields of Study table was not found")
    return records


def _markdown_catalogue_records(document: str) -> list[dict[str, object]]:
    records = []
    for match in _MARKDOWN_ROW_RE.finditer(document):
        degrees = _master_degrees(match.group("offerings"))
        if not degrees:
            continue
        records.append(
            {
                "name": _normalise(match.group("name")),
                "source_url": _official_url(match.group("url")),
                "degrees": degrees,
            }
        )
    return records


def _html_catalogue_records(document: str) -> list[dict[str, object]]:
    soup = BeautifulSoup(document, "html.parser")
    records = []
    for row in soup.select("tr"):
        cells = row.find_all(["td", "th"], recursive=False)
        if len(cells) < 2:
            continue
        link = cells[0].find("a", href=True)
        if link is None:
            continue
        degrees = _master_degrees(cells[1].get_text(" ", strip=True))
        if not degrees:
            continue
        records.append(
            {
                "name": _normalise(link.get_text(" ", strip=True)),
                "source_url": _official_url(urljoin(CATALOG_URL, link["href"])),
                "degrees": degrees,
            }
        )
    return records


def _official_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.hostname != "gradschool.princeton.edu":
        raise ValueError(f"Princeton catalogue contained a non-official URL: {value}")
    return parsed._replace(scheme="https", query="", fragment="").geturl()


def _master_degrees(value: str) -> list[str]:
    return list(dict.fromkeys(_DEGREE_RE.findall(value)))


def _document_text(document: str) -> str:
    if "<html" in document[:1000].lower() or "<main" in document[:1000].lower():
        document = BeautifulSoup(document, "html.parser").get_text("\n", strip=True)
    return _normalise(document)


def _next_cycle_opening_policy(document: str) -> dict[str, object]:
    text = _document_text(document)
    match = _OPENING_POLICY_RE.search(text)
    if match is None:
        raise ValueError("Princeton's official next application cycle was not found")
    exact_date = None
    if match.group("day"):
        exact_date = (
            datetime.strptime(
                f"{match.group('month')} {match.group('day')} {match.group('year')}",
                "%B %d %Y",
            )
            .date()
            .isoformat()
        )
    if exact_date is None:
        raise ValueError(
            "Princeton's official next application cycle has no exact opening date"
        )
    return {
        "intake_year": int(match.group("intake")),
        "text": _normalise(match.group(0)),
        "exact_date": exact_date,
    }


def _deadline_rows(document: str, intake_year: int) -> list[dict[str, str]]:
    rows = []
    if "<" in document[:1000]:
        soup = BeautifulSoup(document, "html.parser")
        for row in soup.select("tr"):
            cells = row.find_all(["th", "td"], recursive=False)
            if len(cells) < 2:
                continue
            field_items = [
                item.get_text(" ", strip=True) for item in cells[1].select("li")
            ]
            if not field_items:
                field_items = [
                    item.strip()
                    for item in cells[1].get_text(" ", strip=True).split(",")
                    if item.strip()
                ]
            for field_item in field_items:
                _append_deadline_row(
                    rows,
                    cells[0].get_text(" ", strip=True),
                    field_item,
                    intake_year,
                )
    else:
        for line in document.splitlines():
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) >= 2:
                _append_deadline_row(rows, cells[0], cells[1], intake_year)
    if not rows:
        raise ValueError("Princeton's central deadline table was not found")
    return rows


def _append_deadline_row(
    rows: list[dict[str, str]], date_text: str, fields_text: str, intake_year: int
) -> None:
    match = _DATE_RE.search(date_text)
    if match is None:
        return
    month = datetime.strptime(match.group("month"), "%B").month
    year = int(match.group("year") or (intake_year - 1 if month >= 7 else intake_year))
    closes_at = datetime(year, month, int(match.group("day"))).date().isoformat()
    rows.append({"closes_at": closes_at, "fields": _normalise(fields_text)})


def _central_closing_date(
    rows: list[dict[str, str]], *, department: str, degree_label: str
) -> str:
    for row in rows:
        fields = row["fields"]
        if department.casefold() not in fields.casefold():
            continue
        explicit_degrees = _master_degrees(fields)
        if explicit_degrees and degree_label not in explicit_degrees:
            continue
        if "ph.d." in fields.lower() and degree_label not in explicit_degrees:
            continue
        return row["closes_at"]
    raise ValueError(
        "Princeton's central deadline table did not contain "
        f"{department} {degree_label}"
    )


def _programme(
    *,
    department: str,
    degree_label: str,
    source_url: str,
    closes_at: str,
    intake_year: int,
    opening_policy: dict[str, object],
    evidence_document: str,
) -> DiscoveredProgramme:
    degree_type = _DEGREE_TYPES[degree_label]
    department_slug = _slug(department)
    if department_slug.startswith("princeton-"):
        department_slug = department_slug.removeprefix("princeton-")
    programme_id = f"princeton-{department_slug}-{degree_type.lower()}"
    if department == "Computer Science" and degree_type == "MSE":
        programme_id = EXISTING_COMPUTER_SCIENCE_ID
    name = f"{degree_label} in {department}"
    if programme_id == EXISTING_COMPUTER_SCIENCE_ID:
        name = "MSE in Computer Science"
    policy_text = str(opening_policy["text"])
    restriction = RESTRICTED_MASTER_POLICIES.get(department)
    return DiscoveredProgramme(
        id=programme_id,
        name=name,
        degree_type=degree_type,
        faculty="Princeton University Graduate School",
        department=department,
        source_url=source_url,
        application_url=APPLICATION_URL,
        windows=[
            DiscoveredWindow(
                round="Main deadline",
                closes_at=closes_at,
                opens_at=str(opening_policy["exact_date"]),
                intake=f"Fall {intake_year}",
                source_url=DEADLINES_URL,
                opens_at_basis="official",
            )
        ],
        deadline_text=(
            f"Princeton lists Fall {intake_year} applications as opening on "
            f"{opening_policy['exact_date']} and the {degree_label} deadline as "
            f"{closes_at}. {policy_text}."
            + (f" Restricted route: {restriction}" if restriction else "")
        ),
        parse_status="parsed",
        retrieval_method="official-html",
        evidence_quality="official-full-text",
        evidence_document_hash=hashlib.sha256(
            evidence_document.encode("utf-8")
        ).hexdigest(),
        admission_route="restricted-master" if restriction else "direct-master",
    )


def _slug(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    )
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", ascii_value.lower())).strip(
        "-"
    )


def _normalise(value: str) -> str:
    return " ".join(str(value).replace("\u00a0", " ").split())
