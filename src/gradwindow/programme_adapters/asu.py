from __future__ import annotations

from urllib.parse import urlsplit

import httpx
from bs4 import BeautifulSoup

from gradwindow.http_client import DEFAULT_USER_AGENT

from .base import DiscoveredCatalog, DiscoveredProgramme, Fetcher
from .official_catalog import (
    CatalogEntry,
    OfficialCatalogAdapter,
    entry,
    normalise,
    slug,
)

CATALOG_URL = "https://degrees.apps.asu.edu/masters-phd/major-list/letter/all"
APPLICATION_URL = "https://admission.asu.edu/apply/graduate"


class ASUAdapter(OfficialCatalogAdapter):
    university_id = "arizona-state-university"
    school_prefix = "asu"
    institution_name = "Arizona State University"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 390
    retrieval_method = "official-graduate-degree-search"

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        with httpx.Client(
            follow_redirects=True,
            timeout=60,
            headers={"User-Agent": DEFAULT_USER_AGENT},
        ) as client:
            response = client.get(CATALOG_URL)
            response.raise_for_status()
            catalog = response.text
        fetcher(APPLICATION_URL)
        return self.parse_catalog(catalog)

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries: list[CatalogEntry] = []
        for row in soup.select("tr[id]"):
            source = row.select_one('a.majorUrl[href*="/masters-phd/major/"]')
            degree = row.select_one("td.degree [title]")
            if source is None or degree is None:
                continue
            if "Master" not in str(degree.get("title", "")):
                continue
            entries.append(
                entry(
                    name=source.get_text(" ", strip=True),
                    degree_type=degree.get_text(" ", strip=True),
                    source_url=str(source["href"]),
                    base_url=CATALOG_URL,
                )
            )
        return entries

    def _catalog(self, entries: list[CatalogEntry]) -> DiscoveredCatalog:
        programmes: dict[str, DiscoveredProgramme] = {}
        for catalog_entry in entries:
            name = normalise(catalog_entry.name)
            degree_type = normalise(catalog_entry.degree_type)
            source_url = catalog_entry.source_url.strip()
            path_parts = urlsplit(source_url).path.strip("/").split("/")
            try:
                programme_code = path_parts[path_parts.index("ASU00") + 1]
            except (ValueError, IndexError):
                continue
            programme_id = (
                f"asu-{slug(programme_code)}-{slug(name)}-{slug(degree_type)}"
            )
            programmes[programme_id] = DiscoveredProgramme(
                id=programme_id,
                name=name,
                degree_type=degree_type,
                faculty=self.institution_name,
                department=self.institution_name,
                source_url=source_url,
                application_url=self.application_url,
                windows=[],
                deadline_text=(
                    "Programme found in Arizona State University's official "
                    "graduate degree search. No official programme-specific "
                    "pair of exact opening and closing dates was published, so "
                    "no date is inferred."
                ),
                parse_status="no-deadline",
                retrieval_method=self.retrieval_method,
                evidence_quality="official-full-text",
            )
        result = sorted(programmes.values(), key=lambda item: item.name.casefold())
        if len(result) < self.minimum_expected_programmes:
            raise ValueError(
                "Arizona State University's official directory contained "
                f"{len(result)} master's programmes; expected at least "
                f"{self.minimum_expected_programmes}"
            )
        return DiscoveredCatalog(application_opens_at=None, programmes=result)
