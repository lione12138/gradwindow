from __future__ import annotations

from urllib.parse import unquote, urljoin

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, degree_from, entry

CATALOG_URL = "https://www.tu.berlin/en/studying/study-programs/all-programs-offered"
APPLICATION_URL = (
    "https://www.tu.berlin/en/studying/applying-and-enrolling/dates-deadlines"
)


class TUBerlinAdapter(OfficialCatalogAdapter):
    university_id = "technische-universit-t-berlin"
    school_prefix = "tu-berlin"
    institution_name = "Technische Universität Berlin"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (APPLICATION_URL,)
    minimum_expected_programmes = 85
    retrieval_method = "official-master-filtered-programme-directory"

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        directory = fetcher(CATALOG_URL)
        soup = BeautifulSoup(directory, "html.parser")
        master_filter = next(
            (
                link
                for link in soup.select("a[href]")
                if link.get_text(" ", strip=True).startswith("Master (")
            ),
            None,
        )
        if master_filter is None:
            raise ValueError("TU Berlin master's degree filter was not found")
        filtered_url = urljoin(CATALOG_URL, master_filter["href"])
        first_page = fetcher(filtered_url)
        page_soup = BeautifulSoup(first_page, "html.parser")
        page_urls = {
            urljoin(filtered_url, link["href"])
            for link in page_soup.select("a[href]")
            if "studypathlist" in unquote(link["href"])
            and "[page]" in unquote(link["href"])
        }
        entries = self.extract_entries(first_page)
        for page_url in sorted(page_urls):
            entries.extend(self.extract_entries(fetcher(page_url)))
        fetcher(APPLICATION_URL)
        return self._catalog(entries)

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries = []
        for heading in soup.select("h2.studypaths__listItemName"):
            link = heading.find_parent("a", href=True)
            name = heading.get_text(" ", strip=True)
            if link is None or not name:
                continue
            entries.append(
                entry(
                    name=name,
                    degree_type=degree_from(name.replace(".", "")),
                    source_url=link["href"],
                    base_url=CATALOG_URL,
                )
            )
        return entries
