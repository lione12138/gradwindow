from __future__ import annotations

from bs4 import BeautifulSoup

from .base import (
    BaseProgrammeAdapter,
    DiscoveredCatalog,
    DiscoveredProgramme,
    Fetcher,
)
from .official_catalog import normalise, slug

CATALOG_URL = "https://www.osaka-u.ac.jp/en/education/announcement/main/academic_degree"
APPLICATION_URL = "https://www.osaka-u.ac.jp/en/admissions/graduate/"


class OsakaAdapter(BaseProgrammeAdapter):
    university_id = "the-university-of-osaka"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by graduate school"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    minimum_expected_programmes = 22

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
                if "Master's Degree" in normalise(item.get_text(" ", strip=True))
            ),
            None,
        )
        if table is None:
            raise ValueError("Osaka's official master's degree table is missing")

        programmes: dict[str, DiscoveredProgramme] = {}
        for row in table.select("tr"):
            cells = row.find_all("td")
            if len(cells) != 2:
                continue
            school = normalise(cells[0].get_text(" ", strip=True))
            if not school:
                continue
            faculty = f"Graduate School of {school}"
            degrees = (
                normalise(value)
                for text in cells[1].stripped_strings
                for value in text.split("|")
            )
            for degree in degrees:
                if not degree:
                    continue
                programme_id = f"osaka-{slug(school)}-{slug(degree)}-master"
                programmes[programme_id] = DiscoveredProgramme(
                    id=programme_id,
                    name=f"{degree} ({faculty})",
                    degree_type="Master",
                    faculty=faculty,
                    department=faculty,
                    source_url=CATALOG_URL,
                    application_url=APPLICATION_URL,
                    windows=[],
                    deadline_text=(
                        "Osaka's official degree table confirms this master's "
                        "degree. Entrance-examination schedules are maintained by "
                        "the individual graduate schools, and the central page does "
                        "not provide one complete exact date pair, so no dates are "
                        "inferred."
                    ),
                    parse_status="no-deadline",
                    retrieval_method="official-graduate-degree-table",
                    evidence_quality="official-full-text",
                )

        result = sorted(programmes.values(), key=lambda item: item.id)
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                "Osaka's official degree table contained "
                f"{len(result)} master's degrees; expected at least "
                f"{self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)
