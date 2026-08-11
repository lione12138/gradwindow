from __future__ import annotations

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = (
    "https://graduateschool.cuanschutz.edu/programs-of-study/"
    "graduate-and-certificate-programs"
)
APPLICATION_URL = "https://graduateschool.cuanschutz.edu/admissions"


class CUAnschutzAdapter(OfficialCatalogAdapter):
    university_id = "university-of-colorado-anschutz-medical-campus"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "cu-anschutz"
    institution_name = "University of Colorado Anschutz Medical Campus"
    minimum_expected_programmes = 10
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-graduate-degree-table"
    catalogue_limitation_reason = (
        "CU Anschutz's official Graduate School table identifies current master's "
        "programmes and their degree types. Exact deadlines are set by individual "
        "programmes, so the central catalogue is not treated as an exact window."
    )

    def __init__(self, minimum_expected_programmes: int = 10) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.select("table")
        if len(tables) < 3:
            return []
        rows: list[CatalogEntry] = []
        for table_row in tables[2].select("tr"):
            cells = table_row.select("td")
            link = cells[0].select_one("a[href]") if cells else None
            if link is None:
                continue
            degree = next(
                (
                    normalise(cell.get_text(" ", strip=True))
                    for cell in cells
                    if normalise(cell.get_text(" ", strip=True)) in {"MS", "MSCS"}
                ),
                None,
            )
            if degree is None:
                continue
            rows.append(
                CatalogEntry(
                    name=normalise(link.get_text(" ", strip=True)),
                    degree_type=degree,
                    source_url=str(link["href"]),
                )
            )
        return rows
