from __future__ import annotations

import json
from urllib.parse import urlencode

from gradwindow.http_client import DEFAULT_USER_AGENT, fetch_page

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import (
    CatalogEntry,
    OfficialCatalogAdapter,
    degree_from,
    entry,
)

CATALOG_URL = "https://www.chalmers.se/en/education/find-masters-programme/"
SEARCH_API_URL = "https://www.chalmers.se/api/ProgrammeListingPageSearch"
APPLICATION_URL = (
    "https://www.chalmers.se/en/education/application-and-admission/"
    "how-to-apply-from-application-to-admission/"
)


class ChalmersAdapter(OfficialCatalogAdapter):
    university_id = "chalmers-university-of-technology"
    school_prefix = "chalmers"
    institution_name = "Chalmers University of Technology"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 30
    retrieval_method = "official-programme-search-api"

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        wrapper = fetcher(CATALOG_URL)
        if "find-masters-programme" not in wrapper.casefold():
            raise ValueError("Chalmers programme search was not found")
        fetcher(APPLICATION_URL)
        variables = {
            "language": "en",
            "indexes": ["CmsSearch"],
            "size": 100,
            "from": 0,
            "filter": {"contentType": {"_eq": "ProgrammePageV2"}},
        }
        api_url = f"{SEARCH_API_URL}?{urlencode({'variables': json.dumps(variables, separators=(',', ':'))})}"
        page = fetch_page(
            api_url,
            user_agent=DEFAULT_USER_AGENT,
            timeout=90,
            max_bytes=1_000_000,
            attempts=3,
            accept="application/json",
        )
        return self.parse_catalog(page.body)

    def extract_entries(self, payload: str) -> list[CatalogEntry]:
        results = json.loads(payload)["search"]["results"]
        return [
            entry(
                name=str(row.get("title") or ""),
                degree_type=degree_from(str(row.get("title") or "")),
                source_url=str(row.get("url") or ""),
                base_url=CATALOG_URL,
            )
            for row in results
            if row.get("contentType") == "ProgrammePageV2"
            and str(row.get("title") or "").strip()
            and str(row.get("url") or "").strip()
        ]
