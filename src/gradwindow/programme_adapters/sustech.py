from __future__ import annotations

from bs4 import BeautifulSoup

from .official_catalog import CatalogEntry, OfficialCatalogAdapter, normalise

CATALOG_URL = "https://med.sustech.edu.cn/en/NewsDetailNE?AID=7174&classIDNow=3451"
APPLICATION_URL = CATALOG_URL


class SUSTechAdapter(OfficialCatalogAdapter):
    university_id = "southern-university-of-science-and-technology"
    catalog_url = CATALOG_URL
    application_url = APPLICATION_URL
    school_prefix = "sustech"
    institution_name = "Southern University of Science and Technology"
    minimum_expected_programmes = 11
    window_watch_urls = (CATALOG_URL,)
    retrieval_method = "official-international-postgraduate-table"
    catalogue_limitation_reason = (
        "SUSTech's official 2026 international postgraduate guide marks the "
        "majors accepting master's applicants. The published guide is retained "
        "as a catalogue source and does not expose a complete exact future "
        "opening-and-closing date pair."
    )

    def __init__(self, minimum_expected_programmes: int = 11) -> None:
        self.minimum_expected_programmes = minimum_expected_programmes

    def extract_entries(self, html: str) -> list[CatalogEntry]:
        soup = BeautifulSoup(html, "html.parser")
        tables = soup.select("table")
        if not tables:
            return []
        rows: list[CatalogEntry] = []
        for table_row in tables[0].select("tr"):
            cells = [
                normalise(cell.get_text(" ", strip=True))
                for cell in table_row.select("th,td")
            ]
            if (
                len(cells) < 4
                or cells[0].casefold() == "code"
                or not cells[0].strip().isalnum()
            ):
                continue
            if not cells[3]:
                continue
            rows.append(
                CatalogEntry(
                    name=cells[1],
                    degree_type="Master",
                    source_url=CATALOG_URL,
                )
            )
        return rows
