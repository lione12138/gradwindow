from __future__ import annotations

import json

import httpx

from gradwindow.http_client import DEFAULT_USER_AGENT

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry

CATALOG_URL = "https://vu.nl/en/education/master/programmes"
SEARCH_API_URL = "https://vu.nl/api/search"
APPLICATION_URL = "https://vu.nl/en/education/more-about/apply-masters-programme"


class VUAmsterdamAdapter(OfficialCatalogAdapter):
    university_id = "vrije-universiteit-amsterdam"
    school_prefix = "vu-amsterdam"
    institution_name = "Vrije Universiteit Amsterdam"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 100
    retrieval_method = "official-study-search-api"

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        wrapper = fetcher(CATALOG_URL)
        if 'search-index="vuweb"' not in wrapper:
            raise ValueError("VU Amsterdam study search widget was not found")
        fetcher(APPLICATION_URL)
        body = {
            "queryType": "full",
            "filter": (
                "ItemType/any(c: search.in(c, 'Study')) and "
                "ItemType/any(c: search.in(c, 'Master')) and Language eq 'EN'"
            ),
            "search": "*",
            "count": True,
            "skip": 0,
            "top": 1000,
            "orderby": "Title asc",
        }
        last_error: Exception | None = None
        for _attempt in range(3):
            try:
                response = httpx.post(
                    SEARCH_API_URL,
                    json=body,
                    headers={
                        "User-Agent": DEFAULT_USER_AGENT,
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        "index": "vuweb",
                        "api-version": "2020-06-30",
                        "Referer": CATALOG_URL,
                    },
                    timeout=90,
                    follow_redirects=True,
                )
                response.raise_for_status()
                return self.parse_catalog(response.text)
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
        raise RuntimeError("VU Amsterdam study search failed") from last_error

    def extract_entries(self, payload: str) -> list[CatalogEntry]:
        rows = json.loads(payload)["value"]
        entries = []
        for row in rows:
            item_types = set(row.get("ItemType") or [])
            if (
                not {"Study", "Master"}.issubset(item_types)
                or "PreMaster" in item_types
                or "Specialization" in item_types
            ):
                continue
            entries.append(
                entry(
                    name=str(row.get("Title") or ""),
                    degree_type="Master",
                    source_url=str(row.get("Url") or ""),
                    base_url=CATALOG_URL,
                )
            )
        return entries
