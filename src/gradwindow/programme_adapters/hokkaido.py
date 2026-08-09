from __future__ import annotations

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry

CATALOG_URL = (
    "https://www.global.hokudai.ac.jp/admissions/graduate-admissions-overview/"
)
APPLICATION_URL = CATALOG_URL


class HokkaidoAdapter(OfficialCatalogAdapter):
    university_id = "hokkaido-university"
    school_prefix = "hokkaido"
    institution_name = "Hokkaido University"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL,)
    minimum_expected_programmes = 7
    retrieval_method = "official-english-graduate-programme-directory"

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        heading = soup.select_one("#study-in-english")
        if heading is None:
            return []
        programme_list = heading.find_next("ul")
        if programme_list is None:
            return []
        entries: list[CatalogEntry] = []
        for anchor in programme_list.select("a[href]"):
            name = anchor.get_text(" ", strip=True)
            if "Doctoral Program" in name:
                continue
            entries.append(
                entry(
                    name=name,
                    degree_type="Master",
                    source_url=str(anchor["href"]),
                    base_url=CATALOG_URL,
                )
            )
        return entries
