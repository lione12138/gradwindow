from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = "https://www.nd.edu/academics/programs/"
APPLICATION_URL = "https://www.nd.edu/admissions/graduate-admissions/"
MASTER_TITLE_RE = re.compile(
    r"(?:\bMaster(?:'s)?\b|\bM(?:\.[A-Z]+){1,4}\.?|\bMBA\b|\bLLM\b)",
    re.IGNORECASE,
)


class NotreDameAdapter(OfficialCatalogAdapter):
    university_id = "university-of-notre-dame"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "notre-dame"
    institution_name = "University of Notre Dame"
    minimum_expected_programmes = 35
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-university-wide-academic-programmes-directory"
    catalogue_limitation_reason = (
        "Notre Dame's university-wide academic directory covers graduate master's "
        "programmes across its colleges and professional schools. Application "
        "requirements and dates vary by programme, so no central window is inferred."
    )

    def __init__(self, minimum_expected_programmes: int = 35) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalog = self.parse_catalog(fetcher(CATALOG_URL))
        guidance = normalise(
            BeautifulSoup(fetcher(APPLICATION_URL), "html.parser").get_text(
                " ", strip=True
            )
        ).casefold()
        if (
            "requirements for admission" not in guidance
            or "vary by program" not in guidance
        ):
            raise ValueError("Notre Dame's graduate admission guidance is missing")
        return catalog

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        for card in soup.select(".card"):
            meta = card.select_one(".card-meta")
            link = card.select_one("h2.card-title a[href]")
            if meta is None or link is None:
                continue
            if (
                not normalise(meta.get_text(" ", strip=True))
                .casefold()
                .startswith("graduate")
            ):
                continue
            label = normalise(link.get_text(" ", strip=True))
            if MASTER_TITLE_RE.search(label) is None:
                continue
            rows.append(
                CatalogEntry(
                    name=label,
                    degree_type="Master",
                    source_url=urljoin(CATALOG_URL, str(link["href"])),
                )
            )
        return rows
