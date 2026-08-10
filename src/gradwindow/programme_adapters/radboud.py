from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry, normalise

CATALOG_URL = "https://www.ru.nl/en/education/masters/overview"
APPLICATION_URL = (
    "https://www.ru.nl/en/education/application-and-admission/"
    "application-procedure-masters/deadlines"
)


class RadboudAdapter(OfficialCatalogAdapter):
    university_id = "radboud-university-nijmegen"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "radboud"
    institution_name = "Radboud University Nijmegen"
    minimum_expected_programmes = 60
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-paginated-masters-overview"
    catalogue_limitation_reason = (
        "Radboud publishes recurring central dates for regular master's "
        "programmes, but placement programmes and several applicant categories "
        "have exceptions. Exact windows remain programme-level monitoring data "
        "until each catalogue entry can be classified safely."
    )

    def __init__(self, minimum_expected_programmes: int = 60) -> None:
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
        deadlines = normalise(
            BeautifulSoup(fetcher(APPLICATION_URL), "html.parser").get_text(
                " ", strip=True
            )
        ).casefold()
        required = ("1 october onwards", "1 may onwards", "placement procedure")
        if not all(marker in deadlines for marker in required):
            raise ValueError("Radboud's recurring deadline policy is incomplete")
        return self._catalog(entries)

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        for heading in soup.select("h2.card__title"):
            link = heading.select_one("a[href]")
            if link is None:
                continue
            rows.append(
                entry(
                    name=normalise(link.get_text(" ", strip=True)),
                    degree_type="Master",
                    source_url=str(link["href"]),
                    base_url=CATALOG_URL,
                )
            )
        return rows


def _next_page_url(html: str, current_url: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    link = soup.select_one('a[rel~="next"][href]')
    return urljoin(current_url, str(link["href"])) if link else None
