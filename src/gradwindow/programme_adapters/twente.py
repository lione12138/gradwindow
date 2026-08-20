from __future__ import annotations

import re
from dataclasses import replace
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .base import (
    DiscoveredCatalog,
    DiscoveredWindow,
    Fetcher,
    OfficialSourceTransportError,
    ParserZeroResultError,
)
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = "https://www.utwente.nl/en/education/master/programmes/"
APPLICATION_URL = (
    "https://www.utwente.nl/en/education/master/application-admission/master-deadlines/"
)
DEVIATING_PROGRAMMES = {
    "geo-information science and earth observation",
    "geographical information management and applications",
    "psychology",
}


class TwenteAdapter(OfficialCatalogAdapter):
    university_id = "university-of-twente"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "twente"
    institution_name = "University of Twente"
    minimum_expected_programmes = 30
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-masters-study-finder"
    catalogue_limitation_reason = (
        "Twente's official study finder provides the master's catalogue. The "
        "standard EEA and non-EEA application periods are published as annual "
        "rules; programmes explicitly listed with deviating deadlines are kept "
        "in monitoring until their separate rules are parsed."
    )

    def __init__(
        self,
        minimum_expected_programmes: int = 30,
        target_cycle_year: int | None = None,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.target_cycle_year = target_cycle_year or (
            datetime.now(timezone.utc).year + 1
        )

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalog = self.parse_catalog(fetcher(CATALOG_URL))
        try:
            deadlines_html = fetcher(APPLICATION_URL)
        except Exception as exc:
            raise OfficialSourceTransportError(
                "Twente's critical official master-deadline source was unavailable"
            ) from exc
        windows = _application_windows(deadlines_html, self.target_cycle_year)
        if not windows:
            raise ParserZeroResultError(
                "Twente's official deadline page produced zero standard EEA and "
                "non-EEA application windows."
            )
        for programme in catalog.programmes:
            if programme.name.casefold() in DEVIATING_PROGRAMMES:
                continue
            programme.windows = [
                replace(
                    window,
                    applicant_categories=list(window.applicant_categories),
                )
                for window in windows
            ]
            programme.deadline_text = (
                "Twente's official master-deadline page publishes annual "
                "application periods by intake and EEA/non-EEA nationality."
            )
            programme.parse_status = "recurring-policy"
        return catalog

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        for link in soup.select("a.studyfinder__programme__link[href]"):
            href = str(link["href"])
            if "/specialisation/" in href or "/specialisations/" in href:
                continue
            title = link.select_one(".studyfinder__programme__title__text")
            degree = link.select_one(".studyfinder__programme__metadata .degree")
            if title is None or degree is None:
                continue
            degree_type = normalise(degree.get_text(" ", strip=True))
            if degree_type.casefold() != "msc":
                continue
            source_url = urljoin(CATALOG_URL, href)
            hostname = (urlparse(source_url).hostname or "").casefold()
            if hostname != "utwente.nl" and not hostname.endswith(".utwente.nl"):
                source_url = CATALOG_URL
            rows.append(
                CatalogEntry(
                    name=normalise(title.get_text(" ", strip=True)),
                    degree_type=degree_type,
                    source_url=source_url,
                )
            )
        return rows


def _application_windows(html: str, cycle_year: int) -> list[DiscoveredWindow]:
    soup = BeautifulSoup(html, "html.parser")
    definitions = []
    for table in soup.find_all("table"):
        container = table.find_parent(class_="wh-form__richtext") or table.parent
        context = normalise(container.get_text(" ", strip=True)).casefold()
        if "non-eea" in context:
            category = "non-eu-efta"
        elif "eea nationality" in context and "non-dutch" in context:
            category = "eu-efta"
        else:
            continue
        rows = [
            [normalise(cell.get_text(" ", strip=True)) for cell in row.find_all("td")]
            for row in table.find_all("tr")
        ]
        if not rows or len(rows[0]) < 3:
            continue
        intakes = rows[0][1:3]
        opening_row = next(
            (
                row
                for row in rows[1:]
                if row and "start your application" in row[0].casefold()
            ),
            None,
        )
        deadline_row = next(
            (
                row
                for row in rows[1:]
                if row and "deadline completed application" in row[0].casefold()
            ),
            None,
        )
        if opening_row is None or deadline_row is None:
            continue
        for index, intake_label in enumerate(intakes, start=1):
            intake_month = (
                "September"
                if "september" in intake_label.casefold()
                else ("February" if "february" in intake_label.casefold() else "")
            )
            if (
                not intake_month
                or len(opening_row) <= index
                or len(deadline_row) <= index
            ):
                continue
            opening_year = cycle_year - 1
            deadline_year = (
                cycle_year if intake_month == "September" else cycle_year - 1
            )
            definitions.append(
                DiscoveredWindow(
                    round="Standard application deadline",
                    applicant_categories=[category],
                    opens_at=_annual_date(opening_row[index], opening_year),
                    closes_at=_annual_date(deadline_row[index], deadline_year),
                    intake=f"{intake_month} {cycle_year}",
                    source_url=APPLICATION_URL,
                    opens_at_basis="official-recurring-policy",
                    deadline_semantics=(
                        "before"
                        if deadline_row[index].casefold().startswith("before ")
                        else "on"
                    ),
                )
            )
    return sorted(
        definitions,
        key=lambda window: (window.intake or "", window.applicant_categories),
    )


def _annual_date(value: str, year: int) -> str:
    match = re.search(
        r"(?P<day>\d{1,2})\s+"
        r"(?P<month>January|February|March|April|May|June|July|August|"
        r"September|October|November|December)",
        value,
        re.I,
    )
    if match is None:
        raise ParserZeroResultError(
            f"Twente deadline table contained an invalid annual date: {value}"
        )
    return (
        datetime.strptime(
            f"{match.group('day')} {match.group('month')} {year}",
            "%d %B %Y",
        )
        .date()
        .isoformat()
    )
