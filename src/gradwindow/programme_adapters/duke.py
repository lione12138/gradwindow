from __future__ import annotations

import re
import unicodedata
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import BaseProgrammeAdapter, DiscoveredCatalog, DiscoveredProgramme, Fetcher

UNIVERSITY_ID = "duke-university"
CATALOG_URL = (
    "https://gradschool.duke.edu/academics/programs-and-degrees/masters-programs/"
)
DEADLINES_URL = "https://gradschool.duke.edu/admissions/application-deadlines/"
APPLICATION_URL = "https://gradschool.duke.edu/admissions/application-instructions/"


class DukeAdapter(BaseProgrammeAdapter):
    university_id = UNIVERSITY_ID
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    application_opens_at_basis = "missing"
    replace_pending_candidates = True

    def __init__(self, minimum_expected_programmes: int = 26) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        deadline_text = " ".join(
            BeautifulSoup(fetcher(DEADLINES_URL), "html.parser").stripped_strings
        )
        if "Master's Deadlines" not in deadline_text:
            raise ValueError("Duke official master's deadline table was unavailable")
        return self.parse_catalog(fetcher(CATALOG_URL))

    def parse_catalog(self, html: str) -> DiscoveredCatalog:
        soup = BeautifulSoup(html, "html.parser")
        programmes = {}
        for link in soup.select('a[href*="/academics/programs-degrees/"]'):
            name = " ".join(link.stripped_strings)
            if not name:
                continue
            source_url = urljoin(CATALOG_URL, str(link.get("href", "")))
            programme_id = f"duke-{_slug(name)}-master"
            if name == "Computer Science":
                programme_id = "duke-computer-science-ms"
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type="Master",
                faculty="The Graduate School",
                department=name,
                source_url=source_url,
                application_url=APPLICATION_URL,
                windows=[],
                deadline_text="Duke publishes exact master's closing dates, but the official source does not publish an exact application opening date. No opening date is inferred.",
                parse_status="no-deadline",
                retrieval_method="official-masters-directory",
                evidence_quality="official-full-text",
            )
        result = sorted(programmes.values(), key=lambda item: item.name)
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                f"Duke catalogue contained {len(result)} master's programmes; expected at least {self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)


def _slug(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    )
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")
