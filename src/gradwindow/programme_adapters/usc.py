from __future__ import annotations

from urllib.parse import urlencode

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, degree_from, entry

CATALOG_URL = "https://www.usc.edu/graduate-professional/"
APPLICATION_URL = "https://gradadm.usc.edu/apply/"


class USCAdapter(OfficialCatalogAdapter):
    university_id = "university-of-southern-california"
    school_prefix = "usc"
    institution_name = "University of Southern California"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-filtered-graduate-programme-directory"

    def __init__(self, minimum_expected_programmes: int = 300) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        index = fetcher(CATALOG_URL)
        degree_values = _master_degree_values(index)
        if not degree_values:
            raise ValueError("USC directory did not expose master's degree filters")
        next_url: str | None = (
            CATALOG_URL
            + "?"
            + urlencode([("program-degrees[]", value) for value in degree_values])
        )
        visited: set[str] = set()
        entries: list[CatalogEntry] = []
        while next_url:
            if next_url in visited or len(visited) >= 60:
                raise ValueError("USC programme pagination did not terminate")
            visited.add(next_url)
            html = fetcher(next_url)
            entries.extend(self.extract_entries(html))
            soup = BeautifulSoup(html, "html.parser")
            next_link = next(
                (
                    link
                    for link in soup.select("nav.pager a[href]")
                    if link.get_text(" ", strip=True).casefold() == "next page"
                ),
                None,
            )
            next_url = str(next_link.get("href")) if next_link is not None else None
        return self._catalog(entries)

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries = []
        for link in soup.select("li a[href]"):
            if link.get_text(" ", strip=True).casefold() != "learn more":
                continue
            item = link.find_parent("li")
            heading = item.select_one(".item-title") if item is not None else None
            name = heading.get_text(" ", strip=True) if heading is not None else ""
            source_url = str(link.get("href", ""))
            if not name or "catalogue.usc.edu/" not in source_url:
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


def _master_degree_values(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    values = []
    for field in soup.select('input[name="program-degrees[]"][value]'):
        label = soup.find("label", attrs={"for": field.get("id")})
        if label is not None and "master" in label.get_text(" ", strip=True).casefold():
            values.append(str(field.get("value")))
    return values
