from __future__ import annotations

import re
from urllib.parse import urlencode, urljoin

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = "https://www.unipd.it/en/corsi-di-laurea-magistrale"
APPLICATION_URL = "https://www.unipd.it/en/avvisi-ammissione-lauree-magistrali"
_TOTAL_PAGES_RE = re.compile(r'totalPages(?:\\"|\")?\s*:\s*(?P<count>\d+)')


class PaduaAdapter(OfficialCatalogAdapter):
    university_id = "university-of-padua"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "padua"
    institution_name = "University of Padua"
    minimum_expected_programmes = 120
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-paginated-masters-catalogue"
    catalogue_limitation_reason = (
        "Padua's official admissions page states that master's programmes have "
        "different deadlines and entry requirements. Programme-specific calls "
        "remain monitored and no common exact window is inferred."
    )

    def __init__(self, minimum_expected_programmes: int = 120) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        first_page = fetcher(CATALOG_URL)
        pages = [first_page]
        total_pages = _total_pages(first_page)
        if total_pages > 50:
            raise ValueError("Padua catalogue pagination exceeded its safety bound")
        for page_number in range(2, total_pages + 1):
            pages.append(fetcher(f"{CATALOG_URL}?{urlencode({'page': page_number})}"))
        policy = normalise(
            BeautifulSoup(fetcher(APPLICATION_URL), "html.parser").get_text(
                " ", strip=True
            )
        ).casefold()
        if (
            "degree programmes have different deadlines and entry requirements"
            not in policy
        ):
            raise ValueError("Padua's programme-specific deadline policy is missing")
        entries = [entry for page in pages for entry in self.extract_entries(page)]
        return self._catalog(entries)

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        for link in soup.select("a[href]"):
            classes = " ".join(link.get("class", []))
            if "cardCorsiBox" not in classes:
                continue
            text = normalise(link.get_text(" ", strip=True))
            title = link.find("h4")
            if title is None or "Master's Degree" not in text:
                continue
            rows.append(
                CatalogEntry(
                    name=normalise(title.get_text(" ", strip=True)),
                    degree_type="Master's Degree",
                    source_url=urljoin(CATALOG_URL, str(link["href"])),
                )
            )
        return rows


def _total_pages(html: str) -> int:
    match = _TOTAL_PAGES_RE.search(html)
    if match is not None:
        return int(match.group("count"))
    soup = BeautifulSoup(html, "html.parser")
    page_numbers = []
    for control in soup.select("[aria-label*='page']"):
        label = normalise(str(control.get("aria-label", "")))
        number = re.search(r"\d+", label)
        if number is not None:
            page_numbers.append(int(number.group()))
    return max(page_numbers, default=1)
