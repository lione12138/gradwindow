from __future__ import annotations

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import (
    CatalogEntry,
    OfficialCatalogAdapter,
    degree_from,
    normalise,
)

CATALOG_URL = "https://graduate.dartmouth.edu/admissions/programs"
APPLICATION_URL = "https://graduate.dartmouth.edu/admissions/applying-dartmouth"
MASTER_HEADINGS = {
    "master of fine arts": "MFA",
    "master's programs (ms and ma)": "Master",
    "master's programs (geisel based ms)": "MS",
    "professional degrees": "Master",
}


class DartmouthAdapter(OfficialCatalogAdapter):
    university_id = "dartmouth-college"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "dartmouth"
    institution_name = "Dartmouth College"
    minimum_expected_programmes = 14
    catalogue_status = "partial"
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-guarini-and-geisel-programmes-list"
    catalogue_limitation_reason = (
        "The official Guarini page covers Guarini and listed Geisel master's "
        "programmes, but not every professional degree offered independently by "
        "Dartmouth's other schools. Fall 2027 is announced only as opening in "
        "September, which is not an exact opening date."
    )

    def __init__(self, minimum_expected_programmes: int = 14) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalog = self.parse_catalog(fetcher(CATALOG_URL))
        admissions = normalise(
            BeautifulSoup(fetcher(APPLICATION_URL), "html.parser").get_text(
                " ", strip=True
            )
        ).casefold()
        if "fall 2027 will open in september" not in admissions:
            raise ValueError("Dartmouth's Fall 2027 application notice is missing")
        return catalog

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        for heading in soup.select("h2"):
            heading_text = normalise(heading.get_text(" ", strip=True)).casefold()
            default_degree = MASTER_HEADINGS.get(heading_text)
            if default_degree is None:
                continue
            listing = heading.find_next_sibling("div")
            if listing is None:
                continue
            for link in listing.select("a[href]"):
                name = normalise(link.get_text(" ", strip=True))
                degree_type = degree_from(name, default=default_degree)
                rows.append(
                    CatalogEntry(
                        name=name,
                        degree_type=degree_type,
                        source_url=str(link["href"]),
                    )
                )
        return rows
