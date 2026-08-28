from __future__ import annotations

import hashlib
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
ADMISSION_PERIODS_URL = (
    "https://www.meduniwien.ac.at/web/en/studies-further-education/"
    "application-admission/admission-periods/"
)
MOLECULAR_PRECISION_MEDICINE_URL = (
    "https://www.meduniwien.ac.at/web/en/studies-further-education/"
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
    window_watch_urls = (
        ADMISSION_PERIODS_URL,
        MOLECULAR_PRECISION_MEDICINE_URL,
        PSYCHOTHERAPY_URL,
    )
    window_watch_fingerprint_version = 3
    retrieval_method = "official-canonical-programme-registry"
    catalogue_limitation_reason = (
        "MedUni Vienna's three current master's programmes are monitored through "
        "their canonical official pages. Exact windows are recorded only where a "
        "programme page or its linked central admissions source publishes both "
        "dates and the intake."
    )

    def __init__(
        self,
        minimum_expected_programmes: int = 3,
        today: date | None = None,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.today = today or date.today()

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

        try:
            admission_periods_html = fetcher(ADMISSION_PERIODS_URL)
        except Exception as exc:
            raise OfficialSourceTransportError(
                "MedUni Vienna's official admission-periods source was unavailable"
            ) from exc
        if "admission periods" not in _page_text(admission_periods_html).casefold():
            raise ParserZeroResultError(
                "MedUni Vienna's official admission-periods page no longer "
                "identified its admission periods"
            )

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

        informatics_windows = _medical_informatics_windows(
            admission_periods_html,
            today=self.today,
        )
        if informatics_windows:
            _attach_general_admission_periods(
                programmes["Medical Informatics"], informatics_windows
            )

        precision_window = _molecular_precision_medicine_window(
            pages["Molecular Precision Medicine"]
        )
        if precision_window is None and _has_precision_application_date_signal(
            pages["Molecular Precision Medicine"]
        ):
            raise ParserZeroResultError(
                "MedUni Vienna's Molecular Precision Medicine page did not produce "
                "its advertised application period"
            )
        psychotherapy_window = _psychotherapy_window(pages["Psychotherapy"])
        if psychotherapy_window is None and _has_psychotherapy_application_date_signal(
            pages["Psychotherapy"]
        ):
            raise ParserZeroResultError(
                "MedUni Vienna's Psychotherapy page did not produce its advertised "
                "application period"
            )
        if precision_window is not None:
            _attach_window(programmes["Molecular Precision Medicine"], precision_window)
        if psychotherapy_window is not None:
            _attach_window(programmes["Psychotherapy"], psychotherapy_window)
        watched_sections = {
            url: self.window_watch_content(url, content)
            for url, content in (
                (ADMISSION_PERIODS_URL, admission_periods_html),
                (
                    MOLECULAR_PRECISION_MEDICINE_URL,
                    pages["Molecular Precision Medicine"],
                ),
                (PSYCHOTHERAPY_URL, pages["Psychotherapy"]),
            )
        }
        catalog.diagnostics["applicationSectionFingerprints"] = {
            url: hashlib.sha256(section.casefold().encode("utf-8")).hexdigest()
            for url, section in watched_sections.items()
        }
        return catalog

    def window_watch_content(self, url: str, content: str) -> str:
        if url == ADMISSION_PERIODS_URL:
            section = _general_admission_period_fingerprint_text(content)
        elif url == MOLECULAR_PRECISION_MEDICINE_URL:
            section = _precision_application_section(content)
        elif url == PSYCHOTHERAPY_URL:
            section = _psychotherapy_application_section(content)
        else:
            section = ""
        return f"<main>{section}</main>" if section else ""

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


def _attach_general_admission_periods(
    programme: DiscoveredProgramme,
    windows: list[DiscoveredWindow],
) -> None:
    programme.windows = windows
    programme.deadline_text = (
        "The Medical Informatics page directs applicants to MedUni Vienna's "
        "official admission deadlines. These dates are labelled General admission "
        "periods and are not a selective programme application period."
    )
    programme.parse_status = "parsed"


def _medical_informatics_windows(
    html: str,
    *,
    today: date,
) -> list[DiscoveredWindow]:
    windows = []
    for item in _general_admission_period_rows(html):
        closes_at = _iso_date(
            item["close_day"], item["close_month"], item["close_year"]
        )
        if closes_at < today.isoformat():
            continue
        windows.append(
            DiscoveredWindow(
                round="General admission period",
                applicant_categories=["all"],
                opens_at=_iso_date(
                    item["open_day"], item["open_month"], item["open_year"]
                ),
                closes_at=closes_at,
                intake=item["intake"],
                source_url=ADMISSION_PERIODS_URL,
                opens_at_basis="official",
            )
        )
    return windows


def _general_admission_period_rows(html: str) -> list[dict[str, object]]:
    text = _page_text(html)
    pattern = re.compile(
        r"(?P<intake>(?:Winter|Summer) semester 20\d{2}(?:/\d{2})?)\s+"
        r"(?P<open_day>\d{1,2})\s+(?P<open_month>[A-Za-z]+)\s+"
        r"(?P<open_year>20\d{2})\s*[-–—]\s*"
        r"(?P<close_day>\d{1,2})\s+(?P<close_month>[A-Za-z]+)\s+"
        r"(?P<close_year>20\d{2})\s*\|?\s*General admission period\b",
        re.I,
    )
    return [
        {
            "intake": normalise(match.group("intake")),
            "open_day": int(match.group("open_day")),
            "open_month": match.group("open_month"),
            "open_year": int(match.group("open_year")),
            "close_day": int(match.group("close_day")),
            "close_month": match.group("close_month"),
            "close_year": int(match.group("close_year")),
        }
        for match in pattern.finditer(text)
    ]


def _general_admission_period_fingerprint_text(html: str) -> str:
    lines = []
    for item in _general_admission_period_rows(html):
        opens_at = _iso_date(item["open_day"], item["open_month"], item["open_year"])
        closes_at = _iso_date(
            item["close_day"], item["close_month"], item["close_year"]
        )
        lines.append(
            f"{item['intake']}: {opens_at} - {closes_at} General admission period"
        )
    return "\n".join(lines)


def _molecular_precision_medicine_window(html: str) -> DiscoveredWindow | None:
    text = _page_text(html)
    if "start in winter semester" not in text.casefold():
        return None
    application_section = _precision_application_section(html)
    match = re.search(
        r"(?P<open_day>\d{1,2})(?:\s*(?:st|nd|rd|th))?\s+"
        r"(?P<open_month>[A-Za-z]+)\s*[-–—]\s*"
        r"(?P<close_day>\d{1,2})(?:\s*(?:st|nd|rd|th))?\s+"
        r"(?P<close_month>[A-Za-z]+)\s+(?P<year>20\d{2})",
        application_section,
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


def _application_section(text: str) -> str:
    lower = text.casefold()
    # The global navigation repeats this label before the programme content.
    # The final occurrence is the programme-specific application section.
    start = lower.rfind("application & admission")
    if start < 0:
        return ""
    end_candidates = [
        position
        for heading in (
            "language of instruction",
            "admission requirements",
            "tuition fees",
            "curriculum",
            "contact",
        )
        if (position := lower.find(heading, start + 24)) >= 0
    ]
    end = min(end_candidates) if end_candidates else min(len(text), start + 1600)
    return text[start:end]


def _has_precision_application_date_signal(html: str) -> bool:
    section = _precision_application_section(html)
    return bool(
        re.search(
            r"\b\d{1,2}(?:\s*(?:st|nd|rd|th)|\.)?\s+"
            r"[A-Za-zÀ-ſ]+\s+20\d{2}\b",
            section,
            re.I,
        )
    )


def _precision_application_section(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    heading = next(
        (
            item
            for item in soup.select(".program__title")
            if normalise(item.get_text(" ", strip=True)).casefold()
            == "application & admission"
        ),
        None,
    )
    if heading is not None:
        container = heading.find_parent(class_="program__item")
        if container is not None:
            return normalise(container.get_text(" ", strip=True))
    return _application_section(_page_text(html))


def _has_psychotherapy_application_date_signal(html: str) -> bool:
    return bool(
        re.search(
            r"Antragsfrist\s+für\s+das\s+Studienjahr\s+20\d{2}/\d{2}",
            _page_text(html),
            re.I,
        )
    )


def _psychotherapy_application_section(html: str) -> str:
    text = _page_text(html)
    match = re.search(
        r"Antragsfrist\s+für\s+das\s+Studienjahr\s+20\d{2}/\d{2}\s*:\s*"
        r"\d{1,2}\.\s*[A-Za-zÀ-ſ]+\s+bis\s+\d{1,2}\.\s*"
        r"[A-Za-zÀ-ſ]+\s+20\d{2}",
        text,
        re.I,
    )
    return normalise(match.group(0)) if match else ""


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
