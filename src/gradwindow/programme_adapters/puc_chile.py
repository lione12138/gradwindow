from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry, normalise

CATALOG_URL = "https://admision.uc.cl/postgrado/magister/"
APPLICATION_URL = (
    "https://admision.uc.cl/postgrado/admision-al-postgrado/"
    "requisitos-y-postulacion-postgrado/"
)


class PUCChileAdapter(OfficialCatalogAdapter):
    university_id = "pontificia-universidad-cat-lica-de-chile"
    school_prefix = "puc-chile"
    institution_name = "Pontificia Universidad Católica de Chile"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-paginated-magister-directory"

    def __init__(self, minimum_expected_programmes: int = 80) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        first_page = fetcher(CATALOG_URL)
        soup = BeautifulSoup(first_page, "html.parser")
        pages = [1]
        for link in soup.select('a[href*="/postgrado/magister/page/"]'):
            match = re.search(r"/page/(\d+)/", str(link.get("href", "")))
            if match:
                pages.append(int(match.group(1)))
        entries = self.extract_entries(first_page)
        for page in range(2, max(pages) + 1):
            entries.extend(self.extract_entries(fetcher(f"{CATALOG_URL}page/{page}/")))
        return self._catalog(entries)

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries: list[CatalogEntry] = []
        for link in soup.select('a[href*="/postgrado/magister/"]'):
            name = normalise(link.get_text(" ", strip=True))
            source_url = urljoin(CATALOG_URL, str(link.get("href", "")))
            path = urlparse(source_url).path.rstrip("/")
            if (
                not name.casefold().startswith("magíster ")
                or "/page/" in path
                or path == "/postgrado/magister"
            ):
                continue
            entries.append(
                entry(
                    name=name,
                    degree_type="Magíster",
                    source_url=source_url,
                    base_url=CATALOG_URL,
                )
            )
        return entries
