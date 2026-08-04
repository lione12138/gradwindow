from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import (
    BaseProgrammeAdapter,
    DiscoveredCatalog,
    DiscoveredProgramme,
    Fetcher,
)
from .official_catalog import normalise, slug

CATALOG_URL = "https://www.tohoku.ac.jp/en/academics/graduate.html"
APPLICATION_URL = "https://www.tohoku.ac.jp/en/admissions/admission_graduate.html"


class TohokuAdapter(BaseProgrammeAdapter):
    university_id = "tohoku-university"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    minimum_expected_programmes = 8

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalog = self.parse_catalog(fetcher(CATALOG_URL))
        fetcher(APPLICATION_URL)
        return catalog

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        programmes: dict[str, DiscoveredProgramme] = {}
        for item in soup.select("li"):
            text = normalise(item.get_text(" ", strip=True))
            heading = item.find("h4")
            if heading is None or "Degree: Master" not in text:
                continue
            link = heading.find_parent("a", href=True)
            if link is None:
                continue
            name = normalise(heading.get_text(" ", strip=True))
            source_url = urljoin(CATALOG_URL, str(link.get("href", "")))
            programme_id = f"tohoku-english-{slug(name)}-master"
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type="Master",
                faculty="Tohoku University",
                department="Degree courses taught in English",
                source_url=source_url,
                application_url=APPLICATION_URL,
                windows=[],
                deadline_text=(
                    "Tohoku's official English degree-course directory explicitly "
                    "marks this route as Master or Master/Doctor. Application "
                    "schedules vary by graduate school and no complete central exact "
                    "date pair is published, so no dates are inferred."
                ),
                parse_status="no-deadline",
                retrieval_method="official-english-degree-course-directory",
                evidence_quality="official-full-text",
            )

        result = sorted(programmes.values(), key=lambda item: item.id)
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                "Tohoku's official English directory contained "
                f"{len(result)} master's routes; expected at least "
                f"{self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)
