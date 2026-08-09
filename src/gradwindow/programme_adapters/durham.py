from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, degree_from, entry

CATALOG_URL = "https://apps.dur.ac.uk/faculty.handbook/2026/PG"
APPLICATION_URL = "https://www.durham.ac.uk/study/postgraduate/how-to-apply/"

_MASTER_RE = re.compile(
    r"\b(?:MA|MBA|MDS|MEd|MEng|MFA|MLitt|MMath|MPhil|MPH|MRes|MSc|MS|Master)\b",
    re.IGNORECASE,
)


class DurhamAdapter(OfficialCatalogAdapter):
    university_id = "durham-university"
    school_prefix = "durham"
    institution_name = "Durham University"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-2026-27-postgraduate-programme-handbook"

    def __init__(self, minimum_expected_programmes: int = 100) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        index = BeautifulSoup(fetcher(CATALOG_URL), "html.parser")
        department_urls = sorted(
            {
                urljoin(CATALOG_URL, str(link["href"]))
                for link in index.select('a[href*="/PG/department/"]')
            }
        )
        if not department_urls:
            raise ValueError("Durham handbook exposed no postgraduate departments")
        entries: list[CatalogEntry] = []
        for department_url in department_urls:
            entries.extend(self.extract_entries(fetcher(department_url)))
        return self._catalog(entries)

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries: list[CatalogEntry] = []
        for link in soup.select('a[href*="/PG/programme/"]'):
            label = " ".join(link.get_text(" ", strip=True).split())
            name = label.split(":", 1)[-1].strip()
            lower = name.casefold()
            if (
                not _MASTER_RE.search(name)
                or "postgraduate certificate" in lower
                or "postgraduate diploma" in lower
                or "last intake" in lower
            ):
                continue
            entries.append(
                entry(
                    name=name,
                    degree_type=degree_from(name),
                    source_url=str(link["href"]),
                    base_url=CATALOG_URL,
                )
            )
        return entries
