from __future__ import annotations

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry, normalise

CATALOG_URL = "https://prpg.usp.br/mestrado-e-doutorado/"
APPLICATION_URL = "https://uspdigital.usp.br/janus/comum/entrada.jsf"


class USPAdapter(OfficialCatalogAdapter):
    university_id = "universidade-de-s-o-paulo-usp"
    school_prefix = "usp"
    institution_name = "Universidade de São Paulo"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    minimum_expected_programmes = 200
    retrieval_method = "official-masters-and-doctoral-programme-table"

    def __init__(self, minimum_expected_programmes: int = 200) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries: list[CatalogEntry] = []
        for row in soup.select("table tr"):
            cells = row.select("td")
            if len(cells) < 2:
                continue
            name = normalise(cells[0].get_text(" ", strip=True))
            email = normalise(cells[1].get_text(" ", strip=True))
            if not name or "@" not in email:
                continue
            entries.append(
                entry(
                    name=name,
                    degree_type="Graduate programme",
                    source_url=CATALOG_URL,
                    base_url=CATALOG_URL,
                )
            )
        return entries
