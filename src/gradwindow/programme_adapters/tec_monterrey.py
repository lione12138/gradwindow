from __future__ import annotations

from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = "https://maestriasydiplomados.tec.mx/programas/posgrados"
APPLICATION_URL = "https://maestriasydiplomados.tec.mx/admisiones"


class TecMonterreyAdapter(OfficialCatalogAdapter):
    university_id = "tecnol-gico-de-monterrey-itesm"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "tec"
    institution_name = "Tecnológico de Monterrey"
    retrieval_method = "official-postgraduate-programme-index"
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)

    def __init__(self, minimum_expected_programmes: int = 30) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        entries = []
        for link in soup.select("a.link-program[href]"):
            name = normalise(link.get_text(" ", strip=True))
            source_url = urljoin(CATALOG_URL, str(link.get("href", "")))
            if not name.casefold().startswith("maestría "):
                continue
            if not _is_official_programme(source_url):
                continue
            entries.append(
                CatalogEntry(
                    name=name,
                    degree_type="Master",
                    source_url=source_url,
                )
            )
        return entries


def _is_official_programme(url: str) -> bool:
    parsed = urlparse(url)
    return (
        parsed.scheme == "https"
        and parsed.hostname is not None
        and parsed.hostname.endswith(".tec.mx")
        and parsed.path.startswith("/posgrados/")
    )
