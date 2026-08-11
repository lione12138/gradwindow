from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = "https://www.kaust.edu.sa/en/study/division-programs"
APPLICATION_URL = "https://admissions.kaust.edu.sa/"


class KAUSTAdapter(OfficialCatalogAdapter):
    university_id = "king-abdullah-university-of-science-and-technology"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "kaust"
    institution_name = "King Abdullah University of Science and Technology"
    minimum_expected_programmes = 14
    window_watch_urls = (
        CATALOG_URL,
        "https://www.kaust.edu.sa/en/study/masters-program",
    )
    retrieval_method = "official-programmes-by-division"
    catalogue_limitation_reason = (
        "KAUST's official division page enumerates its current graduate "
        "programmes, all of which offer the M.S. degree. The admissions page "
        "currently describes the next opening only as mid-August, which is not "
        "an exact date."
    )

    def __init__(self, minimum_expected_programmes: int = 14) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        rows: list[CatalogEntry] = []
        for article in soup.select("article.kaust-category"):
            heading = article.select_one("h3")
            link = article.select_one("a.category.button[href]")
            if heading is None or link is None:
                continue
            rows.append(
                CatalogEntry(
                    name=normalise(heading.get_text(" ", strip=True)),
                    degree_type="MS",
                    source_url=urljoin(CATALOG_URL, str(link["href"])),
                )
            )
        return rows
