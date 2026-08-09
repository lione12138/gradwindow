from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry, normalise

CATALOG_URL = "https://www.tue.nl/en/education/graduate-school/master-programs"
APPLICATION_URL = (
    "https://www.tue.nl/en/education/become-a-tue-student/admission-and-application"
)
PROGRAMME_PATH = "/en/education/graduate-school/master-"


class TUEAdapter(OfficialCatalogAdapter):
    university_id = "eindhoven-university-of-technology"
    school_prefix = "tue"
    institution_name = "Eindhoven University of Technology"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-load-more-master-directory"

    def __init__(self, minimum_expected_programmes: int = 20) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        next_url: str | None = CATALOG_URL
        visited: set[str] = set()
        entries: list[CatalogEntry] = []
        while next_url:
            if next_url in visited or len(visited) >= 20:
                raise ValueError("TU/e master directory pagination did not terminate")
            visited.add(next_url)
            html = fetcher(next_url)
            entries.extend(self.extract_entries(html))
            soup = BeautifulSoup(html, "html.parser")
            more = soup.select_one("a.loadmore[href], a.loadMoreButton[href]")
            next_url = (
                urljoin(CATALOG_URL, str(more.get("href")))
                if more is not None
                else None
            )
        return self._catalog(entries)

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries = []
        for link in soup.select(f'a[href^="{PROGRAMME_PATH}"]'):
            heading = link.select_one(".entryBlock-title, h2, h3")
            name = normalise(heading.get_text(" ", strip=True)) if heading else ""
            if not name.casefold().startswith("master "):
                continue
            entries.append(
                entry(
                    name=name,
                    degree_type="Master",
                    source_url=str(link.get("href", "")),
                    base_url=CATALOG_URL,
                )
            )
        return entries
