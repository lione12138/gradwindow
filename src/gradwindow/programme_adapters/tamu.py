from __future__ import annotations

from bs4 import BeautifulSoup

from .base import (
    BaseProgrammeAdapter,
    DiscoveredCatalog,
    DiscoveredProgramme,
    Fetcher,
)
from .official_catalog import normalise, slug

CATALOG_URL = "https://catalog.tamu.edu/graduate/degrees-programs/"
APPLICATION_URL = "https://admissions.tamu.edu/apply/graduate.html"


class TAMUAdapter(BaseProgrammeAdapter):
    university_id = "texas-a-and-m-university"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    minimum_expected_programmes = 170

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalog = self.parse_catalog(fetcher(CATALOG_URL))
        fetcher(APPLICATION_URL)
        return catalog

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        programmes: dict[str, DiscoveredProgramme] = {}
        for table in soup.select("table"):
            heading = table.find_previous(["h2", "h3"])
            faculty = (
                normalise(heading.get_text(" ", strip=True))
                if heading is not None
                else "Texas A&M University"
            )
            for row in table.select("tr"):
                cells = row.find_all("td")
                if len(cells) < 5:
                    continue
                name = normalise(cells[0].get_text(" ", strip=True))
                degrees = normalise(cells[2].get_text(" ", strip=True))
                if not name or not degrees:
                    continue
                for degree_type in map(normalise, degrees.split(",")):
                    if not degree_type:
                        continue
                    programme_id = f"tamu-{slug(name)}-{slug(degree_type)}"
                    programmes.setdefault(
                        programme_id,
                        DiscoveredProgramme(
                            id=programme_id,
                            name=name,
                            degree_type=degree_type,
                            faculty=faculty,
                            department=faculty,
                            source_url=CATALOG_URL,
                            application_url=APPLICATION_URL,
                            windows=[],
                            deadline_text=(
                                "Texas A&M's official 2026-2027 catalogue lists "
                                f"this {degree_type} degree. Graduate deadlines are "
                                "programme-specific, and the central admissions page "
                                "does not publish a complete universal exact date "
                                "pair, so no dates are inferred."
                            ),
                            parse_status="no-deadline",
                            retrieval_method="official-2026-2027-degree-catalogue",
                            evidence_quality="official-full-text",
                        ),
                    )

        result = sorted(programmes.values(), key=lambda item: item.id)
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                "Texas A&M's official catalogue contained "
                f"{len(result)} master's degree routes; expected at least "
                f"{self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)
