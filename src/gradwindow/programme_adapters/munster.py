from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .base import DiscoveredCatalog, Fetcher
from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = "https://www.uni-muenster.de/ZSB/studienfuehrer/suchergebnis"
APPLICATION_URL = (
    "https://www.uni-muenster.de/studieninteressierte/en/bewerbung/master.html"
)


class MunsterAdapter(OfficialCatalogAdapter):
    university_id = "university-of-munster"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "munster"
    institution_name = "University of Münster"
    minimum_expected_programmes = 145
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-study-guide-table"
    catalogue_limitation_reason = (
        "Münster's official study guide distinguishes each master's degree and "
        "teacher-training variant. Application routes and deadlines vary by "
        "programme, so no university-wide exact date pair is inferred."
    )

    def __init__(self, minimum_expected_programmes: int = 145) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def parse_catalog_from_fetcher(self, fetcher: Fetcher) -> DiscoveredCatalog:
        catalog = self.parse_catalog(fetcher(CATALOG_URL))
        guidance = normalise(
            BeautifulSoup(fetcher(APPLICATION_URL), "html.parser").get_text(
                " ", strip=True
            )
        ).casefold()
        if "online application portal" not in guidance or "up to three" not in guidance:
            raise ValueError("Münster's official master's application guide is missing")
        return catalog

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        rows = []
        for table_row in soup.select("table tr"):
            cells = table_row.find_all("td", recursive=False)
            if len(cells) < 3:
                continue
            subject = normalise(cells[0].get_text(" ", strip=True))
            if not subject:
                continue
            for link in cells[2].select("a[href]"):
                abbreviation = normalise(link.get_text(" ", strip=True))
                degree = normalise(str(link.get("title") or abbreviation))
                if not abbreviation or not degree.casefold().startswith("master"):
                    continue
                rows.append(
                    CatalogEntry(
                        name=f"{subject} ({abbreviation})",
                        degree_type=degree,
                        source_url=urljoin(CATALOG_URL, str(link["href"])),
                    )
                )
        return rows
