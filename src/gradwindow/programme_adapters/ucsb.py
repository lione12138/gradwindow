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

CATALOG_URL = "https://www.graddiv.ucsb.edu/graduate-programs/departments"
APPLICATION_URL = "https://www.graddiv.ucsb.edu/how-apply"

_MASTER_DEGREE_RE = re.compile(r"(?<![A-Za-z])M[A-Za-z]{1,5}(?![A-Za-z])")


class UCSBAdapter(BaseProgrammeAdapter):
    university_id = "university-of-california-santa-barbara-ucsb"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Primarily Fall; varies by programme"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    minimum_expected_programmes = 50

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalog = self.parse_catalog(fetcher(CATALOG_URL))
        fetcher(APPLICATION_URL)
        return catalog

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        programmes: dict[str, DiscoveredProgramme] = {}
        for row in soup.select(".views-row"):
            title = row.select_one(".views-field-title a[href]")
            degree_field = row.select_one(".views-field-field-degrees")
            if title is None or degree_field is None:
                continue
            name = normalise(title.get_text(" ", strip=True))
            source_url = urljoin(CATALOG_URL, str(title.get("href", "")))
            for degree_type in set(
                _MASTER_DEGREE_RE.findall(
                    normalise(degree_field.get_text(" ", strip=True))
                )
            ):
                programme_id = f"ucsb-{slug(name)}-{slug(degree_type)}"
                programmes[programme_id] = DiscoveredProgramme(
                    id=programme_id,
                    name=name,
                    degree_type=degree_type,
                    faculty="UC Santa Barbara Graduate Division",
                    department=name,
                    source_url=source_url,
                    application_url=APPLICATION_URL,
                    windows=[],
                    deadline_text=(
                        "UCSB's official Graduate Division directory lists this "
                        f"{degree_type} route. The directory notes that deadlines "
                        "are department-specific and that some master's/PhD routes "
                        "require doctoral-program enrollment; no complete universal "
                        "exact date pair is published, so no dates are inferred."
                    ),
                    parse_status="no-deadline",
                    retrieval_method="official-graduate-program-directory",
                    evidence_quality="official-full-text",
                )

        result = sorted(programmes.values(), key=lambda item: item.id)
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                "UCSB's official directory contained "
                f"{len(result)} master's degree routes; expected at least "
                f"{self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)
