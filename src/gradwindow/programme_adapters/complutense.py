from __future__ import annotations

from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry

CATALOG_URL = "https://www.ucm.es/estudios/master"
APPLICATION_URL = "https://www.ucm.es/proceso-de-admision-masteres"


class ComplutenseAdapter(OfficialCatalogAdapter):
    university_id = "university-complutense-madrid"
    school_prefix = "complutense"
    institution_name = "Universidad Complutense de Madrid"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    minimum_expected_programmes = 100
    retrieval_method = "official-2026-2027-master-directory"

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries: list[CatalogEntry] = []
        for anchor in soup.select("ul.menu_pag a[href]"):
            source_url = urljoin(CATALOG_URL, str(anchor["href"]))
            if not urlsplit(source_url).path.startswith("/estudios/master-"):
                continue
            entries.append(
                entry(
                    name=anchor.get_text(" ", strip=True),
                    degree_type="Máster",
                    source_url=source_url,
                    base_url=CATALOG_URL,
                )
            )
        return entries
