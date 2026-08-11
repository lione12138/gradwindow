from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = (
    "https://www.gu.se/en/study-in-gothenburg/programs-and-courses/masters-programs"
)
APPLICATION_URL = (
    "https://www.gu.se/en/study-in-gothenburg/apply/apply-for-masters-program"
)


class GothenburgAdapter(OfficialCatalogAdapter):
    university_id = "university-of-gothenburg"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "gothenburg"
    institution_name = "University of Gothenburg"
    minimum_expected_programmes = 75
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-international-masters-directory"
    catalogue_limitation_reason = (
        "Gothenburg's official international master's directory covers the "
        "programmes available through the national application system. Dates can "
        "differ by programme and applicant round, so no common window is inferred."
    )

    def __init__(self, minimum_expected_programmes: int = 75) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalog = self.parse_catalog(fetcher(CATALOG_URL))
        guidance = normalise(
            BeautifulSoup(fetcher(APPLICATION_URL), "html.parser").get_text(
                " ", strip=True
            )
        ).casefold()
        if (
            "up to four programs" not in guidance
            or "general entry requirements" not in guidance
        ):
            raise ValueError(
                "Gothenburg's official master's application guide is missing"
            )
        return catalog

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        seen_urls: set[str] = set()
        for link in soup.select('#main a[href*="/en/study-gothenburg/"]'):
            source_url = urljoin(CATALOG_URL, str(link["href"]))
            if source_url in seen_urls:
                continue
            name = normalise(link.get_text(" ", strip=True))
            name = name.removesuffix(" (External link)")
            if not name:
                continue
            seen_urls.add(source_url)
            rows.append(
                CatalogEntry(
                    name=name,
                    degree_type="Master",
                    source_url=source_url,
                )
            )
        return rows
