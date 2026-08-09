from __future__ import annotations

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, degree_from, entry

CATALOG_URL = "https://graduatestudies.ksu.edu.sa/en/node/1148"
APPLICATION_URL = "https://graduatestudies.ksu.edu.sa/en"


class KSUAdapter(OfficialCatalogAdapter):
    university_id = "king-saud-university"
    school_prefix = "ksu"
    institution_name = "King Saud University"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-available-masters-programmes-table"

    def __init__(self, minimum_expected_programmes: int = 30) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries: list[CatalogEntry] = []
        for cell in soup.select("table td"):
            name = " ".join(cell.get_text(" ", strip=True).split()).rstrip(".")
            if not name.casefold().startswith(("master", "executive master")):
                continue
            entries.append(
                entry(
                    name=name,
                    degree_type=degree_from(name),
                    source_url=CATALOG_URL,
                    base_url=CATALOG_URL,
                )
            )
        return entries
