from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, degree_from, entry

CATALOG_URL = "https://www.curtin.edu.au/study/courses/"
APPLICATION_URL = "https://www.curtin.edu.au/study/applying/"
PAGE_RE = re.compile(r"/study/courses/page/(\d+)/")


class CurtinAdapter(OfficialCatalogAdapter):
    university_id = "curtin-university"
    school_prefix = "curtin"
    institution_name = "Curtin University"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    minimum_expected_programmes = 20
    retrieval_method = "official-paginated-course-directory"

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        first_page = fetcher(CATALOG_URL)
        page_numbers = [int(value) for value in PAGE_RE.findall(first_page)]
        page_count = max(page_numbers, default=1)
        urls = [
            f"https://www.curtin.edu.au/study/courses/page/{page}/"
            for page in range(2, page_count + 1)
        ]
        entries = self.extract_entries(first_page)
        with ThreadPoolExecutor(max_workers=5) as executor:
            for html in executor.map(fetcher, urls):
                entries.extend(self.extract_entries(html))
        return self._catalog(entries)

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries: list[CatalogEntry] = []
        for anchor in soup.select("h3 a[href]"):
            name = anchor.get_text(" ", strip=True)
            source_url = urljoin(CATALOG_URL, str(anchor["href"]))
            if not urlsplit(source_url).path.startswith("/study/courses/"):
                continue
            if not name.casefold().startswith("master"):
                continue
            entries.append(
                entry(
                    name=name,
                    degree_type=degree_from(name),
                    source_url=source_url,
                    base_url=CATALOG_URL,
                )
            )
        return entries
