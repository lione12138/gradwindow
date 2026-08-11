from __future__ import annotations

import re
from datetime import datetime

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, DiscoveredProgramme, DiscoveredWindow, Fetcher
from .official_catalog import normalise, slug

CATALOG_URL = (
    "https://www.mdanderson.org/education-training/degree-granting-schools.html"
)
APPLICATION_URL = "https://apply.uth.edu/"
_BASE = (
    "https://www.mdanderson.org/education-training/degree-granting-schools/"
    "school-of-health-professions/prospective-students/"
)
DIAGNOSTIC_URL = f"{_BASE}diagnostic-genetics-application.html"
DOSIMETRY_URL = f"{_BASE}medical-dosimetry-application.html"
RADIOLOGIC_URL = f"{_BASE}radiologic-sciences-application.html"
_PROGRAMMES = {
    "Diagnostic Genetics and Genomics",
    "M.S. in Medical Dosimetry",
    "Radiologic Sciences",
    "Individualized MS Program in Biomedical Sciences",
    "Genetic Counseling",
    "Medical Physics",
}


class MDAndersonAdapter:
    university_id = "university-of-texas-md-anderson-cancer-center"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "official"
    replace_pending_candidates = True
    window_watch_urls = (
        CATALOG_URL,
        DIAGNOSTIC_URL,
        DOSIMETRY_URL,
        RADIOLOGIC_URL,
    )
    retrieval_method = "official-degree-programme-and-application-pages"

    def __init__(self, minimum_expected_programmes: int = 6) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        rows = _catalogue_rows(fetcher(CATALOG_URL))
        if len(rows) < self.minimum_expected_programmes:
            raise ValueError(
                f"MD Anderson catalogue contained {len(rows)} master's programmes; "
                f"expected at least {self.minimum_expected_programmes}"
            )
        windows = {
            "Diagnostic Genetics and Genomics": _diagnostic_windows(
                fetcher(DIAGNOSTIC_URL)
            ),
            "M.S. in Medical Dosimetry": _dosimetry_windows(fetcher(DOSIMETRY_URL)),
            "Radiologic Sciences": _radiologic_windows(fetcher(RADIOLOGIC_URL)),
        }
        programmes: list[DiscoveredProgramme] = []
        for name, source_url in rows:
            programme_windows = windows.get(name, [])
            programme_id = f"md-anderson-{slug(name)}-master"
            programmes.append(
                DiscoveredProgramme(
                    id=programme_id,
                    name=name,
                    degree_type="MS",
                    faculty=(
                        "School of Health Professions"
                        if name in windows
                        else "MD Anderson UTHealth Houston Graduate School"
                    ),
                    department=name,
                    source_url=source_url,
                    application_url=(
                        programme_windows[0].source_url
                        if programme_windows
                        and programme_windows[0].source_url is not None
                        else APPLICATION_URL
                    ),
                    windows=programme_windows,
                    deadline_text=(
                        "Exact application dates are published on the official "
                        "programme application page."
                        if programme_windows
                        else "The official catalogue lists this MS programme, but "
                        "no programme-specific pair of exact opening and closing "
                        "dates was verified, so no dates are inferred."
                    ),
                    parse_status="parsed" if programme_windows else "no-deadline",
                    retrieval_method=self.retrieval_method,
                    evidence_quality="official-full-text",
                )
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=programmes)


def _catalogue_rows(html: str) -> list[tuple[str, str]]:
    rows: dict[str, str] = {}
    soup = BeautifulSoup(html, "html.parser")
    for heading in soup.select("h4"):
        name = normalise(heading.get_text(" ", strip=True))
        if name not in _PROGRAMMES:
            continue
        link = heading.find_parent("a", href=True)
        if link is None:
            continue
        rows[name] = str(link["href"]).strip()
    return sorted(rows.items(), key=lambda item: item[0].casefold())


def _diagnostic_windows(html: str) -> list[DiscoveredWindow]:
    text = _text(html)
    match = re.search(
        r"Fall 2026 Admission.*?"
        r"(?P<open>Sept\.?\s+15,\s*2025)\s+Applications open.*?"
        r"(?P<priority>April\s+30,\s*2026)\s+Priority applications deadline.*?"
        r"(?P<close>May\s+30,\s*2026)\s+Applications close",
        text,
        re.IGNORECASE,
    )
    if match is None:
        raise ValueError("MD Anderson DGG page did not expose its exact dates")
    opens_at = _date(match.group("open"))
    return [
        _window(
            "Priority deadline",
            opens_at,
            _date(match.group("priority")),
            "Fall 2026",
            DIAGNOSTIC_URL,
        ),
        _window(
            "Final deadline",
            opens_at,
            _date(match.group("close")),
            "Fall 2026",
            DIAGNOSTIC_URL,
        ),
    ]


def _dosimetry_windows(html: str) -> list[DiscoveredWindow]:
    text = _text(html)
    match = re.search(
        r"Fall 2027 Admission Process\s+Accepting applications\s+"
        r"(?P<open>Dec\.?\s+1,\s*2026)\s+Application deadline\s+"
        r"(?P<close>March\s+15,\s*2027)",
        text,
        re.IGNORECASE,
    )
    if match is None:
        raise ValueError("MD Anderson dosimetry page did not expose its exact dates")
    return [
        _window(
            "Fall admission",
            _date(match.group("open")),
            _date(match.group("close")),
            "Fall 2027",
            DOSIMETRY_URL,
        )
    ]


def _radiologic_windows(html: str) -> list[DiscoveredWindow]:
    text = _text(html)
    match = re.search(
        r"Spring 2027 Admission Process\s+Accepting applications\s+"
        r"May\s+1\s*[-\u2013\u2014]\s*Sept\.?\s+30,\s*2026",
        text,
        re.IGNORECASE,
    )
    if match is None:
        raise ValueError("MD Anderson radiologic page did not expose its exact dates")
    return [
        _window(
            "Spring admission",
            "2026-05-01",
            "2026-09-30",
            "Spring 2027",
            RADIOLOGIC_URL,
        )
    ]


def _window(
    round_name: str, opens_at: str, closes_at: str, intake: str, source_url: str
) -> DiscoveredWindow:
    return DiscoveredWindow(
        round=round_name,
        applicant_categories=["all"],
        opens_at=opens_at,
        closes_at=closes_at,
        intake=intake,
        source_url=source_url,
        opens_at_basis="official",
    )


def _text(html: str) -> str:
    return normalise(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))


def _date(value: str) -> str:
    cleaned = re.sub(r"\bSept\.?", "Sep", value, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bDec\.?", "Dec", cleaned, flags=re.IGNORECASE)
    compact = normalise(cleaned)
    for date_format in ("%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(compact, date_format).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"Unsupported MD Anderson date: {value}")
