from __future__ import annotations

import json
import re

import httpx

from gradwindow.http_client import DEFAULT_USER_AGENT

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry

CATALOG_URL = "https://www.qmul.ac.uk/postgraduate/taught/coursefinder/"
SEARCH_URL = "https://searchcloud-1-eu-west-2.searchstax.com/29847/qmu-1736/emselect"
APPLICATION_URL = "https://www.qmul.ac.uk/postgraduate/taught/applyfortaughtprogrammes/"
SEARCH_TOKEN_RE = re.compile(r"select_auth_token:\s*['\"]([^'\"]+)")


class QMULAdapter(OfficialCatalogAdapter):
    university_id = "queen-mary-university-of-london-qmul"
    school_prefix = "qmul"
    institution_name = "Queen Mary University of London"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    minimum_expected_programmes = 250
    retrieval_method = "official-coursefinder-search-api"

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalog_html = fetcher(CATALOG_URL)
        fetcher(APPLICATION_URL)
        token_match = SEARCH_TOKEN_RE.search(catalog_html)
        if token_match is None:
            raise ValueError("QMUL coursefinder did not expose its public search token")
        response = httpx.get(
            SEARCH_URL,
            params={
                "q": "*",
                "rows": "500",
                "model": "coursefinder-pg",
                "language": "en",
                "fl": "coursetitle,awardshortname,coursepageurl,deptname",
                "hl": "false",
                "facet": "false",
            },
            headers={
                "User-Agent": DEFAULT_USER_AGENT,
                "Accept": "application/json",
                "Authorization": f"Token {token_match.group(1)}",
                "Referer": CATALOG_URL,
            },
            timeout=60,
            follow_redirects=True,
        )
        response.raise_for_status()
        return self.parse_catalog(response.text)

    def extract_entries(self, payload: str) -> list[CatalogEntry]:
        documents = json.loads(payload).get("response", {}).get("docs", [])
        entries: list[CatalogEntry] = []
        for document in documents:
            name = _first(document.get("coursetitle"))
            degree = _first(document.get("awardshortname"))
            source_url = _first(document.get("coursepageurl"))
            if not (name and degree and source_url):
                continue
            entries.append(
                entry(
                    name=name,
                    degree_type=degree,
                    source_url=source_url,
                    base_url=CATALOG_URL,
                )
            )
        return entries


def _first(value: object) -> str:
    if isinstance(value, list):
        return str(value[0]) if value else ""
    return str(value or "")
