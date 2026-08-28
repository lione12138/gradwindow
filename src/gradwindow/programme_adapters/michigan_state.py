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

CATALOG_URL = "https://reg.msu.edu/academicprograms/Programs.aspx?PType=GRADLAWM"
REGISTRAR_CATALOG_URLS = (
    CATALOG_URL,
    f"{CATALOG_URL}&Sort=College",
    f"{CATALOG_URL}&Sort=Department",
)
ADMISSIONS_FALLBACK_URL = (
    "https://admissions.msu.edu/academics/majors-degrees-programs"
    "?f-academic_level=Master%27s+degree"
)
ADMISSIONS_COMPLETE_SELECTOR = (
    "#gradwindow-msu-programmes[data-complete='true'] a.program-wrapper"
)
ADMISSIONS_PAGINATION_SCRIPT = r"""
void (async () => {
  const rootId = "gradwindow-msu-programmes";
  if (document.getElementById(rootId)) return;
  const output = document.createElement("div");
  output.id = rootId;
  document.body.appendChild(output);
  const seen = new Set();
  const delay = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));
  const waitFor = async (predicate, attempts = 80) => {
    for (let index = 0; index < attempts; index += 1) {
      if (predicate()) return true;
      await delay(125);
    }
    return false;
  };
  const cards = () => Array.from(document.querySelectorAll(".filtered-content a.program-wrapper"));
  await waitFor(() => cards().length > 0);
  for (let page = 1; page <= 30; page += 1) {
    for (const card of cards()) {
      const key = `${card.href}|${card.innerText}`;
      if (!seen.has(key)) {
        seen.add(key);
        output.appendChild(card.cloneNode(true));
      }
    }
    const nextPage = page + 1;
    const next = document.querySelector(
      `nav[aria-label="pagination"] a[href="#${nextPage}"]`
    );
    if (!next) break;
    const firstHref = cards()[0]?.href || "";
    next.click();
    const changed = await waitFor(
      () => cards().length > 0 && (cards()[0]?.href || "") !== firstHref
    );
    if (!changed) break;
  }
  output.dataset.complete = "true";
})();
"""
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
    "DUAL",
    "DDS",
    "DMA",
    "DNP",
    "DO",
    "DVM",
    "EDD",
    "EDS",
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
    catalogue_status = "ok"

    def __init__(
        self,
        minimum_expected_programmes: int = 120,
        browser_content_fetcher: Fetcher | None = None,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.browser_content_fetcher = (
            browser_content_fetcher
            or browser_content_fetcher_from_environment(
                wait_for_selectors={
                    ADMISSIONS_FALLBACK_URL: ADMISSIONS_COMPLETE_SELECTOR,
                },
                scripts={
                    ADMISSIONS_FALLBACK_URL: ADMISSIONS_PAGINATION_SCRIPT,
                },
            )
        )
        self.current_retrieval_method = self.retrieval_method

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        self.catalogue_status = "ok"
        self.current_retrieval_method = self.retrieval_method
        failures = []
        for url in REGISTRAR_CATALOG_URLS:
            try:
                html = fetcher(url)
            except Exception as exc:
                failures.append(f"{url}: {type(exc).__name__}")
                continue
            if _is_access_challenge(html):
                failures.append(f"{url}: access challenge")
                continue
            try:
                return self.parse_catalog(html)
            except ValueError as exc:
                failures.append(f"{url}: {exc}")

        if self.browser_content_fetcher is not None:
            self.current_retrieval_method = "cloudflare-browser-rendering"
            for url in REGISTRAR_CATALOG_URLS:
                try:
                    html = self.browser_content_fetcher(url)
                    if _is_access_challenge(html):
                        raise ValueError("access challenge")
                    return self.parse_catalog(html)
                except Exception as exc:
                    failures.append(
                        f"Browser Rendering {url}: {type(exc).__name__}: {exc}"
                    )

            try:
                html = self.browser_content_fetcher(ADMISSIONS_FALLBACK_URL)
                catalog = self._parse_admissions_fallback(html)
            except Exception as exc:
                failures.append(
                    "Browser Rendering admissions fallback: "
                    f"{type(exc).__name__}: {exc}"
                )
            else:
                self.catalogue_status = "partial"
                return catalog

        browser_note = (
            "Browser Rendering and the official admissions fallback also failed"
            if self.browser_content_fetcher is not None
            else "Browser Rendering is not configured"
        )
        detail = "; ".join(failures[-5:])
        raise OfficialSourceTransportError(
            "Michigan State's Registrar catalogue was unavailable across all "
            f"official entry points; {browser_note}. {detail}"
        )

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
            moratorium = _moratorium_period(label)
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
                    "Michigan State's official Registrar marks this programme as "
                    f"in moratorium from {moratorium[0]} through {moratorium[1]}."
                    if moratorium
                    else (
                        "Programme found in Michigan State University's official "
                        "Registrar graduate-degree catalogue. Admissions deadlines "
                        "are programme-specific, so no exact dates are inferred."
                    )
                ),
                parse_status="no-deadline",
                retrieval_method=self.current_retrieval_method,
                evidence_quality="official-full-text",
                admission_status="paused" if moratorium else None,
                moratorium_from=moratorium[0] if moratorium else None,
                moratorium_to=moratorium[1] if moratorium else None,
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

    def _parse_admissions_fallback(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select("#gradwindow-msu-programmes a.program-wrapper")
        if not cards:
            cards = soup.select("a.program-wrapper")
        programmes: dict[str, DiscoveredProgramme] = {}
        for card in cards:
            level = normalise(
                (card.select_one(".pre-header") or card).get_text(" ", strip=True)
            )
            title_node = card.select_one(".h2")
            if level.casefold() != "master's degree" or title_node is None:
                continue
            name = normalise(title_node.get_text(" ", strip=True))
            source_url = urljoin(
                ADMISSIONS_FALLBACK_URL,
                normalise(card.get("href", "")),
            )
            if not name or not source_url:
                continue
            faculty_node = card.select_one(".collegeName")
            faculty = (
                normalise(faculty_node.get_text(" ", strip=True))
                if faculty_node is not None
                else self.institution_name
            )
            identity = _plan_code(source_url) or source_url
            programme_id = (
                f"michigan-state-fallback-{slug(name)}-{slug(identity)[-48:]}"
            )
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type="Master",
                faculty=faculty,
                department=faculty,
                source_url=source_url,
                application_url=APPLICATION_URL,
                windows=[],
                deadline_text=(
                    "Programme found in Michigan State University's official "
                    "Admissions directory fallback. The Registrar source was "
                    "unavailable, and programme-specific dates are not inferred."
                ),
                parse_status="no-deadline",
                retrieval_method="cloudflare-browser-rendering-admissions-directory",
                evidence_quality="official-full-text",
            )
        result = sorted(programmes.values(), key=lambda item: (item.name, item.id))
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                "Michigan State Admissions fallback contained "
                f"{len(result)} master's programmes; expected at least "
                f"{self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(
            application_opens_at=None,
            programmes=result,
            warnings=[
                {
                    "reason": "FALLBACK_CATALOGUE_IDENTITY",
                    "message": (
                        "The Registrar was unavailable, so programme identities "
                        "came from the official Admissions directory and require "
                        "reconciliation before approval."
                    ),
                    "sourceUrl": ADMISSIONS_FALLBACK_URL,
                }
            ],
            diagnostics={"catalogueFallback": "official-admissions-directory"},
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


def _moratorium_period(label: str) -> tuple[str, str] | None:
    match = re.search(
        r"this program is in moratorium effective\s+"
        r"(?P<from_term>Fall|Spring|Summer|Winter)\s+(?P<from_year>20\d{2})"
        r"\s+through\s+"
        r"(?P<to_term>Fall|Spring|Summer|Winter)\s+(?P<to_year>20\d{2})",
        label,
        re.I,
    )
    if match is None:
        return None
    return (
        f"{match.group('from_term').title()} {match.group('from_year')}",
        f"{match.group('to_term').title()} {match.group('to_year')}",
    )


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
