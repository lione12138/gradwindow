from __future__ import annotations

import re
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, DiscoveredProgramme, DiscoveredWindow, Fetcher
from .official_catalog import normalise, slug

SEARCH_URL = "https://www.ulb.be/servlet/search"
DEADLINES_URL = "https://www.ulb.be/en/prepare-your-application/submission-deadlines"
APPLICATION_URL = "https://www.ulb.be/en/enrolment"


def catalog_page_url(page: int) -> str:
    params = (
        ("l", "0"),
        ("beanKey", "beanKeyRechercheFormation"),
        ("types", "formation"),
        ("s", "FACULTE_ASC"),
        ("limit", "100"),
        ("typeFo", "MA"),
        ("typeFo", "MA60"),
        ("page", str(page)),
    )
    return f"{SEARCH_URL}?{urlencode(params)}"


CATALOG_URL = catalog_page_url(1)


class ULBAdapter:
    university_id = "universite-libre-de-bruxelles-ulb"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "2026-2027 academic year"
    application_opens_at_basis = "official"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, DEADLINES_URL, APPLICATION_URL)
    retrieval_method = "official-master-programme-search"
    known_programme_window_scope_type = "programme-group"
    known_programme_window_scope_id = "ulb-standard-master-admissions"
    catalogue_limitation_reason = (
        "ULB notes that some specialised master's programmes use different "
        "dates. The shared policy is therefore kept at programme-group scope "
        "and marked as an official recurring policy, not an exact literal-year "
        "programme window."
    )

    def __init__(
        self,
        minimum_expected_programmes: int = 120,
        maximum_expected_programmes: int = 140,
    ) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes
        self.maximum_expected_programmes = maximum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        first_page = fetcher(CATALOG_URL)
        pages = [first_page]
        for page in range(2, _page_count(first_page) + 1):
            pages.append(fetcher(catalog_page_url(page)))
        programmes = _programmes(pages)
        if not (
            self.minimum_expected_programmes
            <= len(programmes)
            <= self.maximum_expected_programmes
        ):
            raise ValueError(
                f"ULB catalogue contained {len(programmes)} master's programmes; "
                f"expected {self.minimum_expected_programmes}-"
                f"{self.maximum_expected_programmes}"
            )
        windows = _application_windows(
            fetcher(DEADLINES_URL),
            fetcher(APPLICATION_URL),
        )
        programmes.append(
            DiscoveredProgramme(
                id="ulb-standard-master-admissions",
                name="Standard master's admissions",
                degree_type="Master",
                faculty="Université Libre de Bruxelles",
                department="Enrolment Service",
                source_url=DEADLINES_URL,
                application_url=APPLICATION_URL,
                windows=windows,
                deadline_text=(
                    "ULB's official 2026-2027 enrolment page and recurring "
                    "submission policy publish these applicant-category periods. "
                    "Specialised master's exceptions must be checked with the "
                    "faculty."
                ),
                parse_status="recurring-policy",
                retrieval_method="official-enrolment-and-recurring-deadline-policy",
                evidence_quality="official-full-text",
            )
        )
        return DiscoveredCatalog(application_opens_at=None, programmes=programmes)


def _page_count(html: str) -> int:
    pages = [1]
    soup = BeautifulSoup(html, "html.parser")
    for link in soup.select('a[href*="page="]'):
        match = re.search(r"[?&]page=(\d+)", str(link.get("href", "")))
        if match:
            pages.append(int(match.group(1)))
    return max(pages)


def _programmes(pages: list[str]) -> list[DiscoveredProgramme]:
    programmes: dict[str, DiscoveredProgramme] = {}
    for html in pages:
        soup = BeautifulSoup(html, "html.parser")
        for card in soup.select(".search-result__result-item"):
            link = card.select_one("a.item-title__element_title[href]")
            title = card.select_one(".search-result__structure-intitule")
            mnemonic = card.select_one(".search-result__mnemonique")
            faculty = card.select_one(".search-result__structure-rattachement")
            if link is None or title is None or mnemonic is None:
                continue
            name = normalise(title.get_text(" ", strip=True))
            code = normalise(mnemonic.get_text(" ", strip=True))
            if not name.casefold().startswith("master") or not code:
                continue
            source_url = str(link["href"])
            programme_id = f"ulb-{slug(code)}"
            faculty_name = (
                normalise(faculty.get_text(" ", strip=True))
                if faculty is not None
                else "Université Libre de Bruxelles"
            )
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type="Master",
                faculty=faculty_name,
                department=faculty_name,
                source_url=source_url,
                application_url=APPLICATION_URL,
                windows=[],
                deadline_text=(
                    "Programme found in ULB's official master programme search. "
                    "The shared admissions policy is represented once at group "
                    "scope; specialised-master exceptions require faculty review."
                ),
                parse_status="no-deadline",
                retrieval_method="official-master-programme-search",
                evidence_quality="official-full-text",
            )
    return sorted(programmes.values(), key=lambda item: item.name.casefold())


def _application_windows(
    deadlines_html: str, enrolment_html: str
) -> list[DiscoveredWindow]:
    deadlines = normalise(
        BeautifulSoup(deadlines_html, "html.parser").get_text(" ", strip=True)
    )
    enrolment = normalise(
        BeautifulSoup(enrolment_html, "html.parser").get_text(" ", strip=True)
    )
    required_deadlines = (
        "Master and Specialized Masters From 1 April to 30 September",
        "Non-European students For all programs From 16 February to 31 March",
    )
    if not all(
        value.casefold() in deadlines.casefold() for value in required_deadlines
    ):
        raise ValueError("ULB submission page did not expose both recurring periods")
    if re.search(r"Academic\s+year\s+2026\s*[–—-]\s*2027", enrolment, re.I) is None:
        raise ValueError("ULB enrolment page did not confirm academic year 2026-2027")
    definitions = (
        (
            "Belgian, European, EU-resident and Swiss applicants",
            ["domestic", "eu-eea"],
            "2026-04-01",
            "2026-09-30",
        ),
        (
            "Non-European applicants",
            ["international-students"],
            "2026-02-16",
            "2026-03-31",
        ),
    )
    return [
        DiscoveredWindow(
            round=round_name,
            applicant_categories=categories,
            opens_at=opens_at,
            closes_at=closes_at,
            intake="2026-2027 academic year",
            source_url=DEADLINES_URL,
            opens_at_basis="official-recurring-policy",
        )
        for round_name, categories, opens_at, closes_at in definitions
    ]
