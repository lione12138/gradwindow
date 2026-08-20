from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from bs4 import BeautifulSoup

from .base import (
    DiscoveredCatalog,
    DiscoveredProgramme,
    DiscoveredWindow,
    Fetcher,
    OfficialSourceTransportError,
    ParserZeroResultError,
)
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = (
    "https://www.meduniwien.ac.at/web/en/studies-further-education/study-programmes/"
)
MEDICAL_INFORMATICS_URL = (
    "https://www.meduniwien.ac.at/web/en/studies-further-education/"
    "application-admission/masters-programme-in-medical-informatics/"
)
MOLECULAR_PRECISION_MEDICINE_URL = (
    "https://t310-web.meduniwien.ac.at/web/en/studies-further-education/"
    "the-molecular-precision-medicine-masters-programme/"
)
PSYCHOTHERAPY_URL = (
    "https://www.meduniwien.ac.at/web/studierende/mein-studium/"
    "masterstudium-psychotherapie/"
)
APPLICATION_URL = CATALOG_URL


@dataclass(frozen=True, slots=True)
class KnownProgramme:
    name: str
    source_url: str
    page_signal: str


KNOWN_PROGRAMMES = (
    KnownProgramme(
        name="Medical Informatics",
        source_url=MEDICAL_INFORMATICS_URL,
        page_signal="medical informatics",
    ),
    KnownProgramme(
        name="Molecular Precision Medicine",
        source_url=MOLECULAR_PRECISION_MEDICINE_URL,
        page_signal="molecular precision medicine",
    ),
    KnownProgramme(
        name="Psychotherapy",
        source_url=PSYCHOTHERAPY_URL,
        page_signal="masterstudium psychotherapie",
    ),
)


class MedUniViennaAdapter(OfficialCatalogAdapter):
    university_id = "medical-university-of-vienna"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "meduni-vienna"
    institution_name = "Medical University of Vienna"
    minimum_expected_programmes = 3
    window_watch_urls = tuple(item.source_url for item in KNOWN_PROGRAMMES)
    retrieval_method = "official-canonical-programme-registry"
    catalogue_limitation_reason = (
        "MedUni Vienna's three current master's programmes are monitored through "
        "their canonical official pages. Exact windows are recorded only where a "
        "programme page publishes both dates and the intake."
    )

    def __init__(self, minimum_expected_programmes: int = 3) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        pages: dict[str, str] = {}
        for programme in KNOWN_PROGRAMMES:
            try:
                pages[programme.name] = fetcher(programme.source_url)
            except Exception as exc:
                raise OfficialSourceTransportError(
                    f"MedUni Vienna's canonical {programme.name} catalogue source "
                    "was unavailable"
                ) from exc

        for programme in KNOWN_PROGRAMMES:
            text = _page_text(pages[programme.name])
            if programme.page_signal not in text.casefold():
                raise ParserZeroResultError(
                    f"MedUni Vienna's canonical {programme.name} page no longer "
                    "identified the expected programme"
                )

        catalog = self._catalog(
            [
                CatalogEntry(
                    name=programme.name,
                    degree_type="Master",
                    source_url=programme.source_url,
                )
                for programme in KNOWN_PROGRAMMES
            ]
        )
        programmes = {programme.name: programme for programme in catalog.programmes}
        for known in KNOWN_PROGRAMMES:
            programmes[known.name].application_url = known.source_url

        precision_window = _molecular_precision_medicine_window(
            pages["Molecular Precision Medicine"]
        )
        if precision_window is None and _has_date_signal(
            pages["Molecular Precision Medicine"]
        ):
            raise ParserZeroResultError(
                "MedUni Vienna's Molecular Precision Medicine page did not produce "
                "its advertised application period"
            )
        psychotherapy_window = _psychotherapy_window(pages["Psychotherapy"])
        if psychotherapy_window is None and _has_date_signal(pages["Psychotherapy"]):
            raise ParserZeroResultError(
                "MedUni Vienna's Psychotherapy page did not produce its advertised "
                "application period"
            )
        if precision_window is not None:
            _attach_window(programmes["Molecular Precision Medicine"], precision_window)
        if psychotherapy_window is not None:
            _attach_window(programmes["Psychotherapy"], psychotherapy_window)
        return catalog

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        """Retained for the base parser contract; live discovery uses URLs."""
        text = _page_text(html).casefold()
        return [
            CatalogEntry(
                name=programme.name,
                degree_type="Master",
                source_url=programme.source_url,
            )
            for programme in KNOWN_PROGRAMMES
            if programme.page_signal in text
        ]


def _attach_window(programme: DiscoveredProgramme, window: DiscoveredWindow) -> None:
    programme.windows = [window]
    programme.deadline_text = (
        "The canonical official programme page publishes an exact application "
        "opening date, closing date, and intake."
    )
    programme.parse_status = "parsed"


def _molecular_precision_medicine_window(html: str) -> DiscoveredWindow | None:
    text = _page_text(html)
    if "start in winter semester" not in text.casefold():
        return None
    match = re.search(
        r"(?P<open_day>\d{1,2})(?:\s*(?:st|nd|rd|th))?\s+"
        r"(?P<open_month>[A-Za-z]+)\s*[-–—]\s*"
        r"(?P<close_day>\d{1,2})(?:\s*(?:st|nd|rd|th))?\s+"
        r"(?P<close_month>[A-Za-z]+)\s+(?P<year>20\d{2})",
        text,
        re.I,
    )
    if match is None:
        return None
    year = int(match.group("year"))
    return DiscoveredWindow(
        round="Annual application period",
        applicant_categories=["all"],
        opens_at=_iso_date(
            int(match.group("open_day")), match.group("open_month"), year
        ),
        closes_at=_iso_date(
            int(match.group("close_day")), match.group("close_month"), year
        ),
        intake=f"Winter semester {year}",
        source_url=MOLECULAR_PRECISION_MEDICINE_URL,
        opens_at_basis="official",
    )


def _psychotherapy_window(html: str) -> DiscoveredWindow | None:
    text = _page_text(html)
    match = re.search(
        r"Antragsfrist\s+für\s+das\s+Studienjahr\s+"
        r"(?P<intake>20\d{2}/\d{2})\s*:\s*"
        r"(?P<open_day>\d{1,2})\.\s*(?P<open_month>[A-Za-zÀ-ſ]+)\s+"
        r"bis\s+(?P<close_day>\d{1,2})\.\s*"
        r"(?P<close_month>[A-Za-zÀ-ſ]+)\s+(?P<year>20\d{2})",
        text,
        re.I,
    )
    if match is None:
        return None
    year = int(match.group("year"))
    return DiscoveredWindow(
        round="Application period",
        applicant_categories=["all"],
        opens_at=_iso_date(
            int(match.group("open_day")), match.group("open_month"), year
        ),
        closes_at=_iso_date(
            int(match.group("close_day")), match.group("close_month"), year
        ),
        intake=f"Academic year {match.group('intake')}",
        source_url=PSYCHOTHERAPY_URL,
        opens_at_basis="official",
    )


def _page_text(html: str) -> str:
    return normalise(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))


def _has_date_signal(html: str) -> bool:
    return bool(
        re.search(
            r"\b\d{1,2}(?:\s*(?:st|nd|rd|th)|\.)?\s+"
            r"[A-Za-zÀ-ſ]+\s+20\d{2}\b",
            _page_text(html),
            re.I,
        )
    )


def _iso_date(day: int, month: str, year: int) -> str:
    month_number = {
        "january": 1,
        "february": 2,
        "march": 3,
        "märz": 3,
        "april": 4,
        "may": 5,
        "june": 6,
        "july": 7,
        "august": 8,
        "september": 9,
        "october": 10,
        "november": 11,
        "december": 12,
    }.get(month.casefold())
    if month_number is None:
        raise ParserZeroResultError(f"Unknown MedUni Vienna month: {month}")
    return date(year, month_number, day).isoformat()
