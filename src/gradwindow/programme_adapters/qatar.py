from __future__ import annotations

from bs4 import BeautifulSoup

from .base import (
    BaseProgrammeAdapter,
    DiscoveredCatalog,
    DiscoveredProgramme,
    Fetcher,
)
from .official_catalog import normalise, slug

CATALOG_URL = (
    "https://www.qu.edu.qa/en-us/students/admission/graduate/Pages/"
    "academic-programs.aspx"
)
APPLICATION_URL = "https://www.qu.edu.qa/en-us/students/admission/graduate/"


class QatarAdapter(BaseProgrammeAdapter):
    university_id = "qatar-university"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    minimum_expected_programmes = 33

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalog = self.parse_catalog(fetcher(CATALOG_URL))
        fetcher(APPLICATION_URL)
        return catalog

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        table = next(
            (
                item
                for item in soup.select("table")
                if "Major (Program)" in normalise(item.get_text(" ", strip=True))
            ),
            None,
        )
        if table is None:
            raise ValueError(
                "Qatar University's official academic-program table is missing"
            )

        programmes: dict[str, DiscoveredProgramme] = {}
        for row in table.select("tr"):
            cells = row.find_all("td")
            if (
                len(cells) < 3
                or normalise(cells[1].get_text(" ", strip=True)) != "Master"
            ):
                continue
            faculty = normalise(cells[0].get_text(" ", strip=True))
            name = normalise(cells[2].get_text(" ", strip=True))
            if not faculty or not name:
                continue
            programme_id = f"qatar-{slug(name)}-master"
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type="Master",
                faculty=faculty,
                department=faculty,
                source_url=CATALOG_URL,
                application_url=APPLICATION_URL,
                windows=[],
                deadline_text=(
                    "Qatar University's official academic-program table explicitly "
                    "marks this degree as Master. Admission availability and "
                    "timelines vary by programme, and the checked central pages do "
                    "not provide one complete reusable exact date pair, so no dates "
                    "are inferred."
                ),
                parse_status="no-deadline",
                retrieval_method="official-graduate-academic-program-table",
                evidence_quality="official-full-text",
            )

        result = sorted(programmes.values(), key=lambda item: item.id)
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                "Qatar University's official table contained "
                f"{len(result)} master's programmes; expected at least "
                f"{self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)
