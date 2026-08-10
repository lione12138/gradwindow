from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry, normalise

CATALOG_URL = "https://www.rochester.edu/academics/programs.html"
APPLICATION_URL = "https://www.rochester.edu/admissions/"
MASTER_DEGREES = {
    "MA",
    "MALS",
    "MAT",
    "MBA",
    "MEd",
    "ME",
    "MEng",
    "MFA",
    "MM",
    "MPA",
    "MPH",
    "MS",
    "MSN",
    "MSW",
}


class RochesterAdapter(OfficialCatalogAdapter):
    university_id = "university-of-rochester"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "rochester"
    institution_name = "University of Rochester"
    minimum_expected_programmes = 75
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-university-academic-programmes-index"
    catalogue_limitation_reason = (
        "Rochester's university-wide index covers graduate programmes across its "
        "schools. The university states that each graduate school or programme "
        "sets its own application process and deadlines, so exact-window discovery "
        "continues at the programme level."
    )

    def __init__(self, minimum_expected_programmes: int = 75) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalog = self.parse_catalog(fetcher(CATALOG_URL))
        admissions = normalise(
            BeautifulSoup(fetcher(APPLICATION_URL), "html.parser").get_text(
                " ", strip=True
            )
        ).casefold()
        if "each of our schools has its own application process" not in admissions:
            raise ValueError("Rochester's school-specific admissions policy is missing")
        return catalog

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        for item in soup.select(".research-link.grad"):
            link = item.select_one("a[href]")
            degree_label = item.select_one(".cert")
            if link is None or degree_label is None:
                continue
            name = normalise(link.get_text(" ", strip=True))
            degrees = {
                normalise(token)
                for token in re.split(r"[,/]", degree_label.get_text(" ", strip=True))
            }
            for degree_type in sorted(degrees & MASTER_DEGREES):
                rows.append(
                    entry(
                        name=name,
                        degree_type=degree_type,
                        source_url=str(link["href"]),
                        base_url=CATALOG_URL,
                    )
                )
        return rows
