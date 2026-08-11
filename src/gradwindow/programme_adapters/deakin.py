from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = "https://handbook.deakin.edu.au/courses-search/allcourses.php"
APPLICATION_URL = "https://www.deakin.edu.au/study/how-to-apply"


class DeakinAdapter(OfficialCatalogAdapter):
    university_id = "deakin-university"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "deakin"
    institution_name = "Deakin University"
    minimum_expected_programmes = 85
    window_watch_urls = (CATALOG_URL, APPLICATION_URL)
    retrieval_method = "official-current-course-handbook"
    catalogue_limitation_reason = (
        "Deakin's official course handbook identifies current coursework and "
        "research master's course versions. Intakes and application timing vary "
        "by course and applicant category, so no common exact window is inferred."
    )

    def __init__(self, minimum_expected_programmes: int = 85) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.select("table")
        if len(tables) < 4:
            return []
        rows: list[CatalogEntry] = []
        seen: set[str] = set()
        for table in (tables[2], tables[3]):
            for table_row in table.select("tr"):
                link = table_row.select_one("a[href]")
                if link is None:
                    continue
                name = normalise(link.get_text(" ", strip=True))
                row_text = normalise(table_row.get_text(" ", strip=True))
                if not name.startswith(("Master ", "Executive Master ")):
                    continue
                if "onwards" not in row_text.casefold() or name in seen:
                    continue
                seen.add(name)
                rows.append(
                    CatalogEntry(
                        name=name,
                        degree_type="Master",
                        source_url=urljoin(CATALOG_URL, str(link["href"])),
                    )
                )
        return rows
