from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, entry

CATALOG_URL = "https://uchile.cl/postgrados/buscar/magister"
APPLICATION_URL = "https://postulacionpostgrado.uchile.cl/"
MASTER_PATH_RE = re.compile(r"^/postgrados/\d+/[^/?#]+/?$")


class UChileAdapter(OfficialCatalogAdapter):
    university_id = "universidad-de-chile"
    school_prefix = "uchile"
    institution_name = "Universidad de Chile"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    minimum_expected_programmes = 110
    retrieval_method = "official-magister-directory"

    def _catalog(self, entries: list[CatalogEntry]):
        catalog = super()._catalog(entries)
        for programme in catalog.programmes:
            if programme.name == "Magíster en Ciencias, mención Computación":
                programme.id = "uchile-magister-ciencias-computacion"
        return catalog

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries: list[CatalogEntry] = []
        for anchor in soup.select("a.mod__link[href]"):
            source_path = str(anchor["href"])
            name = anchor.get_text(" ", strip=True)
            if not MASTER_PATH_RE.match(source_path):
                continue
            if not name.casefold().startswith(("magíster", "master")):
                continue
            entries.append(
                entry(
                    name=name,
                    degree_type="Magíster",
                    source_url=urljoin(CATALOG_URL, source_path),
                    base_url=CATALOG_URL,
                )
            )
        return entries
