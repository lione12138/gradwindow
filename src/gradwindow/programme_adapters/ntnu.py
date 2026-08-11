from __future__ import annotations

from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = "https://www.ntnu.edu/studies/international/master"
APPLICATION_URL = "https://www.ntnu.edu/studies/admissions/master"


class NTNUAdapter(OfficialCatalogAdapter):
    university_id = "norwegian-university-of-science-and-technology"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "ntnu"
    institution_name = "Norwegian University of Science and Technology"
    minimum_expected_programmes = 38
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-international-masters-table"
    catalogue_limitation_reason = (
        "NTNU's official international master's page enumerates the programmes "
        "offered in English. Its displayed deadlines are applicant-category and "
        "cycle dependent, and the page does not currently publish a future exact "
        "opening-and-closing pair for every listed programme."
    )

    def __init__(self, minimum_expected_programmes: int = 38) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        rows: list[CatalogEntry] = []
        for table_row in soup.select("table tr"):
            link = table_row.select_one("a[href]")
            if link is None:
                continue
            name = normalise(link.get_text(" ", strip=True))
            if not name:
                continue
            source_url = urljoin(CATALOG_URL, str(link["href"]))
            hostname = (urlparse(source_url).hostname or "").casefold()
            if hostname != "ntnu.edu" and not hostname.endswith(".ntnu.edu"):
                source_url = CATALOG_URL
            rows.append(
                CatalogEntry(
                    name=name,
                    degree_type="Master",
                    source_url=source_url,
                )
            )
        return rows
