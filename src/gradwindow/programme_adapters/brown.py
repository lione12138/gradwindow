from __future__ import annotations

import re
import unicodedata
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme, Fetcher

UNIVERSITY_ID = "brown-university"
CATALOG_URL = "https://graduateprograms.brown.edu/graduate_programs"
APPLICATION_URL = "https://masters.brown.edu/admissions/application-process"
DEADLINES_URL = "https://masters.brown.edu/admissions/tuition-aid/deadlines-credits"


class BrownAdapter(BaseProgrammeAdapter):
    university_id = UNIVERSITY_ID
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    application_opens_at_basis = "missing"
    replace_pending_candidates = True

    def __init__(self, minimum_expected_programmes: int = 40) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        if "Program of Study" not in fetcher(DEADLINES_URL):
            raise ValueError("Brown official master's deadline table was unavailable")
        return self.parse_catalog(fetcher(CATALOG_URL))

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        programmes = {}
        for row in soup.select(".views-row"):
            category = row.select_one(".term-item")
            title_link = row.select_one("h2 a[href]")
            degree_node = row.select_one(".views-field-field-program-degree-type")
            if (
                category is None
                or "Master Program" not in category.get_text(" ", strip=True)
                or title_link is None
                or degree_node is None
            ):
                continue
            name = title_link.get_text(" ", strip=True)
            degree = degree_node.get_text(" ", strip=True)
            source_url = urljoin(CATALOG_URL, str(title_link.get("href", "")))
            programme_id = f"brown-{_slug(name)}-{_slug(degree)}"
            if name == "Computer Science":
                programme_id = "brown-computer-science-scm"
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type=degree,
                faculty="Brown University",
                department=name,
                source_url=source_url,
                application_url=APPLICATION_URL,
                windows=[],
                deadline_text="Brown publishes exact closing dates by master's programme, but the official source does not publish one exact opening date. No opening date is inferred.",
                parse_status="no-deadline",
                retrieval_method="official-graduate-program-directory",
                evidence_quality="official-full-text",
            )
        result = sorted(programmes.values(), key=lambda item: item.name)
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                f"Brown catalogue contained {len(result)} master's programmes; expected at least {self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)


def _slug(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    )
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")
