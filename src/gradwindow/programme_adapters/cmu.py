from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import (
    BaseProgrammeAdapter,
    DiscoveredCatalog,
    DiscoveredProgramme,
    Fetcher,
)
from .official_catalog import normalise, slug

CATALOG_URL = (
    "https://www.materials.cmu.edu/education/graduate/masters-programs/index.html"
)
APPLICATION_URL = "https://www.cmu.edu/graduate/prospective/"


class CMUAdapter(BaseProgrammeAdapter):
    university_id = "carnegie-mellon-university"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    minimum_expected_programmes = 3

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalog = self.parse_catalog(fetcher(CATALOG_URL))
        fetcher(APPLICATION_URL)
        return catalog

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        heading = next(
            (
                item
                for item in soup.select("h2, h3")
                if "following master of science degrees"
                in normalise(item.get_text(" ", strip=True)).casefold()
            ),
            None,
        )
        listing = heading.find_next_sibling("ul") if heading is not None else None
        if listing is None:
            raise ValueError("CMU Materials' official master's list is missing")

        programmes: dict[str, DiscoveredProgramme] = {}
        for item in listing.find_all("li", recursive=False):
            link = item.find("a", href=True, recursive=False)
            if link is None:
                continue
            name = normalise(link.get_text(" ", strip=True))
            if re.match(r"^(?:M\.?S\.?|Master)", name, re.I) is None:
                continue
            source_url = urljoin(CATALOG_URL, str(link.get("href", "")))
            programme_id = f"cmu-materials-{slug(name)}"
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type="MS",
                faculty="College of Engineering",
                department="Materials Science and Engineering",
                source_url=source_url,
                application_url=APPLICATION_URL,
                windows=[],
                deadline_text=(
                    "Carnegie Mellon's official Materials Science and Engineering "
                    "directory lists this master's route. This adapter currently "
                    "covers that department because the central CourseLeaf host is "
                    "not reliably reachable by the monitor. Deadlines are handled "
                    "by individual programmes and no complete exact date pair is "
                    "published on the checked pages, so no dates are inferred."
                ),
                parse_status="no-deadline",
                retrieval_method="official-cmu-materials-masters-directory",
                evidence_quality="official-full-text",
            )

        result = sorted(programmes.values(), key=lambda programme: programme.id)
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                "CMU Materials' official directory contained "
                f"{len(result)} master's programmes; expected at least "
                f"{self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)
