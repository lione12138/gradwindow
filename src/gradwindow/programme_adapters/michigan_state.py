from __future__ import annotations

import re
from urllib.parse import parse_qs, urljoin, urlsplit

from bs4 import BeautifulSoup

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme
from .official_catalog import normalise, slug

CATALOG_URL = (
    "https://reg.msu.edu/academicprograms/"
    "Programs.aspx?PType=GRADLAWM&Sort=CollegeDepartment"
)
APPLICATION_URL = "https://grad.msu.edu/admissions/apply"
MASTER_DEGREE_CODES = {
    "LLM",
    "MA",
    "MBA",
    "MFA",
    "MHRL",
    "MIPS",
    "MJ",
    "MLS",
    "MMUS",
    "MPH",
    "MPP",
    "MS",
    "MSN",
    "MSW",
    "MURP",
}


class MichiganStateAdapter(BaseProgrammeAdapter):
    """Discover programme-level master's routes from the official Registrar."""

    university_id = "michigan-state-university"
    school_prefix = "michigan-state"
    institution_name = "Michigan State University"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL,)
    retrieval_method = "official-registrar-graduate-degrees"
    catalogue_granularity = "programme-level"
    catalogue_limitation_reason = (
        "Michigan State's Registrar provides the canonical graduate degree "
        "catalogue. Application dates remain programme-specific, so no exact "
        "opening or closing date is inferred from the catalogue."
    )

    def __init__(self, minimum_expected_programmes: int = 120) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        programmes: dict[str, DiscoveredProgramme] = {}
        for link in soup.select('a[href*="ProgramDetail.aspx"]'):
            label = normalise(link.get_text(" ", strip=True))
            degree_code = _degree_code(label)
            if degree_code is None:
                continue
            source_url = urljoin(CATALOG_URL, str(link.get("href", "")))
            plan_code = _plan_code(source_url)
            name = _programme_name(label)
            if not name or not plan_code:
                continue
            faculty, department = _organisational_context(link)
            programme_id = f"michigan-state-{slug(name)}-{slug(plan_code.lower())}"
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type=_display_degree(degree_code),
                faculty=faculty or self.institution_name,
                department=department or faculty or self.institution_name,
                source_url=source_url,
                application_url=APPLICATION_URL,
                windows=[],
                deadline_text=(
                    "Programme found in Michigan State University's official "
                    "Registrar graduate-degree catalogue. Admissions deadlines "
                    "are programme-specific, so no exact dates are inferred."
                ),
                parse_status="no-deadline",
                retrieval_method=self.retrieval_method,
                evidence_quality="official-full-text",
            )

        result = sorted(programmes.values(), key=lambda item: (item.name, item.id))
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                "Michigan State Registrar catalogue contained "
                f"{len(result)} master's routes; expected at least "
                f"{self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)


def _degree_code(label: str) -> str | None:
    match = re.search(r"\(([A-Z.]+)\)\s*$", label)
    if match is None:
        return None
    code = match.group(1).replace(".", "").upper()
    if code not in MASTER_DEGREE_CODES:
        return None
    return code


def _programme_name(label: str) -> str:
    without_code = re.sub(r"\s*\([A-Z.]+\)\s*$", "", label).strip()
    name = re.split(r"\s+-\s+Master\b", without_code, maxsplit=1, flags=re.I)[0]
    name = re.sub(
        r"\s*\((?:this program|applications?)[^)]+\)\s*$",
        "",
        name,
        flags=re.I,
    )
    return normalise(name)


def _plan_code(source_url: str) -> str:
    values = parse_qs(urlsplit(source_url).query).get("Program", [])
    return normalise(values[0]) if values else ""


def _organisational_context(link) -> tuple[str, str]:
    faculty = ""
    department = ""
    for heading in link.find_all_previous(["h2", "h3", "h4"]):
        label = normalise(heading.get_text(" ", strip=True))
        if not label or label.casefold() == "graduate degrees":
            continue
        if heading.name == "h4" and not department:
            department = label
        elif heading.name in {"h2", "h3"} and not faculty:
            faculty = label
        if faculty and department:
            break
    return faculty, department


def _display_degree(code: str) -> str:
    return "MMus" if code == "MMUS" else code
