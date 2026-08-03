from __future__ import annotations

import json
import re

import httpx

from gradwindow.http_client import DEFAULT_USER_AGENT

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import (
    CatalogEntry,
    OfficialCatalogAdapter,
    degree_from,
    entry,
)

CATALOG_URL = "https://www.su.se/english/education/course-catalogue"
APPLICATION_URL = "https://www.su.se/english/education/how-to-apply"
PORTLET_RE = re.compile(
    r"AppRegistry\.registerInitialState\('(?P<id>[^']+)',"
    r'\{"searchResult":'
)
MASTER_RE = re.compile(r"\b(master|LL\.M|LLM)\b", re.IGNORECASE)


class StockholmAdapter(OfficialCatalogAdapter):
    university_id = "stockholm-university"
    school_prefix = "stockholm"
    institution_name = "Stockholm University"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (
        APPLICATION_URL,
        "https://www.su.se/english/education/how-to-apply/important-dates",
    )
    minimum_expected_programmes = 160
    retrieval_method = "official-course-catalogue-api"

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        wrapper = fetcher(CATALOG_URL)
        match = PORTLET_RE.search(wrapper)
        if match is None:
            raise ValueError("Stockholm catalogue portlet was not found")
        portlet_id = match.group("id")
        endpoint = (
            f"{CATALOG_URL}?sv.target={portlet_id}&sv.{portlet_id}.route=%2Fsearch"
        )
        headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": CATALOG_URL,
        }
        facets = {
            "educationLevelId": ["2"],
            "educationTypeId": ["78 101270"],
        }
        rows: list[dict[str, object]] = []
        with httpx.Client(timeout=60, follow_redirects=True) as client:
            page = 0
            while True:
                response = client.post(
                    endpoint,
                    json={"query": "", "facets": facets, "p": page},
                    headers=headers,
                )
                response.raise_for_status()
                payload = response.json()
                rows.extend(payload.get("items", []))
                page += 1
                if page >= int(payload.get("numPages", 0)):
                    break
        return self.parse_catalog(json.dumps(rows))

    def extract_entries(self, payload: str) -> list[CatalogEntry]:
        rows = json.loads(payload)
        return [
            entry(
                name=row["name"],
                degree_type=degree_from(row["name"]),
                source_url=row["uri"],
                base_url=CATALOG_URL,
            )
            for row in rows
            if row.get("educationType") in {"Programme", "Specialisation"}
            and MASTER_RE.search(str(row.get("name", "")))
            and str(row.get("uri", "")).strip()
        ]
