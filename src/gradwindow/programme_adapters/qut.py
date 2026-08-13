from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = "https://online.qut.edu.au/"
APPLICATION_URL = "https://online.qut.edu.au/how-to-apply/"


class QUTAdapter(OfficialCatalogAdapter):
    university_id = "queensland-university-of-technology"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "qut-online"
    institution_name = "QUT Online"
    minimum_expected_programmes = 10
    window_watch_urls = (CATALOG_URL,)
    catalogue_status = "partial"
    retrieval_method = "official-qut-online-course-directory"
    catalogue_limitation_reason = (
        "This official directory covers QUT Online master's degrees, not every "
        "on-campus postgraduate course at QUT. QUT Online uses multiple teaching "
        "periods and does not publish one exact opening and closing pair for the "
        "whole subset."
    )

    def __init__(self, minimum_expected_programmes: int = 10) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries = []
        for link in soup.select("a[href*='/online-courses/']"):
            name = normalise(link.get_text(" ", strip=True))
            if not name.casefold().startswith("master of "):
                continue
            entries.append(
                CatalogEntry(
                    name=name,
                    degree_type="Master",
                    source_url=urljoin(CATALOG_URL, str(link.get("href", ""))),
                )
            )
        return entries
