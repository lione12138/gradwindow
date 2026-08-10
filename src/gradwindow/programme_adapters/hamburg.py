from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = "https://www.uni-hamburg.de/en/campuscenter/studienangebot"
CATALOG_ASSET_URL = (
    "https://www.uni-hamburg.de/onTEAM/admin/onteam/templates/v5/"
    "scripts/studiengaenge/indexEN.js"
)
ADMISSIONS_URL = (
    "https://www.uni-hamburg.de/en/campuscenter/bewerbung/international/master.html"
)
PROGRAMME_BASE_URL = "https://www.uni-hamburg.de/en/campuscenter/"
MASTER_DEGREES = {"M.A.", "M.Sc.", "M.Ed.", "LL.M.", "MBA", "M.P.H."}


class HamburgAdapter(OfficialCatalogAdapter):
    university_id = "university-of-hamburg"
    catalog_url = CATALOG_URL
    application_url = ADMISSIONS_URL
    school_prefix = "hamburg"
    institution_name = "University of Hamburg"
    minimum_expected_programmes = 100
    window_watch_urls = (CATALOG_ASSET_URL, ADMISSIONS_URL)
    retrieval_method = "official-degree-programme-catalogue-asset"
    catalogue_limitation_reason = (
        "Hamburg publishes programme-specific application requirements and "
        "deadlines. The central catalogue is complete, while programme-level "
        "exact opening-and-closing pairs remain monitored."
    )

    def __init__(self, minimum_expected_programmes: int = 100) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        shell = fetcher(CATALOG_URL)
        if "studiengaenge/indexEN.js" not in shell:
            raise ValueError("Hamburg's official catalogue asset is missing")
        entries = self.extract_entries(fetcher(CATALOG_ASSET_URL))
        policy = normalise(
            BeautifulSoup(fetcher(ADMISSIONS_URL), "html.parser").get_text(
                " ", strip=True
            )
        ).casefold()
        if "master" not in policy or "application" not in policy:
            raise ValueError("Hamburg's official master's admissions policy is missing")
        return self._catalog(entries)

    def extract_entries(self, javascript: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(javascript, "html.parser")
        rows = []
        for row in soup.select("table#studiengaenge tbody tr"):
            cells = row.select("td")
            if len(cells) < 6:
                continue
            degree_type = normalise(cells[1].get_text(" ", strip=True))
            start = normalise(cells[4].get_text(" ", strip=True)).casefold()
            link = cells[0].select_one("a[href]")
            if degree_type not in MASTER_DEGREES or link is None or "expires" in start:
                continue
            raw_name = normalise(link.get_text(" ", strip=True))
            name = re.sub(
                r"\s+Master of (?:Arts|Science|Education|Laws|Business Administration)$",
                "",
                raw_name,
                flags=re.IGNORECASE,
            )
            rows.append(
                CatalogEntry(
                    name=name,
                    degree_type=degree_type,
                    source_url=urljoin(PROGRAMME_BASE_URL, str(link["href"])),
                )
            )
        return rows
