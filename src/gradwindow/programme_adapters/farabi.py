from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry, normalise

CATALOG_URL = "https://welcome.kaznu.kz/en/education_programs/magistracy/"
APPLICATION_URL = "https://welcome.kaznu.kz/en/admissions/magistracy/"


class FarabiAdapter(OfficialCatalogAdapter):
    university_id = "al-farabi-kazakh-national-university"
    school_prefix = "farabi"
    institution_name = "Al-Farabi Kazakh National University"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-paginated-masters-directory"

    def __init__(self, minimum_expected_programmes: int = 200) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        first_page = fetcher(CATALOG_URL)
        soup = BeautifulSoup(first_page, "html.parser")
        pages = [1]
        for link in soup.select('a[href*="page="]'):
            match = re.search(r"[?&]page=(\d+)", str(link.get("href", "")))
            if match:
                pages.append(int(match.group(1)))
        entries = self.extract_entries(first_page)
        for page in range(2, max(pages) + 1):
            entries.extend(self.extract_entries(fetcher(f"{CATALOG_URL}?page={page}")))
        return self._catalog(entries)

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries = []
        for card in soup.select(
            'a.card[href*="/education_programs/magistracy/speciality/"]'
        ):
            code_node = card.select_one(".code")
            heading = card.select_one("h2")
            code = normalise(code_node.get_text(" ", strip=True)) if code_node else ""
            name = normalise(heading.get_text(" ", strip=True)) if heading else ""
            if not code.startswith("7M") or not name:
                continue
            entries.append(
                entry(
                    name=f"{name} ({code})",
                    degree_type="Master",
                    source_url=urljoin(CATALOG_URL, str(card.get("href", ""))),
                    base_url=CATALOG_URL,
                )
            )
        return entries
