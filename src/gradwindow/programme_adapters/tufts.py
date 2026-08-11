from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = "https://www.tufts.edu/graduate-programs"
APPLICATION_URL = "https://www.tufts.edu/admissions/graduate"


class TuftsAdapter(OfficialCatalogAdapter):
    university_id = "tufts-university"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "tufts"
    institution_name = "Tufts University"
    minimum_expected_programmes = 90
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-paginated-graduate-programmes-directory"
    catalogue_limitation_reason = (
        "Tufts' university-wide directory identifies master's programmes across "
        "its graduate schools. Each school and programme maintains its own "
        "requirements and dates, so exact windows remain programme-level monitors."
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
        if "requirements at each of our graduate schools" not in guidance:
            raise ValueError("Tufts' graduate-school admissions guidance is missing")
        return self._catalog(entries)

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        for card in soup.select("article.node--type-program"):
            title = card.select_one("h4.program--title")
            degree = card.select_one(".program--degree")
            link = card.select_one("a.program--cta[href]")
            if title is None or degree is None or link is None:
                continue
            degree_text = normalise(degree.get_text(" ", strip=True))
            if "master" not in degree_text.casefold():
                continue
            label = normalise(title.get_text(" ", strip=True))
            name = re.sub(
                r"\s+-\s+Master(?:'s|’s)(?: and Doctorate)?$", "", label
            ).strip()
            rows.append(
                CatalogEntry(
                    name=name,
                    degree_type="Master",
                    source_url=urljoin(CATALOG_URL, str(link["href"])),
                )
            )
        return rows


def _next_page_url(html: str, current_url: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    link = soup.select_one('a[rel~="next"][href]')
    return urljoin(current_url, str(link["href"])) if link else None
