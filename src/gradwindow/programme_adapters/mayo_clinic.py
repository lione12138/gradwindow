from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, DiscoveredProgramme, DiscoveredWindow, Fetcher
from .official_catalog import normalise, slug

HEALTH_CATALOG_URL = (
    "https://college.mayo.edu/academics/health-sciences-education/programs-a-z/"
)
BIOMEDICAL_CATALOG_URL = (
    "https://college.mayo.edu/academics/biomedical-research-training/programs/"
)
APPLICATION_URL = (
    "https://college.mayo.edu/academics/health-sciences-education/admissions/"
)
PROFESSIONAL_CATALOG_URL = (
    "https://catalog.mayo.edu/graduate-biomedical-sciences/"
    "employee-professional-masters-degree-programs/"
    "employee-professional-masters-degree-programs.pdf"
)
RESIDENT_CATALOG_URL = (
    "https://catalog.mayo.edu/graduate-biomedical-sciences/"
    "clinical-masters-degree-programs/clinical-masters-degree-programs.pdf"
)
POSTDOCTORAL_CATALOG_URL = (
    "https://catalog.mayo.edu/graduate-biomedical-sciences/"
    "postdoctoral-basic-science-masters-degree-programs/"
    "postdoctoral-basic-science-masters-degree-programs.pdf"
)

_TRACK_RE = re.compile(r"•\s*(?P<name>.+?)\s*\((?P<url>https://.+?)\)", re.DOTALL)
_WINDOW_RE = re.compile(
    r"Application\s+window\s*:\s*"
    r"(?P<opens>[A-Z][a-z]+\.?\s+\d{1,2},\s*20\d{2})\s*[-–—]\s*"
    r"(?P<closes>[A-Z][a-z]+\.?\s+\d{1,2},\s*20\d{2})",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class _TrackCatalog:
    url: str
    faculty: str
    stop_heading: str


TRACK_CATALOGS = (
    _TrackCatalog(
        PROFESSIONAL_CATALOG_URL,
        "Mayo Clinic Graduate School of Biomedical Sciences",
        "Application",
    ),
    _TrackCatalog(
        RESIDENT_CATALOG_URL,
        "Mayo Clinic Graduate School of Biomedical Sciences",
        "Eligibility",
    ),
    _TrackCatalog(
        POSTDOCTORAL_CATALOG_URL,
        "Mayo Clinic Graduate School of Biomedical Sciences",
        "Application",
    ),
)


class MayoClinicAdapter:
    university_id = "mayo-clinic-college-of-medicine-and-science"
    catalog_url = HEALTH_CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (
        HEALTH_CATALOG_URL,
        BIOMEDICAL_CATALOG_URL,
        PROFESSIONAL_CATALOG_URL,
        RESIDENT_CATALOG_URL,
        POSTDOCTORAL_CATALOG_URL,
    )
    retrieval_method = "official-health-sciences-html-and-biomedical-catalog-pdfs"
    catalogue_limitation_reason = (
        "Most Mayo biomedical master's tracks are restricted to Mayo employees, "
        "residents or postdoctoral appointees and use internal applications. "
        "Only a programme publishing a literal-year opening and closing pair "
        "produces an exact-window candidate."
    )

    def __init__(
        self,
        minimum_expected_programmes: int = 18,
        maximum_expected_programmes: int = 22,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.maximum_expected_programmes = maximum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        biomedical_index = normalise(
            BeautifulSoup(fetcher(BIOMEDICAL_CATALOG_URL), "html.parser").get_text(
                " ", strip=True
            )
        )
        if "Master’s of Science Degree Programs" not in biomedical_index:
            raise ValueError("Mayo biomedical master's catalogue link is missing")

        health_programmes = _health_programmes(fetcher(HEALTH_CATALOG_URL))
        for programme in health_programmes:
            detail_html = fetcher(programme.source_url)
            _add_health_window(programme, detail_html)

        programmes = {programme.id: programme for programme in health_programmes}
        for catalog in TRACK_CATALOGS:
            for programme in _track_programmes(fetcher(catalog.url), catalog):
                programmes[programme.id] = programme
        result = sorted(programmes.values(), key=lambda item: item.name.casefold())
        if not (
            self.minimum_expected_programmes
            <= len(result)
            <= self.maximum_expected_programmes
        ):
            raise ValueError(
                f"Mayo catalogues contained {len(result)} master's programmes; "
                f"expected {self.minimum_expected_programmes}-"
                f"{self.maximum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)


def _health_programmes(html: str) -> list[DiscoveredProgramme]:
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.find(id="master")
    if heading is None:
        raise ValueError("Mayo health-sciences catalogue has no master's section")
    programmes = []
    for node in heading.find_all_next():
        if node is not heading and node.name == heading.name and node.get("id"):
            break
        if node.name != "a" or not node.get("href"):
            continue
        name = normalise(node.get_text(" ", strip=True))
        if name != "Physician Assistant Program":
            continue
        source_url = urljoin(HEALTH_CATALOG_URL, str(node["href"]))
        location = source_url.rstrip("/").split("-")[-1]
        programme_id = f"mayo-physician-assistant-{slug(location)}"
        programmes.append(
            DiscoveredProgramme(
                id=programme_id,
                name=f"Physician Assistant Program ({_pa_location(source_url)})",
                degree_type="Master",
                faculty="Mayo Clinic School of Health Sciences",
                department="Physician Assistant Program",
                source_url=source_url,
                application_url=f"{source_url.rstrip('/')}/how-to-apply/",
                windows=[],
                deadline_text=(
                    "Programme found in Mayo Clinic School of Health Sciences' "
                    "official master's catalogue."
                ),
                parse_status="no-deadline",
                retrieval_method="official-health-sciences-programme-catalogue",
                evidence_quality="official-full-text",
            )
        )
    return list({programme.id: programme for programme in programmes}.values())


def _pa_location(url: str) -> str:
    if "university-of-wisconsin" in url:
        return "Mayo Clinic/University of Wisconsin-La Crosse"
    return "Minnesota"


def _add_health_window(programme: DiscoveredProgramme, html: str) -> None:
    text = normalise(BeautifulSoup(html, "html.parser").get_text(" ", strip=True))
    match = _WINDOW_RE.search(text)
    if match is None:
        programme.deadline_text = (
            "The official programme page publishes deadline guidance but no "
            "literal-year pair of exact opening and closing dates, so no window "
            "is inferred."
        )
        return
    intake_match = re.search(
        r"class\s+starting\s+in\s+(.+?\(Class\s+of\s+20\d{2}\))", text, re.I
    )
    intake = normalise(intake_match.group(1)) if intake_match else "Varies"
    programme.windows = [
        DiscoveredWindow(
            round="Application window",
            applicant_categories=["all"],
            opens_at=_date(match.group("opens")),
            closes_at=_date(match.group("closes")),
            intake=intake,
            source_url=programme.source_url,
            opens_at_basis="official",
        )
    ]
    programme.deadline_text = (
        "Mayo Clinic's official programme page publishes this literal-year "
        "application window and intake."
    )
    programme.parse_status = "parsed"


def _track_programmes(text: str, catalog: _TrackCatalog) -> list[DiscoveredProgramme]:
    section = text.split(catalog.stop_heading, 1)[0]
    programmes = []
    for match in _TRACK_RE.finditer(section):
        name = normalise(match.group("name"))
        source_url = re.sub(r"\s+", "", match.group("url"))
        programme_id = f"mayo-{slug(name)}"
        programmes.append(
            DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type="Master of Science",
                faculty=catalog.faculty,
                department=catalog.faculty,
                source_url=source_url,
                application_url=catalog.url,
                windows=[],
                deadline_text=(
                    "Track found in Mayo Clinic's official current graduate "
                    "catalogue. Eligibility is appointment-specific and the "
                    "catalogue publishes no exact external application window."
                ),
                parse_status="no-deadline",
                retrieval_method="official-current-graduate-catalogue-pdf",
                evidence_quality="official-full-text",
            )
        )
    return programmes


def _date(value: str) -> str:
    compact = normalise(value).replace(".", "")
    for pattern in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(compact, pattern).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"Unsupported Mayo application date: {value}")
