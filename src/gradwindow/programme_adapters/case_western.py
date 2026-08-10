from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = (
    "https://case.edu/gradstudies/prospective-students/degree-programs-offered"
)
APPLICATION_URL = (
    "https://case.edu/gradstudies/prospective-students/admissions-information/"
    "application-deadlines"
)
MASTER_DEGREE_RE = re.compile(
    r"^(?:LLM|MA|MBA|ME|MEng|MFA|MPH|MS|MSA|MSM|MSN|MSW)$", re.IGNORECASE
)


class CaseWesternAdapter(OfficialCatalogAdapter):
    university_id = "case-western-reserve-university"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "case-western"
    institution_name = "Case Western Reserve University"
    minimum_expected_programmes = 50
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-graduate-degree-programmes-tables"
    catalogue_limitation_reason = (
        "Case Western publishes programme- and term-specific closing dates but "
        "does not publish a matching exact opening date in the central deadline "
        "tables. The tables are monitored without shifting prior-cycle dates."
    )

    def __init__(self, minimum_expected_programmes: int = 50) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalog = self.parse_catalog(fetcher(CATALOG_URL))
        deadlines = normalise(
            BeautifulSoup(fetcher(APPLICATION_URL), "html.parser").get_text(
                " ", strip=True
            )
        ).casefold()
        if "application deadlines vary among departments" not in deadlines:
            raise ValueError("Case Western's department deadline policy is missing")
        return catalog

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        for row in soup.select("table tr"):
            cells = row.select(":scope > td")
            if len(cells) < 2:
                continue
            name = _programme_name(cells[0])
            for link in cells[1].select("a[href]"):
                degree_type = normalise(link.get_text(" ", strip=True))
                if not MASTER_DEGREE_RE.fullmatch(degree_type):
                    continue
                rows.append(
                    CatalogEntry(
                        name=name,
                        degree_type=degree_type,
                        source_url=str(link["href"]),
                    )
                )
        return rows


def _programme_name(cell) -> str:
    first_paragraph = cell.find("p")
    raw = (
        first_paragraph.get_text(" ", strip=True)
        if first_paragraph is not None
        else cell.get_text(" ", strip=True)
    )
    return normalise(raw)
