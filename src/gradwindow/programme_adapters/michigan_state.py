from __future__ import annotations

import re
from urllib.parse import parse_qs, urljoin, urlsplit

from bs4 import BeautifulSoup

from ..browser_rendering import browser_content_fetcher_from_environment
from .base import (
    BaseProgrammeAdapter,
    DiscoveredCatalog,
    DiscoveredProgramme,
    Fetcher,
    OfficialSourceTransportError,
)
from .official_catalog import normalise, slug

CATALOG_URL = (
    "https://reg.msu.edu/academicprograms/"
    "Programs.aspx?PType=GRADLAWM&Sort=CollegeDepartment"
)
APPLICATION_URL = "https://grad.msu.edu/admissions/apply"
MASTER_DEGREE_CODES = {
    "LLM",
    "MA",
    "MAT",
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
NON_MASTER_DEGREE_CODES = {
    "DDS",
    "DMA",
    "DNP",
    "DO",
    "DVM",
    "EDD",
    "JD",
    "MD",
    "PHD",
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

    def __init__(
        self,
        minimum_expected_programmes: int = 120,
        browser_content_fetcher: Fetcher | None = None,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.browser_content_fetcher = (
            browser_content_fetcher or browser_content_fetcher_from_environment()
        )
        self.current_retrieval_method = self.retrieval_method

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        html = fetcher(self.catalog_url)
        self.current_retrieval_method = self.retrieval_method
        if _is_access_challenge(html):
            if self.browser_content_fetcher is None:
                raise OfficialSourceTransportError(
                    "Michigan State's Registrar catalogue returned an access "
                    "challenge and Browser Rendering is not configured"
                )
            try:
                html = self.browser_content_fetcher(self.catalog_url)
            except Exception as exc:
                raise OfficialSourceTransportError(
                    "Michigan State's Registrar catalogue remained unavailable "
                    "through Browser Rendering"
                ) from exc
            if _is_access_challenge(html):
                raise OfficialSourceTransportError(
                    "Michigan State's Registrar catalogue returned an access "
                    "challenge through Browser Rendering"
                )
            self.current_retrieval_method = "cloudflare-browser-rendering"
        return self.parse_catalog(html)

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        programmes: dict[str, DiscoveredProgramme] = {}
        observed_degree_codes: set[str] = set()
        unknown_degree_codes: set[str] = set()
        for link in soup.select('a[href*="ProgramDetail.aspx"]'):
            label = normalise(link.get_text(" ", strip=True))
            degree_code = _raw_degree_code(label)
            if degree_code is None:
                continue
            observed_degree_codes.add(degree_code)
            if degree_code in NON_MASTER_DEGREE_CODES:
                continue
            if degree_code not in MASTER_DEGREE_CODES:
                unknown_degree_codes.add(degree_code)
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
                retrieval_method=self.current_retrieval_method,
                evidence_quality="official-full-text",
            )

        result = sorted(programmes.values(), key=lambda item: (item.name, item.id))
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                "Michigan State Registrar catalogue contained "
                f"{len(result)} master's routes; expected at least "
                f"{self.minimum_expected_programmes}"
            )
        warnings = []
        if unknown_degree_codes:
            warnings.append(
                {
                    "reason": "UNKNOWN_DEGREE_CODE",
                    "message": (
                        "Michigan State's official graduate catalogue exposed "
                        "unclassified degree codes; those routes were not ingested."
                    ),
                    "sourceUrl": CATALOG_URL,
                    "unknownDegreeCodes": sorted(unknown_degree_codes),
                }
            )
        return DiscoveredCatalog(
            application_opens_at=None,
            programmes=result,
            warnings=warnings,
            diagnostics={
                "observedGraduateDegreeCodes": sorted(observed_degree_codes),
                "unknownGraduateDegreeCodes": sorted(unknown_degree_codes),
            },
        )


def _raw_degree_code(label: str) -> str | None:
    match = re.search(r"\(([A-Z.]+)\)\s*$", label)
    if match is None:
        return None
    return match.group(1).replace(".", "").upper()


def _is_access_challenge(html: str) -> bool:
    lowered = html.casefold()
    return any(
        marker in lowered
        for marker in (
            "_incapsula_resource",
            "incapsula incident id",
            "request unsuccessful",
        )
    )


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
