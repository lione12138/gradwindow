from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = "https://catalog.uab.edu/graduate/programindex/"
APPLICATION_URL = "https://catalog.uab.edu/graduate/admission/"
PROGRAMME_RE = re.compile(r"^(?P<name>.+?)\s*\((?P<degrees>[^)]*)\)\s*$")


class UABAdapter(OfficialCatalogAdapter):
    university_id = "university-of-alabama-at-birmingham"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "uab"
    institution_name = "University of Alabama at Birmingham"
    minimum_expected_programmes = 65
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-graduate-program-index"
    catalogue_limitation_reason = (
        "UAB's official graduate catalog index identifies master's awards and "
        "their catalog pages. Departments set programme-specific requirements and "
        "deadlines, so no common exact window is inferred."
    )

    def __init__(self, minimum_expected_programmes: int = 65) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalog = self.parse_catalog(fetcher(CATALOG_URL))
        guidance = normalise(
            BeautifulSoup(fetcher(APPLICATION_URL), "html.parser").get_text(
                " ", strip=True
            )
        ).casefold()
        if "application for admission" not in guidance or "graduate" not in guidance:
            raise ValueError("UAB's official graduate admission guide is missing")
        return catalog

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        for link in soup.select("table a[href]"):
            label = normalise(link.get_text(" ", strip=True))
            match = PROGRAMME_RE.match(label)
            if match is None:
                continue
            degrees = []
            for token in re.split(r"[,/]", match.group("degrees")):
                degree = normalise(token)
                compact = degree.upper().replace(".", "")
                if not degree.upper().startswith("M") or compact == "MD":
                    continue
                if degree not in degrees:
                    degrees.append(degree)
            if not degrees:
                continue
            rows.append(
                CatalogEntry(
                    name=match.group("name"),
                    degree_type=", ".join(degrees),
                    source_url=urljoin(CATALOG_URL, str(link["href"])),
                )
            )
        return rows
