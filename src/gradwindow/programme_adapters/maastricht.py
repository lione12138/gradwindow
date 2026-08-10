from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import (
    CatalogEntry,
    OfficialCatalogAdapter,
    degree_from,
    entry,
    normalise,
)

CATALOG_URL = "https://www.maastrichtuniversity.nl/education/master/programmes"
APPLICATION_URL = "https://www.maastrichtuniversity.nl/study/admission-enrolment"


class MaastrichtAdapter(OfficialCatalogAdapter):
    university_id = "maastricht-university"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "maastricht"
    institution_name = "Maastricht University"
    minimum_expected_programmes = 100
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-paginated-masters-catalogue"
    catalogue_limitation_reason = (
        "Maastricht's official catalogue is complete, but application dates and "
        "eligibility routes vary by programme and applicant background. Programme "
        "pages remain monitored until an exact official opening-and-closing pair "
        "can be assigned safely."
    )

    def __init__(self, minimum_expected_programmes: int = 100) -> None:
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
        admissions = normalise(
            BeautifulSoup(fetcher(APPLICATION_URL), "html.parser").get_text(
                " ", strip=True
            )
        ).casefold()
        if "admission" not in admissions or "enrol" not in admissions:
            raise ValueError("Maastricht's official admission guidance is missing")
        return self._catalog(entries)

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        for article in soup.select(
            'article[data-component-id="um_corporate:list-item"]'
        ):
            link = article.select_one("h2 a[href]")
            if link is None:
                continue
            name = normalise(link.get_text(" ", strip=True))
            rows.append(
                entry(
                    name=name,
                    degree_type=degree_from(name),
                    source_url=str(link["href"]),
                    base_url=CATALOG_URL,
                )
            )
        return rows


def _next_page_url(html: str, current_url: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    link = soup.select_one('a[rel~="next"][href]')
    return urljoin(current_url, str(link["href"])) if link else None
