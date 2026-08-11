from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = (
    "https://grad.ucalgary.ca/future-students/graduate/discover-opportunities/"
    "explore-programs"
)
APPLICATION_URL = (
    "https://grad.ucalgary.ca/future-students/graduate/admissions/how-apply"
)


class CalgaryAdapter(OfficialCatalogAdapter):
    university_id = "university-of-calgary"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "calgary"
    institution_name = "University of Calgary"
    minimum_expected_programmes = 90
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-paginated-graduate-programme-finder"
    catalogue_limitation_reason = (
        "Calgary's official graduate finder covers course- and thesis-based "
        "master's degrees. The university directs applicants to each programme "
        "for its deadline, so no common exact opening-and-closing pair is inferred."
    )

    def __init__(self, minimum_expected_programmes: int = 90) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        entries: list[CatalogEntry] = []
        next_url: str | None = CATALOG_URL
        seen: set[str] = set()
        while next_url and next_url not in seen:
            seen.add(next_url)
            html = fetcher(next_url)
            entries.extend(self.extract_entries(html))
            next_url = _next_page_url(html, next_url)
        guidance = normalise(
            BeautifulSoup(fetcher(APPLICATION_URL), "html.parser").get_text(
                " ", strip=True
            )
        ).casefold()
        if "review the application deadlines for your graduate program" not in guidance:
            raise ValueError(
                "Calgary's programme-specific deadline guidance is missing"
            )
        return self._catalog(entries)

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        for card in soup.select(".row.results .result"):
            credential = card.select_one(".credential")
            link = card.select_one(".program a[href]")
            if credential is None or link is None:
                continue
            degree_type = normalise(credential.get_text(" ", strip=True))
            if not degree_type.casefold().startswith("master"):
                continue
            label = normalise(link.get_text(" ", strip=True))
            parts = re.split(r"\s*-\s*", label)
            name = parts[0]
            if len(parts) > 2 and re.fullmatch(r"M[A-Za-z.]+", parts[1]):
                name = f"{name} ({' - '.join(parts[2:])})"
            rows.append(
                CatalogEntry(
                    name=name,
                    degree_type=degree_type,
                    source_url=urljoin(CATALOG_URL, str(link["href"])),
                )
            )
        return rows


def _next_page_url(html: str, current_url: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    link = soup.select_one(".pager__item--next:not(.disabled) a[href]")
    return urljoin(current_url, str(link["href"])) if link else None
