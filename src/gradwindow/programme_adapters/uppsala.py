from __future__ import annotations

import html
import json
import re

import httpx

from gradwindow.http_client import DEFAULT_USER_AGENT

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, degree_from, entry

CATALOG_URL = "https://www.uu.se/en/study/masters-studies/masters-programmes"
APPLICATION_URL = "https://www.uu.se/en/study/masters-studies/application.html"
PORTLET_RE = re.compile(
    r"AppRegistry\.registerInitialState\('(?P<id>[^']+)',"
    r'\{"displayMode":"search","categoryId":"educationInternationalMastersProgrammes"'
)


class UppsalaAdapter(OfficialCatalogAdapter):
    university_id = "uppsala-university"
    school_prefix = "uppsala"
    institution_name = "Uppsala University"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 105
    retrieval_method = "official-international-masters-search-api"

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        wrapper = fetcher(CATALOG_URL)
        match = PORTLET_RE.search(wrapper)
        if match is None:
            raise ValueError(
                "Uppsala international master's search portlet was not found"
            )
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
        rows: list[dict[str, object]] = []
        expected_count: int | None = None
        with httpx.Client(timeout=60, follow_redirects=True) as client:
            start = 0
            while expected_count is None or start < expected_count:
                response = client.post(
                    endpoint,
                    json={
                        "category": "educationInternationalMastersProgrammes",
                        "query": "",
                        "start": start,
                        "showMore": "true",
                    },
                    headers=headers,
                )
                response.raise_for_status()
                result = response.json().get("result", {})
                hits = result.get("hits", [])
                if not isinstance(hits, list):
                    raise ValueError("Uppsala search API returned invalid hits")
                if expected_count is None:
                    expected_count = int(result.get("count", 0))
                    if not 0 < expected_count <= 1000:
                        raise ValueError("Uppsala search API returned invalid count")
                elif int(result.get("count", 0)) != expected_count:
                    raise ValueError(
                        "Uppsala search API count changed during pagination"
                    )
                if not hits or len(rows) + len(hits) > expected_count:
                    raise ValueError(
                        "Uppsala search API returned incomplete pagination"
                    )
                if any(
                    not isinstance(row, dict) or row.get("type") != "programme"
                    for row in hits
                ):
                    raise ValueError("Uppsala master's search returned non-programmes")
                seen_urls = {row["uri"] for row in rows}
                for row in hits:
                    uri = row.get("uri")
                    if not uri or uri in seen_urls:
                        raise ValueError(
                            "Uppsala search API returned duplicate/missing URLs"
                        )
                    seen_urls.add(uri)
                rows.extend(hits)
                start += len(hits)
        fetcher(APPLICATION_URL)
        return self.parse_catalog(json.dumps(rows, ensure_ascii=False))

    def extract_entries(self, payload: str) -> list[CatalogEntry]:
        rows = json.loads(payload)
        return [
            entry(
                name=html.unescape(str(row["title"])),
                degree_type=degree_from(html.unescape(str(row["title"]))),
                source_url=str(row["uri"]),
                base_url=CATALOG_URL,
            )
            for row in rows
            if str(row.get("title", "")).strip() and str(row.get("uri", "")).strip()
        ]
