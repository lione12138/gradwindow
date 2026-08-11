from __future__ import annotations

import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = (
    "https://studieninteressierte.uni-koeln.de/range_of_courses/index_eng.html"
)
APPLICATION_URL = (
    "https://www.uni-koeln.de/en/international/study-in-cologne/"
    "international-applications/master-students-prospective"
)
MASTER_LABEL_RE = re.compile(r"^(?P<name>.+),\s+(?P<degree>Master.+)$", re.IGNORECASE)


class CologneAdapter(OfficialCatalogAdapter):
    university_id = "university-of-cologne"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "cologne"
    institution_name = "University of Cologne"
    minimum_expected_programmes = 200
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-degree-programme-directory"
    catalogue_limitation_reason = (
        "Cologne's official degree directory enumerates its master's variants. "
        "Admission procedures and dates depend on the programme and applicant "
        "background, so no common exact application window is inferred."
    )

    def __init__(self, minimum_expected_programmes: int = 200) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalog = self.parse_catalog(fetcher(CATALOG_URL))
        guidance = normalise(
            BeautifulSoup(fetcher(APPLICATION_URL), "html.parser").get_text(
                " ", strip=True
            )
        ).casefold()
        if "two-stage application process" not in guidance or "klips" not in guidance:
            raise ValueError("Cologne's official master's application guide is missing")
        return catalog

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        for card in soup.select("article.c-card"):
            link = card.select_one("a.c-card__link[href]")
            if link is None:
                continue
            label = normalise(link.get_text(" ", strip=True))
            match = MASTER_LABEL_RE.match(label)
            if match is None:
                continue
            rows.append(
                CatalogEntry(
                    name=match.group("name"),
                    degree_type=match.group("degree"),
                    source_url=urljoin(CATALOG_URL, str(link["href"])),
                )
            )
        return rows
