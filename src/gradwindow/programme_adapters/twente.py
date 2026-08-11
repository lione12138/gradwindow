from __future__ import annotations

from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = "https://www.utwente.nl/en/education/master/programmes/"
APPLICATION_URL = "https://www.utwente.nl/en/education/master/how-to-apply/"


class TwenteAdapter(OfficialCatalogAdapter):
    university_id = "university-of-twente"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "twente"
    institution_name = "University of Twente"
    minimum_expected_programmes = 30
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-masters-study-finder"
    catalogue_limitation_reason = (
        "Twente's official study finder provides a complete master's catalogue. "
        "Application deadlines vary by programme, nationality, prior education, "
        "and intake, so exact window discovery remains programme-specific."
    )

    def __init__(self, minimum_expected_programmes: int = 30) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalog = self.parse_catalog(fetcher(CATALOG_URL))
        guidance = normalise(
            BeautifulSoup(fetcher(APPLICATION_URL), "html.parser").get_text(
                " ", strip=True
            )
        ).casefold()
        if "studielink" not in guidance or "application deadline" not in guidance:
            raise ValueError(
                "Twente's official master's application guidance is missing"
            )
        return catalog

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        for link in soup.select("a.studyfinder__programme__link[href]"):
            href = str(link["href"])
            if "/specialisation/" in href or "/specialisations/" in href:
                continue
            title = link.select_one(".studyfinder__programme__title__text")
            degree = link.select_one(".studyfinder__programme__metadata .degree")
            if title is None or degree is None:
                continue
            degree_type = normalise(degree.get_text(" ", strip=True))
            if degree_type.casefold() != "msc":
                continue
            source_url = urljoin(CATALOG_URL, href)
            hostname = (urlparse(source_url).hostname or "").casefold()
            if hostname != "utwente.nl" and not hostname.endswith(".utwente.nl"):
                source_url = CATALOG_URL
            rows.append(
                CatalogEntry(
                    name=normalise(title.get_text(" ", strip=True)),
                    degree_type=degree_type,
                    source_url=source_url,
                )
            )
        return rows
