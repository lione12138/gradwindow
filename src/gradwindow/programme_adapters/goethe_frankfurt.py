from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = "https://www.uni-frankfurt.de/en/studium/studiengaenge?pageSize=all"
APPLICATION_URL = (
    "https://www.uni-frankfurt.de/en/studium/bewerbung-einschreibung/"
    "master-studiengaenge/termine-fristen"
)


class GoetheFrankfurtAdapter(OfficialCatalogAdapter):
    university_id = "goethe-university-frankfurt"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "goethe-frankfurt"
    institution_name = "Goethe University Frankfurt"
    minimum_expected_programmes = 90
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-all-programmes-directory"
    catalogue_limitation_reason = (
        "Goethe University publishes application deadlines on each respective "
        "degree programme page, so the catalogue is complete but no common "
        "exact master's window is inferred."
    )

    def __init__(self, minimum_expected_programmes: int = 90) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalog = self.parse_catalog(fetcher(CATALOG_URL))
        policy = normalise(
            BeautifulSoup(fetcher(APPLICATION_URL), "html.parser").get_text(
                " ", strip=True
            )
        ).casefold()
        if (
            "deadlines for your degree program on the respective degree program pages"
            not in policy
        ):
            raise ValueError("Goethe's programme-specific deadline policy is missing")
        return catalog

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        for card in soup.select("article"):
            degree = card.select_one("[aria-description='Course Degree']")
            title = card.find("h4")
            link = card.select_one("a[href]")
            if degree is None or title is None or link is None:
                continue
            degree_type = normalise(degree.get_text(" ", strip=True))
            if "master" not in degree_type.casefold():
                continue
            rows.append(
                CatalogEntry(
                    name=normalise(title.get_text(" ", strip=True)),
                    degree_type=degree_type,
                    source_url=urljoin(CATALOG_URL, str(link["href"])),
                )
            )
        return rows
