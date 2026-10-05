from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry

CATALOG_URL = "https://www.tuwien.at/en/studies/studies/master-programmes"
APPLICATION_URL = "https://www.tuwien.at/en/studies/admission"
LANGUAGE_URLS = (
    CATALOG_URL + "/deutschsprachige-masterstudien",
    CATALOG_URL + "/english-taught-masters-programmes",
)
DETAIL_PATH_RE = re.compile(r"^/en/studies/studies/master-programmes/[^/]+/[^/]+/?$")
NAME_RE = re.compile(
    r"^(?:International(?:e)?\s+)?Master[’']?s?\s+Programme\s+",
    re.IGNORECASE,
)


class TUWienAdapter(OfficialCatalogAdapter):
    university_id = "vienna-university-of-technology"
    school_prefix = "tu-wien"
    institution_name = "TU Wien"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 30
    retrieval_method = "official-master-programme-directory"

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        html = fetcher(CATALOG_URL)
        soup = BeautifulSoup(html, "html.parser")
        main = soup.find("main") or soup
        links = {
            urljoin(CATALOG_URL, a["href"]).rstrip("/") for a in main.select("a[href]")
        }
        if not all(url in links for url in LANGUAGE_URLS):
            raise ValueError(
                "TU Wien master's language directories were not both found"
            )
        entries = self.extract_entries(html)
        for url in LANGUAGE_URLS:
            page_entries = self.extract_entries(fetcher(url))
            if not page_entries:
                raise ValueError("TU Wien master's language directory was empty")
            entries.extend(page_entries)
        return self._catalog(entries)

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        main = soup.find("main") or soup
        entries = []
        for anchor in main.find_all("a", href=True):
            label = " ".join(anchor.get_text(" ", strip=True).split())
            source_url = urljoin(CATALOG_URL, anchor["href"].strip())
            parsed = urlparse(source_url)
            host = (parsed.hostname or "").lower()
            if host not in {
                "tuwien.at",
                "informatics.tuwien.ac.at",
            } and not host.endswith(".tuwien.at"):
                continue
            current_detail = host in {
                "www.tuwien.at",
                "tuwien.at",
            } and DETAIL_PATH_RE.fullmatch(parsed.path)
            double_degree = host == "informatics.tuwien.ac.at" and re.fullmatch(
                r"/master/double-degree-[^/]+/?", parsed.path
            )
            if not label or not (
                NAME_RE.match(label) or current_detail or double_degree
            ):
                continue
            entries.append(
                entry(
                    name=NAME_RE.sub("", label),
                    degree_type="Master",
                    source_url=source_url,
                    base_url=CATALOG_URL,
                )
            )
        return entries
