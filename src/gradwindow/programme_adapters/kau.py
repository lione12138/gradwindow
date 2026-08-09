from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry

CATALOG_URL = "https://www.kau.edu.sa/en/programs?page=1"
APPLICATION_URL = "https://kau.edu.sa/en/page/admission-to-postgraduate-studies"
# Next.js serialises the page count inside an escaped React Server Component
# payload in production, while fixtures and older renders may expose plain JSON.
TOTAL_PAGES_RE = re.compile(r'totalPages\\?"\s*:\s*(\d+)')


class KAUAdapter(OfficialCatalogAdapter):
    university_id = "king-abdul-aziz-university-kau"
    school_prefix = "kau"
    institution_name = "King Abdulaziz University"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    minimum_expected_programmes = 100
    retrieval_method = "official-paginated-academic-programme-catalogue"

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        first_page = fetcher(CATALOG_URL)
        match = TOTAL_PAGES_RE.search(first_page)
        if not match:
            raise ValueError("KAU catalogue did not expose its page count")
        page_count = int(match.group(1))
        entries = self.extract_entries(first_page)
        # The production catalogue intermittently redirects concurrent page
        # requests back to page one, so crawl its small fixed page set serially.
        for page in range(2, page_count + 1):
            entries.extend(
                self.extract_entries(
                    fetcher(f"https://www.kau.edu.sa/en/programs?page={page}")
                )
            )
        return self._catalog(entries)

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries: list[CatalogEntry] = []
        for card in soup.select("article"):
            heading = card.select_one("h3")
            link = card.select_one('a[href*="/programs/"]')
            badge = card.select_one("div.mb-2")
            if heading is None or link is None or badge is None:
                continue
            badge_text = badge.get_text(" ", strip=True).casefold()
            name = heading.get_text(" ", strip=True)
            if "master" not in badge_text:
                continue
            details = card.select_one("div.space-y-2")
            detail_rows = details.find_all("div", recursive=False) if details else []
            if len(detail_rows) > 1:
                degree_text = detail_rows[1].get_text(" ", strip=True).casefold()
                if "master" not in degree_text:
                    continue
            if "bachelor" in name.casefold() or "بكالوريوس" in name:
                continue
            entries.append(
                entry(
                    name=name,
                    degree_type="Master",
                    source_url=urljoin(CATALOG_URL, str(link["href"])),
                    base_url=CATALOG_URL,
                )
            )
        return entries
