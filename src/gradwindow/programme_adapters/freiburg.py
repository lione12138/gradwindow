from __future__ import annotations

import json

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = "https://uni-freiburg.de/wp-json/study-search/v1/studies"
DETAIL_BASE_URL = (
    "https://uni-freiburg.de/en/studies/degree-programmes/degree-programme/"
)
APPLICATION_URL = "https://uni-freiburg.de/en/studies/applying/how-do-i-apply/"


class FreiburgAdapter(OfficialCatalogAdapter):
    university_id = "university-of-freiburg"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "freiburg"
    institution_name = "University of Freiburg"
    minimum_expected_programmes = 125
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-study-search-json-api"
    catalogue_limitation_reason = (
        "Freiburg's first-party study-search API identifies active master's "
        "programmes and their programme detail pages. The university directs "
        "applicants to programme-specific periods, so no common window is inferred."
    )

    def __init__(self, minimum_expected_programmes: int = 125) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalog = self.parse_catalog(fetcher(CATALOG_URL))
        guidance = normalise(
            BeautifulSoup(fetcher(APPLICATION_URL), "html.parser").get_text(
                " ", strip=True
            )
        ).casefold()
        if (
            "applying for master" not in guidance
            or "online application portal" not in guidance
        ):
            raise ValueError(
                "Freiburg's official master's application guide is missing"
            )
        return catalog

    def extract_entries(self, payload: str) -> list[CatalogEntry]:
        data = json.loads(payload)
        rows = []
        for item in data.get("data", []):
            degree = normalise(item.get("abschlussnameen") or "")
            if not degree.casefold().startswith("master") or item.get("status") != 1:
                continue
            name = normalise(item.get("nameen") or item.get("namede") or "")
            variant = normalise(item.get("fachnameen") or "")
            if variant:
                name = f"{name} ({variant})"
            rows.append(
                CatalogEntry(
                    name=name,
                    degree_type=degree,
                    source_url=f"{DETAIL_BASE_URL}{item['id']}/",
                )
            )
        return rows
