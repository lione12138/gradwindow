from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import (
    CatalogEntry,
    OfficialCatalogAdapter,
    degree_from,
    entry,
)

CATALOG_URL = "https://sgs.upm.edu.my/programme_of_study/programme_by_coursework-4574"
APPLICATION_URL = "https://sgs.upm.edu.my/admissions-2964"
FACULTY_PATH_RE = re.compile(r"/programme_by_coursework/[a-z0-9_]+-\d+$")


class UPMAdapter(OfficialCatalogAdapter):
    university_id = "universiti-putra-malaysia-upm"
    school_prefix = "upm"
    institution_name = "Universiti Putra Malaysia"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    minimum_expected_programmes = 50
    retrieval_method = "official-coursework-programme-directory"

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        index_html = fetcher(CATALOG_URL)
        faculty_urls = self.extract_faculty_urls(index_html)
        entries: list[CatalogEntry] = []
        for source_url in faculty_urls:
            entries.extend(self.extract_entries(fetcher(source_url), source_url))
        fetcher(APPLICATION_URL)
        return self._catalog(entries)

    def extract_faculty_urls(self, html: str) -> list[str]:
        soup = BeautifulSoup(html, "html.parser")
        urls = {
            entry(
                name="placeholder",
                degree_type="Master",
                source_url=str(anchor["href"]),
                base_url=CATALOG_URL,
            ).source_url
            for anchor in soup.select("a[href]")
            if FACULTY_PATH_RE.search(str(anchor["href"]))
            or "master_by_coursework" in str(anchor["href"])
        }
        return sorted(urls)

    def extract_entries(
        self, html: str, source_url: str = CATALOG_URL
    ) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        names = {
            strong.get_text(" ", strip=True)
            for strong in soup.select("strong")
            if strong.get_text(" ", strip=True)
            .lower()
            .startswith(("master of ", "master in "))
        }
        return [
            entry(
                name=name,
                degree_type=degree_from(name),
                source_url=source_url,
                base_url=CATALOG_URL,
            )
            for name in sorted(names)
        ]
