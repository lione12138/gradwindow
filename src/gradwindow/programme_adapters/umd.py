from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme, Fetcher
from .official_catalog import normalise, slug

CATALOG_URL = "https://academiccatalog.umd.edu/filters/"
DEADLINES_URL = "https://gradschool.umd.edu/calendar/deadlines/admissions-deadlines"
APPLICATION_URL = "https://gradschool.umd.edu/admissions/application-process"
_NON_FACULTY_KEYWORDS = {
    "doctoral",
    "master",
    "master of public health",
    "dual degree",
    "certificate (non-degree)",
    "research",
    "professional",
    "fully online",
    "off-site",
    "internship or clinical experience",
}


class UMDAdapter(BaseProgrammeAdapter):
    university_id = "university-of-maryland-college-park"
    catalog_url = CATALOG_URL
    admissions_url = DEADLINES_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, DEADLINES_URL)
    retrieval_method = "official-filterable-graduate-catalogue"
    catalogue_limitation_reason = (
        "The official Graduate School states that every programme or department "
        "sets its own deadline. The central catalogue does not publish complete "
        "exact opening-and-closing pairs, so programme pages remain monitored."
    )

    def __init__(self, minimum_expected_programmes: int = 240) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalogue = self.parse_catalog(fetcher(CATALOG_URL))
        policy_text = normalise(
            BeautifulSoup(fetcher(DEADLINES_URL), "html.parser").get_text(
                " ", strip=True
            )
        ).casefold()
        if "each program/department sets its own deadline" not in policy_text:
            raise ValueError("UMD's programme-specific deadline policy is missing")
        return catalogue

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        programmes: dict[str, DiscoveredProgramme] = {}
        for item in soup.select("ul.isotope > li.item"):
            keywords = [
                normalise(keyword.get_text(" ", strip=True))
                for keyword in item.select(".keyword")
            ]
            lowered = {keyword.casefold() for keyword in keywords}
            if "master" not in lowered and "master of public health" not in lowered:
                continue
            link = item.select_one("a[href]")
            title = item.select_one(".title")
            if link is None or title is None:
                continue
            name = normalise(title.get_text(" ", strip=True).replace("\u200b", ""))
            source_url = urljoin(CATALOG_URL, link["href"])
            faculty = next(
                (
                    keyword
                    for keyword in keywords
                    if keyword.casefold() not in _NON_FACULTY_KEYWORDS
                ),
                "University of Maryland Graduate School",
            )
            degree_type = (
                "Master of Public Health"
                if "master of public health" in lowered
                else "Master"
            )
            programme_id = f"umd-{slug(name)}"
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type=degree_type,
                faculty=faculty,
                department=faculty,
                source_url=source_url,
                application_url=APPLICATION_URL,
                windows=[],
                deadline_text=(
                    "Programme found in the official 2026-2027 graduate catalogue. "
                    "UMD states that each programme or department sets its own "
                    "deadlines, and no complete exact opening-and-closing pair is "
                    "published here."
                ),
                parse_status="no-deadline",
                retrieval_method=self.retrieval_method,
                evidence_quality="official-full-text",
            )
        result = sorted(programmes.values(), key=lambda row: row.name.casefold())
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                f"UMD catalogue contained {len(result)} master's programme routes; "
                f"expected at least {self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)
