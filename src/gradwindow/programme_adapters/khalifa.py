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

CATALOG_URL = "https://www.ku.ac.ae/academics/graduate-programs"
APPLICATION_URL = "https://www.ku.ac.ae/postgraduate-admissions"


class KhalifaAdapter(BaseProgrammeAdapter):
    university_id = "khalifa-university-of-science-and-technology"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    intake = "Varies by admission cycle"
    application_opens_at_basis = "missing"
    replace_pending_candidates = True
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    minimum_expected_programmes = 21

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalog = self.parse_catalog(fetcher(CATALOG_URL))
        fetcher(APPLICATION_URL)
        return catalog

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        programmes: dict[str, DiscoveredProgramme] = {}
        for link in soup.select("a[href]"):
            raw_name = normalise(link.get_text(" ", strip=True))
            if (
                re.match(r"^(?:MSc|Msc|MEng|Master of Public Health)\b", raw_name)
                is None
            ):
                continue
            name = re.sub(r"\s*-\s*NEW\s*$", "", raw_name, flags=re.I)
            name = re.sub(
                r"\s*\(\s*Program Delivery Mode:.*?\)\s*",
                "",
                name,
                flags=re.I,
            )
            name = re.sub(r"^Msc\b", "MSc", normalise(name))
            faculty_heading = link.find_previous("h3")
            faculty = (
                normalise(faculty_heading.get_text(" ", strip=True))
                if faculty_heading is not None
                else "Khalifa University"
            )
            degree_type = (
                "MPH"
                if name.startswith("Master of Public Health")
                else "MEng"
                if name.startswith("MEng")
                else "MSc"
            )
            programme_id = f"khalifa-{slug(name)}"
            if programme_id in programmes:
                continue
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type=degree_type,
                faculty=faculty,
                department=faculty,
                source_url=urljoin(CATALOG_URL, str(link.get("href", ""))),
                application_url=APPLICATION_URL,
                windows=[],
                deadline_text=(
                    "Khalifa University's official graduate-programmes page lists "
                    "this master's degree. The postgraduate admissions page currently "
                    "states that Fall 2026 is closed without publishing a reusable "
                    "complete exact opening-and-closing pair, so no dates are inferred."
                ),
                parse_status="no-deadline",
                retrieval_method="official-graduate-programmes-directory",
                evidence_quality="official-full-text",
            )

        result = sorted(programmes.values(), key=lambda item: item.id)
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                "Khalifa's official directory contained "
                f"{len(result)} master's programmes; expected at least "
                f"{self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)
