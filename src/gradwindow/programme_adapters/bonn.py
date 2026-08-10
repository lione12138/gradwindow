from __future__ import annotations

import re
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry, normalise

CATALOG_URL = "https://www.uni-bonn.de/en/studying/degree-programs/degree-programs-a-z"
DEADLINES_URL = (
    "https://www.uni-bonn.de/en/studying/application-admission-and-enrollment/"
    "application-deadlines"
)


class BonnAdapter(OfficialCatalogAdapter):
    university_id = "university-of-bonn"
    catalog_url = CATALOG_URL
    admissions_url = DEADLINES_URL
    application_url = DEADLINES_URL
    school_prefix = "bonn"
    institution_name = "University of Bonn"
    minimum_expected_programmes = 120
    window_watch_urls = (CATALOG_URL, DEADLINES_URL)
    retrieval_method = "official-paginated-degree-programme-catalogue"
    catalogue_limitation_reason = (
        "The University of Bonn explicitly states that postgraduate programmes "
        "have no uniform application deadlines and directs applicants to each "
        "master's programme description. Programme pages remain monitored."
    )

    def __init__(self, minimum_expected_programmes: int = 120) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        first_page = fetcher(CATALOG_URL)
        pages = [first_page]
        total = _result_count(first_page)
        for offset in range(30, total, 30):
            query = urlencode({"b_start:int": offset})
            pages.append(fetcher(f"{CATALOG_URL}?{query}"))
        entries = [item for page in pages for item in self.extract_entries(page)]
        policy = normalise(
            BeautifulSoup(fetcher(DEADLINES_URL), "html.parser").get_text(
                " ", strip=True
            )
        ).casefold()
        if "no uniform rules governing application deadlines" not in policy:
            raise ValueError("Bonn's postgraduate deadline policy is missing")
        return self._catalog(entries)

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        for link in soup.select("a.course[href]"):
            title = link.select_one("label.title")
            graduation = link.select_one(".graduation-title")
            if title is None or graduation is None:
                continue
            degree_type = normalise(graduation.get_text(" ", strip=True))
            if "master" not in degree_type.casefold():
                continue
            rows.append(
                entry(
                    name=title.get_text(" ", strip=True),
                    degree_type=degree_type,
                    source_url=str(link["href"]),
                    base_url=CATALOG_URL,
                )
            )
        return rows


def _result_count(html: str) -> int:
    soup = BeautifulSoup(html, "html.parser")
    label = soup.select_one(".results-count")
    match = re.search(r"\d+", label.get_text(" ", strip=True) if label else "")
    if match is None:
        raise ValueError("Bonn catalogue result count is missing")
    return int(match.group())
