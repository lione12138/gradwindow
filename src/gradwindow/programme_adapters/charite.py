from __future__ import annotations

from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = "https://www.charite.de/en/teaching_learning/degree_programs/"
APPLICATION_URL = "https://www.charite.de/en/teaching_learning/application_admission/"


class ChariteAdapter(OfficialCatalogAdapter):
    university_id = "charite-universitatsmedizin-berlin"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "charite"
    institution_name = "Charité – Universitätsmedizin Berlin"
    minimum_expected_programmes = 7
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-degree-programmes-directory"
    catalogue_limitation_reason = (
        "Charité's official directory lists active master's programmes across its "
        "partner schools and institutes. Application procedures vary by course, so "
        "no institution-wide exact date pair is inferred."
    )

    def __init__(self, minimum_expected_programmes: int = 7) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalog = self.parse_catalog(fetcher(CATALOG_URL))
        guidance = normalise(
            BeautifulSoup(fetcher(APPLICATION_URL), "html.parser").get_text(
                " ", strip=True
            )
        ).casefold()
        if "application" not in guidance or "degree program" not in guidance:
            raise ValueError("Charité's official application guidance is missing")
        return catalog

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        main = soup.select_one("main")
        if main is None:
            return []
        rows = []
        for link in main.select("a[title][href]"):
            if "section-teaser" in (link.get("class") or []):
                continue
            description = normalise(link.get_text(" ", strip=True)).casefold()
            if "master" not in description and "msc program" not in description:
                continue
            name = normalise(str(link.get("title") or "")).rstrip("*")
            source_url = urljoin(CATALOG_URL, str(link["href"]))
            hostname = (urlparse(source_url).hostname or "").casefold()
            if hostname != "charite.de" and not hostname.endswith(".charite.de"):
                source_url = CATALOG_URL
            elif source_url.startswith("http://"):
                source_url = "https://" + source_url.removeprefix("http://")
            rows.append(
                CatalogEntry(
                    name=name,
                    degree_type="MSc",
                    source_url=source_url,
                )
            )
        return rows
